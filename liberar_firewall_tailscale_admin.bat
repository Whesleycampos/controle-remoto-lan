@echo off
echo Este script precisa ser executado como Administrador.
echo Ele libera as portas TCP 8765 e 8767 somente para IPs Tailscale 100.64.0.0/10.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$name='Controle Remoto LAN Host - Tailscale'; Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule; New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765,8767 -RemoteAddress 100.64.0.0/10 -Profile Any"
pause
