# -*- coding: utf-8 -*-
"""
Regressao com a BIBLIOTECA DE XMLs REAIS (nao versionada no GitHub; fica no Drive:
PROJETO XML - INTELIGENCIA DE COMPRAS\\12_TESTES_VALIDACAO\\BASE_FISCAL\\XML_REFERENCIA_REAL).

Uso: python testes/teste_referencia_real.py --ref "<pasta XML_REFERENCIA_REAL>" --rede "<REDE_CNPJS.csv>"
Os arquivos sao identificados pelo prefixo REFnn do nome. Expectativas em <ref>/EXPECTATIVAS_REFERENCIA_REAL.csv (fica no Drive junto dos XMLs reais;
nao vai para o repositorio publico porque contem valores reais de compra). Modelo: MODELO_EXPECTATIVAS.csv.
"""
import argparse
import csv
import glob
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import extrator_base_fiscal_xml as ext  # noqa: E402
import motor_custo_fiscal as motor  # noqa: E402


def ler(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--rede", required=True)
    ap.add_argument("--expectativas", default="", help="Padrao: <ref>/EXPECTATIVAS_REFERENCIA_REAL.csv")
    a = ap.parse_args(argv)
    tmp = tempfile.mkdtemp(prefix="teste_ref_")
    assert ext.main(["--origem", a.ref, "--saida", tmp, "--cnpjs-rede", a.rede, "--sem-xlsx"]) == 0
    exec_dir = glob.glob(os.path.join(tmp, "EXEC_*"))[0]
    assert motor.main(["--exec", exec_dir]) == 0
    mdir = glob.glob(os.path.join(exec_dir, "MOTOR_*"))[0]

    def chave(r):
        nome = os.path.basename((r.get("ARQ_CAMINHO_COMPLETO") or "").split("::")[0])
        return nome[:5], r["ID_REGISTRO"].rsplit("-", 1)[1].lstrip("0")

    tabelas = {"BASE": {chave(r): r for r in ler(os.path.join(exec_dir, "02_BASE_ITENS_XML.csv"))},
               "CUSTO": {chave(r): r for r in ler(os.path.join(mdir, "08_CUSTO_FISCAL_ITENS.csv"))},
               "FORA": {chave(r): r for r in ler(os.path.join(mdir, "12_ITENS_FORA_DO_ESCOPO.csv"))}}
    falhas = 0
    total = 0
    for e in ler(a.expectativas or os.path.join(a.ref, "EXPECTATIVAS_REFERENCIA_REAL.csv")):
        tab = tabelas[e["TABELA"]]
        alvos = list(tab.values()) if e["REF"] == "*" else [tab.get((e["REF"], e["NUMERO_ITEM"]))]
        for r in alvos:
            total += 1
            if r is None:
                print("FALHA - %s item %s nao encontrado em %s" % (e["REF"], e["NUMERO_ITEM"], e["TABELA"]))
                falhas += 1
                continue
            v = r.get(e["CAMPO"], "")
            ok = (v == e["VALOR_ESPERADO"]) if e["OPERADOR"] == "=" else (e["VALOR_ESPERADO"] in (v or ""))
            if not ok or e["REF"] != "*":
                print("%s - %s/%s %s.%s %s '%s' (obtido '%s') - %s" % ("OK   " if ok else "FALHA", e["REF"], e["NUMERO_ITEM"], e["TABELA"],
                                                                       e["CAMPO"], e["OPERADOR"], e["VALOR_ESPERADO"], v, e["MOTIVO"]))
            falhas += 0 if ok else 1
    print("Checagens globais (*) executadas sobre todos os itens do escopo.")
    shutil.rmtree(tmp)
    print("\nRESULTADO: %s (%d checagens, %d falhas)" % ("APROVADO" if not falhas else "REPROVADO", total, falhas))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
