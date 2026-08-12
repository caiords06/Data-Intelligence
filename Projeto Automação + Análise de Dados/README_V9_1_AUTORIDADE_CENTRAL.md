# Data Intelligence V9.1 — Autoridade Central Corporativa

## O problema que esta versão resolve

Nas versões anteriores, Central e Cliente podiam possuir um `app.db` local e parte dos módulos ainda executava operações diretamente nele. Isso criava risco de duas estações enxergarem estados diferentes de Financeiro, RH, Compras, Estoque, Tecnologia e demais módulos.

A V9.1 introduz uma fronteira de servidor para as operações de domínio. Em estações configuradas como `central` ou `cliente`, as APIs transacionais permitidas dos módulos são enviadas ao Servidor Corporativo por HTTP(S). O servidor recompõe o `ator` a partir do bearer token e executa a regra no banco do servidor.

```text
Central / Cliente
       │
       │ HTTPS / HTTP privado de laboratório
       ▼
Servidor Corporativo :8770
       │
       ├── autenticação / sessões
       ├── RPC de domínio restrito
       ├── correio corporativo
       ├── arquivos / backups
       ├── heartbeat do Agente TI
       └── banco operacional único
```

## Garantia contra spoofing de usuário

O cliente pode enviar argumentos normais da função, mas não controla a identidade efetiva. Se a função possuir parâmetro `ator`, o servidor substitui o valor recebido por `sessao.ator()`. Empresa e filial vêm da sessão validada no servidor.

O endpoint `/api/v1/rpc` não aceita módulo/função arbitrários. Existe uma allowlist explícita em `core/rpc_central.py`.

## Módulos centralizados

A camada remota cobre RH, Financeiro, Compras, Estoque, Tecnologia, módulos genéricos (Marketing, Administrativo, Jurídico, Comercial), Central de Aprovações/Notificações, tarefas, recursos, workflows, integrações, jobs e datasets nas operações que não dependem de um arquivo local.

Operações que dependem do filesystem da estação são bloqueadas em modo remoto quando ainda não possuem um fluxo dedicado de upload/download. A decisão é proposital: é melhor mostrar uma mensagem clara do que gravar silenciosamente no banco-cache local.

## Tecnologia e Agente TI

Quando a estação está conectada ao Servidor Corporativo, a Central não abre mais uma segunda API local na porta 8765. O próprio servidor corporativo recebe:

`POST /api/v1/ti/agentes/heartbeat`

Portanto o Agente TI deve usar a mesma URL do servidor, por exemplo:

`http://192.168.1.4:8770`

O servidor continua validando Agent ID, HMAC, timestamp, nonce e patrimônio antes de registrar inventário/telemetria.

## Banco local das estações

Central/Cliente ainda mantêm um SQLite pequeno para cache de identidade, empresa, filial e permissões necessárias à navegação da interface. Ele **não é a autoridade dos registros de negócio**. Se o servidor cair, operações remotas falham; não existe fallback para gravar localmente e sincronizar depois.

Isso evita split-brain.

## Backup

Quando `criar_backup()` é chamado por uma estação conectada, a solicitação é encaminhada ao Servidor Corporativo e o backup completo é criado sobre a base e os arquivos do servidor. Não é mais criado um backup do cache vazio da estação como se fosse um backup empresarial.

## PostgreSQL

A V9.1 cria a fronteira necessária para trocar o mecanismo de persistência sem modificar cada estação. **O banco operacional desta entrega continua sendo SQLite, porém agora existe apenas no servidor como autoridade única.**

A migração efetiva de todo o esquema legado para PostgreSQL não foi marcada como concluída nesta versão. O projeto possui centenas de consultas e triggers escritos no dialeto SQLite; fazer uma conversão parcial ou uma camada de tradução improvisada colocaria dados financeiros/RH em risco. Com o RPC centralizado, a migração para PostgreSQL passa a ser uma alteração exclusivamente server-side e pode ser feita com testes de equivalência por módulo.

## Instalação de laboratório

1. Instale `DataIntelligenceServer.exe` no computador servidor.
2. A regra de firewall do instalador libera apenas TCP/8770 em perfil Private/LocalSubnet.
3. Configure a Central:

```powershell
.\Configurar-Estacao-Central.ps1 -ServerUrl "http://192.168.1.4:8770" -AllowPrivateHttp
```

4. Configure cada Cliente:

```powershell
.\Configurar-Estacao-Cliente.ps1 -ServerUrl "http://192.168.1.4:8770" -AllowPrivateHttp
```

5. Para o Agente TI, use também `http://192.168.1.4:8770` como `ServerUrl`.

Em produção use HTTPS e certificado válido; HTTP privado existe somente para laboratório controlado.
