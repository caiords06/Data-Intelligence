$ErrorActionPreference = "Stop"

function Assert-NativeSuccess([string]$Mensagem) { if ($LASTEXITCODE -ne 0) { throw $Mensagem } }

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "[1/4] Validando Python de release..."
python scripts\verificar_python_release.py
Assert-NativeSuccess "Python incompatível com o release V10."

Write-Host "[2/4] Instalando dependências travadas do agente..."
python -m pip install -r requirements-agent.lock.txt
Assert-NativeSuccess "Falha ao instalar dependências do agente."
python -m pip install -r requirements-build.lock.txt
Assert-NativeSuccess "Falha ao instalar PyInstaller."

Write-Host "[3/4] Executando os testes do agente..."
python -m unittest tests.test_agente_ti -v
Assert-NativeSuccess "Os testes do agente falharam."

Write-Host "[4/4] Gerando executável..."
python -m PyInstaller --noconfirm --clean agente_ti.spec
Assert-NativeSuccess "Falha ao gerar o executável do agente."

$Executable = Join-Path $ProjectRoot "dist\DataIntelligenceTIAgent.exe"
if (-not (Test-Path $Executable)) {
    throw "O executável não foi gerado em $Executable"
}

Write-Host "Executável criado com sucesso:"
Write-Host $Executable
