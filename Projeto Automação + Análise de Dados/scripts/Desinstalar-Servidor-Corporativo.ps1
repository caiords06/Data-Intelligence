param([switch]$PurgeData)
$ErrorActionPreference="Stop"
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Execute como Administrador."
}
$Exe = Join-Path $env:ProgramFiles "Data Intelligence\Server\DataIntelligenceServer.exe"
if (Test-Path $Exe) {
    & $Exe uninstall-task
    if ($LASTEXITCODE -ne 0) { Write-Warning "A tarefa do servidor não pôde ser removida pelo executável." }
}
Get-NetFirewallRule -DisplayName "Data Intelligence - Corporate Server" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:ProgramFiles "Data Intelligence\Server") -Recurse -Force -ErrorAction SilentlyContinue
if ($PurgeData) {
    Remove-Item (Join-Path $env:PROGRAMDATA "DataIntelligence\Server") -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "Servidor removido. Dados preservados: $(-not $PurgeData)"
