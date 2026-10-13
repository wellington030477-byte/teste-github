# INVENTARIO DO PROJETO E GAP PARA O CUSTO FISCAL DE AQUISICAO

Data: 13/10/2026. Referência: pedido de continuação "MOTOR DE CUSTO FISCAL DE AQUISICAO".
Legenda: **FATO** (verificado), **INFERENCIA**, **HIPOTESE**, **PENDENTE** (depende de validação).

## 1. Ambiente

| Item | Situação |
|---|---|
| Projeto no Drive | FATO: pasta existente movida (não copiada) para `PC_WORK\01_PROJETOS` e renomeada para `PROJETO XML - INTELIGENCIA DE COMPRAS`. Subpastas e arquivos preservados. |
| BASE_XML | FATO: permanece onde está; nada foi movido, renomeado ou alterado. |
| Divergência de caminho | FATO: no Drive, `TRABALHO FARMACIA` está dentro de `PC_WORK`. INFERENCIA: no T: o caminho é `T:\Meu Drive\PC_WORK\TRABALHO FARMACIA\...\BASE_XML`. O `.bat` v1.1 testa os dois caminhos e aceita o caminho como parâmetro. |
| Execuções reais da fase 1 | FATO: nenhuma pasta `EXEC_` no Drive; o `.bat` ainda não foi executado no computador. |
| Repositório GitHub | Público: contém só código, regras e testes fictícios. XMLs reais, CNPJs da rede e valores reais ficam no Drive. |

## 2. O que já atende ao objetivo de custo

- Extração por item com todos os campos de ICMS, ICMS-ST, FCP, DIFAL, IPI, II, PIS, COFINS, IBS/CBS/IS, descontos e despesas acessórias, mais a tabela longa com toda tag folha.
- CRT literal do emitente (o XML não distingue Lucro Real de Presumido em CRT 3; isso é registrado).
- Rastreabilidade completa: `ID_REGISTRO` → chave → arquivo (caminho + SHA-256) → emitente/CNPJ → destinatário/loja → data → CFOP.
- Separação dado original x classificação x indício; validação quantitativa; identificadores como texto.
- Divergências por EAN, mapa de cenários, amostra por cenário.

## 3. O que foi ajustado nesta continuação (extrator 1.0.0 → 1.1.0)

| Ajuste | Motivo (FATO encontrado nos XMLs reais) |
|---|---|
| Operação por cadastro de CNPJs da rede (`CLASS_DOC_OPERACAO_CODIGO`) | A regra por raiz de CNPJ classificava venda da loja para CPF como "emitente terceiro" e não reconhecia loja com raiz de CNPJ diferente. |
| Natureza do CFOP, regime documental do CRT | Separar bonificação, ST, transferência e venda. |
| Reconstrução e conferência do `vItem` | Fórmula do valor documentado conferida item a item com o valor informado pelo emitente. |
| Formas de pagamento, nota sem pagamento, notas referenciadas | Bonificação (tPag 90) e devoluções. |
| Novos alertas | vItem divergente, desoneração citada só no texto, cProd com formato de GTIN em item SEM GTIN, operação indeterminada, nota sem CNPJ da rede, mesma raiz com um lado fora do cadastro. |
| Pasta de execução sempre única | Duas execuções no mesmo segundo colidiam. |

## 4. O que foi criado

- `motor_custo_fiscal.py` + `config/REGRAS_CREDITO_LUCRO_REAL.csv` (ver `MOTOR_CUSTO_FISCAL.md`).
- Biblioteca mínima de XMLs reais (cópias, vínculo ao original) em `12_TESTES_VALIDACAO\BASE_FISCAL\XML_REFERENCIA_REAL` no Drive, com manifesto e expectativas.
- Testes: sintético do motor (22 checagens) e regressão sobre a biblioteca real (89 checagens), todos aprovados.

## 5. Cenários reais encontrados na BASE_XML

FATO (verificado pelo extrator): ICMS 00, 10, 20 e 60 (inclusive 00 e 60 na mesma nota); ST destacada; BC ST
informada com ST zero; CST 60 sem valores retidos; CSOSN 102 (Simples) com bonificação e sem pagamento;
PIS/COFINS 01, 02, 04 e 49 (Outr); IPINT e IPITrib 99 sem valor; IBS/CBS com redução 100% e cClassTrib;
transferência entre lojas; venda própria interestadual com DIFAL; compra interestadual (MG) a 7%;
item SEM GTIN; desoneração citada só em informações complementares.

NAO ENCONTRADOS ainda (precisam de busca dirigida na base completa, após rodar o `.bat`): ICMS 40, 51 e 70
com amostra verificada, PIS/COFINS 06 (alíquota zero) e 07/08, IPI com valor destacado, FCP-ST com valor,
vCredICMSSN preenchido. Três cópias da biblioteca (REF09, REF12, REF13) ainda não foram verificadas pelo extrator.

## 6. O que ainda falta

1. Rodar o `.bat` v1.1 na base completa (no computador) e revisar `05_MAPA_CENARIOS_FISCAIS` e `11_PENDENCIAS_VALIDACAO`.
2. Validar regra por regra com a contabilidade (seção 8) e registrar no CSV de regras.
3. Custo de referência para transferências (ligar a transferência à compra original por EAN/lote/data).
4. Política para bonificação, brinde e devolução no custo médio.
5. Biblioteca: completar os cenários não encontrados.

## 7. Dados externos realmente necessários

| Dado | Por quê | Prioridade |
|---|---|---|
| Cadastro oficial dos CNPJs das lojas (`config\REDE_CNPJS.csv`) | Hoje inferido pelas pastas de loja (INFERENCIA). | Alta |
| Guias de ICMS antecipação / ST / carga média pagas pela loja em MT | Não aparecem na NF-e do fornecedor e alteram o custo, principalmente em compras interestaduais. | Alta |
| Frete pago à parte (CT-e) | Custo de aquisição fora da nota. | Média |
| Verbas, bonificações e descontos fora da nota | Condição comercial que reduz o custo. | Média |
| Regime LR/LP do fornecedor CRT 3 | HIPOTESE: não altera o crédito da farmácia em Lucro Real; buscar só se a contabilidade exigir. | Baixa |

## 8. Pontos que dependem de validação fiscal/contábil

1. Crédito de ICMS próprio por cenário (regime da loja, produtos com ST/antecipação em MT, estornos).
2. Lista de produtos monofásicos / alíquota zero por NCM (PIS/COFINS), independente do CST do fornecedor.
3. Base do crédito de PIS/COFINS: exclusão do ICMS destacado; inclusão ou não de IPI, ST e frete.
4. Crédito em compras de fornecedor do Simples (ICMS via vCredICMSSN; PIS/COFINS conforme o produto).
5. IBS/CBS em 2026 (fase de teste): fora do custo, sem crédito efetivo.
6. Bonificação/brinde: custo zero ou valor da nota; efeito no custo médio.
7. Transferências: custo de origem e eventual crédito/débito de ICMS.
8. IPI: confirmar que nenhuma loja é equiparada a industrial (IPI integra o custo).
9. Notas com BC ST informada e ST zero: responsabilidade de recolhimento na entrada.
