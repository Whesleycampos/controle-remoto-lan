@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv_host\Scripts\python.exe" (
  call instalar_host.bat
)

".venv_host\Scripts\python.exe" remote_host.py
pause
