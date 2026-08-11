param(
    [Parameter(Mandatory=$true)][string]$ServerUrl,
    [Parameter(Mandatory=$true)][string]$Patrimonio,
    [Parameter(Mandatory=$true)][string]$AgentId,
    [ValidateSet("AnyDesk","TeamViewer","RustDesk")][string]$Provider = "AnyDesk",
    [switch]$AllowPrivateHttp
)

$ErrorActionPreference = "Stop"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Execute este instalador pelo PowerShell como Administrador."
}

$OrigemExe = Join-Path $PSScriptRoot "DataIntelligenceTIAgent.exe"
if (-not (Test-Path $OrigemExe)) {
    throw "Coloque DataIntelligenceTIAgent.exe na mesma pasta deste script."
}

$InstallDir = Join-Path $env:ProgramFiles "DataIntelligence\TIAgent"
$DestinoExe = Join-Path $InstallDir "DataIntelligenceTIAgent.exe"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item $OrigemExe $DestinoExe -Force

$Secure = Read-Host "Cole o token exibido pela Central de Tecnologia" -AsSecureString
$BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
try {
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($BSTR)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
}
if ([string]::IsNullOrWhiteSpace($Token) -or $Token.Length -lt 24) {
    throw "Token inválido."
}

$env:DATA_TI_AGENT_TOKEN = $Token
try {
    $Args = @(
        "configure",
        "--server-url", $ServerUrl,
        "--patrimonio", $Patrimonio,
        "--agent-id", $AgentId,
        "--provider", $Provider
    )
    if ($AllowPrivateHttp) { $Args += "--allow-private-http" }
    & $DestinoExe @Args
    if ($LASTEXITCODE -ne 0) { throw "Falha ao configurar o agente." }
} finally {
    Remove-Item Env:DATA_TI_AGENT_TOKEN -ErrorAction SilentlyContinue
    $Token = $null
}

Write-Host "Testando o primeiro heartbeat..."
& $DestinoExe once
if ($LASTEXITCODE -ne 0) {
    throw "A configuração foi salva, mas o primeiro heartbeat falhou. Verifique URL, firewall e credencial."
}

Write-Host "Instalando inicialização automática..."
& $DestinoExe install --executable $DestinoExe
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar a tarefa do agente." }

Write-Host "Iniciando o agente agora, sem aguardar o próximo reboot..."
& schtasks.exe /Run /TN "DataIntelligence-TIAgent" | Out-Null
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Agente instalado com sucesso em: $DestinoExe"
Write-Host "Configuração: $env:PROGRAMDATA\DataIntelligence\TIAgent\agent.json"
Write-Host "Logs: $env:PROGRAMDATA\DataIntelligence\TIAgent\ti-agent.log"
