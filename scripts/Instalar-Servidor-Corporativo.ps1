param([int]$Porta=8770)
$ErrorActionPreference="Stop"
$identidade=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]$identidade
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw "Execute como Administrador." }
$Origem=Join-Path $PSScriptRoot "DataIntelligenceServer.exe"
if (-not (Test-Path $Origem)) { throw "DataIntelligenceServer.exe não está ao lado do instalador." }
$Destino=Join-Path $env:ProgramFiles "DataIntelligence\Server"
$DataDir=Join-Path $env:PROGRAMDATA "DataIntelligence\Server"
New-Item -ItemType Directory -Path $Destino,$DataDir -Force | Out-Null
Copy-Item $Origem (Join-Path $Destino "DataIntelligenceServer.exe") -Force
$cfg=@{host="0.0.0.0";porta=$Porta;tls=$false;certificado=$null;chave_privada=$null;max_upload_mb=1024}|ConvertTo-Json
Set-Content (Join-Path $DataDir "server.json") $cfg -Encoding UTF8
$Regra="Data Intelligence - Corporate Server"
Get-NetFirewallRule -DisplayName $Regra -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $Regra -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Porta -Profile Private -RemoteAddress LocalSubnet | Out-Null
$Exe=Join-Path $Destino "DataIntelligenceServer.exe"
& $Exe init-admin
if ($LASTEXITCODE -ne 0) { throw "Falha ao inicializar administrador do servidor." }
$Acao=New-ScheduledTaskAction -Execute $Exe -Argument "run"
$Gatilho=New-ScheduledTaskTrigger -AtStartup
$Principal=New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "DataIntelligenceCorporateServer" -Action $Acao -Trigger $Gatilho -Principal $Principal -Force | Out-Null
Start-ScheduledTask -TaskName "DataIntelligenceCorporateServer"
Write-Host "Servidor instalado. Porta: $Porta / perfil Private / origem LocalSubnet." -ForegroundColor Green
Write-Host "Dados persistentes: $DataDir"
