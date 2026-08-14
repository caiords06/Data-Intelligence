param([switch]$SkipPyInstaller)

$ErrorActionPreference = "Stop"

$ProjectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
Set-Location -LiteralPath $ProjectRoot

function Assert-NativeSuccess([string]$Mensagem) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Mensagem ExitCode=$LASTEXITCODE"
    }
}

if ($env:OS -ne "Windows_NT") {
    throw "O Setup.exe so pode ser compilado no Windows."
}

python ".\scripts\verificar_python_release.py"
Assert-NativeSuccess "Python incompativel com o release V11.1.0."

python ".\scripts\auditar_autoridade_servidor.py"
Assert-NativeSuccess "Auditoria Server First/PostgreSQL falhou."
python ".\scripts\verificar_instalador_v10.py"
Assert-NativeSuccess "Validação estrutural do instalador V10 falhou."
python ".\scripts\verificar_instalador_v10_1.py"
Assert-NativeSuccess "Validação estrutural do instalador V10.1 falhou."

if (-not $SkipPyInstaller) {
    python -m PyInstaller --noconfirm --clean ".\DataIntelligencePlatform.spec"
    Assert-NativeSuccess "Falha no desktop."

    python -m PyInstaller --noconfirm --clean ".\agente_ti.spec"
    Assert-NativeSuccess "Falha no agente TI."

    python -m PyInstaller --noconfirm --clean ".\DataIntelligenceServer.spec"
    Assert-NativeSuccess "Falha no servidor."

    python -m PyInstaller --noconfirm --clean ".\DataIntelligenceUpdateHelper.spec"
    Assert-NativeSuccess "Falha no helper de atualização."
}

$PlatformDir = Join-Path $ProjectRoot "dist\DataIntelligencePlatform"
$PlatformExe = Join-Path $PlatformDir "DataIntelligencePlatform.exe"
$AgentExe    = Join-Path $ProjectRoot "dist\DataIntelligenceTIAgent.exe"
$ServerExe   = Join-Path $ProjectRoot "dist\DataIntelligenceServer.exe"
$UpdateExe   = Join-Path $ProjectRoot "dist\DataIntelligenceUpdateHelper.exe"
$IssFile     = Join-Path $ProjectRoot "installer\DataIntelligenceSetup.iss"
$ReleaseDir  = Join-Path $ProjectRoot "release"
$Setup       = Join-Path $ReleaseDir "DataIntelligence_Setup_V11.1.0.exe"

$Required = @(
    $PlatformExe,
    $AgentExe,
    $ServerExe,
    $UpdateExe,
    $IssFile
)

foreach ($Item in $Required) {
    Write-Host "Verificando: $Item"
    if (-not (Test-Path -LiteralPath $Item)) {
        throw "Artefato ausente: $Item"
    }
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

$ISCC = $env:INNO_SETUP_COMPILER

if ($ISCC -and -not (Test-Path -LiteralPath $ISCC)) {
    Write-Warning "INNO_SETUP_COMPILER aponta para um arquivo inexistente: $ISCC"
    $ISCC = $null
}

if (-not $ISCC) {
    $Candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )

    $ISCC = $Candidates |
        Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
        Select-Object -First 1
}

if (-not $ISCC) {
    throw "Inno Setup 6 nao encontrado. Defina INNO_SETUP_COMPILER apontando para ISCC.exe."
}

# O Inno compila em staging fora do OneDrive. Isso evita falhas de resolucao
# de caminho causadas pela arvore longa/sincronizada do projeto.
$StageRoot = Join-Path $env:TEMP "DataIntelligence_Inno_V10_1_1"
$StageInstaller = Join-Path $StageRoot "installer"
$StageDist = Join-Path $StageRoot "dist"
$StageRelease = Join-Path $StageRoot "release"
$StagePlatform = Join-Path $StageDist "DataIntelligencePlatform"
$StageIss = Join-Path $StageInstaller "DataIntelligenceSetup.iss"
$StageSetup = Join-Path $StageRelease "DataIntelligence_Setup_V11.1.0.exe"

Remove-Item -LiteralPath $StageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $StageInstaller,$StageDist,$StageRelease | Out-Null

Write-Host ""
Write-Host "Preparando staging curto para o Inno Setup..."
Write-Host "Staging: $StageRoot"

Copy-Item -LiteralPath $IssFile -Destination $StageIss -Force
Copy-Item -LiteralPath $PlatformDir -Destination $StagePlatform -Recurse -Force
Copy-Item -LiteralPath $ServerExe -Destination (Join-Path $StageDist "DataIntelligenceServer.exe") -Force
Copy-Item -LiteralPath $AgentExe -Destination (Join-Path $StageDist "DataIntelligenceTIAgent.exe") -Force
Copy-Item -LiteralPath $UpdateExe -Destination (Join-Path $StageDist "DataIntelligenceUpdateHelper.exe") -Force

$StageRequired = @(
    (Join-Path $StagePlatform "DataIntelligencePlatform.exe"),
    (Join-Path $StageDist "DataIntelligenceServer.exe"),
    (Join-Path $StageDist "DataIntelligenceTIAgent.exe"),
    (Join-Path $StageDist "DataIntelligenceUpdateHelper.exe"),
    $StageIss
)

foreach ($Item in $StageRequired) {
    if (-not (Test-Path -LiteralPath $Item)) {
        throw "Falha ao preparar staging: $Item"
    }
}

Write-Host ""
Write-Host "============================================"
Write-Host " Data Intelligence - Setup V11.1.0"
Write-Host "============================================"
Write-Host "Projeto : $ProjectRoot"
Write-Host "Inno    : $ISCC"
Write-Host "Script  : $StageIss"
Write-Host "Saida   : $StageRelease"
Write-Host ""

& $ISCC $StageIss
Assert-NativeSuccess "Falha ao compilar o Setup.exe. Staging preservado em: $StageRoot"

if (-not (Test-Path -LiteralPath $StageSetup)) {
    throw "Setup nao foi gerado no staging: $StageSetup"
}

Copy-Item -LiteralPath $StageSetup -Destination $Setup -Force

if (-not (Test-Path -LiteralPath $Setup)) {
    throw "Setup esperado nao foi copiado para o release: $Setup"
}

$Hash = (Get-FileHash -LiteralPath $Setup -Algorithm SHA256).Hash
$Size = (Get-Item -LiteralPath $Setup).Length

Write-Host ""
Write-Host "============================================"
Write-Host " BUILD CONCLUIDO"
Write-Host "============================================"
Write-Host "Setup V11.1.0 pronto:" -ForegroundColor Green
Write-Host $Setup -ForegroundColor Green
Write-Host "Tamanho: $Size bytes"
Write-Host "SHA-256: $Hash"

# Limpa staging apenas apos sucesso; em caso de erro ele fica preservado.
Remove-Item -LiteralPath $StageRoot -Recurse -Force -ErrorAction SilentlyContinue
