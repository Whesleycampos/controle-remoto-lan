$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$python = Join-Path $scriptDir ".venv_host\Scripts\python.exe"
$hostScript = Join-Path $scriptDir "remote_host.py"
$outLog = Join-Path $scriptDir "host-output.log"
$errLog = Join-Path $scriptDir "host-error.log"
$pidPath = Join-Path $scriptDir "host.pid"

function Test-HostPortOpen {
  try {
    $listener = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -ne $listener
  } catch {
    return $false
  }
}

while ($true) {
  if (-not (Test-Path $python) -or -not (Test-Path $hostScript)) {
    Start-Sleep -Seconds 10
    continue
  }

  if (Test-HostPortOpen) {
    Start-Sleep -Seconds 10
    continue
  }

  try {
    $process = Start-Process -FilePath $python `
      -ArgumentList @("-u", "remote_host.py") `
      -WorkingDirectory $scriptDir `
      -WindowStyle Hidden `
      -RedirectStandardOutput $outLog `
      -RedirectStandardError $errLog `
      -PassThru
    Set-Content -Path $pidPath -Value $process.Id
    $process.WaitForExit()
  } catch {
    Add-Content -Path $errLog -Value ("[{0}] Watchdog: {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $_.Exception.Message)
    Start-Sleep -Seconds 5
  }
}
