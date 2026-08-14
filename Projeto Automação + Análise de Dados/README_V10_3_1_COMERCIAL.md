# V10.3.1 — Comercial especializado

O Comercial deixa o renderizador departamental genérico e passa a usar o **Revenue Workspace**. O módulo reutiliza `crm_empresas`, `crm_contatos` e `crm_leads`, evitando duplicidade entre Marketing e Vendas.

Entregas: pipeline configurável, oportunidades com valor/probabilidade/próxima ação, atividades, propostas, metas, forecast ponderado, resumo para Analytics, serviço departamental, RPC Server First e migration `021_v10_3_1_comercial`.

A tabela legada `oportunidades_comerciais` é preservada. Seus registros são copiados idempotentemente para `comercial_oportunidades` por `legacy_oportunidade_id`.
