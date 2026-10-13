# MOTOR DE CUSTO FISCAL DE AQUISICAO (v0.1.2)

Calcula, por item de NF-e, **como cada componente fiscal afeta o custo da compra** de uma farmácia em
**Lucro Real**, de forma auditável. Lê a base do extrator (`02_BASE_ITENS_XML.csv`, extrator >= 1.1.0)
e **não altera** a base nem os XMLs.

> Status: ferramenta pronta, **regras de crédito todas PENDENTES**. Sem validação contábil, o custo
> oficial (`C_CUSTO_FISCAL_EFETIVO_VALIDADO`) é igual ao valor documentado, sem crédito nenhum.
> Nenhum crédito é assumido automaticamente. Preço de venda está fora do escopo.

## 1. Fórmula conceitual (não é regra fiscal definitiva)

```
CUSTO FISCAL EFETIVO = VALOR DOCUMENTADO DO ITEM
                       - CREDITOS EFETIVAMENTE APROVEITAVEIS (somente regras VALIDADAS e APLICAR=S)
                       + AJUSTES EXTERNOS (guias, frete CT-e, verbas, etc., com fonte)
```

`VALOR DOCUMENTADO DO ITEM` (camada 3 CALCULO, conferido contra `vItem` quando o emitente informa):

```
vProd - vDesc + vFrete + vSeg + vOutro + vICMSST + vFCPST + vIPI + vII - vICMSDeson (somente se indDeduzDeson = 1)
```

Os tributos que já estão no valor pago (ST, FCP-ST, IPI) **ficam no custo** até que uma regra validada diga
o contrário. Tributos "por dentro" (ICMS próprio, PIS, COFINS do fornecedor) já estão no `vProd`. O crédito,
quando existe, é **subtraído**. IBS/CBS de 2026 não entram no `vItem` (conferido em itens reais) e ficam
`FORA_DO_CUSTO`.

## 2. Camadas em cada valor (coluna `CAMADA` da composição)

| Camada | Exemplo |
|---|---|
| 1 DADO LITERAL DO XML | `L_vProd`, `L_ICMS_ST`, `L_PIS_CST` |
| 2 CLASSIFICACAO DOCUMENTAL | `CLASS_DOC_OPERACAO_CODIGO`, natureza do CFOP |
| 3 CALCULO | `C_VALOR_DOCUMENTADO_ITEM`, `C_CONFERE_VITEM`, custo validado |
| 4 INFERENCIA | operação inferida pelo cadastro da rede |
| 5 HIPOTESE | `H_<TRIBUTO>_CREDITO_HIPOTESE`, `H_CUSTO_FISCAL_CENARIO_HIPOTESE` |
| 6 PENDENTE DE VALIDACAO FISCAL | regra aplicada com `STATUS_VALIDACAO = PENDENTE` |

## 3. Escopo

| `CLASS_DOC_OPERACAO_CODIGO` | Tratamento |
|---|---|
| `COMPRA_DE_TERCEIRO` | AQUISICAO: custo calculado |
| `TRANSFERENCIA_ENTRE_LOJAS` | TRANSFERENCIA: calculado e sinalizado; o custo de referência deve vir da compra original |
| demais (`SAIDA_PROPRIA_DA_REDE`, `ENTRADA_EMITIDA_PELA_REDE`, `TERCEIRO_PARA_TERCEIRO`, `INDETERMINADA`) | listados em `12_ITENS_FORA_DO_ESCOPO` com o motivo |

## 4. Regras (`config/REGRAS_CREDITO_LUCRO_REAL.csv`)

Uma linha por regra; a primeira que casar (menor `PRIORIDADE`) por tributo é aplicada.

| Coluna | Uso |
|---|---|
| `TRIBUTO` | ICMS, ICMS_SN, ICMS_ST, FCP_ST, IPI, PIS, COFINS, IBS, CBS |
| `OPERACAO_IN` | códigos de operação separados por `|` |
| `COND1_*`, `COND2_*` | campo da base + operador (`IN`, `NOT_IN`, `GT0`, `VAZIO`, `NAO_VAZIO`) + valores `|` |
| `TRATAMENTO` | `CREDITO`, `CUSTO_SEM_CREDITO`, `FORA_DO_CUSTO`, `INDEFINIDO` |
| `BASE_FORMULA` | `CAMPO:<coluna>`, `VALOR_AQUISICAO` ou `VALOR_AQUISICAO_SEM_ICMS` (documentado - ICMS próprio) |
| `ALIQUOTA_PERC` | percentual aplicado sobre a base (100 = valor do campo) |
| `STATUS_VALIDACAO` / `APLICAR` | crédito entra no custo oficial **somente** com `VALIDADA` e `S` |
| `FUNDAMENTO_A_CONFIRMAR`, `VALIDADO_POR`, `DATA_VALIDACAO` | rastreabilidade da decisão |

Regras entregues (todas `PENDENTE`, `APLICAR = N`):

| Regra | Hipótese registrada |
|---|---|
| ICMS-01 | crédito do ICMS próprio destacado em ICMS00/20/51/90 |
| ICMS-02 | ICMS próprio em operação com ST (10/30/60/70): sem crédito |
| ICMS-03 | crédito de Simples informado em `vCredICMSSN` |
| ICMS-04 | fornecedor Simples sem crédito informado: sem crédito |
| ST-01, FCPST-01, IPI-01 | ST, FCP-ST e IPI destacados integram o custo |
| PIS-01 / COFINS-01 | CST 01: crédito 1,65% / 7,6% sobre a base sem ICMS |
| PIS-02 / COFINS-02 | CST 02 a 09: sem crédito |
| PIS-03 / COFINS-03 | CST 49/98/99: indefinido (sem efeito até decisão) |
| IBS-01 / CBS-01 | destaque 2026 fora do custo |

**O CST do fornecedor não define sozinho o direito ao crédito de PIS/COFINS**: o crédito depende de
como o produto é tributado na revenda da farmácia. Por isso PIS-01/COFINS-01 exigem validação por produto/NCM.

### Como validar uma regra

1. Abrir `config\REGRAS_CREDITO_LUCRO_REAL.csv` (no Excel, importar como texto separado por `;`).
2. Conferir com a contabilidade a descrição, as condições e a base.
3. Preencher `STATUS_VALIDACAO = VALIDADA`, `APLICAR = S`, `VALIDADO_POR`, `DATA_VALIDACAO`.
4. Rodar de novo. A execução anterior é preservada; a nova cria outra pasta `MOTOR_...`.

Regra rejeitada: `STATUS_VALIDACAO = REJEITADA`. Ela é ignorada e vale a próxima regra do mesmo tributo que casar.
Se nenhuma casar, o tributo fica `SEM_REGRA` e vira pendência quando há valor.

## 5. Ajustes externos (`config/AJUSTES_EXTERNOS.csv`, opcional)

```
ID_REGISTRO;TIPO;VALOR;FONTE;OBS
<chave>-001;ICMS_ANTECIPACAO;2,50;GUIA 123/2026;rateio por item
```

Valor positivo aumenta o custo, negativo reduz (ex.: verba). Decimal com vírgula ou ponto, sem separador de milhar. `FONTE` é obrigatória para auditoria.

## 6. Saídas (`EXEC_...\MOTOR_AAAAMMDD_HHMMSS\`)

| Arquivo | Conteúdo |
|---|---|
| `08_CUSTO_FISCAL_ITENS.csv` | 1 linha por item no escopo: literais, regra/tratamento/status por tributo, crédito hipótese x validado, custo validado e hipótese (total e unitário), situações para decisão, pendências |
| `09_COMPOSICAO_CUSTO_LONGA.csv` | 1 linha por componente do custo, com `CAMADA`, sinal, fórmula e observação |
| `10_REGRAS_APLICADAS_RESUMO.csv` | uso de cada regra (itens, valor) |
| `11_PENDENCIAS_VALIDACAO.csv` | pendências e situações agrupadas, com exemplo de `ID_REGISTRO` |
| `12_ITENS_FORA_DO_ESCOPO.csv` | itens fora do escopo e motivo |
| `13_LOG_MOTOR.csv`, `MOTOR_EXECUCAO.json` | log, versão, totais |

Rastreabilidade: cada linha traz `ID_REGISTRO` (chave + item), chave, emitente, destinatário/loja,
data, CFOP, EAN e o caminho do XML de origem.

## 7. Situações sinalizadas para decisão

Nota sem pagamento (tPag 90), CFOP de bonificação, finalidade complementar/ajuste/devolução,
transferência, valor documentado diferente do `vItem`, fornecedor CRT 3 (LR x LP não determinável pelo XML),
operação interestadual (antecipação/diferencial é dado externo) e alertas documentais do extrator.

## 8. Execução

```
python motor_custo_fiscal.py --exec "<pasta EXEC_...>" [--regras <csv>] [--ajustes <csv>]
python motor_custo_fiscal.py --ultima-exec-em "<pasta de saida do extrator>"
```

Testes: `testes/teste_motor_sintetico.py` (dados fictícios) e `testes/teste_referencia_real.py`
(XMLs reais da biblioteca no Drive; expectativas reais ficam no Drive, fora deste repositório público).
