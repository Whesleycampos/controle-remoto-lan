@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv_host\Scripts\python.exe" (
  echo Ambiente do Host nao encontrado.
  echo Rode instalar_host.bat primeiro.
  if /I not "%~1"=="/quiet" pause
  exit /b 1
)

".venv_host\Scripts\python.exe" remote_host.py --easy-access
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0registrar_host_automatico.ps1"
if errorlevel 1 (
  echo.
  echo Nao consegui registrar o Host automatico.
  if /I not "%~1"=="/quiet" pause
  exit /b 1
)

echo.
echo Acesso remoto sempre ligado foi ativado.
echo Quando este usuario entrar no Windows, o Host abre sozinho em segundo plano.
echo A senha continua sendo: controle
if /I not "%~1"=="/quiet" pause
