@echo off
setlocal
set "TS="
if exist "%ProgramFiles%\Tailscale\tailscale.exe" set "TS=%ProgramFiles%\Tailscale\tailscale.exe"
if not defined TS (
  for /f "delims=" %%T in ('where tailscale 2^>nul') do if not defined TS set "TS=%%T"
)

if not defined TS (
  echo Nao encontrei o Tailscale neste computador.
  echo Rode instalar_tailscale_outra_rede.bat primeiro.
  pause
  exit /b 1
)

echo Endereco do Host para usar em outra rede Wi-Fi:
echo.
set "FOUND="
for /f "delims=" %%A in ('"%TS%" ip -4 2^>nul') do (
  set "FOUND=1"
  echo http://%%A:8765
)
if not defined FOUND (
  echo Nao consegui obter o IP Tailscale.
  echo Abra o Tailscale, faca login e tente novamente.
)
echo.
pause
