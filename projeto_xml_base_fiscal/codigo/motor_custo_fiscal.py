# -*- coding: utf-8 -*-
"""
MOTOR DE CUSTO FISCAL DE AQUISICAO - PROJETO XML - INTELIGENCIA DE COMPRAS
=========================================================================

Le a base do extrator (02_BASE_ITENS_XML.csv de uma pasta EXEC_...) e explica,
por item de nota, como cada componente fiscal afeta o custo da compra para a
farmacia (COMPRADORA = LUCRO REAL).

Estrutura conceitual (cada parcela com sua camada de confiabilidade):

  VALOR DOCUMENTADO DO ITEM  (vProd - vDesc + frete + seguro + outras + ICMS-ST + FCP-ST + IPI + II)
  - CREDITOS FISCAIS VALIDADOS (somente regras com STATUS_VALIDACAO=VALIDADA e APLICAR=S)
  + AJUSTES EXTERNOS INFORMADOS (ex.: ICMS antecipacao paga pela loja, CT-e de frete)
  = CUSTO FISCAL EFETIVO VALIDADO

  Em paralelo, e SEM substituir o valor validado:
  CUSTO FISCAL - CENARIO HIPOTESE = documentado - creditos das regras PENDENTES

Nenhum credito e assumido automaticamente: a tabela de regras
(config/REGRAS_CREDITO_LUCRO_REAL.csv) vem com STATUS_VALIDACAO=PENDENTE e
APLICAR=N. Imposto destacado NAO vira credito sem regra validada.

Camadas (coluna CAMADA da composicao):
  1 DADO LITERAL DO XML | 2 CLASSIFICACAO DOCUMENTAL | 3 CALCULO |
  4 INFERENCIA | 5 HIPOTESE | 6 PENDENTE DE VALIDACAO FISCAL | 7 DADO EXTERNO | 8 VALIDADO

USO
  python motor_custo_fiscal.py --exec "<pasta EXEC_...>" [--regras config/REGRAS_CREDITO_LUCRO_REAL.csv]
                               [--ajustes AJUSTES_EXTERNOS.csv]

Saida: subpasta MOTOR_AAAAMMDD_HHMMSS dentro da pasta EXEC (nada e sobrescrito).
"""

import argparse
import csv
import datetime as dt
import glob
import json
import os
import sys
from collections import Counter, OrderedDict, defaultdict

VERSAO_MOTOR = "0.1.1"

CAMADA = {
    "LIT": "1 DADO LITERAL DO XML",
    "DOC": "2 CLASSIFICACAO DOCUMENTAL",
    "CALC": "3 CALCULO",
    "INF": "4 INFERENCIA",
    "HIP": "5 HIPOTESE",
    "PEND": "6 PENDENTE DE VALIDACAO FISCAL",
    "EXT": "7 DADO EXTERNO",
    "VAL": "8 VALIDADO",
}

TRIBUTOS = ["ICMS", "ICMS_SN", "ICMS_ST", "FCP_ST", "IPI", "PIS", "COFINS", "IBS", "CBS"]

# coluna da base que contem o valor literal de cada tributo
VALOR_TRIBUTO = {
    "ICMS": "ICMS_vICMS", "ICMS_SN": "ICMS_vCredICMSSN", "ICMS_ST": "ICMS_vICMSST", "FCP_ST": "ICMS_vFCPST",
    "IPI": "IPI_vIPI", "PIS": "PIS_VALOR", "COFINS": "COFINS_VALOR", "IBS": "IBS_VALOR", "CBS": "CBS_VALOR",
}

ESCOPO_CUSTO = {"COMPRA_DE_TERCEIRO": "AQUISICAO", "TRANSFERENCIA_ENTRE_LOJAS": "TRANSFERENCIA"}

RASTRO = ["ID_REGISTRO", "CHAVE_NFE", "NUMERO_NF", "SERIE", "DATA_EMISSAO", "EMIT_CNPJ", "EMIT_RAZAO_SOCIAL", "EMIT_UF",
          "EMIT_CRT", "EMIT_REGIME_DOCUMENTAL", "DEST_CNPJ", "DEST_RAZAO_SOCIAL", "DEST_UF", "ARQ_CAMINHO_COMPLETO",
          "NUMERO_ITEM", "EAN_CHAVE_VINCULO", "EAN", "COD_PRODUTO_FORNECEDOR", "DESCRICAO_PRODUTO", "NCM", "CEST", "CFOP",
          "CLASS_DOC_OPERACAO_CODIGO", "CLASS_DOC_NATUREZA_CFOP", "CENARIO_FISCAL_ID", "UNID_COMERCIAL", "QTD_COMERCIAL"]


def num(v):
    if v is None:
        return None
    v = str(v).strip()
    if v == "":
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def z(v):
    return v if v is not None else 0.0


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return ("%.4f" % v).rstrip("0").rstrip(".").replace(".", ",") if v != int(v) else ("%d" % v)
    return v


def ler_csv(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def gravar_csv(caminho, cab, linhas):
    with open(caminho, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(cab)
        for l in linhas:
            w.writerow([fmt(l.get(c)) for c in cab])


# ----------------------------------------------------------------------------
# Regras
# ----------------------------------------------------------------------------

OPERADORES = {"IN", "NOT_IN", "GT0", "VAZIO", "NAO_VAZIO"}
TRATAMENTOS = {"CREDITO", "CUSTO_SEM_CREDITO", "FORA_DO_CUSTO", "INDEFINIDO"}


def carregar_regras(caminho, log):
    regras = []
    for i, r in enumerate(ler_csv(caminho), 2):
        erro = []
        if r["TRIBUTO"] not in TRIBUTOS:
            erro.append("TRIBUTO invalido")
        if r["TRATAMENTO"] not in TRATAMENTOS:
            erro.append("TRATAMENTO invalido")
        for k in ("COND1_OP", "COND2_OP"):
            if r.get(k) and r[k] not in OPERADORES:
                erro.append("%s invalido" % k)
        bf = r.get("BASE_FORMULA") or ""
        if not (bf.startswith("CAMPO:") or bf in ("VALOR_AQUISICAO", "VALOR_AQUISICAO_SEM_ICMS")):
            erro.append("BASE_FORMULA invalida")
        if r.get("STATUS_VALIDACAO") not in ("PENDENTE", "VALIDADA", "REJEITADA"):
            erro.append("STATUS_VALIDACAO invalido")
        if erro:
            log.append(OrderedDict([("NIVEL", "ERRO"), ("ETAPA", "REGRAS"), ("REFERENCIA", "linha %d %s" % (i, r.get("ID_REGRA"))),
                                    ("MENSAGEM", "; ".join(erro)), ("ACAO", "Regra ignorada")]))
            continue
        r["_prio"] = int(r.get("PRIORIDADE") or 999)
        r["_aliq"] = num(r.get("ALIQUOTA_PERC")) or 0.0
        regras.append(r)
    regras.sort(key=lambda x: (x["TRIBUTO"], x["_prio"], x["ID_REGRA"]))
    return regras


def cond_ok(item, campo, op, valores):
    if not campo:
        return True
    v = item.get(campo, "")
    v = "" if v is None else v.strip()
    vals = [x.strip() for x in (valores or "").split("|") if x.strip() != ""]
    if op == "IN":
        return v in vals
    if op == "NOT_IN":
        return v not in vals
    if op == "GT0":
        n = num(v)
        return n is not None and n > 0
    if op == "VAZIO":
        return v == ""
    if op == "NAO_VAZIO":
        return v != ""
    return False


def regra_para(item, tributo, regras):
    for r in regras:
        if r["TRIBUTO"] != tributo or r.get("STATUS_VALIDACAO") == "REJEITADA":
            continue
        ops = [o.strip() for o in (r.get("OPERACAO_IN") or "").split("|") if o.strip()]
        if ops and item.get("CLASS_DOC_OPERACAO_CODIGO") not in ops:
            continue
        if cond_ok(item, r.get("COND1_CAMPO"), r.get("COND1_OP"), r.get("COND1_VALORES")) and \
                cond_ok(item, r.get("COND2_CAMPO"), r.get("COND2_OP"), r.get("COND2_VALORES")):
            return r
    return None


def base_regra(item, r, comp):
    bf = r["BASE_FORMULA"]
    if bf.startswith("CAMPO:"):
        return z(num(item.get(bf.split(":", 1)[1]))), bf
    base = comp["C_VALOR_DOCUMENTADO_ITEM"]
    if bf == "VALOR_AQUISICAO_SEM_ICMS":
        base -= z(comp["L_ICMS_PROPRIO_DESTACADO"])
    return base, bf


# ----------------------------------------------------------------------------
# Calculo por item
# ----------------------------------------------------------------------------

def calcular(item, regras, ajustes):
    g = lambda c: num(item.get(c))
    out = OrderedDict((c, item.get(c, "")) for c in RASTRO)
    comp = []  # composicao longa

    def C(ordem, componente, sinal, valor, camada, origem, obs=""):
        comp.append(OrderedDict([("ID_REGISTRO", item["ID_REGISTRO"]), ("ORDEM", ordem), ("COMPONENTE", componente),
                                 ("EFEITO_NO_CUSTO", sinal), ("VALOR", valor), ("CAMADA", camada), ("ORIGEM", origem), ("OBS", obs)]))

    lit = OrderedDict([
        ("L_VALOR_BRUTO", ("VALOR_PRODUTO", "det/prod/vProd", "+")),
        ("L_DESCONTO", ("VALOR_DESCONTO", "det/prod/vDesc", "-")),
        ("L_FRETE", ("VALOR_FRETE", "det/prod/vFrete", "+")),
        ("L_SEGURO", ("VALOR_SEGURO", "det/prod/vSeg", "+")),
        ("L_OUTRAS_DESP", ("VALOR_OUTRAS_DESP", "det/prod/vOutro", "+")),
        ("L_ICMS_ST", ("ICMS_vICMSST", "ICMSxx/vICMSST", "+")),
        ("L_FCP_ST", ("ICMS_vFCPST", "ICMSxx/vFCPST", "+")),
        ("L_IPI", ("IPI_vIPI", "IPI/IPITrib/vIPI", "+")),
        ("L_II", ("II_vII", "II/vII", "+")),
        ("L_ICMS_DESONERADO", ("ICMS_vICMSDeson", "ICMSxx/vICMSDeson", "-SE indDeduzDeson=1")),
        ("L_ICMS_PROPRIO_DESTACADO", ("ICMS_vICMS", "ICMSxx/vICMS", "0 (embutido no preco)")),
        ("L_PIS_DESTACADO", ("PIS_VALOR", "PISxx/vPIS", "0 (embutido no preco)")),
        ("L_COFINS_DESTACADO", ("COFINS_VALOR", "COFINSxx/vCOFINS", "0 (embutido no preco)")),
        ("L_IBS_DESTACADO", ("IBS_VALOR", "IBSCBS/gIBSCBS/vIBS", "0 (fora do vItem em 2026)")),
        ("L_CBS_DESTACADO", ("CBS_VALOR", "IBSCBS/gIBSCBS/gCBS/vCBS", "0 (fora do vItem em 2026)")),
        ("L_ICMS_SN_CREDITO_INFORMADO", ("ICMS_vCredICMSSN", "ICMSSN/vCredICMSSN", "0 (informativo)")),
        ("L_VITEM", ("VALOR_TOTAL_ITEM_XML", "det/vItem", "referencia")),
    ])
    vals = {}
    for i, (k, (col, tag, efeito)) in enumerate(lit.items(), 1):
        vals[k] = g(col)
        out[k] = vals[k]
        if vals[k] is not None:
            C(i, k, efeito, vals[k], CAMADA["LIT"], tag)

    ded_deson = item.get("ICMS_indDeduzDeson") == "1"
    acess = z(vals["L_FRETE"]) + z(vals["L_SEGURO"]) + z(vals["L_OUTRAS_DESP"])
    por_fora = z(vals["L_ICMS_ST"]) + z(vals["L_FCP_ST"]) + z(vals["L_IPI"]) + z(vals["L_II"])
    documentado = z(vals["L_VALOR_BRUTO"]) - z(vals["L_DESCONTO"]) + acess + por_fora - (z(vals["L_ICMS_DESONERADO"]) if ded_deson else 0.0)
    documentado = round(documentado, 2)
    out["C_DESPESAS_ACESSORIAS"] = round(acess, 2)
    out["C_VALOR_MERCADORIA_LIQUIDO"] = round(z(vals["L_VALOR_BRUTO"]) - z(vals["L_DESCONTO"]), 2)
    out["C_TRIBUTOS_POR_FORA"] = round(por_fora, 2)
    out["C_VALOR_DOCUMENTADO_ITEM"] = documentado
    out["C_CONFERE_VITEM"] = ("SEM_VITEM" if vals["L_VITEM"] is None else
                              ("SIM" if abs(vals["L_VITEM"] - documentado) <= 0.011 else "NAO (dif %.2f)" % (vals["L_VITEM"] - documentado)))
    C(50, "C_VALOR_DOCUMENTADO_ITEM", "=", documentado, CAMADA["CALC"],
      "vProd - vDesc + vFrete + vSeg + vOutro + vICMSST + vFCPST + vIPI + vII (- vICMSDeson se indDeduzDeson=1)",
      "Confere com vItem: %s" % out["C_CONFERE_VITEM"])

    # --- tributos x regras
    cred_val = cred_hip = 0.0
    pend = []
    compb = {"C_VALOR_DOCUMENTADO_ITEM": documentado, "L_ICMS_PROPRIO_DESTACADO": vals["L_ICMS_PROPRIO_DESTACADO"]}
    ordem = 60
    for t in TRIBUTOS:
        r = regra_para(item, t, regras)
        valor_trib = num(item.get(VALOR_TRIBUTO[t]))
        if r is None:
            out["R_%s_REGRA" % t] = ""
            out["R_%s_TRATAMENTO" % t] = "SEM_REGRA"
            out["R_%s_STATUS" % t] = ""
            out["H_%s_CREDITO_HIPOTESE" % t] = None
            out["V_%s_CREDITO_VALIDADO" % t] = 0.0
            if valor_trib:
                pend.append("%s: valor %.2f sem regra cadastrada" % (t, valor_trib))
            continue
        validada = r["STATUS_VALIDACAO"] == "VALIDADA" and (r.get("APLICAR") or "N").upper() == "S"
        out["R_%s_REGRA" % t] = r["ID_REGRA"]
        out["R_%s_TRATAMENTO" % t] = r["TRATAMENTO"]
        out["R_%s_STATUS" % t] = "VALIDADA_E_APLICADA" if validada else r["STATUS_VALIDACAO"] + ("" if r["STATUS_VALIDACAO"] == "PENDENTE" else "_NAO_APLICADA")
        hip = None
        if r["TRATAMENTO"] == "CREDITO":
            base, bf = base_regra(item, r, compb)
            hip = round(base * r["_aliq"] / 100.0, 2)
        out["H_%s_CREDITO_HIPOTESE" % t] = hip
        out["V_%s_CREDITO_VALIDADO" % t] = hip if (validada and hip) else 0.0
        if hip:
            cred_hip += hip
            if validada:
                cred_val += hip
        camada = CAMADA["VAL"] if validada else CAMADA["PEND"]
        ordem += 1
        if r["TRATAMENTO"] == "CREDITO":
            C(ordem, "CREDITO_%s" % t, "-", hip, camada if validada else CAMADA["HIP"],
              "Regra %s: %s x %s%%" % (r["ID_REGRA"], r["BASE_FORMULA"], fmt(r["_aliq"])),
              "Aplicado no custo validado" if validada else "NAO aplicado: regra %s" % r["STATUS_VALIDACAO"])
        else:
            C(ordem, "TRATAMENTO_%s" % t, {"CUSTO_SEM_CREDITO": "permanece no custo", "FORA_DO_CUSTO": "nao compoe o custo",
                                           "INDEFINIDO": "indefinido"}[r["TRATAMENTO"]],
              valor_trib, camada, "Regra %s" % r["ID_REGRA"], r.get("DESCRICAO", ""))
        if not validada:
            pend.append("%s: regra %s %s" % (t, r["ID_REGRA"], r["STATUS_VALIDACAO"]))

    # --- ajustes externos
    aj = ajustes.get(item["ID_REGISTRO"], [])
    v_aj = round(sum(z(num(a.get("VALOR"))) for a in aj), 2)
    out["E_AJUSTES_EXTERNOS"] = v_aj if aj else None
    out["E_AJUSTES_DESCRICAO"] = " ; ".join("%s=%s (%s)" % (a.get("TIPO"), a.get("VALOR"), a.get("FONTE")) for a in aj) or ""
    for a in aj:
        ordem += 1
        C(ordem, "AJUSTE_%s" % a.get("TIPO"), "+/-", num(a.get("VALOR")), CAMADA["EXT"], a.get("FONTE", ""), a.get("OBS", ""))

    out["V_CREDITOS_VALIDADOS_TOTAL"] = round(cred_val, 2)
    out["H_CREDITOS_HIPOTESE_TOTAL"] = round(cred_hip, 2)
    custo_val = round(documentado - cred_val + z(out["E_AJUSTES_EXTERNOS"]), 2)
    custo_hip = round(documentado - cred_hip + z(out["E_AJUSTES_EXTERNOS"]), 2)
    out["C_CUSTO_FISCAL_EFETIVO_VALIDADO"] = custo_val
    out["H_CUSTO_FISCAL_CENARIO_HIPOTESE"] = custo_hip
    q = num(item.get("QTD_COMERCIAL"))
    out["C_CUSTO_UNITARIO_VALIDADO"] = round(custo_val / q, 4) if q else None
    out["H_CUSTO_UNITARIO_HIPOTESE"] = round(custo_hip / q, 4) if q else None
    out["C_PART_TRIBUTOS_POR_FORA_PCT"] = round(100.0 * por_fora / documentado, 2) if documentado else None
    out["H_PART_CREDITOS_HIPOTESE_PCT"] = round(100.0 * cred_hip / documentado, 2) if documentado else None
    C(900, "C_CUSTO_FISCAL_EFETIVO_VALIDADO", "=", custo_val, CAMADA["CALC"],
      "C_VALOR_DOCUMENTADO_ITEM - creditos VALIDADOS + ajustes externos", "Creditos validados: %.2f" % cred_val)
    C(901, "H_CUSTO_FISCAL_CENARIO_HIPOTESE", "=", custo_hip, CAMADA["HIP"],
      "C_VALOR_DOCUMENTADO_ITEM - creditos das regras (inclusive PENDENTES) + ajustes", "NAO usar como custo oficial ate validar")

    # --- situacoes que exigem decisao
    flags = []
    if item.get("NF_SEM_PAGAMENTO") == "S":
        flags.append("NOTA SEM PAGAMENTO (tPag 90): tratamento de custo de bonificacao/brinde requer definicao")
    if "BONIFICACAO" in (item.get("CLASS_DOC_NATUREZA_CFOP") or ""):
        flags.append("CFOP DE BONIFICACAO/BRINDE")
    if item.get("CLASS_DOC_OPERACAO_CODIGO") == "TRANSFERENCIA_ENTRE_LOJAS":
        flags.append("TRANSFERENCIA: custo de referencia deve vir da compra original")
    if out["C_CONFERE_VITEM"].startswith("NAO"):
        flags.append("VALOR DOCUMENTADO NAO CONFERE COM vItem")
    if item.get("EMIT_CRT") == "3":
        flags.append("FORNECEDOR CRT 3: Lucro Real x Presumido nao determinavel pelo XML (informacao externa, se necessaria)")
    if (item.get("ID_DEST") == "2") or (item.get("EMIT_UF") and item.get("DEST_UF") and item.get("EMIT_UF") != item.get("DEST_UF")):
        flags.append("OPERACAO INTERESTADUAL: verificar ICMS antecipacao/diferencial devido pela loja na entrada (dado externo)")
    if item.get("ALERTAS_DOCUMENTAIS"):
        flags.append("ALERTAS DOCUMENTAIS: " + item["ALERTAS_DOCUMENTAIS"])
    out["SITUACOES_PARA_DECISAO"] = " | ".join(flags)
    out["PENDENCIAS_VALIDACAO"] = " | ".join(pend)
    out["STATUS_CUSTO"] = ("CUSTO = VALOR DOCUMENTADO (NENHUM CREDITO VALIDADO)" if cred_val == 0 and not aj else
                           "CUSTO COM CREDITOS VALIDADOS E/OU AJUSTES EXTERNOS")
    return out, comp, pend, flags


def main(argv=None):
    aqui = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Motor de custo fiscal de aquisicao (le a base do extrator).")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--exec", help="Pasta EXEC_... gerada pelo extrator")
    grp.add_argument("--ultima-exec-em", help="Pasta de saida do extrator: usa a EXEC_* mais recente (pelo nome)")
    ap.add_argument("--regras", default=os.path.join(aqui, "config", "REGRAS_CREDITO_LUCRO_REAL.csv"))
    ap.add_argument("--ajustes", default="", help="CSV opcional: ID_REGISTRO;TIPO;VALOR;FONTE;OBS (dados externos)")
    a = ap.parse_args(argv)

    if a.ultima_exec_em:
        execs = sorted(d for d in glob.glob(os.path.join(a.ultima_exec_em, "EXEC_*")) if os.path.isdir(d))
        if not execs:
            print("ERRO: nenhuma pasta EXEC_* em %s" % a.ultima_exec_em)
            return 2
        a.exec = execs[-1]
        print("EXEC utilizada: %s" % a.exec)
    inicio = dt.datetime.now()
    base_csv = os.path.join(a.exec, "02_BASE_ITENS_XML.csv")
    if not os.path.exists(base_csv):
        print("ERRO: base nao encontrada: %s" % base_csv)
        return 2
    saida = os.path.join(a.exec, "MOTOR_" + inicio.strftime("%Y%m%d_%H%M%S"))
    n = 1
    while os.path.exists(saida):  # nunca sobrescreve execucao anterior
        n += 1
        saida = os.path.join(a.exec, "MOTOR_%s_%02d" % (inicio.strftime("%Y%m%d_%H%M%S"), n))
    os.makedirs(saida, exist_ok=False)
    log = []
    regras = carregar_regras(a.regras, log)
    ajustes = defaultdict(list)
    if a.ajustes:
        for r in ler_csv(a.ajustes):
            ajustes[r.get("ID_REGISTRO", "")].append(r)

    itens = ler_csv(base_csv)
    no_escopo, fora, composicao = [], [], []
    uso_regra = Counter()
    pend_count = Counter()
    pend_ex = {}
    flag_count = Counter()
    for it in itens:
        op = it.get("CLASS_DOC_OPERACAO_CODIGO") or ""
        if op not in ESCOPO_CUSTO:
            fora.append(OrderedDict([("ID_REGISTRO", it["ID_REGISTRO"]), ("CLASS_DOC_OPERACAO_CODIGO", op),
                                     ("CLASS_DOC_NATUREZA_CFOP", it.get("CLASS_DOC_NATUREZA_CFOP")),
                                     ("EMIT_CNPJ", it.get("EMIT_CNPJ")), ("DEST_CNPJ", it.get("DEST_CNPJ")),
                                     ("ARQ_CAMINHO_COMPLETO", it.get("ARQ_CAMINHO_COMPLETO")),
                                     ("MOTIVO", "Operacao fora do escopo de custo de aquisicao (%s)" % (op or "SEM CODIGO - rodar extrator >= 1.1.0"))]))
            continue
        out, comp, pend, flags = calcular(it, regras, ajustes)
        out["ESCOPO_CUSTO"] = ESCOPO_CUSTO[op]
        no_escopo.append(out)
        composicao.extend(comp)
        for t in TRIBUTOS:
            if out.get("R_%s_REGRA" % t):
                uso_regra[out["R_%s_REGRA" % t]] += 1
        for p in pend:
            k = p.split(" valor ")[0] if "sem regra" in p else p
            pend_count[k] += 1
            pend_ex.setdefault(k, it["ID_REGISTRO"])
        for f in flags:
            k = f.split(":")[0]
            flag_count[k] += 1

    resumo_regras = []
    for r in regras:
        hip = sum(z(o.get("H_%s_CREDITO_HIPOTESE" % r["TRIBUTO"])) for o in no_escopo if o.get("R_%s_REGRA" % r["TRIBUTO"]) == r["ID_REGRA"])
        val = sum(z(o.get("V_%s_CREDITO_VALIDADO" % r["TRIBUTO"])) for o in no_escopo if o.get("R_%s_REGRA" % r["TRIBUTO"]) == r["ID_REGRA"])
        resumo_regras.append(OrderedDict([("ID_REGRA", r["ID_REGRA"]), ("TRIBUTO", r["TRIBUTO"]), ("TRATAMENTO", r["TRATAMENTO"]),
                                          ("STATUS_VALIDACAO", r["STATUS_VALIDACAO"]), ("APLICAR", r.get("APLICAR")),
                                          ("ITENS_AFETADOS", uso_regra.get(r["ID_REGRA"], 0)), ("CREDITO_HIPOTESE_TOTAL", round(hip, 2)),
                                          ("CREDITO_VALIDADO_TOTAL", round(val, 2)), ("DESCRICAO", r.get("DESCRICAO")),
                                          ("FUNDAMENTO_A_CONFIRMAR", r.get("FUNDAMENTO_A_CONFIRMAR"))]))
    pendencias = [OrderedDict([("PENDENCIA", k), ("ITENS", v), ("EXEMPLO_ID_REGISTRO", pend_ex[k]),
                               ("CAMADA", CAMADA["PEND"])]) for k, v in pend_count.most_common()]
    pendencias += [OrderedDict([("PENDENCIA", "SITUACAO: " + k), ("ITENS", v), ("EXEMPLO_ID_REGISTRO", ""), ("CAMADA", "DECISAO GERENCIAL/FISCAL")])
                   for k, v in flag_count.most_common()]

    cab_itens = list(no_escopo[0].keys()) if no_escopo else RASTRO
    gravar_csv(os.path.join(saida, "08_CUSTO_FISCAL_ITENS.csv"), cab_itens, no_escopo)
    cab_comp = ["ID_REGISTRO", "ORDEM", "COMPONENTE", "EFEITO_NO_CUSTO", "VALOR", "CAMADA", "ORIGEM", "OBS"]
    composicao.sort(key=lambda c: (c["ID_REGISTRO"], c["ORDEM"]))
    gravar_csv(os.path.join(saida, "09_COMPOSICAO_CUSTO_LONGA.csv"), cab_comp, composicao)
    gravar_csv(os.path.join(saida, "10_REGRAS_APLICADAS_RESUMO.csv"),
               list(resumo_regras[0].keys()) if resumo_regras else ["ID_REGRA"], resumo_regras)
    gravar_csv(os.path.join(saida, "11_PENDENCIAS_VALIDACAO.csv"), ["PENDENCIA", "ITENS", "EXEMPLO_ID_REGISTRO", "CAMADA"], pendencias)
    gravar_csv(os.path.join(saida, "12_ITENS_FORA_DO_ESCOPO.csv"),
               ["ID_REGISTRO", "CLASS_DOC_OPERACAO_CODIGO", "CLASS_DOC_NATUREZA_CFOP", "EMIT_CNPJ", "DEST_CNPJ", "ARQ_CAMINHO_COMPLETO", "MOTIVO"], fora)
    gravar_csv(os.path.join(saida, "13_LOG_MOTOR.csv"), ["NIVEL", "ETAPA", "REFERENCIA", "MENSAGEM", "ACAO"], log)

    conf = Counter(o["C_CONFERE_VITEM"].split(" ")[0] for o in no_escopo)
    resumo = OrderedDict([
        ("VERSAO_MOTOR", VERSAO_MOTOR), ("EXEC_BASE", a.exec), ("REGRAS", a.regras), ("AJUSTES", a.ajustes),
        ("INICIO", inicio.strftime("%Y-%m-%d %H:%M:%S")),
        ("ITENS_BASE", len(itens)), ("ITENS_NO_ESCOPO", len(no_escopo)), ("ITENS_FORA_DO_ESCOPO", len(fora)),
        ("REGRAS_CARREGADAS", len(regras)),
        ("REGRAS_VALIDADAS_E_APLICADAS", sum(1 for r in regras if r["STATUS_VALIDACAO"] == "VALIDADA" and (r.get("APLICAR") or "").upper() == "S")),
        ("CONFERENCIA_VITEM", dict(conf)),
        ("VALOR_DOCUMENTADO_TOTAL", round(sum(o["C_VALOR_DOCUMENTADO_ITEM"] for o in no_escopo), 2)),
        ("CREDITOS_VALIDADOS_TOTAL", round(sum(o["V_CREDITOS_VALIDADOS_TOTAL"] for o in no_escopo), 2)),
        ("CREDITOS_HIPOTESE_TOTAL", round(sum(o["H_CREDITOS_HIPOTESE_TOTAL"] for o in no_escopo), 2)),
        ("CUSTO_EFETIVO_VALIDADO_TOTAL", round(sum(o["C_CUSTO_FISCAL_EFETIVO_VALIDADO"] for o in no_escopo), 2)),
        ("CUSTO_CENARIO_HIPOTESE_TOTAL", round(sum(o["H_CUSTO_FISCAL_CENARIO_HIPOTESE"] for o in no_escopo), 2)),
    ])
    with open(os.path.join(saida, "MOTOR_EXECUCAO.json"), "w", encoding="utf-8") as fh:
        json.dump(resumo, fh, ensure_ascii=False, indent=2)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print("Saida:", saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
