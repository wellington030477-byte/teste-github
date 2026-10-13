@echo off
REM ==========================================================================
REM  PROJETO XML - BASE FISCAL PARA PRECIFICACAO
REM  1) Baixa o extrator fixado no commit publicado (se ainda nao existir aqui)
REM  2) Confere o SHA-256 (nao executa se o arquivo for diferente)
REM  3) Executa a extracao (somente leitura dos XMLs)
REM ==========================================================================
chcp 65001 >nul
setlocal

set "COMMIT=a4d094e6efd71c968aa8dbd2aeb6120fc11fe7cc"
set "HASH_ESPERADO=08697A6C0619117B1C451CF3FBF5FF7A587EDA66603307190E1B682AA47F1483"
set "URL=https://raw.githubusercontent.com/wellington030477-byte/teste-github/%COMMIT%/projeto_xml_base_fiscal/codigo/extrator_base_fiscal_xml.py"
set "SCRIPT=%~dp0extrator_base_fiscal_xml.py"

set "ORIGEM=T:\Meu Drive\TRABALHO FARMACIA\BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO\BASE_XML"
set "PROJETO=%ORIGEM%\PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS"
set "SAIDA=%PROJETO%\02_BASE_PROCESSADA\BASE_FISCAL"

if not exist "%SCRIPT%" (
  echo Baixando extrator do commit %COMMIT% ...
  curl -sSL -o "%SCRIPT%" "%URL%" || (echo ERRO: falha no download. & pause & exit /b 4)
)

for /f %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%SCRIPT%').Hash"') do set "HASH_ATUAL=%%H"
if /I not "%HASH_ATUAL%"=="%HASH_ESPERADO%" (
  echo ERRO: SHA-256 do extrator nao confere.
  echo Esperado: %HASH_ESPERADO%
  echo Atual   : %HASH_ATUAL%
  echo Nada foi executado. Apague "%SCRIPT%" e rode novamente.
  pause
  exit /b 5
)
echo Extrator conferido (SHA-256 OK).

if not exist "%ORIGEM%" (
  echo ERRO: pasta de origem nao encontrada: "%ORIGEM%"
  echo Verifique se o Google Drive para computador esta aberto e a unidade T: montada.
  pause
  exit /b 2
)

python --version >nul 2>&1 || (
  echo ERRO: Python nao encontrado. Instale Python 3.9+ marcando "Add python.exe to PATH".
  pause
  exit /b 3
)

python -c "import openpyxl" >nul 2>&1 || (
  echo Instalando openpyxl ^(necessario para gerar o .xlsx^)...
  python -m pip install --user openpyxl
)

python "%SCRIPT%" --origem "%ORIGEM%" --saida "%SAIDA%" --excluir "PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS" --excluir "PROJETO_XML"

echo.
echo Concluido. Resultados em: "%SAIDA%"
pause
