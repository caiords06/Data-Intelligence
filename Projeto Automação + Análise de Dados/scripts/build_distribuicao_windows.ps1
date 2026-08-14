$ErrorActionPreference = "Stop"

function Assert-NativeSuccess([string]$Mensagem) {
    if ($LASTEXITCODE -ne 0) { throw $Mensagem }
}

if ($env:OS -ne "Windows_NT") { throw "O pacote Windows deve ser compilado no Windows." }
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$env:PYTHONUTF8 = "1"

Write-Host "[1/12] Limpando artefatos de builds anteriores..."
foreach ($Pasta in @("build", "dist", "release")) {
    $Alvo = Join-Path $ProjectRoot $Pasta
    Remove-Item -LiteralPath $Alvo -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "release") | Out-Null

Write-Host "[2/12] Validando Python de release..."
python scripts\verificar_python_release.py
Assert-NativeSuccess "Versão de Python incompatível com o release V11.1.0."

Write-Host "[3/12] Instalando dependências travadas da aplicação e do build..."
python -m pip install --upgrade pip
Assert-NativeSuccess "Falha ao atualizar o pip."
python -m pip install -r requirements.lock.txt
Assert-NativeSuccess "Falha ao instalar as dependências homologadas da aplicação."
python -m pip install -r requirements-build.lock.txt
Assert-NativeSuccess "Falha ao instalar as ferramentas de build homologadas."

Write-Host "[4/12] Validando código, migrations e regressões..."
python -m compileall -q .
Assert-NativeSuccess "Falha na compilação sintática do Python."
python scripts\auditar_autoridade_servidor.py
Assert-NativeSuccess "A auditoria Server First/PostgreSQL falhou; o build foi cancelado."
for ($Grupo = 1; $Grupo -le 6; $Grupo++) {
    python scripts\executar_grupo_testes.py --grupo $Grupo --total 6 --timeout-arquivo 90
    Assert-NativeSuccess "Grupo de testes $Grupo/6 falhou; o build foi cancelado."
}
# Smoke Tk real é obrigatório no build Windows.
# Primeiro validamos o próprio runtime Tcl/Tk. Depois executamos cada família
# de smoke em um processo Python separado para impedir que o ciclo de vida de
# muitos interpretadores Tcl/Tk contamine a próxima família de testes.
python scripts\verificar_tk_release.py
Assert-NativeSuccess "Tcl/Tk do Python de release não está utilizável; o build foi cancelado."

$env:RUN_TK_SMOKE = "1"
try {
    python -m pytest -q tests/test_interface_smoke_v8_2.py
    Assert-NativeSuccess "O smoke gráfico Tk V8.2 falhou; o build foi cancelado."

    python -m pytest -q tests/test_v9_interface_smoke.py
    Assert-NativeSuccess "O smoke gráfico Tk V9 falhou; o build foi cancelado."
}
finally {
    Remove-Item Env:RUN_TK_SMOKE -ErrorAction SilentlyContinue
}

Write-Host "[5/12] Compilando aplicação desktop (onedir)..."
python -m PyInstaller --noconfirm --clean DataIntelligencePlatform.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligencePlatform.exe."

Write-Host "[6/12] Compilando agente TI (onefile)..."
python -m PyInstaller --noconfirm --clean agente_ti.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligenceTIAgent.exe."

Write-Host "[7/12] Compilando Servidor Corporativo (onefile)..."
python -m PyInstaller --noconfirm --clean DataIntelligenceServer.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligenceServer.exe."
python -m PyInstaller --noconfirm --clean DataIntelligenceUpdateHelper.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligenceUpdateHelper.exe."

Write-Host "[8/12] Montando pacote de distribuição..."
$ReleaseRoot = Join-Path $ProjectRoot "release\DataIntelligence-Deployment"
Remove-Item $ReleaseRoot -Recurse -Force -ErrorAction SilentlyContinue
$Central = Join-Path $ReleaseRoot "Central"
$Cliente = Join-Path $ReleaseRoot "Cliente"
$Agente = Join-Path $ReleaseRoot "Agente-TI"
$Servidor = Join-Path $ReleaseRoot "Servidor"
New-Item -ItemType Directory -Path $Central,$Cliente,$Agente,$Servidor -Force | Out-Null

# A pasta desktop pode ser copiada para Central e Cliente. O papel efetivo é
# definido pelo node.json gerado pelos scripts de configuração.
Copy-Item (Join-Path $ProjectRoot "dist\DataIntelligencePlatform") (Join-Path $Central "DataIntelligencePlatform") -Recurse
Copy-Item (Join-Path $ProjectRoot "dist\DataIntelligencePlatform") (Join-Path $Cliente "DataIntelligencePlatform") -Recurse
Copy-Item (Join-Path $ProjectRoot "scripts\Configurar-Estacao-Central.ps1") $Central
Copy-Item (Join-Path $ProjectRoot "scripts\Testar-Servidor-Corporativo.ps1") $Central
Copy-Item (Join-Path $ProjectRoot "scripts\Configurar-Estacao-Cliente.ps1") $Cliente
Copy-Item (Join-Path $ProjectRoot "README_DISTRIBUICAO_WINDOWS.md") $Central
Copy-Item (Join-Path $ProjectRoot "README_DISTRIBUICAO_WINDOWS.md") $Cliente
Copy-Item (Join-Path $ProjectRoot "README_CENTRAL_TI.md") $Central
Copy-Item (Join-Path $ProjectRoot "README_V10_1_1_ESTABILIDADE.md") $Central
Copy-Item (Join-Path $ProjectRoot "README_V10_1_1_ESTABILIDADE.md") $Cliente

Copy-Item (Join-Path $ProjectRoot "dist\DataIntelligenceTIAgent.exe") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Instalar-Agente-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Desinstalar-Agente-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Testar-Agente-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Diagnosticar-Conexao-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "README_DISPOSITIVO_TI.md") $Agente

Copy-Item (Join-Path $ProjectRoot "dist\DataIntelligenceServer.exe") $Servidor
Copy-Item (Join-Path $ProjectRoot "dist\DataIntelligenceUpdateHelper.exe") $ReleaseRoot
Copy-Item (Join-Path $ProjectRoot "scripts\Instalar-Servidor-Corporativo.ps1") $Servidor
Copy-Item (Join-Path $ProjectRoot "scripts\Testar-Servidor-Corporativo.ps1") $Servidor
Copy-Item (Join-Path $ProjectRoot "scripts\Desinstalar-Servidor-Corporativo.ps1") $Servidor
Copy-Item (Join-Path $ProjectRoot "README_SERVIDOR_CORPORATIVO.md") $Servidor
Copy-Item (Join-Path $ProjectRoot "README_SERVIDOR_CORPORATIVO.md") $ReleaseRoot
Copy-Item (Join-Path $ProjectRoot "README_V10_1_POSTGRESQL_SERVER_FIRST.md") $ReleaseRoot
Copy-Item (Join-Path $ProjectRoot "README_V10_1_1_ESTABILIDADE.md") $ReleaseRoot
Copy-Item (Join-Path $ProjectRoot "VERSAO_V11_1_0.txt") $ReleaseRoot
Copy-Item (Join-Path $ProjectRoot "README.md") $ReleaseRoot

Write-Host "[9/12] Validando que o pacote não contém banco, Git ou caches..."
python scripts\verificar_pacote_limpo.py $ReleaseRoot
Assert-NativeSuccess "O pacote contém material operacional/de desenvolvimento proibido."

Write-Host "[10/12] Criando ZIP de deployment legado..."
$Zip = Join-Path $ProjectRoot "release\DataIntelligence-Deployment-Windows.zip"
Remove-Item $Zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $ReleaseRoot "*") -DestinationPath $Zip -CompressionLevel Optimal
Write-Host "Pacote pronto: $Zip" -ForegroundColor Green


Write-Host "[11/12] Gerando e validando pacote-fonte reproduzível V11.1.0..."
$SourceZip = Join-Path $ProjectRoot "release\DataIntelligence-Source-V11.1.0.zip"
python scripts\empacotar_fonte_limpa.py $SourceZip
Assert-NativeSuccess "Falha ao gerar o pacote-fonte limpo V11."
python scripts\verificar_fonte_reproduzivel.py $SourceZip
Assert-NativeSuccess "O pacote-fonte V11 falhou na validação estrutural/reprodutível."
Write-Host "Pacote-fonte pronto: $SourceZip" -ForegroundColor Green

Write-Host "[12/12] Compilando Setup.exe unificado V11.1.0..."
powershell -ExecutionPolicy Bypass -File scripts\build_setup_windows.ps1 -SkipPyInstaller
Assert-NativeSuccess "Falha ao gerar o Setup.exe unificado V11.1.0."
Write-Host "Artefato principal: release\DataIntelligence_Setup_V11.1.0.exe" -ForegroundColor Green
