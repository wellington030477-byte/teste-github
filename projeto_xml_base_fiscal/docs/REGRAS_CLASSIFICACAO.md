# REGRAS DE CLASSIFICACAO DOCUMENTAL, ALERTAS E INDICIOS

Status de todas as regras abaixo: **REGRA TECNICA DE ORGANIZACAO** (não é regra fiscal).
Nenhuma delas conclui tributação de produto. Toda conclusão fiscal fica em `STATUS_VALIDACAO_FISCAL = PENDENTE`.

## 1. Classificação documental (camada B)

| Coluna | Regra | Observação |
|---|---|---|
| `CLASS_DOC_OPERACAO_CODIGO` (v1.1) | Pelo cadastro de CNPJs da rede (`--cnpjs-rede` + pastas de loja): emitente e destinatário da rede → `TRANSFERENCIA_ENTRE_LOJAS`; emitente da rede e `tpNF=0` → `ENTRADA_EMITIDA_PELA_REDE`; emitente da rede → `SAIDA_PROPRIA_DA_REDE`; destinatário da rede → `COMPRA_DE_TERCEIRO`; nenhum dos dois → `TERCEIRO_PARA_TERCEIRO`; sem cadastro → `INDETERMINADA`. | Usado pelo motor de custo. Corrige a regra por raiz (venda a CPF e loja de raiz diferente). |
| `CLASS_DOC_NATUREZA_CFOP` (v1.1) | Família do CFOP (venda, ST, bonificação, transferência, devolução...) + esfera (estadual/interestadual/exterior). | Descritivo. |
| `EMIT_REGIME_DOCUMENTAL` (v1.1) | Texto do CRT. CRT 3 = regime normal, **Lucro Real ou Presumido não determinável pelo XML**. | |
| `CLASS_DOC_TIPO_OPERACAO` (legado) | Raiz do CNPJ (8 dígitos) emitente = destinatário → `MESMA RAIZ (PROVAVEL TRANSFERENCIA INTERNA)`; senão `EMITENTE TERCEIRO`. Acrescenta finalidade (`finNFe`) e `tpNF`. | Transferências entre lojas podem ter CST/CFOP diferentes da compra original. |
| `CLASS_DOC_ICMS` | Texto pelo grupo/CST/CSOSN do XML + situação dos valores ST (destacada, BC informada com vICMSST zero, retida informada, sem valores). | Descreve o documento, não a regra da UF. |
| `CLASS_DOC_PIS` / `CLASS_DOC_COFINS` | Grupo + CST + descrição da **tabela de CST** para o código informado pelo emitente + valor destacado ou não. | A descrição da tabela CST é o significado do código, não validação do enquadramento do produto. |
| `CLASS_DOC_IPI` | Grupo (`IPITrib`/`IPINT`) + CST + valor destacado. | |
| `FLAG_ST_DESTACADA` | `vICMSST > 0` | |
| `FLAG_BC_ST_INFORMADA` | `vBCST > 0` | |
| `FLAG_ST_RETIDA_ANTERIOR_INFO` | `vBCSTRet > 0` ou `vICMSSTRet > 0` | |
| `FLAG_ICMS_DESONERADO` | `vICMSDeson > 0` | |
| `FLAG_DIFERIMENTO` | `pDif > 0` ou `vICMSDif > 0` | |
| `FLAG_FCP` | `vFCP`, `vFCPST` ou `vFCPSTRet > 0` | |
| `FLAG_IPI_VALOR` | `vIPI > 0` | |
| `FLAG_DIFAL` | grupo `ICMSUFDest` presente | |
| `CENARIO_FISCAL_CHAVE` | `ICMS:grupo/CST ou CSOSN` \| situação ST \| `PIS:grupo/CST` \| `COFINS:grupo/CST` \| `IPI:grupo/CST(+V se vIPI>0)` \| `IBSCBS:CST` | CFOP, origem, NCM e fornecedor ficam como dimensões no mapa, não na chave. |

## 2. Alertas documentais (checagens objetivas)

| Alerta | Condição |
|---|---|
| `BC_ST_INFORMADA_COM_VICMSST_ZERO` | vBCST > 0 e vICMSST = 0 |
| `CST60_SEM_VALORES_ST_RETIDO` | CST 60 sem vBCSTRet/vICMSSTRet > 0 |
| `PIS_CST_TRIBUTADO_SEM_VALOR` / `COFINS_...` | CST 01/02 sem valor destacado |
| `CST_PIS_DIFERENTE_CST_COFINS` | CST PIS ≠ CST COFINS no mesmo item |
| `VPROD_DIFERE_QCOM_X_VUNCOM` | \|vProd − qCom×vUnCom\| > 0,011 |
| `VICMS_DIFERE_BC_X_ALIQ` | \|vICMS − vBC×pICMS/100\| > 0,02 |
| `EAN_AUSENTE_OU_SEM_GTIN` / `EAN_INVALIDO_DV_OU_TAMANHO` | regra GS1 |
| `EAN_DIFERENTE_EAN_TRIB` | cEAN ≠ cEANTrib |
| `UNID_COMERCIAL_DIFERENTE_TRIBUTAVEL` | uCom ≠ uTrib |
| `NCM_AUSENTE_OU_FORA_PADRAO` | NCM sem 8 dígitos |
| `CFOP_INTERNO_COM_IDDEST_INTERESTADUAL` / inverso | 1º dígito do CFOP x idDest |
| `NOTA_SEM_PROTOCOLO_NO_ARQUIVO` / `PROTOCOLO_CSTAT_x` | sem protNFe ou cStat ≠ 100/150 |
| `NOTA_COM_EVENTO_CANCELAMENTO` | evento 110111 encontrado na origem |
| `ITEM_SEM_GRUPO_ICMS` / `ITEM_SEM_GRUPO_PIS_OU_COFINS` | grupo ausente |
| `VITEM_DIFERE_DA_RECONSTRUCAO` (v1.1) | \|vItem − (vProd − vDesc + vFrete + vSeg + vOutro + ST + FCP-ST + IPI + II − vICMSDeson dedutível)\| > 0,011 |
| `INFCPL_CITA_DESONERACAO_SEM_vICMSDeson_NO_ITEM` (v1.1) | informações complementares citam desoneração e o item não tem vICMSDeson |
| `CPROD_TEM_FORMATO_GTIN_COM_CEAN_SEM_GTIN` (v1.1) | cEAN vazio ou SEM GTIN e cProd com formato/DV de GTIN válido |
| `OPERACAO_INDETERMINADA_SEM_CADASTRO_DA_REDE` (v1.1) | nenhum CNPJ da rede disponível |
| `NOTA_SEM_CNPJ_DA_REDE_COMO_EMITENTE_OU_DESTINATARIO` (v1.1) | operação `TERCEIRO_PARA_TERCEIRO` |
| `MESMA_RAIZ_CNPJ_MAS_UM_LADO_FORA_DO_CADASTRO_DA_REDE` (v1.1) | mesma raiz de CNPJ e só um lado no cadastro |

## 3. Indícios (camada C, hipóteses)

| Texto | Gatilho no XML |
|---|---|
| `POSSIVEL MONOFASICO PIS/COFINS - REQUER VALIDACAO FISCAL` | CST PIS ou COFINS = 04 |
| `TRATAMENTO COMPATIVEL COM ALIQUOTA ZERO NO XML - REQUER VALIDACAO LEGAL` | CST 06 |
| `PIS/COFINS ST NO XML - REQUER VALIDACAO FISCAL` | CST 05 |
| `PIS/COFINS SEM DEBITO NO XML (CST x/y) - ENQUADRAMENTO DO PRODUTO NAO DEMONSTRADO` | CST 07, 08, 09, 49, 99 |
| `PRODUTO COM INDICIO DE ICMS-ST NO DOCUMENTO - REGRA DE ST DA UF REQUER VALIDACAO` | ST destacada, BC ST informada ou CST 60 |
| `DOCUMENTO DE TRANSFERENCIA INTERNA - TRIBUTACAO PODE NAO REPRESENTAR A DA COMPRA` | mesma raiz de CNPJ |

## 4. Divergências por produto

Vínculo por `EAN_CHAVE_VINCULO` (cEAN válido; senão cEANTrib válido). Código interno do fornecedor **não** é usado como
identificador global. Campos comparados: NCM, CEST, CFOP, grupo/CST/CSOSN/origem ICMS, flags ST, pICMS, pRedBC, pMVAST,
pRedBCST, pICMSST, grupo/CST/alíquota PIS e COFINS, grupo/CST/alíquota IPI, CST e cClassTrib IBS/CBS, cBenef e a chave do cenário.
Cada divergência informa se ocorre dentro do mesmo fornecedor e se persiste considerando só compras de terceiros.

## 5. Seleção da amostra (`MOTIVO_SELECAO`)

1. Até N exemplos por cenário (padrão 3), maximizando fornecedor, CFOP, NCM e EAN novos; para quando não há diversidade (evita repetidos).
2. Cobertura: pelo menos 1 exemplo de cada CFOP, origem, fornecedor, grupo ICMS/PIS/COFINS/IPI, CST IBS/CBS e CEST.
3. EAN com divergência: 1 exemplo por variante (cenário + NCM + CFOP).
4. Atípicos: 1 exemplo por tipo de alerta, até 2 fornecedores diferentes.
Desempate por completude (EAN válido, CEST, NCM, protocolo 100, sem alertas, compra de terceiro).
