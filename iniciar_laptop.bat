@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv_laptop\Scripts\python.exe" (
  call instalar_laptop.bat
)

".venv_laptop\Scripts\pythonw.exe" remote_laptop.py
