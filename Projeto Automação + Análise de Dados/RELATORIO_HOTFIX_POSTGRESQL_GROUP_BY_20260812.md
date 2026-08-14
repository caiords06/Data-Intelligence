# Hotfix PostgreSQL – falha após login / GROUP BY

Data: 12/08/2026
Versão: Data Intelligence V10.1.1

## Causa observada no server.log

O login conclui com HTTP 200. Na primeira carga do cockpit, o Servidor Corporativo chama `enterprise.central.resumo_cockpit`, que calcula os resumos dos módulos. Ao chegar ao Estoque, `gerar_alertas_estoque()` executava uma consulta compatível com o comportamento permissivo do SQLite, mas inválida no PostgreSQL:

```sql
SELECT l.*, i.nome item_nome, s.deposito_id, SUM(s.quantidade_fisica) quantidade
FROM est_lotes l
JOIN est_itens i ON i.id=l.item_id
JOIN est_saldos s ON s.lote_id=l.id
WHERE l.empresa_id=? AND s.filial_id IS ?
  AND s.quantidade_fisica>0 AND l.validade IS NOT NULL
GROUP BY l.id,s.deposito_id
```

`i.nome` não estava agregado nem presente no GROUP BY. PostgreSQL retorna `psycopg.errors.GroupingError`, o RPC devolve HTTP 500 e a tela principal não consegue concluir a carga.

## Correções aplicadas

1. Consulta de alertas de lote: `GROUP BY l.id, i.nome, s.deposito_id`.
2. Listagem de lotes: inclusão de `i.codigo` e `i.nome` no GROUP BY.
3. Consultas de itens/inventários: inclusão das colunas de tabelas associadas no GROUP BY.
4. Operações de estoque: inclusão dos nomes dos depósitos no GROUP BY.
5. Tecnologia: correção de GROUP BY com responsável e remoção de alias de SELECT usado no HAVING.
6. Correio: GROUP BY passou a incluir os campos selecionados de usuário/destinatário.
7. Análise de estoque: removidos aliases de SELECT do HAVING, usando as expressões agregadas diretamente.
8. Cockpit: falha inesperada de um único módulo agora é registrada no log e isolada; não derruba toda a tela principal.
9. Adicionado teste de regressão `test_v10_1_1_postgresql_groupby_cockpit.py`.

## Validação

- `python -m compileall -q`: aprovado.
- 19 testes direcionados de PostgreSQL/pós-login/novo hotfix: aprovados.
- A suíte completa via pytest avançou sem falhas até o limite de tempo do ambiente; os testes direcionados que cobrem esta regressão estão verdes.

## Observação sobre sqlite3.DatabaseError no traceback

O banco que falhou é PostgreSQL (`psycopg.errors.GroupingError`). O nome `sqlite3.DatabaseError` aparece porque o adapter PostgreSQL ainda converte exceções DB-API para tipos legados que o restante da aplicação já captura. Isso não indica que dados estejam sendo gravados em SQLite local.
