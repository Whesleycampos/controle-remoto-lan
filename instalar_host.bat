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

echo Criando ambiente do Host...
%PYTHON_CMD% -m venv ".venv_host"
if errorlevel 1 (
  echo Falha ao criar ambiente virtual.
  pause
  exit /b 1
)

".venv_host\Scripts\python.exe" -m pip install --upgrade pip
".venv_host\Scripts\python.exe" -m pip install -r requirements-host.txt
if errorlevel 1 (
  echo Falha ao instalar dependencias do Host.
  pause
  exit /b 1
)

".venv_host\Scripts\python.exe" remote_host.py --easy-access

set "SHORTCUT_TARGET=%~dp0iniciar_host.bat"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path $desktop 'Controle Remoto LAN - Host.lnk')); $s.TargetPath=$env:SHORTCUT_TARGET; $s.WorkingDirectory=(Split-Path $env:SHORTCUT_TARGET); $s.IconLocation='shell32.dll,18'; $s.Save()"

call ativar_acesso_remoto_sempre.bat /quiet

echo.
echo Instalacao do Host concluida.
echo O Host foi configurado para iniciar sozinho com o Windows.
echo Use o atalho "Controle Remoto LAN - Host" na Area de Trabalho se quiser abrir manualmente.
echo Se o Windows Firewall perguntar, permita acesso em redes privadas.
pause
