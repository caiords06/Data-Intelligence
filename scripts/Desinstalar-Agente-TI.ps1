param([switch]$RemoverDados)
$ErrorActionPreference = "Stop"
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Execute como Administrador."
}
$Exe = Join-Path $env:ProgramFiles "DataIntelligence\TIAgent\DataIntelligenceTIAgent.exe"
if (Test-Path $Exe) { & $Exe uninstall }
Remove-Item (Split-Path $Exe -Parent) -Recurse -Force -ErrorAction SilentlyContinue
if ($RemoverDados) {
    Remove-Item (Join-Path $env:PROGRAMDATA "DataIntelligence\TIAgent") -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "Agente removido."
