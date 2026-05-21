@echo off
echo Este script precisa ser executado como Administrador.
echo Ele libera a porta TCP 8765 somente no perfil de rede privada do Windows.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "New-NetFirewallRule -DisplayName 'Controle Remoto LAN Host' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -Profile Private"
pause
