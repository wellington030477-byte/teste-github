# PROJETO XML - INTELIGENCIA DE COMPRAS: BASE FISCAL E CUSTO FISCAL DE AQUISICAO

Base de amostras fiscais **rastreável e auditável**, extraída exclusivamente dos XMLs de NF-e,
com separação rigorosa entre **dado original**, **classificação documental** e **interpretação fiscal (pendente)**.

> Fase 1 (concluída): base fiscal por item (extrator v1.1.0).
> Fase 2 (em andamento): **motor de custo fiscal de aquisição** para farmácias em Lucro Real
> (`docs/MOTOR_CUSTO_FISCAL.md`). Regras de crédito todas PENDENTES de validação contábil.
> Não define preço, margem nem mark-up. Estado e lacunas: `docs/INVENTARIO_E_GAP_CUSTO_FISCAL.md`.

## Estrutura

```
projeto_xml_base_fiscal/
  codigo/
    extrator_base_fiscal_xml.py      extrator reproduzível (somente leitura dos XMLs)
    motor_custo_fiscal.py            motor de custo fiscal (lê a base do extrator)
    config/REGRAS_CREDITO_LUCRO_REAL.csv  regras de crédito parametrizáveis (validação contábil)
    EXECUTAR_EXTRACAO.bat            extrator + motor a partir desta pasta
    INSTALAR_E_EXECUTAR.bat          baixa extrator e motor fixados em commit, confere SHA-256 e executa
    testes/teste_extrator_sintetico.py  XMLs fictícios (30 checagens)
    testes/teste_motor_sintetico.py     XMLs fictícios (22 checagens)
    testes/teste_referencia_real.py     regressão sobre a biblioteca de XMLs reais do Drive
    testes/MODELO_EXPECTATIVAS.csv      formato das expectativas (as reais ficam no Drive)
  docs/
    INVENTARIO_E_GAP_CUSTO_FISCAL.md estado atual x objetivo de custo, dados externos, validações
    MOTOR_CUSTO_FISCAL.md            fórmula, camadas, regras, ajustes e saídas do motor
    RELATORIO_EXECUCAO_FASE1.md      relatório desta execução (confirmado x classificado x pendente)
    REGRAS_CLASSIFICACAO.md          regras documentais, alertas e indícios usados pelo extrator
    POWER_QUERY_IMPORTACAO.pq        importação no Excel preservando identificadores como texto
```

## Onde fica no Drive

Projeto: `PC_WORK\01_PROJETOS\PROJETO XML - INTELIGENCIA DE COMPRAS` (pasta existente movida, sem duplicar).
Origem dos XMLs (somente leitura, não é movida): `TRABALHO FARMACIA\BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO\BASE_XML`
(no Drive, `TRABALHO FARMACIA` está dentro de `PC_WORK`; o `.bat` testa os dois caminhos no T:).

| Conteúdo | Pasta do projeto |
|---|---|
| `.bat`, `config\` (regras, `REDE_CNPJS.csv`, `AJUSTES_EXTERNOS.csv`) | `11_SCRIPTS_AUTOMACAO\BASE_FISCAL` |
| Saídas | `02_BASE_PROCESSADA\BASE_FISCAL\EXEC_...\MOTOR_...` |
| Documentação | `01_DOCUMENTACAO` |
| Biblioteca de XMLs reais (cópias), manifesto e expectativas | `12_TESTES_VALIDACAO\BASE_FISCAL\XML_REFERENCIA_REAL` |

## Como executar (Windows)

1. Instalar Python 3.9+ (marcar *Add python.exe to PATH*).
2. Duplo clique em `11_SCRIPTS_AUTOMACAO\BASE_FISCAL\INSTALAR_E_EXECUTAR.bat` (v1.1). Ele baixa extrator e motor
   do commit fixado para `v1.1\`, confere o SHA-256 (não executa se divergir), baixa as regras para `config\`
   se ainda não existirem, roda o extrator e depois o motor.
3. BASE_XML em outro lugar: `INSTALAR_E_EXECUTAR.bat "caminho da BASE_XML"`.
4. Resultado: nova pasta `EXEC_AAAAMMDD_HHMMSS` (base fiscal) com subpasta `MOTOR_AAAAMMDD_HHMMSS` (custo).

Linha de comando equivalente:

```
python extrator_base_fiscal_xml.py --origem "<BASE_XML>" --saida "<PROJETO>\02_BASE_PROCESSADA\BASE_FISCAL" --cnpjs-rede config\REDE_CNPJS.csv
python motor_custo_fiscal.py --ultima-exec-em "<PROJETO>\02_BASE_PROCESSADA\BASE_FISCAL" --regras config\REGRAS_CREDITO_LUCRO_REAL.csv
```

Sem `--cnpjs-rede`, os CNPJs da rede são inferidos pelas pastas de loja (14 dígitos) da BASE_XML.

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
| `EXECUCAO.json` | Versão do extrator, parâmetros, CNPJs da rede usados, contagens (para a aba `EXECUCOES` do controle mestre). |
| `MOTOR_...\08` a `13` | Custo fiscal por item, composição em camadas, regras, pendências, fora do escopo, log (ver `docs/MOTOR_CUSTO_FISCAL.md`). |

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

## Próximas tabelas (não implementadas)

`CUSTO_REFERENCIA_TRANSFERENCIA` (liga transferência à compra original), `CONDICOES_COMERCIAIS`
(verba, bonificação, prazo), `PRECOS_VENDA_E_CONCORRENCIA`, `REGRAS_POR_LOJA`.
Preço de venda só depois das regras de custo validadas.
