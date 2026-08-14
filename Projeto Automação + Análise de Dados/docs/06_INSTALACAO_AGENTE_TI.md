# Instalação do Agente TI

O agente coleta inventário e heartbeat do dispositivo. Instale somente após criar/provisionar o ativo e obter `AgentId` + token válidos.

```powershell
PowerShell -ExecutionPolicy Bypass -File .\Instalar-Agente-TI.ps1 `
  -ServerUrl "http://IP-DO-SERVIDOR:8770" `
  -Patrimonio "NB-001" `
  -AgentId "<ID-PROVISIONADO>" `
  -Provider AnyDesk `
  -AllowPrivateHttp
```

O instalador configura o agente, executa o primeiro heartbeat, instala a tarefa de inicialização e a inicia imediatamente. O token é mantido em variável de processo somente durante a configuração.

Valide:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\Testar-Agente-TI.ps1
```

Arquivos: `%PROGRAMDATA%\DataIntelligence\TIAgent\agent.json` e `ti-agent.log`.
