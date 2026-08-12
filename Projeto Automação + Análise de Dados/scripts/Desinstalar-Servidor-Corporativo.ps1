param([switch]$PurgeData)
$ErrorActionPreference="SilentlyContinue"
Stop-ScheduledTask -TaskName "DataIntelligenceCorporateServer"
Unregister-ScheduledTask -TaskName "DataIntelligenceCorporateServer" -Confirm:$false
Get-NetFirewallRule -DisplayName "Data Intelligence - Corporate Server" | Remove-NetFirewallRule
Remove-Item (Join-Path $env:ProgramFiles "DataIntelligence\Server") -Recurse -Force
if ($PurgeData) { Remove-Item (Join-Path $env:PROGRAMDATA "DataIntelligence\Server") -Recurse -Force }
Write-Host "Servidor removido. Dados preservados: $(-not $PurgeData)"
