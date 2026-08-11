param(
    [Parameter(Mandatory=$true)][string]$ServerUrl,
    [switch]$AllowPrivateHttp
)
$ErrorActionPreference="Stop"
$DataDir=Join-Path $env:PROGRAMDATA "DataIntelligence\Platform"
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
if ($ServerUrl.EndsWith('/')) { $ServerUrl=$ServerUrl.TrimEnd('/') }
$cfg=@{
  papel="central"; servidor_url=$ServerUrl;
  permitir_http_privado=[bool]$AllowPrivateHttp;
  sincronizar_backups=$true; sincronizar_exportacoes=$true;
  intervalo_backup_minutos=15
} | ConvertTo-Json
Set-Content -Path (Join-Path $DataDir "node.json") -Value $cfg -Encoding UTF8
Write-Host "Estação Central configurada para $ServerUrl" -ForegroundColor Green
