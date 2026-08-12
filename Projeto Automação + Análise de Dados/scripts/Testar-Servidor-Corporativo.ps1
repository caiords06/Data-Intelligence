param([string]$ServerUrl="http://127.0.0.1:8770")
$ErrorActionPreference="Stop"
$ServerUrl=$ServerUrl.TrimEnd('/')
$r=Invoke-RestMethod -Uri "$ServerUrl/api/v1/health" -Method Get -TimeoutSec 8
$r | ConvertTo-Json -Depth 5
if (-not $r.ok) { throw "Servidor não retornou estado saudável." }
Write-Host "Servidor corporativo acessível em $ServerUrl" -ForegroundColor Green
