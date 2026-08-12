# Arquitetura canônica V9.2

A partir da estabilização V9.2, novas funcionalidades devem usar uma única rota arquitetural. Componentes antigos permanecem somente como **adapters de compatibilidade para upgrade** e não são fontes de verdade para novos recursos.

## Componentes canônicos

- **Servidor corporativo:** `servidor_corporativo/`
- **Agentes e telemetria de TI:** `agente_ti/`, `servidor_ti/` e tabelas `ti_agentes`/`ti_ativos`
- **Correio corporativo:** `enterprise/correio.py`
- **Sessão:** `auth.sessao.SESSAO.validar()` + `enterprise.contexto.garantir_contexto_sessao()`
- **Migrations:** somente os módulos enumerados em `enterprise.migrations.MIGRACOES`, com prefixo numérico único
- **Armazenamento remoto:** endpoints `/api/v1/files` e `/api/v1/backups` do servidor corporativo

## Compatibilidade legada

Os seguintes componentes continuam disponíveis apenas para migração e testes de contratos históricos:

- `servidor/`
- `enterprise/comunicacao.py`
- `enterprise/nos_plataforma.py`
- tabelas `mensagens`, `mensagem_destinatarios`, `mensagem_anexos`, `nos_plataforma`, `tokens_api` e `nonces_agente`

A migration `019_compatibilidade_v9_legada` cria/normaliza esses contratos quando necessário, inclusive em instalações limpas que ainda executam rotas de compatibilidade. Novas features não devem depender dessas tabelas.

## Regra de evolução

1. Mudanças novas entram apenas nos componentes canônicos.
2. Adapter legado só recebe correções de segurança, integridade ou migração.
3. Toda migration nova recebe um número nunca reutilizado.
4. A remoção de um adapter exige antes uma migration de dados e remoção dos testes que documentam o contrato antigo.
5. O build do servidor deve continuar apontando para `servidor_corporativo`.
