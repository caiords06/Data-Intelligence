# PostgreSQL

## Papel

PostgreSQL é a fonte oficial de autenticação, organização, módulos, Analytics, orquestrações, arquivos (metadados), histórico e preferências. Nenhuma estação Central/Cliente deve abrir SQL diretamente.

## Health

```powershell
Get-Service *postgres*
pg_isready
Invoke-RestMethod http://127.0.0.1:8770/api/v1/health/details
```

`pg_isready` é opcional e depende de as ferramentas do PostgreSQL estarem no PATH.

## Schema

`schema_v10_1.sql` é o baseline histórico de instalações PostgreSQL. Extensões posteriores são aplicadas idempotentemente pelo bootstrap de runtime; a lista esperada é validada no health. Migrations SQLite em `enterprise/migrations/` continuam servindo testes/migração legada, não substituem a autoridade PostgreSQL.

## Segurança

Use usuário dedicado, senha forte e escopo de rede restrito. Para ambientes além de LAN privada, configure TLS e `sslmode=require/verify-ca/verify-full` conforme a infraestrutura de certificados.
