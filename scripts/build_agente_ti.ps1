$ErrorActionPreference = "Stop"

function Assert-NativeSuccess([string]$Mensagem) { if ($LASTEXITCODE -ne 0) { throw $Mensagem } }

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "[1/3] Instalando dependências do agente..."
python -m pip install -r requirements-agent.txt
Assert-NativeSuccess "Falha ao instalar dependências do agente."
python -m pip install -r requirements-agent-build.txt
Assert-NativeSuccess "Falha ao instalar PyInstaller."

Write-Host "[2/3] Executando os testes do agente..."
python -m unittest tests.test_agente_ti -v
Assert-NativeSuccess "Os testes do agente falharam."

Write-Host "[3/3] Gerando executável..."
python -m PyInstaller --noconfirm --clean agente_ti.spec
Assert-NativeSuccess "Falha ao gerar o executável do agente."

$Executable = Join-Path $ProjectRoot "dist\DataIntelligenceTIAgent.exe"
if (-not (Test-Path $Executable)) {
    throw "O executável não foi gerado em $Executable"
}

Write-Host "Executável criado com sucesso:"
Write-Host $Executable
