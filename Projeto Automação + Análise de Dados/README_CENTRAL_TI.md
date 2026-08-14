> **DOCUMENTO HISTÓRICO.** Esta documentação descreve arquitetura anterior à linha final Server First. Para novas instalações, use `docs/README.md`.

# Central de TI — V10.1.1

A Central conectada **não abre uma segunda API autoritativa em 8765**. Ela usa o Servidor Corporativo em `:8770`, que também recebe os heartbeats dos Agentes TI.

## Configuração

Após instalar o papel **PC CENTRAL**, o Setup grava `C:\ProgramData\DataIntelligence\Platform\node.json` apontando para a URL informada.

Fallback administrativo:

```powershell
.\scripts\Configurar-Estacao-Central.ps1 -ServerUrl "http://192.168.1.4:8770" -AllowPrivateHttp
```

O script valida `/api/v1/health/ready` antes de gravar a configuração.

## Fluxo

```text
Central Desktop
     │
     ▼
Servidor Corporativo :8770
     │
     ├─ PostgreSQL
     └─ /api/v1/ti/agentes/heartbeat
```

O servidor corporativo é a autoridade de usuários, permissões, organização e operações de domínio. O banco local da Central é somente cache mínimo.

## Modo standalone legado

A API embutida `servidor_ti` em 8765 continua disponível apenas quando o aplicativo é executado explicitamente em modo `standalone` de desenvolvimento/compatibilidade. Não use esse caminho em uma implantação Server First.
