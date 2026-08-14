# Runbook de produção

## Início do dia

```powershell
Invoke-RestMethod https://SERVIDOR:8770/api/v1/health/ready
```

Confirme PostgreSQL, tarefa do servidor e incidentes de TI. Verifique alertas críticos do Analytics.

Colete `/api/v1/metrics` com uma conta técnica administrativa protegida e alerte para erros 5xx, dead-letter, fila crescendo, sessões anormais, agentes offline, backup atrasado e indisponibilidade do PostgreSQL.

## Incidente

1. obtenha horário, usuário, módulo e `X-Request-ID`;
2. confirme `/health/live` e `/health/ready`;
3. teste TCP/8770 a partir da estação afetada;
4. consulte logs do Servidor Corporativo;
5. confirme PostgreSQL;
6. diferencie falha de rede, autenticação, permissão, domínio e UI;
7. não altere banco manualmente sem plano/backup;
8. registre correção e validação.

## Critério de recuperação

Servidor `ready`, login válido, contexto empresa/filial carregado, operação de leitura/escrita de teste autorizada, Analytics consultável e nenhum erro crítico no log após o smoke.

Antes de liberar uma versão, execute `scripts/teste_carga_api.py`, restauração real em staging, integração PostgreSQL, smoke visual e instalação silenciosa/interativa em snapshots Windows limpos.
