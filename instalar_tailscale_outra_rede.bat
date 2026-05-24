@echo off
setlocal
echo Controle Remoto LAN - acesso por outra rede Wi-Fi
echo ==================================================
echo.
echo Este script instala o Tailscale. Rode nos DOIS computadores.
echo Depois faca login na mesma conta Tailscale nos dois.
echo.

where winget >nul 2>nul
if errorlevel 1 (
  echo Nao encontrei o winget neste Windows.
  echo Instale o Tailscale manualmente em https://tailscale.com/download/windows
  pause
  exit /b 1
)

winget install --id Tailscale.Tailscale -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo.
  echo Nao consegui instalar automaticamente.
  echo Instale manualmente em https://tailscale.com/download/windows
  pause
  exit /b 1
)

echo.
echo Se o Tailscale nao abrir sozinho, abra pelo Menu Iniciar e faca login.
if exist "%ProgramFiles%\Tailscale\tailscale-ipn.exe" (
  start "" "%ProgramFiles%\Tailscale\tailscale-ipn.exe"
)
pause
