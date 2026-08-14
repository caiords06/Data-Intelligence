# Troubleshooting PowerShell

## 1. Servidor responde?

```powershell
Invoke-RestMethod http://127.0.0.1:8770/api/v1/health/live
Invoke-RestMethod http://127.0.0.1:8770/api/v1/health/ready
```

`live` confirma processo HTTP; `ready` confirma também acesso ao banco.

## 2. A porta está escutando?

No servidor:

```powershell
Get-NetTCPConnection -LocalPort 8770
```

Na estação:

```powershell
Test-NetConnection IP-DO-SERVIDOR -Port 8770
```

## 3. Firewall

```powershell
Get-NetFirewallRule | Where-Object DisplayName -Like "*Data Intelligence*"
```

A regra oficial do Servidor Corporativo deve usar perfil `Private`, `RemoteAddress LocalSubnet`, TCP/8770. Não abra `Any` para contornar diagnóstico.

## 4. Tarefa do servidor

```powershell
Get-ScheduledTask | Where-Object TaskName -Like "*DataIntelligence*"
Get-ScheduledTaskInfo -TaskName "DataIntelligenceCorporateServer"
```

Não monte manualmente uma linha `schtasks /Create /TR ...` extensa. O executável/script oficial registra a tarefa sem `cmd.exe`, evitando erros históricos de quoting e caminhos com espaços.

## 5. PostgreSQL

```powershell
Get-Service *postgres*
pg_isready
```

Depois confira `%PROGRAMDATA%\DataIntelligence\Server\server.log` e `install-db-error.log` quando existir.

## 6. `node.json` inválido/BOM

Reexecute `Configurar-Estacao-Central.ps1` ou `Configurar-Estacao-Cliente.ps1`. Esses scripts gravam UTF-8 **sem BOM** e validam o servidor antes da persistência. Evite editar manualmente salvo em emergência documentada.

## 7. Build falha com WinError 32 / arquivo em uso

Verifique processos antes de apagar `build`, `dist` ou `release`:

```powershell
Get-Process python* -ErrorAction SilentlyContinue
Get-Process DataIntelligence* -ErrorAction SilentlyContinue
```

Feche a aplicação, servidor/agente de teste e processos Python iniciados pelo smoke. Não force exclusão de arquivos enquanto um processo legítimo estiver usando-os.

## 8. Agente TI sem heartbeat

```powershell
PowerShell -ExecutionPolicy Bypass -File .\Diagnosticar-Conexao-TI.ps1 -ServerUrl "http://IP-DO-SERVIDOR:8770"
PowerShell -ExecutionPolicy Bypass -File .\Testar-Agente-TI.ps1
```

`Testar-Central-TI.ps1` em TCP/8765 é legado/standalone; para Server First use 8770.
