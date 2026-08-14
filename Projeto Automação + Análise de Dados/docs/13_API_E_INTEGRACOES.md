# API v1 e integrações

## Princípios

O RPC permanece interno/compatível com o desktop. A API REST v1 é o contrato para integrações e futuro front-end Web. Todas as rotas abaixo exigem bearer válido, exceto health/login.

## Recursos iniciais

```text
GET/POST /api/v1/crm/leads
GET/POST /api/v1/comercial/oportunidades
GET/POST /api/v1/marketing/campanhas
GET/POST /api/v1/juridico/processos
GET/POST /api/v1/administrativo/solicitacoes
GET      /api/v1/analytics/insights
POST     /api/v1/analytics/insights/refresh
GET      /api/v1/analytics/executive
GET      /api/v1/orquestracoes
POST     /api/v1/crm/leads/to-opportunity
```

Listagens aceitam `page` e `page_size` (máximo 100), além dos filtros documentados por recurso (`q`, `status`, `modulo`, `severidade`). Respostas novas usam envelope:

```json
{
  "ok": true,
  "data": [],
  "pagination": {"page": 1, "page_size": 50, "total": 0, "has_next": false},
  "request_id": "..."
}
```

Erros de rotas v1 explícitas usam `error.code`, `error.message` e `request_id`. O header `X-Request-ID` deve ser registrado pelo consumidor para suporte.

## Provedores

`enterprise/integrations/` define contratos de capacidade para SMTP, Microsoft 365, Google Workspace e API HTTP/Webhook. Isso é um framework de homologação: uma capacidade catalogada não é apresentada como conectada até existir registro ativo e credencial válida no cofre/referência segura.
