@echo off
echo Desativando acesso remoto sempre ligado...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$taskName='Controle Remoto LAN Host Sempre Ligado'; Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue; $shortcut=Join-Path ([Environment]::GetFolderPath('Startup')) 'Controle Remoto LAN Host Sempre Ligado.lnk'; Remove-Item -LiteralPath $shortcut -Force -ErrorAction SilentlyContinue; Get-CimInstance Win32_Process -Filter \"name='powershell.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*manter_host_ligado.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-NetTCPConnection -LocalPort 8765,8767 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
echo.
echo Desativado.
pause
