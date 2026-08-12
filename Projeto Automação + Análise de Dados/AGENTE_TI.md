# Agente de Tecnologia 1.1

O Agente TI conecta computadores administrados ao módulo Tecnologia da Data Intelligence Enterprise Platform. A versão 1.1 inclui o **receptor central de heartbeats**, autenticação HMAC, proteção contra replay, provisionamento por ativo e scripts de distribuição Windows.

## Fluxo

```text
Computador remoto
  DataIntelligenceTIAgent.exe
            │
            │ POST /api/v1/ti/agentes/heartbeat
            │ HMAC + timestamp + nonce
            ▼
Computador Central
  servidor_ti (embutido no desktop)
            │
            ▼
enterprise.tecnologia.registrar_snapshot_agente()
            │
            ├─ ti_ativos
            ├─ ti_telemetria
            └─ ti_agentes
```

## O que o agente coleta

- patrimônio configurado e identificador do agente;
- hostname e FQDN;
- sistema operacional, versão e arquitetura;
- IP e MAC locais;
- processador;
- memória e armazenamento;
- usuário da sessão;
- CPU, memória, disco, espaço livre e uptime;
- versão do agente;
- ID/alias/versão/estado local do AnyDesk, quando disponível e configurado.

O agente não varre redes arbitrárias e não coleta tela, teclas digitadas, documentos, histórico de navegação, mensagens ou senhas.

## Segurança do transporte

Cada heartbeat possui:

```text
X-Agent-ID
X-Agent-Timestamp
X-Agent-Nonce
X-Agent-Signature
```

O servidor:

1. localiza a credencial do agente;
2. verifica a assinatura HMAC-SHA256 em tempo constante;
3. recusa timestamps fora da janela aceita;
4. registra e recusa nonces repetidos;
5. valida Agent ID e patrimônio contra o ativo provisionado;
6. aplica empresa/filial da credencial, sem confiar no cliente para definir o escopo;
7. só então atualiza inventário e telemetria.

O token em texto puro não é persistido na tabela da Central. Entretanto, o banco e o diretório da Central continuam sendo material sensível e devem possuir ACL e backup apropriados.

No Windows remoto, o token é armazenado separadamente do JSON e protegido com DPAPI no escopo da máquina.

## HTTP de laboratório

HTTP para IP privado é recusado por padrão. Para um laboratório controlado na LAN é necessário habilitá-lo explicitamente:

```text
--allow-private-http
```

Em ambiente real, use HTTPS. HMAC autentica/integridade; HTTP não cifra a telemetria.

## Comandos

```powershell
DataIntelligenceTIAgent.exe collect
DataIntelligenceTIAgent.exe once
DataIntelligenceTIAgent.exe run
DataIntelligenceTIAgent.exe task-status
DataIntelligenceTIAgent.exe uninstall
```

Provisionamento manual:

```powershell
$env:DATA_TI_AGENT_TOKEN = "TOKEN-TEMPORARIO"
DataIntelligenceTIAgent.exe configure `
  --server-url "http://192.168.0.10:8765" `
  --patrimonio "TI-FIN-001" `
  --agent-id "ID-GERADO-PELA-CENTRAL" `
  --provider AnyDesk `
  --allow-private-http
Remove-Item Env:DATA_TI_AGENT_TOKEN
```

Na distribuição normal, prefira `scripts\Instalar-Agente-TI.ps1`, que pede o token ocultamente.

## Build

Para gerar somente o agente:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_agente_ti.ps1
```

Para gerar a distribuição completa Central + Agente:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

Veja também:

- `README_DISTRIBUICAO_WINDOWS.md`
- `README_CENTRAL_TI.md`
- `README_DISPOSITIVO_TI.md`
