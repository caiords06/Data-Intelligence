# V10.3.2 — Administrativo especializado

O Administrativo passa a usar o **Workplace Operations** com fluxo próprio. A experiência deixa de depender de `TelaOperacaoVisual` para as rotas principais.

Entregas: central de solicitações com número, prioridade e SLA; recursos; reservas com prevenção de conflito; facilities/manutenção; viagens; reembolsos; resumo e exportação para Analytics; RPC Server First e migration `022_v10_3_2_administrativo`.

A tabela `solicitacoes_administrativas` continua preservada e é migrada idempotentemente por `legacy_solicitacao_id`.
