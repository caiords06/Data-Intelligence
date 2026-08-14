# V10.1.1 — PostgreSQL + Server First (estabilidade)

A linha V10.1 torna o Servidor Corporativo a autoridade transacional da plataforma. Estações Cliente e Central não mantêm SQLite persistente. Identidade/contexto de sessão ficam em memória e toda persistência transacional é executada no Servidor Corporativo/PostgreSQL.

## Backends

- `postgresql`: recomendado para Servidor Corporativo multiusuário.
- `sqlite`: desativado em produção; permanece somente como origem de migração e backend unitário de testes quando liberado explicitamente.

## Configuração

O servidor lê `db_backend` e os parâmetros PostgreSQL de `server.json`. A senha não é gravada no JSON: no Windows ela é protegida por DPAPI em `ProgramData\DataIntelligence\Server\secrets\postgres.dpapi`.

Comandos:

```powershell
DataIntelligenceServer.exe configure-db --bootstrap-file db-bootstrap.json
DataIntelligenceServer.exe check-db
DataIntelligenceServer.exe migrate-sqlite --source C:\ProgramData\DataIntelligence\Server\app.db
```

## Migração V10.0 -> V10.1

O Setup V10.1 detecta `app.db` no servidor e, quando PostgreSQL é selecionado, executa uma migração preservando IDs, relações e sequences. O SQLite original não é apagado. Um marcador impede repetição acidental da migração.

## Arquitetura

```text
Cliente / Central
       | HTTPS/RPC
       v
Servidor Corporativo
       |
       v
Services / Domains / Repositories
       |
       v
PostgreSQL
```

## Backup

No backend PostgreSQL, backups usam `pg_dump` em formato custom e são verificados com `pg_restore --list`. Restauração usa `pg_restore`. Backups SQLite antigos continuam apenas como formato de compatibilidade/migração; novos backups de produção são PostgreSQL.
