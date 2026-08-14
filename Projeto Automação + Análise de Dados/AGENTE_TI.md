# Agente TI 1.1.1 — Server First

O Agente TI conecta computadores gerenciados ao **Servidor Corporativo** da Data Intelligence V10.1.1.

## Fluxo canônico

```text
PC gerenciado
  DataIntelligenceTIAgent.exe
          │
          │ POST /api/v1/ti/agentes/heartbeat
          │ HMAC + timestamp + nonce
          ▼
Servidor Corporativo :8770
          │
          ▼
enterprise.tecnologia.registrar_snapshot_agente()
```

## Provisionamento

Na Central conectada, abra **Tecnologia → Ativos gerenciados → GERAR / ROTACIONAR AGENTE**. A credencial contém:

- URL do Servidor Corporativo;
- patrimônio;
- Agent ID;
- token exibido no provisionamento.

Instalação normal:

```powershell
.\scripts\Instalar-Agente-TI.ps1 `
  -ServerUrl "http://192.168.1.4:8770" `
  -Patrimonio "TI-FIN-001" `
  -AgentId "ID-GERADO-PELA-CENTRAL" `
  -Provider AnyDesk `
  -AllowPrivateHttp
```

O script solicita o token de forma oculta. Não coloque o token em arquivos de documentação, commits ou linha de comando.

## Segurança

O heartbeat usa Agent ID, HMAC-SHA256, timestamp e nonce. O token é armazenado fora do `agent.json` e protegido por DPAPI no Windows. HTTP privado existe somente para LAN controlada; produção deve usar HTTPS.

## Inicialização automática

A V10.1.1 registra a tarefa `DataIntelligence-TIAgent` usando a API PowerShell ScheduledTasks com executável e argumentos separados, evitando problemas de aspas em `Program Files`.

## Comandos

```powershell
DataIntelligenceTIAgent.exe collect
DataIntelligenceTIAgent.exe once
DataIntelligenceTIAgent.exe run
DataIntelligenceTIAgent.exe task-status
DataIntelligenceTIAgent.exe start-task
DataIntelligenceTIAgent.exe uninstall
```
