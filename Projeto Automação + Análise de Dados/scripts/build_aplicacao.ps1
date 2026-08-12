$ErrorActionPreference = "Stop"

function Assert-NativeSuccess([string]$Mensagem) { if ($LASTEXITCODE -ne 0) { throw $Mensagem } }

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python scripts\verificar_python_release.py
Assert-NativeSuccess "Python incompatível com o release V9.3."
python -m pip install -r requirements.lock.txt
Assert-NativeSuccess "Falha ao instalar dependências homologadas."
python -m pip install -r requirements-build.lock.txt
Assert-NativeSuccess "Falha ao instalar ferramentas de build homologadas."
for ($Grupo = 1; $Grupo -le 3; $Grupo++) {
    python scripts\executar_grupo_testes.py --grupo $Grupo --total 3
    Assert-NativeSuccess "Grupo de testes $Grupo/3 falhou."
}
python -m PyInstaller --noconfirm --clean DataIntelligencePlatform.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligencePlatform.exe."

$Executable = Join-Path $ProjectRoot "dist\DataIntelligencePlatform\DataIntelligencePlatform.exe"
if (-not (Test-Path $Executable)) { throw "O executável da aplicação não foi gerado." }
Write-Host "Aplicação criada em $Executable"
