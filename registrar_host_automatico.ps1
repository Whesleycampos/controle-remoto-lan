$ErrorActionPreference = "Stop"

$taskName = "Controle Remoto LAN Host Sempre Ligado"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$watchdogScript = Join-Path $scriptDir "manter_host_ligado.ps1"
$startupShortcutName = "Controle Remoto LAN Host Sempre Ligado.lnk"
$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$watchdogArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdogScript`""

if (-not (Test-Path $watchdogScript)) {
  throw "Nao encontrei $watchdogScript"
}

function Start-Watchdog {
  Start-Process -FilePath $powershellExe `
    -ArgumentList $watchdogArgs `
    -WorkingDirectory $scriptDir `
    -WindowStyle Hidden
}

try {
  $action = New-ScheduledTaskAction `
    -Execute $powershellExe `
    -Argument $watchdogArgs

  $trigger = New-ScheduledTaskTrigger -AtLogOn
  $settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650)

  Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Mantem o Host do Controle Remoto LAN disponivel em segundo plano." `
    -Force | Out-Null

  Start-ScheduledTask -TaskName $taskName
  Write-Host "Host automatico ativado no Agendador do Windows: $taskName"
} catch {
  $startup = [Environment]::GetFolderPath("Startup")
  $shortcutPath = Join-Path $startup $startupShortcutName
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($shortcutPath)
  $shortcut.TargetPath = $powershellExe
  $shortcut.Arguments = $watchdogArgs
  $shortcut.WorkingDirectory = $scriptDir
  $shortcut.WindowStyle = 7
  $shortcut.Save()
  Start-Watchdog
  Write-Host "Host automatico ativado pela Inicializacao do usuario: $shortcutPath"
}
