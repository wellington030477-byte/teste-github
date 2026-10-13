# RELATORIO FASE 1: BASE FISCAL A PARTIR DOS XMLs

Data: 13/10/2026. Versão do extrator: 1.0.0.
Este relatório no repositório (público) **não contém dados reais de notas** (CNPJ de lojas, preços, chaves).
O detalhamento com dados reais está no Drive: `PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS\12_TESTES_VALIDACAO\BASE_FISCAL`.

## 1. Acesso à origem

| Item | Situação |
|---|---|
| Caminho `T:\Meu Drive\...\BASE_XML` | Não acessível no ambiente de nuvem (unidade `T:` é local do Windows). |
| Mesma pasta via conector Google Drive | **Acessada**: `TRABALHO FARMACIA > BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO > BASE_XML`. |
| Pasta homônima | Existe outra `BASE_XML` em `PC_FARMA_DESCKTOP\BASE ARQUIVOS...` (criada 13/10/2026). **Fora do caminho oficial; não usada.** |
| Projeto existente | `PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS` (00_CONTROLE ... 12_TESTES_VALIDACAO) com README e `CONTROLE_XML_MASTER`. **Reaproveitado, sem recriar.** |

Estrutura observada na origem oficial (mapeamento parcial pelo conector):

```
BASE_XML
  XMLS_23042026_22062026\<CNPJ loja>\NFe\Compras|Entradas|Saidas\*.xml
  xml\XMLS_23082026_30082026\
      XMLS_01062026_20082026\<CNPJ loja>\NFe\Compras|Entradas|Saidas\*.xml
      <CNPJ loja>\NFe\Saidas
      XMLS_01062026_20082026.rar   (~99 MB; provável cópia compactada da pasta acima)
  PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS\   (projeto; excluído da varredura)
```

Uma única pasta `Compras` (1 loja, 1 período) tem mais de 100 XMLs. O volume total não foi contado remotamente:
o conector lista pastas 5 por vez, o que tornaria o inventário remoto completo inviável. **O inventário completo é gerado
pelo script ao rodar no T:** (`01_INVENTARIO_XML`).

## 2. O que foi executado

1. Mapeamento da árvore oficial e do projeto existente no Drive.
2. Download de 4 XMLs reais de fornecedores/estruturas diferentes (3 conferidos byte a byte com o tamanho do Drive;
   1 cópia de teste sem o certificado X509 da assinatura, sem impacto nos dados fiscais). Originais não tocados.
3. Desenvolvimento do extrator reproduzível (`codigo/extrator_base_fiscal_xml.py`).
4. Execução sobre os 4 XMLs reais em espelho da estrutura de pastas: hashes SHA-256 iguais antes/depois.
5. Teste automatizado com XMLs sintéticos (30 checagens, todas aprovadas).
6. Teste de carga: 5.000 notas / 150.000 itens em 4,2 min com pico de 597 MB de RAM.

## 3. Estrutura encontrada nos XMLs reais (amostra de 4 notas, 7 itens)

Confirmado nos arquivos:

- Layout 4.00 com o **grupo `IBSCBS` (reforma tributária)** em 3 das 4 notas: CST 000 / cClassTrib 000001 e CST 200 / cClassTrib 200032,
  com `gRed` (redução de alíquota) em UF e Município. Também a tag `vItem` por item.
- ICMS: `ICMS10` (6 itens) e `ICMS60` (1 item).
- PIS/COFINS: `PISAliq/COFINSAliq` CST 01, `PISNT/COFINSNT` CST 04, `PISOutr/COFINSOutr` CST 49.
- IPI: `IPINT` CST 51 com `cEnq` 999 (4 itens); ausente nos demais.
- Medicamentos: `med/cProdANVISA`, `vPMC` e `rastro` (lote, fabricação, validade).
- `infAdProd` com PMC/PMPF/repasse e FCI; `obsCont`; `nFCI`; `xPed`/`nItemPed`.
- Pastas `Entradas`/`Saidas` contêm **transferências entre lojas** (mesma raiz de CNPJ, série 8, CFOP 5409).

## 4. Achados na amostra real

| Tipo | Achado |
|---|---|
| ATÍPICO | Item de medicamento com `ICMS10`, `vBCST` informado e `vICMSST = 0,00` (alerta `BC_ST_INFORMADA_COM_VICMSST_ZERO`). |
| ATÍPICO | Transferência com `ICMS60` sem valores de ST retido (`vBCSTRet` e `vICMSSTRet` zerados). |
| CLASSIFICADO | 4 cenários fiscais distintos em 7 itens. |
| DIVERGÊNCIA | Nenhuma: os 7 itens têm EANs diferentes (esperado em amostra tão pequena). |

## 5. Pendente de validação fiscal (não concluído)

- Enquadramento monofásico dos itens com PIS/COFINS CST 04 (indício apenas).
- Regra de ST aplicável por NCM/CEST/UF, inclusive o caso de vICMSST zero.
- Tratamento de PIS/COFINS CST 49 nas transferências internas.
- Efeito do IBS/CBS (fase de transição) no custo.

## 6. Limitações

- Base completa não processada nesta sessão: o extrator precisa rodar no PC com acesso ao `T:`.
- `.rar` exige `rarfile` + UnRAR/7-Zip; sem isso fica no inventário como `COMPACTADO_NAO_PROCESSADO`.
  A pasta extraída de mesmo nome provavelmente cobre o conteúdo; a deduplicação por chave evita contar duas vezes.
- A amostra de 4 XMLs não cobre Simples Nacional, ICMS00/20/40/51/70/90, PIS 06, IPI com valor nem DIFAL.
  Esses casos foram validados só com XMLs sintéticos.
