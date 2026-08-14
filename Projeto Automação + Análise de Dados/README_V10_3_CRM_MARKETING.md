# V10.3.0 — CRM compartilhado e Marketing especializado

## Objetivo

Marketing deixa de usar o workspace genérico de `recursos_departamentais` e passa a possuir domínio, serviço, navegação e interface especializados. O CRM compartilhado nasce como núcleo único para empresas, contatos, leads e atividades, preparando a próxima especialização do Comercial sem duplicar cadastros.

## Estrutura nova

- `enterprise/crm.py`
- `enterprise/marketing.py`
- `services/departamentos/marketing.py`
- `interface/marketing.py`
- migration `020_v10_3_crm_marketing`

## Dados

O schema acrescenta empresas/contatos/leads/atividades CRM, canais, campanhas especializadas, conteúdo, automações e métricas de Marketing. A tabela legada `campanhas_marketing` é preservada e migrada de forma idempotente para `marketing_campanhas`.

## Marketing

O Growth Studio oferece Visão geral, Campanhas, Leads, CRM e contatos, Canais, Calendário, Conteúdo, Automações, Atribuição e Relatórios. Os indicadores principais incluem investimento, leads, MQL, conversões, CPL, CAC, receita atribuída e ROAS.

## Compatibilidade

A rota antiga `marketing/registros` é normalizada para `marketing/campanhas`. Os dados legados não são apagados durante a migração.
