$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m pip install -r requirements.txt
python -m pip install -r requirements-agent-build.txt
python -m unittest tests.test_v9_integrada tests.test_tecnologia_3_0 -v
python -m PyInstaller --noconfirm --clean --onefile --console `
    --name DataIntelligenceServer `
    --collect-submodules enterprise.migrations `
    servidor/__main__.py

$Executable = Join-Path $ProjectRoot "dist\DataIntelligenceServer.exe"
if (-not (Test-Path $Executable)) {
    throw "O executável do servidor não foi gerado."
}
Write-Host "Servidor criado em $Executable"
