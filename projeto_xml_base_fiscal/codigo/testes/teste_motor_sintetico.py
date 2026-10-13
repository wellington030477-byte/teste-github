# -*- coding: utf-8 -*-
"""
Teste do motor de custo fiscal com XMLs SINTETICOS (dados ficticios).
Verifica: nenhum credito sem regra VALIDADA; credito aplicado so quando VALIDADA+APLICAR=S;
saida propria fora do escopo; transferencia sinalizada; ajuste externo; conferencia com vItem;
composicao com camadas.

Uso: python testes/teste_motor_sintetico.py
"""
import csv
import glob
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
import extrator_base_fiscal_xml as ext  # noqa: E402
import motor_custo_fiscal as motor  # noqa: E402
import teste_extrator_sintetico as t  # noqa: E402

LOJA = "01234567000189"
LOJA2 = "01234567000270"


def ler(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def item_vitem(n, ean, icms, pis, cof, vprod, vdesc, vst, vitem, cfop="5102"):
    x = t.item(n, ean, "30049099", cfop, icms, pis, cof, vprod=vprod)
    x = x.replace("<indTot>1</indTot>", "<vDesc>%s</vDesc><indTot>1</indTot>" % vdesc)
    return x.replace("</imposto></det>", "</imposto><vItem>%s</vItem></det>" % vitem)


def main():
    tmp = tempfile.mkdtemp(prefix="teste_motor_")
    org = os.path.join(tmp, "BASE_XML", LOJA, "NFe", "Compras")
    os.makedirs(org)
    icms10 = ("<ICMS10><orig>0</orig><CST>10</CST><modBC>3</modBC><vBC>90.00</vBC><pICMS>17.00</pICMS><vICMS>15.30</vICMS>"
              "<modBCST>4</modBCST><pMVAST>30.00</pMVAST><vBCST>117.00</vBCST><pICMSST>17.00</pICMSST><vICMSST>4.59</vICMSST></ICMS10>")
    icms00 = "<ICMS00><orig>0</orig><CST>00</CST><modBC>3</modBC><vBC>90.00</vBC><pICMS>17.00</pICMS><vICMS>15.30</vICMS></ICMS00>"
    pis01 = "<PISAliq><CST>01</CST><vBC>90.00</vBC><pPIS>1.65</pPIS><vPIS>1.49</vPIS></PISAliq>"
    cof01 = "<COFINSAliq><CST>01</CST><vBC>90.00</vBC><pCOFINS>7.60</pCOFINS><vCOFINS>6.84</vCOFINS></COFINSAliq>"
    # A: compra com ICMS00 + PIS/COFINS 01 ; vItem = 100 - 10 = 90
    chA, xA = t.nfe(t.F1, 11, [item_vitem(1, t.EAN_A, icms00, pis01, cof01, "100.00", "10.00", "0", "90.00")], dest=LOJA)
    # B: compra com ST: vItem = 100 - 10 + 4.59 = 94.59
    chB, xB = t.nfe(t.F2, 12, [item_vitem(1, t.EAN_B, icms10, t.PIS04, t.COF04, "100.00", "10.00", "4.59", "94.59", cfop="5403")], dest=LOJA)
    # C: vItem divergente de proposito (atipico)
    chC, xC = t.nfe(t.F3, 13, [item_vitem(1, t.EAN_A, icms00, pis01, cof01, "100.00", "0.00", "0", "99.00")], dest=LOJA)
    # D: transferencia entre lojas
    chD, xD = t.nfe(LOJA2, 14, [t.item(1, t.EAN_A, "30049099", "5152", t.ICMS60, t.PIS99, t.COF99)], dest=LOJA)
    # E: saida propria (venda a CPF)
    chE, xE = t.nfe(LOJA, 15, [t.item(1, t.EAN_A, "30049099", "5102", icms00, pis01, cof01)], dest="00000000000")
    xE = xE.replace("<CNPJ>00000000000</CNPJ>", "<CPF>12345678909</CPF>")
    for nome, x in (("A.xml", xA), ("B.xml", xB), ("C.xml", xC), ("D.xml", xD), ("E.xml", xE)):
        open(os.path.join(org, nome), "w", encoding="utf-8").write(x)
    rede = os.path.join(tmp, "REDE.csv")
    open(rede, "w").write("CNPJ\n%s\n%s\n" % (LOJA, LOJA2))

    saida = os.path.join(tmp, "saida")
    assert ext.main(["--origem", os.path.join(tmp, "BASE_XML"), "--saida", saida, "--cnpjs-rede", rede, "--sem-xlsx"]) == 0
    exec_dir = glob.glob(os.path.join(saida, "EXEC_*"))[0]
    base = {r["CHAVE_NFE"]: r for r in ler(os.path.join(exec_dir, "02_BASE_ITENS_XML.csv"))}

    falhas = []

    def ok(c, m):
        print(("OK   " if c else "FALHA") + " - " + m)
        if not c:
            falhas.append(m)

    ok(base[chA]["CLASS_DOC_OPERACAO_CODIGO"] == "COMPRA_DE_TERCEIRO", "A = COMPRA_DE_TERCEIRO")
    ok(base[chD]["CLASS_DOC_OPERACAO_CODIGO"] == "TRANSFERENCIA_ENTRE_LOJAS", "D = TRANSFERENCIA_ENTRE_LOJAS (raiz igual, ambos na rede)")
    ok(base[chE]["CLASS_DOC_OPERACAO_CODIGO"] == "SAIDA_PROPRIA_DA_REDE", "E (venda a CPF) = SAIDA_PROPRIA_DA_REDE")
    ok("VITEM_DIFERE_DA_RECONSTRUCAO" in (base[chC]["ALERTAS_DOCUMENTAIS"] or ""), "C: vItem divergente alertado no extrator")

    # 1) Regras padrao (todas PENDENTE) -> nenhum credito
    assert motor.main(["--exec", exec_dir]) == 0
    m1 = sorted(glob.glob(os.path.join(exec_dir, "MOTOR_*")))[-1]
    c1 = {r["CHAVE_NFE"]: r for r in ler(os.path.join(m1, "08_CUSTO_FISCAL_ITENS.csv"))}
    ok(chE not in c1, "saida propria fora do escopo de custo")
    ok(any(r["ID_REGISTRO"].startswith(chE) for r in ler(os.path.join(m1, "12_ITENS_FORA_DO_ESCOPO.csv"))), "saida propria listada em 12_ITENS_FORA_DO_ESCOPO")
    ok(c1[chA]["C_VALOR_DOCUMENTADO_ITEM"] == "90" and c1[chA]["C_CONFERE_VITEM"] == "SIM", "A: documentado 90 confere com vItem")
    ok(c1[chB]["C_VALOR_DOCUMENTADO_ITEM"] == "94,59" and c1[chB]["C_CONFERE_VITEM"] == "SIM", "B: documentado 94,59 (com ST) confere com vItem")
    ok(c1[chC]["C_CONFERE_VITEM"].startswith("NAO"), "C: divergencia com vItem evidenciada")
    ok(all(r["V_CREDITOS_VALIDADOS_TOTAL"] == "0" for r in c1.values()), "regras PENDENTES: nenhum credito validado")
    ok(c1[chA]["C_CUSTO_FISCAL_EFETIVO_VALIDADO"] == "90", "A: custo validado = documentado sem credito")
    ok(c1[chA]["H_ICMS_CREDITO_HIPOTESE"] == "15,3", "A: credito ICMS calculado apenas como HIPOTESE")
    ok(c1[chB]["R_ICMS_ST_TRATAMENTO"] == "CUSTO_SEM_CREDITO" and c1[chB]["L_ICMS_ST"] == "4,59", "B: ICMS-ST literal permanece no custo")
    ok("TRANSFERENCIA" in c1[chD]["SITUACOES_PARA_DECISAO"], "D: transferencia sinalizada")
    comp = ler(os.path.join(m1, "09_COMPOSICAO_CUSTO_LONGA.csv"))
    camadas = {c["CAMADA"] for c in comp}
    ok({"1 DADO LITERAL DO XML", "3 CALCULO", "5 HIPOTESE", "6 PENDENTE DE VALIDACAO FISCAL"} <= camadas, "composicao com camadas literal/calculo/hipotese/pendente")

    # 2) Valida ICMS-01 e PIS-01/COFINS-01 numa copia das regras + ajuste externo
    regras_v = os.path.join(tmp, "REGRAS_VALIDADAS.csv")
    linhas = open(motor.os.path.join(os.path.dirname(AQUI), "config", "REGRAS_CREDITO_LUCRO_REAL.csv"), encoding="utf-8-sig").read().splitlines()
    novas = []
    for l in linhas:
        if l.startswith(("ICMS-01;", "PIS-01;", "COFINS-01;")):
            p = l.split(";")
            p[14], p[15], p[17], p[18] = "VALIDADA", "S", "TESTE", "2026-10-13"
            l = ";".join(p)
        novas.append(l)
    open(regras_v, "w", encoding="utf-8").write("\n".join(novas) + "\n")
    aj = os.path.join(tmp, "AJUSTES.csv")
    open(aj, "w", encoding="utf-8").write("ID_REGISTRO;TIPO;VALOR;FONTE;OBS\n%s-001;ICMS_ANTECIPACAO;2.50;GUIA TESTE;ficticio\n" % chA)
    assert motor.main(["--exec", exec_dir, "--regras", regras_v, "--ajustes", aj]) == 0
    m2 = sorted(glob.glob(os.path.join(exec_dir, "MOTOR_*")))[-1]
    c2 = {r["CHAVE_NFE"]: r for r in ler(os.path.join(m2, "08_CUSTO_FISCAL_ITENS.csv"))}
    # A: 90 - ICMS 15,30 - PIS 1,65%*(90-15,30)=1,23 - COFINS 7,6%*74,70=5,68 + 2,50 = 70,29
    ok(c2[chA]["V_ICMS_CREDITO_VALIDADO"] == "15,3", "A: credito ICMS aplicado so apos VALIDADA+APLICAR=S")
    ok(c2[chA]["V_PIS_CREDITO_VALIDADO"] == "1,23" and c2[chA]["V_COFINS_CREDITO_VALIDADO"] == "5,68", "A: PIS/COFINS sobre base sem ICMS")
    ok(c2[chA]["E_AJUSTES_EXTERNOS"] == "2,5", "A: ajuste externo incorporado")
    ok(c2[chA]["C_CUSTO_FISCAL_EFETIVO_VALIDADO"] == "70,29", "A: custo efetivo validado = 90 - 22,21 + 2,50 = 70,29")
    ok(c2[chB]["V_CREDITOS_VALIDADOS_TOTAL"] == "0", "B: produto com ST e PIS 04 continua sem credito")

    shutil.rmtree(tmp)
    print("\nRESULTADO: %s (%d falhas)" % ("APROVADO" if not falhas else "REPROVADO", len(falhas)))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
