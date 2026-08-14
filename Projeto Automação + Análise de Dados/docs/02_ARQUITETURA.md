# Arquitetura

## Fluxo principal

```text
Tkinter / futuro Web
        ↓
services/
        ↓
enterprise/ (domínios e regras)
        ↓
Servidor Corporativo :8770
        ↓
PostgreSQL
```

A interface não deve importar `enterprise.*` diretamente. As fachadas em `services/` são o contrato estável entre UI e domínio. Em Central/Cliente, as operações permitidas são encaminhadas ao Servidor Corporativo por RPC/API; em processo servidor, executam no domínio local contra PostgreSQL.

## Persistência

PostgreSQL é obrigatório em produção. SQLite existe somente para testes/migração legada explicitamente habilitados. Não há fallback automático local.

## API

O RPC restrito continua sendo o canal compatível do desktop. A API `/api/v1` oferece contratos explícitos para integrações e futuro front-end web, com bearer, escopo empresa/filial, validação, paginação e request ID.

## Orquestrações

Fluxos Marketing→Comercial, Estoque→Compras, Jurídico→Financeiro e RH→TI/Estoque/Administrativo/Financeiro são registrados em `orquestracoes_empresariais` e `orquestracao_etapas`. O objetivo é centralizar continuidade operacional sem criar ações financeiras ou de segurança irreversíveis sem confirmação do módulo responsável.
