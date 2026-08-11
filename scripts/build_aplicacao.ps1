$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m pip install -r requirements.txt
python -m pip install -r requirements-agent-build.txt
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name DataIntelligence `
    --add-data "assets;assets" `
    --collect-submodules enterprise.migrations `
    main.py

$Executable = Join-Path $ProjectRoot "dist\DataIntelligence\DataIntelligence.exe"
if (-not (Test-Path $Executable)) {
    throw "O executável da aplicação não foi gerado."
}
Write-Host "Aplicação criada em $Executable"
