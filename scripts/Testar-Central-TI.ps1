param(
    [string]$HostCentral = "127.0.0.1",
    [int]$Porta = 8765
)

$ErrorActionPreference = "Stop"
$Url = "http://${HostCentral}:${Porta}/api/v1/ti/health"
Write-Host "Testando TCP ${HostCentral}:${Porta}..."
$tcp = Test-NetConnection -ComputerName $HostCentral -Port $Porta -WarningAction SilentlyContinue
if (-not $tcp.TcpTestSucceeded) {
    throw "A porta TCP/$Porta não respondeu em $HostCentral. Confirme se a Central está aberta e se o firewall/rede estão corretos."
}
Write-Host "TCP OK. Consultando $Url ..."
$resposta = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 8
$resposta | ConvertTo-Json -Depth 4
