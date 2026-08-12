# Relatório técnico — V9.1 Autoridade Central

## Alterações principais

- Criado `core/rpc_central.py` com serialização tipada, allowlist de módulos/funções e proxies runtime.
- Criado `servidor_corporativo/rpc.py` para despacho seguro no servidor.
- Adicionado `POST /api/v1/rpc` ao Servidor Corporativo.
- O parâmetro `ator` é sempre reconstruído no servidor a partir da sessão bearer.
- RH, Financeiro, Compras, Estoque, Tecnologia e os serviços genéricos agora usam a autoridade do servidor quando o nó é `central`/`cliente`.
- A interface de Estoque deixou de executar SQL direto para obter a primeira linha de conferência.
- Operações de arquivo sem transporte dedicado são bloqueadas em modo remoto para impedir escrita no cache local.
- O Servidor Corporativo passou a receber também `POST /api/v1/ti/agentes/heartbeat`.
- Em modo Central conectado, o desktop deixa de iniciar a API TI local :8765.
- O provisionamento do agente usa a URL do Servidor Corporativo e verifica o health antes de apresentar a credencial.
- Monitor de heartbeat expirado foi incorporado ao processo do servidor corporativo.
- Backup solicitado pela Central conectada é criado no servidor.
- `DataIntelligenceServer.spec` passa a coletar submódulos `enterprise` e `servidor_corporativo` necessários ao dispatcher dinâmico.
- Build Windows inclui regressões V9.1 e deixa de distribuir scripts :8765 na pasta Central conectada.

## Segurança

O RPC não permite importar módulos arbitrários nem executar funções fora da allowlist. O cliente não decide `empresa_id`, `filial_id` ou perfil por meio do dicionário `ator`: esses valores são substituídos pela sessão autenticada no servidor.

Não há fallback automático para operações locais quando o servidor está indisponível.

## Limitação declarada

A autoridade foi centralizada nesta entrega. O armazenamento operacional do servidor ainda é SQLite/WAL. PostgreSQL não foi declarado como concluído porque o esquema legado contém SQL, migrations e triggers específicos do SQLite. O novo limite API elimina a dependência do cliente em relação ao banco e prepara uma migração server-side segura e testável.
