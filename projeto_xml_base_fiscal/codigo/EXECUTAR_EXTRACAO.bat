@echo off
REM ==========================================================================
REM  PROJETO XML - INTELIGENCIA DE COMPRAS : BASE FISCAL + MOTOR DE CUSTO
REM  Versao para rodar a partir de uma copia do repositorio (pasta codigo).
REM  Os XMLs da BASE_XML sao somente lidos. Cada execucao grava pastas novas
REM  EXEC_AAAAMMDD_HHMMSS\MOTOR_AAAAMMDD_HHMMSS (nunca sobrescreve).
REM ==========================================================================
chcp 65001 >nul
setlocal
set "DIR=%~dp0"
set "BASE_REL=TRABALHO FARMACIA\BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO\BASE_XML"
REM PROJETO: pasta-avo deste .bat (...\PROJETO\11_SCRIPTS_AUTOMACAO\BASE_FISCAL); senao caminhos conhecidos
set "PROJETO="
for %%I in ("%~dp0..\..") do if exist "%%~fI\02_BASE_PROCESSADA" set "PROJETO=%%~fI"
if not defined PROJETO if exist "T:\Meu Drive\PC_WORK\01_PROJETOS\01_EM_DESENVOLVIMENTO\PROJETO XML - INTELIGENCIA DE COMPRAS" set "PROJETO=T:\Meu Drive\PC_WORK\01_PROJETOS\01_EM_DESENVOLVIMENTO\PROJETO XML - INTELIGENCIA DE COMPRAS"
if not defined PROJETO set "PROJETO=T:\Meu Drive\PC_WORK\01_PROJETOS\PROJETO XML - INTELIGENCIA DE COMPRAS"

REM BASE_XML: aceita caminho passado como 1o parametro; senao detecta os dois locais conhecidos
set "ORIGEM="
if not "%~1"=="" set "ORIGEM=%~1"
if not defined ORIGEM if exist "T:\Meu Drive\PC_WORK\%BASE_REL%" set "ORIGEM=T:\Meu Drive\PC_WORK\%BASE_REL%"
if not defined ORIGEM if exist "T:\Meu Drive\%BASE_REL%" set "ORIGEM=T:\Meu Drive\%BASE_REL%"
if not defined ORIGEM (
  echo ERRO: BASE_XML nao encontrada. Locais verificados:
  echo   "T:\Meu Drive\PC_WORK\%BASE_REL%"
  echo   "T:\Meu Drive\%BASE_REL%"
  echo Abra o Google Drive para computador ou rode: %~nx0 "caminho da BASE_XML"
  pause
  exit /b 2
)
if not exist "%ORIGEM%" (echo ERRO: pasta nao encontrada: "%ORIGEM%" & pause & exit /b 2)
if not exist "%PROJETO%" (
  echo ERRO: pasta do projeto nao encontrada: "%PROJETO%"
  pause
  exit /b 2
)
set "SAIDA=%PROJETO%\02_BASE_PROCESSADA\BASE_FISCAL"
echo Projeto                   : "%PROJETO%"
echo BASE_XML (somente leitura): "%ORIGEM%"
echo Saida                     : "%SAIDA%"

python --version >nul 2>&1 || (
  echo ERRO: Python nao encontrado. Instale Python 3.9+ marcando "Add python.exe to PATH".
  pause
  exit /b 3
)
python -c "import openpyxl" >nul 2>&1 || (
  echo Instalando openpyxl ^(necessario para gerar o .xlsx^)...
  python -m pip install --user openpyxl
)

REM Cadastro de CNPJs da rede (opcional). Sem ele, o extrator infere pelas pastas de loja.
set "REDE_ARG="
if exist "%~dp0config\REDE_CNPJS.csv" set "REDE_ARG=--cnpjs-rede "%~dp0config\REDE_CNPJS.csv""
if not defined REDE_ARG echo AVISO: config\REDE_CNPJS.csv nao encontrado - CNPJs da rede serao inferidos pelas pastas.

python "%DIR%extrator_base_fiscal_xml.py" --origem "%ORIGEM%" --saida "%SAIDA%" %REDE_ARG% --excluir "PROJETO MESTRE XML - INTELIGENCIA DE COMPRAS" --excluir "PROJETO_XML"
if errorlevel 1 (echo ERRO na extracao. Motor nao executado. & pause & exit /b 6)

REM Motor de custo fiscal sobre a EXEC mais recente (regras em config\, ajustes externos opcionais)
set "AJ_ARG="
if exist "%~dp0config\AJUSTES_EXTERNOS.csv" set "AJ_ARG=--ajustes "%~dp0config\AJUSTES_EXTERNOS.csv""
python "%DIR%motor_custo_fiscal.py" --ultima-exec-em "%SAIDA%" --regras "%DIR%config\REGRAS_CREDITO_LUCRO_REAL.csv" %AJ_ARG%
if errorlevel 1 (echo ERRO no motor de custo. & pause & exit /b 7)

echo.
echo Concluido. Resultados em: "%SAIDA%" ^(pasta EXEC_ mais recente e sua subpasta MOTOR_^)
pause
