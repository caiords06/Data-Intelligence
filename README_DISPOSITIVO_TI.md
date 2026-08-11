# Agente TI · Instalação no computador monitorado

O computador monitorado recebe somente o `DataIntelligenceTIAgent.exe` e os scripts auxiliares. Ele envia inventário e telemetria ao Servidor Corporativo V9.1.

## Antes de instalar

Na Central, abra Tecnologia → Ativos gerenciados, crie/vincule o ativo e use **Gerar / Rotacionar agente**. Guarde:

- URL do servidor;
- patrimônio;
- Agent ID;
- token temporário.

Na V9.1 a URL é a do Servidor Corporativo, por exemplo:

```text
http://192.168.1.4:8770
```

## Diagnóstico

No PC remoto:

```powershell
.\Diagnosticar-Conexao-TI.ps1 -ServerUrl "http://192.168.1.4:8770"
```

Também é útil:

```powershell
Test-NetConnection 192.168.1.4 -Port 8770
```

O esperado é `TcpTestSucceeded : True`.

## Instalação

Abra PowerShell como Administrador:

```powershell
.\Instalar-Agente-TI.ps1 `
  -ServerUrl "http://192.168.1.4:8770" `
  -Patrimonio "TI-FIN-001" `
  -AgentId "COLE-O-AGENT-ID" `
  -Provider AnyDesk `
  -AllowPrivateHttp
```

O token será solicitado de forma oculta.

O agente é instalado em:

```text
C:\Program Files\DataIntelligence\TIAgent
```

Dados operacionais:

```text
C:\ProgramData\DataIntelligence\TIAgent
```

## Teste

```powershell
.\Testar-Agente-TI.ps1
```

ou:

```powershell
& "C:\Program Files\DataIntelligence\TIAgent\DataIntelligenceTIAgent.exe" once
```

O heartbeat deve retornar HTTP 202.

## Segurança

HTTP sem TLS é permitido somente quando explicitamente habilitado para laboratório em IP privado. Em produção use HTTPS e certificado válido.
