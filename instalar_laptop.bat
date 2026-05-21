@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
py -3 --version >nul 2>nul && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD python --version >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo Python nao encontrado.
  echo Instale o Python 3.10 ou superior em https://www.python.org/downloads/windows/
  echo Durante a instalacao, marque "Add python.exe to PATH".
  pause
  exit /b 1
)

echo Criando ambiente do laptop...
%PYTHON_CMD% -m venv ".venv_laptop"
if errorlevel 1 (
  echo Falha ao criar ambiente virtual.
  pause
  exit /b 1
)

".venv_laptop\Scripts\python.exe" -m pip install --upgrade pip
".venv_laptop\Scripts\python.exe" -m pip install -r requirements-laptop.txt
if errorlevel 1 (
  echo Falha ao instalar dependencias do laptop.
  pause
  exit /b 1
)

set "SHORTCUT_TARGET=%~dp0iniciar_laptop.bat"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path $desktop 'Controle Remoto LAN - Laptop.lnk')); $s.TargetPath=$env:SHORTCUT_TARGET; $s.WorkingDirectory=(Split-Path $env:SHORTCUT_TARGET); $s.IconLocation='shell32.dll,21'; $s.Save()"

echo.
echo Instalacao do laptop concluida.
echo Use o atalho "Controle Remoto LAN - Laptop" na Area de Trabalho.
pause
