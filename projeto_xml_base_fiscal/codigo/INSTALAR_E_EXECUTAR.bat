@echo off
REM ==========================================================================
REM  PROJETO XML - INTELIGENCIA DE COMPRAS : BASE FISCAL + MOTOR DE CUSTO (v1.1)
REM  1) Baixa extrator e motor fixados no COMMIT para a subpasta v1.1\
REM     e confere o SHA-256 a cada execucao.
REM  2) Baixa config\REGRAS_CREDITO_LUCRO_REAL.csv so se nao existir (arquivo
REM     editavel para validacao contabil; hash conferido apenas no download).
REM  3) Executa extrator e motor. Os XMLs da BASE_XML sao somente lidos.
REM     Cada execucao grava pastas novas EXEC_...\MOTOR_... (nunca sobrescreve).
REM  Opcionais em config\: REDE_CNPJS.csv e AJUSTES_EXTERNOS.csv
REM ==========================================================================
chcp 65001 >nul
setlocal

set "COMMIT=27a6fc7ae981a0d6190f3d728329101e57a93f4c"
set "RAW=https://raw.githubusercontent.com/wellington030477-byte/teste-github/%COMMIT%/projeto_xml_base_fiscal/codigo"
set "DIR=%~dp0v1.1\"
if not exist "%DIR%" mkdir "%DIR%"
if not exist "%~dp0config" mkdir "%~dp0config"

call :obter "v1.1\extrator_base_fiscal_xml.py" "extrator_base_fiscal_xml.py" "165CFFD6A895804348C269DBC5EB556BA85D55BF5DF799A1307517B059A764CF" SEMPRE || exit /b 5
call :obter "v1.1\motor_custo_fiscal.py" "motor_custo_fiscal.py" "79F3DC37C17046673CBDE3FFC988C2B455AE5CA23915C7F94EBE8635A31CA219" SEMPRE || exit /b 5
call :obter "config\REGRAS_CREDITO_LUCRO_REAL.csv" "config/REGRAS_CREDITO_LUCRO_REAL.csv" "FC8D5867D901078DD8A389BFD9391F1F2BABAEB78EB857F717164DAB14B733FD" SO_DOWNLOAD || exit /b 5
echo Scripts conferidos (SHA-256 OK).

set "BASE_REL=TRABALHO FARMACIA\BASE ARQUIVOS PARA PESQUISA CONSULTA VINCULO\BASE_XML"
set "PROJETO=T:\Meu Drive\PC_WORK\01_PROJETOS\PROJETO XML - INTELIGENCIA DE COMPRAS"

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
python "%DIR%motor_custo_fiscal.py" --ultima-exec-em "%SAIDA%" --regras "%~dp0config\REGRAS_CREDITO_LUCRO_REAL.csv" %AJ_ARG%
if errorlevel 1 (echo ERRO no motor de custo. & pause & exit /b 7)

echo.
echo Concluido. Resultados em: "%SAIDA%" ^(pasta EXEC_ mais recente e sua subpasta MOTOR_^)
pause
exit /b 0

:obter
REM %1 destino relativo a esta pasta  %2 caminho no repositorio  %3 SHA-256 esperado
REM %4 SEMPRE = confere sempre ; SO_DOWNLOAD = confere so ao baixar (arquivo editavel)
set "ARQ=%~dp0%~1"
set "BAIXOU="
if not exist "%ARQ%" (
  echo Baixando %~2 do commit %COMMIT% ...
  curl -sSL -o "%ARQ%" "%RAW%/%~2" || (echo ERRO: falha no download de %~2. & pause & exit /b 4)
  set "BAIXOU=1"
)
if /I "%~4"=="SO_DOWNLOAD" if not defined BAIXOU exit /b 0
set "HASH_ATUAL="
for /f %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%ARQ%').Hash"') do set "HASH_ATUAL=%%H"
if /I not "%HASH_ATUAL%"=="%~3" (
  echo ERRO: SHA-256 nao confere: %~1
  echo Esperado: %~3
  echo Atual   : %HASH_ATUAL%
  echo Nada foi executado. Apague "%ARQ%" e rode novamente.
  pause
  exit /b 5
)
exit /b 0
