$ErrorActionPreference = "Stop"

$repoZip = "https://github.com/Whesleycampos/controle-remoto-lan/archive/refs/heads/main.zip"
$desktop = [Environment]::GetFolderPath("Desktop")
$target = Join-Path $desktop "controle-remoto-lan"
$tempRoot = Join-Path $env:TEMP ("controle-remoto-lan-" + [guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $env:TEMP "controle-remoto-lan.zip"

Write-Host "Baixando Controle Remoto LAN..."
Invoke-WebRequest -Uri $repoZip -OutFile $zipPath

Write-Host "Extraindo..."
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
Expand-Archive -Path $zipPath -DestinationPath $tempRoot -Force

$source = Join-Path $tempRoot "controle-remoto-lan-main"
if (Test-Path $target) {
  Remove-Item -LiteralPath $target -Recurse -Force
}
Move-Item -LiteralPath $source -Destination $target

Write-Host "Instalando no laptop..."
Start-Process -FilePath (Join-Path $target "instalar_laptop.bat") -WorkingDirectory $target -Wait

Write-Host "Abrindo o Controle Remoto LAN..."
Start-Process -FilePath (Join-Path $target "iniciar_laptop.bat") -WorkingDirectory $target
