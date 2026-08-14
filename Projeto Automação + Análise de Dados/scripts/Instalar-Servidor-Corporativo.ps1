param(
    [int]$Porta=8770,
    [string]$PostgresHost="127.0.0.1",
    [int]$PostgresPorta=5432,
    [string]$PostgresBanco="dataintelligence",
    [string]$PostgresUsuario="dataintelligence",
    [ValidateSet("disable","allow","prefer","require","verify-ca","verify-full")][string]$PostgresSslMode="prefer",
    [switch]$PermitirHttpLan
)
$ErrorActionPreference="Stop"

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $Encoding)
}

$identidade=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]$identidade
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw "Execute como Administrador." }
if ($Porta -lt 1024 -or $Porta -gt 65535) { throw "Porta inválida." }
if ($PermitirHttpLan) { throw "HTTP na LAN foi desativado na V11.1. Publique o loopback por proxy reverso HTTPS." }

$Origem=Join-Path $PSScriptRoot "DataIntelligenceServer.exe"
if (-not (Test-Path $Origem)) { throw "DataIntelligenceServer.exe não está ao lado do instalador." }
# Upgrade seguro: encerra a tarefa antiga antes de substituir o executável.
Stop-ScheduledTask -TaskName "DataIntelligenceCorporateServer" -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800
$Destino=Join-Path $env:ProgramFiles "Data Intelligence\Server"
$DataDir=Join-Path $env:PROGRAMDATA "DataIntelligence\Server"
New-Item -ItemType Directory -Path $Destino,$DataDir -Force | Out-Null
$Exe=Join-Path $Destino "DataIntelligenceServer.exe"
Copy-Item $Origem $Exe -Force

# O configure-db grava server.json somente depois de validar a conexão e proteger
# a senha. Não criamos um JSON PostgreSQL parcial antes do segredo existir.

    $Secure = Read-Host "Senha do usuário PostgreSQL '$PostgresUsuario'" -AsSecureString
    $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try { $PgPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($BSTR) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR) }
    if ([string]::IsNullOrWhiteSpace($PgPassword)) { throw "Senha PostgreSQL vazia." }
    $PasswordPath=Join-Path $env:TEMP ("di-pg-password-"+[Guid]::NewGuid().ToString("N")+".txt")
    $BootstrapPath=Join-Path $env:TEMP ("di-pg-bootstrap-"+[Guid]::NewGuid().ToString("N")+".json")
    try {
        Write-Utf8NoBom $PasswordPath $PgPassword
        $ServerHost = "127.0.0.1"
        $ServerAmbiente = "producao"
        $bootstrap=@{
            backend="postgresql";
            server_host=$ServerHost; server_porta=$Porta; server_tls=$false;
            server_max_upload_mb=1024; server_ambiente=$ServerAmbiente;
            host=$PostgresHost; porta=$PostgresPorta; banco=$PostgresBanco;
            usuario=$PostgresUsuario; sslmode=$PostgresSslMode; pool_min=2; pool_max=12;
            password_file=$PasswordPath
        } | ConvertTo-Json
        Write-Utf8NoBom $BootstrapPath $bootstrap
        & $Exe configure-db --bootstrap-file $BootstrapPath
        if ($LASTEXITCODE -ne 0) {
            $ErrorPath=Join-Path $DataDir "install-db-error.log"
            if (Test-Path $ErrorPath) {
                $Detalhe=(Get-Content -LiteralPath $ErrorPath -Raw -ErrorAction SilentlyContinue).Trim()
                if ($Detalhe) { throw $Detalhe }
            }
            throw "Falha ao configurar o PostgreSQL. Confira host, porta, banco, usuário, senha e SSL mode."
        }

        $LegacyDb = Join-Path $DataDir "app.db"
        $MigrationMarker = Join-Path $DataDir "postgresql_migrated_v10_1.marker"
        if ((Test-Path $LegacyDb) -and -not (Test-Path $MigrationMarker)) {
            & $Exe migrate-sqlite --source $LegacyDb
            if ($LASTEXITCODE -ne 0) { throw "Falha ao migrar o SQLite legado para PostgreSQL. O app.db foi preservado." }
            Write-Utf8NoBom $MigrationMarker "V10.1 PostgreSQL migration completed"
        }
    } finally {
        Remove-Item $PasswordPath,$BootstrapPath -Force -ErrorAction SilentlyContinue
        $PgPassword=$null
    }

& $Exe init-admin
if ($LASTEXITCODE -ne 0) { throw "Falha ao inicializar/verificar administrador do servidor." }

# O próprio executável registra a tarefa sem cmd.exe, preservando caminhos com espaços.
& $Exe install-task --executable $Exe
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar a tarefa do Servidor Corporativo." }
try {
    & $Exe start-task
    if ($LASTEXITCODE -ne 0) { throw "Falha ao iniciar a tarefa do Servidor Corporativo." }

    & $Exe wait-ready --timeout 45
    if ($LASTEXITCODE -ne 0) { throw "Servidor instalado, mas não ficou pronto no prazo. Consulte $DataDir\server.log" }

    $Regra="Data Intelligence - Corporate Server"
    Get-NetFirewallRule -DisplayName $Regra -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
} catch {
    & $Exe uninstall-task | Out-Null
    throw
}

$ModoRede = "loopback seguro / publique somente por proxy reverso HTTPS"
Write-Host "Servidor instalado e pronto. Backend: PostgreSQL / Porta: $Porta / Modo: $ModoRede." -ForegroundColor Green
Write-Host "Dados persistentes: $DataDir"
