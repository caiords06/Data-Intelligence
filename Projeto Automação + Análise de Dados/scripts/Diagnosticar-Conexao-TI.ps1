param(
    [Parameter(Mandatory=$true)][string]$ServerUrl
)

$ErrorActionPreference = "Stop"
try {
    $uri = [Uri]$ServerUrl
} catch {
    throw "ServerUrl inválida: $ServerUrl"
}
$porta = if ($uri.IsDefaultPort) { if ($uri.Scheme -eq "https") { 443 } else { 80 } } else { $uri.Port }
Write-Host "Destino: $($uri.Host):$porta"
$tcp = Test-NetConnection -ComputerName $uri.Host -Port $porta -WarningAction SilentlyContinue
Write-Host "TCP: $($tcp.TcpTestSucceeded)"
if (-not $tcp.TcpTestSucceeded) {
    throw "Não foi possível alcançar a Central. Verifique IP, perfil de rede, firewall e se o software da Central está aberto."
}
$health = "$($uri.Scheme)://$($uri.Authority)/api/v1/ti/health"
Write-Host "Health: $health"
try {
    $resposta = Invoke-RestMethod -Uri $health -Method Get -TimeoutSec 8
    $resposta | ConvertTo-Json -Depth 4
} catch {
    throw "A porta respondeu, mas a API não respondeu corretamente: $($_.Exception.Message)"
}
