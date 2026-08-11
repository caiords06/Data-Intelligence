param(
    [Parameter(Mandatory=$true)][string]$ServerUrl,
    [switch]$AllowPrivateHttp
)
$ErrorActionPreference="Stop"
$DataDir=Join-Path $env:PROGRAMDATA "DataIntelligence\Platform"
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
if ($ServerUrl.EndsWith('/')) { $ServerUrl=$ServerUrl.TrimEnd('/') }
$cfg=@{
  papel="cliente"; servidor_url=$ServerUrl;
  permitir_http_privado=[bool]$AllowPrivateHttp;
  sincronizar_backups=$false; sincronizar_exportacoes=$true;
  intervalo_backup_minutos=30
} | ConvertTo-Json
Set-Content -Path (Join-Path $DataDir "node.json") -Value $cfg -Encoding UTF8
Write-Host "Estação Cliente configurada para $ServerUrl" -ForegroundColor Green
Write-Host "Nesta estação o primeiro administrador e a criação de usuários ficam desabilitados." -ForegroundColor Yellow
