$ErrorActionPreference = "Stop"
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Abra o PowerShell como Administrador."
}
$Regra = "Data Intelligence - TI Agent API"
Get-NetFirewallRule -DisplayName $Regra -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Write-Host "Regra do servidor TI removida."
