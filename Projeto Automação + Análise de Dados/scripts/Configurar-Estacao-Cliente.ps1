param(
    [Parameter(Mandatory=$true)][string]$ServerUrl,
    [switch]$AllowPrivateHttp,
    [switch]$SkipHealthCheck
)
$ErrorActionPreference="Stop"

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $Encoding)
}

if ($ServerUrl.EndsWith('/')) { $ServerUrl=$ServerUrl.TrimEnd('/') }
if ($ServerUrl -notmatch '^https?://') { throw "Informe uma URL HTTP(S) válida." }
if (-not $SkipHealthCheck) {
    try {
        $Ready = Invoke-RestMethod -Uri "$ServerUrl/api/v1/health/ready" -Method Get -TimeoutSec 8
        if (-not $Ready.ok -or -not $Ready.pronto) { throw "Servidor respondeu, mas ainda não está pronto." }
    } catch {
        throw "Servidor Corporativo indisponível ou não pronto em $ServerUrl. Detalhe: $($_.Exception.Message)"
    }
}

$DataDir=Join-Path $env:PROGRAMDATA "DataIntelligence\Platform"
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
$cfg=@{
  papel="cliente"; servidor_url=$ServerUrl;
  permitir_http_privado=[bool]$AllowPrivateHttp;
  sincronizar_backups=$false; sincronizar_exportacoes=$true;
  intervalo_backup_minutos=30
} | ConvertTo-Json
Write-Utf8NoBom (Join-Path $DataDir "node.json") $cfg
Write-Host "Estação Cliente configurada para $ServerUrl" -ForegroundColor Green
Write-Host "Servidor validado e node.json gravado em UTF-8 sem BOM." -ForegroundColor Green
Write-Host "Nesta estação o primeiro administrador e a criação local de usuários ficam desabilitados." -ForegroundColor Yellow
