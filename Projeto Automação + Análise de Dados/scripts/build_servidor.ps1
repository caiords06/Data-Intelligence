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
python -m pytest -q tests/test_v9_integrada.py tests/test_v9_1_autoridade_central.py tests/test_auditoria_regressoes.py tests/test_v9_3_release_engineering.py
Assert-NativeSuccess "Os testes do servidor falharam."
python -m PyInstaller --noconfirm --clean DataIntelligenceServer.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligenceServer.exe."

$Executable = Join-Path $ProjectRoot "dist\DataIntelligenceServer.exe"
if (-not (Test-Path $Executable)) { throw "O executável do servidor não foi gerado." }
Write-Host "Servidor criado em $Executable"
