$ErrorActionPreference = "Stop"

function Assert-NativeSuccess([string]$Mensagem) {
    if ($LASTEXITCODE -ne 0) { throw $Mensagem }
}

if ($env:OS -ne "Windows_NT") { throw "O pacote Windows deve ser compilado no Windows." }
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$env:PYTHONUTF8 = "1"

Write-Host "[1/8] Instalando dependências da aplicação e do build..."
python -m pip install --upgrade pip
Assert-NativeSuccess "Falha ao atualizar o pip."
python -m pip install -r requirements.txt
Assert-NativeSuccess "Falha ao instalar as dependências da aplicação."
python -m pip install -r requirements-build.txt
Assert-NativeSuccess "Falha ao instalar as ferramentas de build."

Write-Host "[2/8] Validando código e regressões..."
python -m compileall -q .
Assert-NativeSuccess "Falha na compilação sintática do Python."
$TestGroups = @(
    @("tests/test_auth.py", "tests/test_captura_visual.py", "tests/test_compras_2_0.py", "tests/test_data_engine.py", "tests/test_enterprise_v5.py", "tests/test_estabilizacao_v5_1.py", "tests/test_estabilizacao_v6.py"),
    @("tests/test_estoque_2_0.py", "tests/test_financeiro_departamental.py", "tests/test_historico_preferencias.py", "tests/test_indicadores_v4.py", "tests/test_rh_2_0.py", "tests/test_tratamento_qualidade.py", "tests/test_v8_backend.py"),
    @("tests/test_interface_screenshots.py", "tests/test_interface_v7.py", "tests/test_v8_1_estabilizacao.py"),
    @("tests/test_agente_ti.py", "tests/test_servidor_ti.py", "tests/test_tecnologia_2_0.py", "tests/test_tecnologia_3_0.py", "tests/test_v8_2_1_hotfix.py", "tests/test_v8_2_correcoes.py"),
    @("tests/test_vnext_estabilizacao.py", "tests/test_v9_1_autoridade_central.py")
)
foreach ($grupo in $TestGroups) {
    python -m pytest -q @grupo
    Assert-NativeSuccess "Um lote de testes falhou; o build foi cancelado."
}
# Smoke Tk real é obrigatório no build Windows. As janelas são criadas e
# destruídas automaticamente; screenshots extensivos continuam opcionais.
$env:RUN_TK_SMOKE = "1"
python -m pytest -q tests/test_interface_smoke_v8_2.py tests/test_v9_interface_smoke.py
Assert-NativeSuccess "O smoke gráfico Tk falhou; o build foi cancelado."
Remove-Item Env:RUN_TK_SMOKE -ErrorAction SilentlyContinue

Write-Host "[3/8] Compilando aplicação desktop (onedir)..."
python -m PyInstaller --noconfirm --clean DataIntelligencePlatform.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligencePlatform.exe."

Write-Host "[4/8] Compilando agente TI (onefile)..."
python -m PyInstaller --noconfirm --clean agente_ti.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligenceTIAgent.exe."

Write-Host "[5/8] Compilando Servidor Corporativo (onefile)..."
python -m PyInstaller --noconfirm --clean DataIntelligenceServer.spec
Assert-NativeSuccess "Falha ao gerar DataIntelligenceServer.exe."

Write-Host "[6/8] Montando pacote de distribuição..."
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
Copy-Item (Join-Path $ProjectRoot "README_V9_1_AUTORIDADE_CENTRAL.md") $Central
Copy-Item (Join-Path $ProjectRoot "README_V9_1_AUTORIDADE_CENTRAL.md") $Cliente

Copy-Item (Join-Path $ProjectRoot "dist\DataIntelligenceTIAgent.exe") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Instalar-Agente-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Desinstalar-Agente-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Testar-Agente-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "scripts\Diagnosticar-Conexao-TI.ps1") $Agente
Copy-Item (Join-Path $ProjectRoot "README_DISPOSITIVO_TI.md") $Agente

Copy-Item (Join-Path $ProjectRoot "dist\DataIntelligenceServer.exe") $Servidor
Copy-Item (Join-Path $ProjectRoot "scripts\Instalar-Servidor-Corporativo.ps1") $Servidor
Copy-Item (Join-Path $ProjectRoot "scripts\Testar-Servidor-Corporativo.ps1") $Servidor
Copy-Item (Join-Path $ProjectRoot "scripts\Desinstalar-Servidor-Corporativo.ps1") $Servidor
Copy-Item (Join-Path $ProjectRoot "README_SERVIDOR_CORPORATIVO.md") $Servidor
Copy-Item (Join-Path $ProjectRoot "README_SERVIDOR_CORPORATIVO.md") $ReleaseRoot
Copy-Item (Join-Path $ProjectRoot "README_V9_1_AUTORIDADE_CENTRAL.md") $ReleaseRoot
Copy-Item (Join-Path $ProjectRoot "VERSAO_V9_1.txt") $ReleaseRoot

Write-Host "[7/8] Validando que o pacote não contém banco, Git ou caches..."
python scripts\verificar_pacote_limpo.py $ReleaseRoot
Assert-NativeSuccess "O pacote contém material operacional/de desenvolvimento proibido."

Write-Host "[8/8] Criando ZIP final..."
$Zip = Join-Path $ProjectRoot "release\DataIntelligence-Deployment-Windows.zip"
Remove-Item $Zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $ReleaseRoot "*") -DestinationPath $Zip -CompressionLevel Optimal
Write-Host "Pacote pronto: $Zip" -ForegroundColor Green
