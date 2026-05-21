@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv_host\Scripts\python.exe" (
  call instalar_host.bat
)

".venv_host\Scripts\python.exe" remote_host.py --high-quality
echo.
echo Qualidade alta aplicada. Feche e abra o Host novamente se ele ja estiver rodando.
pause
