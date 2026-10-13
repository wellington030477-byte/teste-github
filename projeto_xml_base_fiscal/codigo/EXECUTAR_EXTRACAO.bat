@echo off
REM ==========================================================================
REM  PROJETO XML - BASE FISCAL PARA PRECIFICACAO
REM  Executa o extrator (somente leitura dos XMLs) e grava uma nova pasta
REM  EXEC_AAAAMMDD_HHMMSS a cada execucao (nunca sobrescreve execucoes antigas).
REM ==========================================================================
chcp 65001 >nul

set "ORIGEM=T:\Meu Drive\TRABALHO FARMACIA\BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO\BASE_XML"
set "PROJETO=%ORIGEM%\PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS"
set "SAIDA=%PROJETO%\02_BASE_PROCESSADA\BASE_FISCAL"

if not exist "%ORIGEM%" (
  echo ERRO: pasta de origem nao encontrada: "%ORIGEM%"
  echo Verifique se o Google Drive para computador esta aberto e a unidade T: montada.
  pause
  exit /b 2
)

python --version >nul 2>&1 || (
  echo ERRO: Python nao encontrado. Instale Python 3.9+ ^(marcar "Add python.exe to PATH"^).
  pause
  exit /b 3
)

python -c "import openpyxl" >nul 2>&1 || (
  echo Instalando openpyxl ^(necessario para gerar o .xlsx^)...
  python -m pip install --user openpyxl
)

python "%~dp0extrator_base_fiscal_xml.py" --origem "%ORIGEM%" --saida "%SAIDA%" --excluir "PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS" --excluir "PROJETO_XML"

echo.
echo Concluido. Resultados em: "%SAIDA%"
pause
