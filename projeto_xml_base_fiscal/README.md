# PROJETO XML: BASE FISCAL PARA PRECIFICACAO

Base de amostras fiscais **rastreável e auditável**, extraída exclusivamente dos XMLs de NF-e,
com separação rigorosa entre **dado original**, **classificação documental** e **interpretação fiscal (pendente)**.

> Fase atual: MAPEAR, INVENTARIAR, INSPECIONAR, EXTRAIR, CLASSIFICAR DOCUMENTALMENTE, AMOSTRAR, VALIDAR e DOCUMENTAR.
> Esta fase **não** define tributação final, preço, margem nem mark-up.

## Estrutura

```
projeto_xml_base_fiscal/
  codigo/
    extrator_base_fiscal_xml.py      extrator reproduzível (somente leitura dos XMLs)
    EXECUTAR_EXTRACAO.bat            execução no Windows (caminhos T:\ já configurados)
    testes/teste_extrator_sintetico.py  teste automatizado com XMLs fictícios (30 checagens)
  docs/
    RELATORIO_EXECUCAO_FASE1.md      relatório desta execução (confirmado x classificado x pendente)
    REGRAS_CLASSIFICACAO.md          regras documentais, alertas e indícios usados pelo extrator
    POWER_QUERY_IMPORTACAO.pq        importação no Excel preservando identificadores como texto
```

## Onde fica no Drive (integração com o projeto existente)

Já existe em `BASE_XML` a estrutura **PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS** (criada em 10/10/2026).
Para não criar estrutura paralela, esta fase usa essa estrutura:

| Conteúdo | Pasta do projeto mestre |
|---|---|
| Código (`.py`, `.bat`) | `11_SCRIPTS_AUTOMACAO\BASE_FISCAL` |
| Saídas de cada execução | `02_BASE_PROCESSADA\BASE_FISCAL\EXEC_AAAAMMDD_HHMMSS` |
| Documentação | `01_DOCUMENTACAO` |
| Evidências de teste | `12_TESTES_VALIDACAO` |

A pasta do projeto mestre é **excluída da varredura** para que saídas nunca sejam lidas como origem.

## Como executar (Windows)

1. Instalar Python 3.9+ (marcar *Add python.exe to PATH*).
2. Copiar `extrator_base_fiscal_xml.py` e `EXECUTAR_EXTRACAO.bat` para a mesma pasta.
3. Dar duplo clique em `EXECUTAR_EXTRACAO.bat`.
4. Resultado: nova pasta `EXEC_AAAAMMDD_HHMMSS` com `BASE_FISCAL_XML.xlsx` + CSVs + `EXECUCAO.json`.

Linha de comando equivalente:

```
python extrator_base_fiscal_xml.py --origem "T:\Meu Drive\TRABALHO FARMACIA\BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO\BASE_XML" --saida "T:\Meu Drive\TRABALHO FARMACIA\BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO\BASE_XML\PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS\02_BASE_PROCESSADA\BASE_FISCAL" --excluir "PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS"
```

Arquivo `.rar`: sem a biblioteca `rarfile` + `UnRAR`/7-Zip no PATH, o RAR é **inventariado como
`COMPACTADO_NAO_PROCESSADO`** (não é ignorado em silêncio). `.zip` é lido em memória, sem extrair.

## Saídas

| Arquivo/aba | Conteúdo |
|---|---|
| `01_INVENTARIO_XML` | 1 linha por arquivo: caminho, tamanho, data, SHA-256, tipo, chave, DV, status, duplicidade, erro. Colunas compatíveis com `CONTROLE_XML_MASTER > ARQUIVOS`. |
| `02_BASE_ITENS_XML` | 1 linha por **XML + nota + item**. 245 colunas: rastreabilidade, cabeçalho, produto, ICMS (todos os campos do grupo + tag de origem), DIFAL, IPI, II, PIS, COFINS, IBS/CBS/IS, totais, calculados de checagem, classificação documental, alertas, indícios. |
| `02B_TAGS_ITEM_LONGA` (CSV) | 1 linha por **tag folha** de cada item, valor original como texto. Garante que nenhum campo do XML se perde, mesmo sem coluna própria. |
| `03_AMOSTRA_FISCAL` | Amostra representativa com `MOTIVO_SELECAO`. |
| `04_DIVERGENCIAS_PRODUTOS` | Mesmo EAN com valores diferentes (NCM, CEST, CFOP, CST, CSOSN, grupos, alíquotas, MVA, IBS/CBS etc.), indicando se diverge dentro do mesmo fornecedor e só entre compras de terceiros. Nada é corrigido. |
| `05_MAPA_CENARIOS_FISCAIS` | Combinações ICMS + ST + PIS + COFINS + IPI + IBS/CBS observadas, com volumes, CFOPs, origens, NCMs e quantidade de amostras. |
| `05B_GRUPOS_TAGS_OBSERVADOS` | Grupos e tags fiscais **realmente presentes** nos XMLs (inspeção de layout). |
| `06_LOG_VALIDACAO` | Checagens quantitativas, estruturais e de amostragem (OK / ATENCAO / ERRO). |
| `06B_LOG_ERROS` | Arquivo, etapa, erro, causa provável, impacto, ação tomada. |
| `07_DICIONARIO_CAMPOS` | Cada coluna: descrição, origem, tag XML, tipo, exemplo real, se é original/calculado/classificação/interpretação, fórmula. |
| `EXECUCAO.json` | Versão do extrator, parâmetros, contagens (para a aba `EXECUCOES` do controle mestre). |

## Três camadas (nunca misturadas)

| Camada | Colunas | Natureza |
|---|---|---|
| A. Dado original | nomes diretos (`ICMS_CST`, `PIS_GRUPO_TAG`, `NCM`...) | Valor do XML, sem transformação. Ausente = vazio. |
| B. Classificação documental | `CLASS_DOC_*`, `FLAG_*`, `CENARIO_FISCAL_*`, `ALERTAS_DOCUMENTAIS` | Organização do que o documento mostra. Não é conclusão fiscal. |
| C. Interpretação fiscal | `INDICIO_PARA_VALIDACAO`, `STATUS_VALIDACAO_FISCAL` | Hipóteses. `STATUS_VALIDACAO_FISCAL = PENDENTE` em 100% dos registros nesta fase. |

## Garantias implementadas

- XMLs abertos só em leitura binária; teste automatizado compara SHA-256 antes/depois.
- Identificadores gravados como texto (XLSX com formato `@`; CSV UTF-8 com BOM e `;`).
- Duplicidade por hash e por chave: o canônico é escolhido de forma determinística
  (nfeProc com protocolo, arquivo solto antes de compactado, caminho mais curto). Os demais ficam no inventário com `DUPLICADO_DE`.
- Evento de cancelamento (110111) marca a nota (`EVENTO_CANCELAMENTO_ENCONTRADO = S`); a nota **não** é removida.
- Conferência `itens extraídos = det do XML` por nota.
- Cada execução cria pasta nova: nenhuma saída anterior é sobrescrita.
- Streaming e baixo uso de memória (uma árvore XML por vez; tabela longa gravada direto em disco).

## Preparação para precificação (não implementado)

Chaves estáveis para futuros vínculos: `ID_REGISTRO` (chave + item), `EAN_CHAVE_VINCULO`, `EMIT_CNPJ`,
`DEST_CNPJ`/`ARQ_PASTA_LOJA_CNPJ`, `NCM`, `CFOP`, `CENARIO_FISCAL_ID`.
Tabelas futuras previstas (a criar em fase própria, após validação fiscal):
`CUSTO_AQUISICAO` (vProd - vDesc + vFrete + vSeg + vOutro + ST + IPI, por item),
`REGRAS_FISCAIS_VALIDADAS` (por EAN/NCM/UF/regime, com fonte e data da validação),
`CONDICOES_COMERCIAIS` (verba, bonificação, prazo), `PRECOS_VENDA_E_CONCORRENCIA`, `REGRAS_POR_LOJA`.
