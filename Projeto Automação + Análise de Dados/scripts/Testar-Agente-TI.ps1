$ErrorActionPreference = "Stop"
$Exe = Join-Path $env:ProgramFiles "Data Intelligence\TIAgent\DataIntelligenceTIAgent.exe"
if (-not (Test-Path $Exe)) { throw "Agente não instalado em $Exe" }
& $Exe task-status
& $Exe collect
& $Exe once
