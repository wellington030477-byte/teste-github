# -*- coding: utf-8 -*-
"""
Teste automatizado do extrator com XMLs SINTETICOS (dados ficticios gerados aqui).
Nao usa XMLs reais. Cobre: duplicidade (hash e chave), XML corrompido, nao-NFe,
evento de cancelamento, ZIP, RAR sem biblioteca, Simples Nacional, aliquota zero,
IPI com valor, DIFAL, latin-1 sem declaracao, SEM GTIN, divergencias de EAN,
preservacao de zeros a esquerda e imutabilidade dos arquivos de origem.

Uso: python testes/teste_extrator_sintetico.py
"""
import csv
import glob
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import extrator_base_fiscal_xml as ext  # noqa: E402

NS = "http://www.portalfiscal.inf.br/nfe"


def dv_chave(c43):
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    s = sum(int(d) * pesos[i % 8] for i, d in enumerate(reversed(c43)))
    r = s % 11
    return c43 + str(0 if r in (0, 1) else 11 - r)


def gtin(body12):
    digits = [int(c) for c in body12][::-1]
    t = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits))
    return body12 + str((10 - t % 10) % 10)


EAN_A = gtin("789000000001")
EAN_B = gtin("789000000002")


def chave(cnpj, nnf):
    return dv_chave("51" + "2609" + cnpj + "55" + "001" + "%09d" % nnf + "1" + "%08d" % nnf)


def item(n, ean, ncm, cfop, icms, pis, cofins, ipi="", extra_imp="", vprod="10.00"):
    return ('<det nItem="%d"><prod><cProd>P%03d</cProd><cEAN>%s</cEAN><xProd>PRODUTO TESTE %d</xProd><NCM>%s</NCM>'
            '<CEST>1300100</CEST><CFOP>%s</CFOP><uCom>UN</uCom><qCom>1.0000</qCom><vUnCom>%s</vUnCom><vProd>%s</vProd>'
            '<cEANTrib>%s</cEANTrib><uTrib>UN</uTrib><qTrib>1.0000</qTrib><vUnTrib>%s</vUnTrib><indTot>1</indTot></prod>'
            '<imposto><ICMS>%s</ICMS>%s<PIS>%s</PIS><COFINS>%s</COFINS>%s</imposto></det>'
            % (n, n, ean, n, ncm, cfop, vprod, vprod, ean, vprod, icms, ipi, pis, cofins, extra_imp))


def nfe(emit_cnpj, nnf, itens, natop="VENDA", crt="3", prot=True, dest="01234567000189", id_dest="1"):
    ch = chave(emit_cnpj, nnf)
    corpo = ('<NFe xmlns="%s"><infNFe versao="4.00" Id="NFe%s"><ide><cUF>51</cUF><natOp>%s</natOp><mod>55</mod>'
             '<serie>1</serie><nNF>%d</nNF><dhEmi>2026-09-01T10:00:00-04:00</dhEmi><tpNF>1</tpNF><idDest>%s</idDest>'
             '<finNFe>1</finNFe><indFinal>0</indFinal></ide><emit><CNPJ>%s</CNPJ><xNome>FORNECEDOR %s</xNome>'
             '<enderEmit><UF>MT</UF></enderEmit><IE>1</IE><CRT>%s</CRT></emit><dest><CNPJ>%s</CNPJ>'
             '<xNome>LOJA TESTE</xNome><enderDest><UF>MT</UF></enderDest><indIEDest>1</indIEDest></dest>%s'
             '<total><ICMSTot><vProd>0</vProd><vNF>0</vNF></ICMSTot></total><transp><modFrete>0</modFrete></transp>'
             '</infNFe></NFe>' % (NS, ch, natop, nnf, id_dest, emit_cnpj, emit_cnpj, crt, dest, "".join(itens)))
    if prot:
        corpo = ('<nfeProc xmlns="%s" versao="4.00">%s<protNFe versao="4.00"><infProt><chNFe>%s</chNFe>'
                 '<cStat>100</cStat><xMotivo>Autorizado o uso da NF-e</xMotivo><nProt>1</nProt></infProt></protNFe></nfeProc>'
                 % (NS, corpo, ch))
    return ch, '<?xml version="1.0" encoding="UTF-8"?>' + corpo


ICMS00 = "<ICMS00><orig>0</orig><CST>00</CST><modBC>3</modBC><vBC>10.00</vBC><pICMS>17.00</pICMS><vICMS>1.70</vICMS></ICMS00>"
ICMS60 = "<ICMS60><orig>0</orig><CST>60</CST><vBCSTRet>12.00</vBCSTRet><pST>17.00</pST><vICMSSTRet>0.34</vICMSSTRet></ICMS60>"
ICMS40 = "<ICMS40><orig>1</orig><CST>40</CST></ICMS40>"
SN102 = "<ICMSSN102><orig>0</orig><CSOSN>102</CSOSN></ICMSSN102>"
PIS01 = "<PISAliq><CST>01</CST><vBC>10.00</vBC><pPIS>1.65</pPIS><vPIS>0.17</vPIS></PISAliq>"
COF01 = "<COFINSAliq><CST>01</CST><vBC>10.00</vBC><pCOFINS>7.60</pCOFINS><vCOFINS>0.76</vCOFINS></COFINSAliq>"
PIS04 = "<PISNT><CST>04</CST></PISNT>"
COF04 = "<COFINSNT><CST>04</CST></COFINSNT>"
PIS06 = "<PISNT><CST>06</CST></PISNT>"
COF06 = "<COFINSNT><CST>06</CST></COFINSNT>"
PIS99 = "<PISOutr><CST>99</CST><vBC>0.00</vBC><pPIS>0.00</pPIS><vPIS>0.00</vPIS></PISOutr>"
COF99 = "<COFINSOutr><CST>99</CST><vBC>0.00</vBC><pCOFINS>0.00</pCOFINS><vCOFINS>0.00</vCOFINS></COFINSOutr>"
IPI50 = "<IPI><cEnq>999</cEnq><IPITrib><CST>50</CST><vBC>10.00</vBC><pIPI>5.00</pIPI><vIPI>0.50</vIPI></IPITrib></IPI>"
DIFAL = ("<ICMSUFDest><vBCUFDest>10.00</vBCUFDest><pFCPUFDest>0.00</pFCPUFDest><pICMSUFDest>17.00</pICMSUFDest>"
         "<pICMSInter>12.00</pICMSInter><pICMSInterPart>100.00</pICMSInterPart><vFCPUFDest>0.00</vFCPUFDest>"
         "<vICMSUFDest>0.50</vICMSUFDest><vICMSUFRemet>0.00</vICMSUFRemet></ICMSUFDest>")

F1, F2, F3 = "01111111000191", "02222222000182", "03333333000173"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def ler(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def main():
    tmp = tempfile.mkdtemp(prefix="teste_extrator_")
    org = os.path.join(tmp, "BASE_XML")
    loja = os.path.join(org, "LOTE1", "01234567000189", "NFe", "Compras")
    os.makedirs(loja)
    w = lambda nome, txt, enc="utf-8": open(os.path.join(loja, nome), "wb").write(txt.encode(enc))

    chA, xA = nfe(F1, 1, [item(1, EAN_A, "30049099", "5405", ICMS00, PIS01, COF01)])
    w("A.xml", xA)
    w("A (1).xml", xA)  # duplicado hash
    _, xA_semprot = nfe(F1, 1, [item(1, EAN_A, "30049099", "5405", ICMS00, PIS01, COF01)], prot=False)
    w("A_sem_protocolo.xml", xA_semprot)  # duplicado chave
    chB, xB = nfe(F2, 2, [item(1, EAN_A, "30049099", "5405", ICMS60, PIS04, COF04), item(2, "SEM GTIN", "3004909", "5405", ICMS60, PIS04, COF04)])
    w("B.xml", xB)
    chC, xC = nfe(F1, 3, [item(1, EAN_A, "30049069", "5405", ICMS00, PIS01, COF01)])
    w("C.xml", xC)  # mesmo forn, NCM diferente
    chD, xD = nfe(F3, 4, [item(1, EAN_B, "33049910", "5102", SN102, PIS99, COF99)], crt="1")
    w("D.xml", xD)
    chE, xE = nfe(F3, 5, [item(1, EAN_B, "33049910", "6102", ICMS40, PIS06, COF06, ipi=IPI50, extra_imp=DIFAL)], id_dest="2")
    w("E.xml", xE)
    w("H_corrompido.xml", xA[:400])
    w("I_nao_nfe.xml", '<?xml version="1.0"?><qualquer><coisa>1</coisa></qualquer>')
    ev = ('<procEventoNFe xmlns="%s" versao="1.00"><evento versao="1.00"><infEvento><chNFe>%s</chNFe>'
          '<tpEvento>110111</tpEvento></infEvento></evento></procEventoNFe>' % (ext_ns(), chB))
    w("J_evento_cancel.xml", ev)
    chM, xM = nfe(F3, 6, [item(1, EAN_B, "33049910", "5102", SN102, PIS99, COF99)], natop="VENDA AÇÃO", crt="1")
    xM = xM.replace('<?xml version="1.0" encoding="UTF-8"?>', "")
    w("M_latin1.xml", xM, "latin-1")
    with zipfile.ZipFile(os.path.join(loja, "K.zip"), "w") as z:
        z.writestr("dentro/D_copia.xml", xD)  # duplicado hash dentro do zip
        chZ, xZ = nfe(F2, 7, [item(1, EAN_B, "33049910", "5102", ICMS00, PIS01, COF01)])
        z.writestr("dentro/Z.xml", xZ)
    open(os.path.join(loja, "L.rar"), "wb").write(b"Rar!\x1a\x07\x00 fake")
    open(os.path.join(loja, "N.pdf"), "wb").write(b"%PDF-1.4")
    # pasta de projeto dentro da origem deve ser ignorada
    os.makedirs(os.path.join(org, "PROJETO_XML"))
    open(os.path.join(org, "PROJETO_XML", "nao_ler.xml"), "w").write(xA)

    antes = {p: sha(p) for p in glob.glob(os.path.join(org, "**", "*"), recursive=True) if os.path.isfile(p)}
    saida = os.path.join(org, "PROJETO_XML", "saidas")
    rc = ext.main(["--origem", org, "--saida", saida, "--excluir", "PROJETO_XML"])
    assert rc == 0
    depois = {p: sha(p) for p in antes}
    assert antes == depois, "ARQUIVOS DE ORIGEM ALTERADOS!"
    exec_dir = glob.glob(os.path.join(saida, "EXEC_*"))[0]

    inv = ler(os.path.join(exec_dir, "01_INVENTARIO_XML.csv"))
    st = {r["NOME_ARQUIVO"]: r["STATUS"] for r in inv}
    falhas = []

    def ok(cond, msg):
        print(("OK   " if cond else "FALHA") + " - " + msg)
        if not cond:
            falhas.append(msg)

    ok("nao_ler.xml" not in st, "pasta PROJETO_XML ignorada na varredura")
    ok(st["A.xml"] == "LIDO_OK", "A.xml lido (canonico)")
    ok(st["A (1).xml"] == "DUPLICADO_HASH", "copia identica -> DUPLICADO_HASH")
    ok(st["A_sem_protocolo.xml"] == "DUPLICADO_CHAVE", "mesma chave sem protocolo -> DUPLICADO_CHAVE (canonico com protocolo)")
    ok(st["H_corrompido.xml"] == "ERRO_LEITURA", "XML truncado -> ERRO_LEITURA")
    ok(st["I_nao_nfe.xml"] == "NAO_NFE", "XML nao NF-e -> NAO_NFE")
    ok(st["J_evento_cancel.xml"] == "EVENTO", "evento registrado")
    ok(st["M_latin1.xml"] in ("LIDO_COM_AVISO", "LIDO_OK"), "latin-1 lido com aviso")
    ok(st["D_copia.xml"] == "DUPLICADO_HASH", "copia dentro do ZIP -> DUPLICADO_HASH")
    ok(st["Z.xml"] == "LIDO_OK", "XML novo dentro do ZIP lido")
    ok(st["L.rar"] == "COMPACTADO_NAO_PROCESSADO", "RAR sem biblioteca -> COMPACTADO_NAO_PROCESSADO (registrado)")
    ok(st["N.pdf"] == "IGNORADO_NAO_XML", "PDF -> IGNORADO_NAO_XML")

    base = ler(os.path.join(exec_dir, "02_BASE_ITENS_XML.csv"))
    ok(len(base) == 8, "8 itens extraidos (A1 + B2 + C1 + D1 + E1 + M1 + Z1) -> %d" % len(base))
    ids = [r["ID_REGISTRO"] for r in base]
    ok(len(ids) == len(set(ids)), "ID_REGISTRO unico")
    rb = [r for r in base if r["CHAVE_NFE"] == chB]
    ok(all(r["EVENTO_CANCELAMENTO_ENCONTRADO"] == "S" for r in rb), "nota B marcada com evento de cancelamento")
    ok(all(r["DEST_CNPJ"] == "01234567000189" for r in base), "zero a esquerda do CNPJ preservado")
    ra = [r for r in base if r["CHAVE_NFE"] == chA][0]
    ok(ra["ICMS_vICMSST"] == "", "campo ausente (vICMSST em ICMS00) fica vazio, nao zero")
    ok(ra["PROT_CSTAT"] == "100", "canonico A tem protocolo")
    rsg = [r for r in rb if r["EAN"] == "SEM GTIN"][0]
    ok("EAN_AUSENTE_OU_SEM_GTIN" in rsg["ALERTAS_DOCUMENTAIS"] and "NCM_AUSENTE_OU_FORA_PADRAO" in rsg["ALERTAS_DOCUMENTAIS"], "SEM GTIN e NCM 7 digitos alertados")
    re_ = [r for r in base if r["CHAVE_NFE"] == chE][0]
    ok(re_["FLAG_IPI_VALOR"] == "S" and re_["FLAG_DIFAL"] == "S" and re_["DIFAL_vICMSUFDest"] == "0,5", "IPI com valor e DIFAL extraidos")
    ok("ALIQUOTA ZERO" in re_["INDICIO_PARA_VALIDACAO"], "CST 06 -> indicio aliquota zero (nao fato)")
    rd = [r for r in base if r["CHAVE_NFE"] == chD][0]
    ok(rd["ICMS_CSOSN"] == "102" and rd["ICMS_CST"] == "", "CSOSN Simples extraido")
    ok(all(r["STATUS_VALIDACAO_FISCAL"] == "PENDENTE" for r in base), "STATUS_VALIDACAO_FISCAL sempre PENDENTE")

    div = ler(os.path.join(exec_dir, "04_DIVERGENCIAS_PRODUTOS.csv"))
    campos_a = {r["CAMPO"]: r for r in div if r["EAN_CHAVE_VINCULO"] == EAN_A}
    ok("ICMS_GRUPO_TAG" in campos_a and "PIS_CST" in campos_a, "EAN_A: divergencia ICMS/PIS entre fornecedores")
    ok(campos_a.get("NCM", {}).get("DIVERGE_DENTRO_DO_MESMO_FORNECEDOR") == "S", "EAN_A: NCM diverge dentro do mesmo fornecedor")
    campos_b = {r["CAMPO"] for r in div if r["EAN_CHAVE_VINCULO"] == EAN_B}
    ok("CFOP" in campos_b and "ICMS_CSOSN" in campos_b, "EAN_B: divergencia CFOP/CSOSN")

    chk = ler(os.path.join(exec_dir, "06_LOG_VALIDACAO.csv"))
    erros_chk = [r for r in chk if r["STATUS"] == "ERRO"]
    ok(not erros_chk, "nenhuma checagem com STATUS=ERRO (%s)" % [r["CHECAGEM"] for r in erros_chk])
    mapa = ler(os.path.join(exec_dir, "05_MAPA_CENARIOS_FISCAIS.csv"))
    ok(all(int(m["QTD_AMOSTRAS_SELECIONADAS"]) >= 1 for m in mapa), "todo cenario tem exemplo na amostra")
    logerr = ler(os.path.join(exec_dir, "06B_LOG_ERROS.csv"))
    ok(any("H_corrompido" in r["ARQUIVO"] for r in logerr), "erro do XML corrompido registrado no log")
    ok(os.path.exists(os.path.join(exec_dir, "BASE_FISCAL_XML.xlsx")), "xlsx gerado")

    shutil.rmtree(tmp)
    print("\nRESULTADO: %s (%d falhas)" % ("APROVADO" if not falhas else "REPROVADO", len(falhas)))
    return 0 if not falhas else 1


def ext_ns():
    return NS


if __name__ == "__main__":
    sys.exit(main())
