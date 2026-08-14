# Relatório de hardening de produção — Data Intelligence V10.5.0

Data de fechamento: 13/08/2026

## Resultado executivo

O hardening prioritário solicitado foi implementado no código-fonte da plataforma. A entrega cobre autenticação multifator obrigatória, sessões persistentes, motor durável de automações, contratos HTTP, segurança/LGPD, backup cifrado, observabilidade, atualização assinada com rollback e controles de qualidade do release.

A classificação correta desta entrega é **candidato pronto para homologação em ambiente controlado**. Nenhum exame somente de código substitui a homologação com PostgreSQL, TLS, cofre de segredos, Windows limpo, carga real, restauração e pentest na infraestrutura de destino.

## Matriz de atendimento

| Prioridade | Implementação entregue | Evidência principal |
|---|---|---|
| MFA obrigatório | TOTP exigido em todos os logins quando habilitado; preparação e confirmação separadas; bloqueio de replay; recuperação de uso único; revogação por epoch | `auth/mfa.py`, `auth/autenticacao.py`, `interface/login.py` |
| Proteção de segredos | AES-256-GCM com chave de ambiente ou DPAPI; segredos TOTP e webhooks cifrados; códigos de recuperação com scrypt | `core/criptografia.py`, `enterprise/webhooks.py` |
| Sessões compartilhadas | Tokens aleatórios, somente hash no banco, validade/atividade, persistência após reinício, lista e revogação remota | `servidor_corporativo/sessoes.py` |
| Automações reais | Fila persistente, scheduler, workers, lease renovável, tentativas com backoff, idempotência, cancelamento, dead-letter, reprocessamento e aprovação | `enterprise/automacao_motor.py` |
| API corporativa | OpenAPI 3.1, DTOs/validações, envelope de erro, request ID, rate limit, idempotency key e concorrência otimista | `servidor_corporativo/openapi.py`, `dto.py`, `controles_api.py`, `app.py` |
| Webhooks | HMAC-SHA256 com timestamp, entrega via fila, tentativas, estado de entrega e proteção SSRF/HTTPS | `enterprise/webhooks.py` |
| Camada de serviços | Fachadas explícitas e contratos compartilháveis entre desktop, web, API e automações | `services/` |
| LGPD | Classificação, mascaramento, auditoria de leitura, retenção simulável, anonimização e descarte seguro de anexos | `enterprise/privacidade.py`, `enterprise/rh.py` |
| Backups | `.dibak` com AES-256-GCM, autenticação antes de restaurar, restauração por fila com confirmação e aprovação humana | `enterprise/backups.py`, `servidor_corporativo/app.py` |
| TLS/produção | Bind remoto de produção falha fechado sem TLS; PostgreSQL remoto exige modo SSL seguro | `servidor_corporativo/config.py` |
| Observabilidade | Liveness/readiness, detalhes administrativos, métricas Prometheus e contadores de fila/sessão | `core/observabilidade.py`, `servidor_corporativo/app.py` |
| Atualização | Manifesto Ed25519, SHA-256/tamanho, download HTTPS público sem redirect, ZIP seguro, anti-downgrade e helper externo com rollback | `core/atualizacoes.py`, `scripts/update_helper.py` |
| Qualidade | Compile, auditoria de camadas, detecção de exceções silenciosas, Ruff, mypy incremental, coverage, Bandit, pip-audit e SBOM no CI | `pyproject.toml`, `.github/workflows/quality.yml` |

## Mudanças de dados

A migração `026_hardening_producao` adiciona estruturas equivalentes em SQLite de desenvolvimento/teste e PostgreSQL de produção:

- estado pendente/confirmado e proteção contra replay do MFA;
- códigos de recuperação;
- sessões persistentes;
- janelas compartilhadas de rate limit;
- respostas idempotentes;
- fila e agendamentos de automação;
- auditoria de leituras sensíveis;
- políticas de retenção;
- endpoints e entregas de webhooks.

Arquivos: `enterprise/migrations/026_hardening_producao.py` e `enterprise/postgresql/schema_hardening.sql`.

## Contratos operacionais adicionados

- `GET /api/v1/openapi.json`
- `GET /api/v1/health/ready` e `GET /api/v1/health/details`
- `GET /api/v1/metrics`
- `GET /api/v1/account/sessions` e `POST /api/v1/account/sessions/revoke-all`
- `POST /api/v1/account/mfa/setup`, `/confirm`, `/recovery/regenerate` e `/disable`
- `GET /api/v1/automations/jobs`
- `POST /api/v1/automations/jobs/{id}/approve|cancel|reprocess`
- `GET|POST /api/v1/webhooks` e `POST /api/v1/webhooks/events`
- `GET /api/v1/privacy/read-audit`
- `POST /api/v1/privacy/retention/policies` e `/run-rh`
- `POST /api/v1/backups/{id}/restore`
- `PATCH /api/v1/users/{id}` com `If-Match`

POSTs públicos de negócio aceitam `Idempotency-Key`. Erros seguem `ok=false`, `error.code`, `error.message` e `request_id`, mantendo o campo legado `erro` durante a transição.

## Configuração segura obrigatória

Em produção, as chaves abaixo devem vir de cofre de segredos e não de arquivos versionados:

- `DATA_INTELLIGENCE_MFA_MASTER_KEY`
- `DATA_INTELLIGENCE_BACKUP_MASTER_KEY`
- `DATA_INTELLIGENCE_WEBHOOK_MASTER_KEY`
- `DATA_INTELLIGENCE_UPDATE_PUBLIC_KEY`
- credencial PostgreSQL referenciada por `DATA_INTELLIGENCE_PG_PASSWORD`

As três chaves mestras simétricas devem decodificar para 32 bytes. A chave de atualização é a chave pública Ed25519 de 32 bytes em Base64. `DATA_INTELLIGENCE_ALLOW_SIGNED_DOWNGRADE=1` existe apenas para recuperação operacional deliberada e não deve permanecer habilitada.

## Validações executadas nesta entrega

- 55 arquivos de testes `unittest` executados em processos isolados;
- 377 testes concluídos, sem falhas;
- 6 regressões específicas de hardening aprovadas;
- compilação integral por `compileall` aprovada;
- auditoria de exceções silenciosas aprovada;
- auditoria de arquitetura em camadas aprovada;
- contratos estáticos do instalador V10.5.0 aprovados;
- smoke de importação das fachadas de serviços aprovado;
- smoke de backup cifrado, sessão persistente, MFA e fila durável aprovado.

Os logs esperados de testes de falha controlada (dead-letter, HTTP 500 simulado e bloqueio de caminho fora do storage) comprovam que as exceções são registradas, e não suprimidas.

## Validações que exigem o ambiente de destino

Estes itens estão automatizados ou instrumentados, mas **não foram declarados como homologados localmente**:

1. migração e concorrência contra PostgreSQL real;
2. teste de carga com perfil representativo de usuários e dados;
3. backup e restauração completos em cópia de homologação;
4. build, instalação, atualização e rollback em Windows limpo;
5. cadeia TLS, proxy reverso, CORS e rota de métricas no ambiente corporativo;
6. pentest autenticado e não autenticado;
7. rotação das chaves, restauração de desastre e revogação de sessões entre múltiplas instâncias;
8. validação jurídica das políticas de retenção e bases legais da organização.

O workflow de CI inclui PostgreSQL 17 e build Windows. O utilitário `scripts/teste_carga_api.py` oferece a base para o ensaio de carga; seus limites devem ser definidos conforme o SLA real.

## Gate recomendado para produção

1. Gerar e custodiar as chaves em cofre, com backup separado e acesso auditado.
2. Restaurar cópia anonimizada de dados no PostgreSQL de homologação.
3. Aplicar a migração 026 e validar contagens, integridade e plano de rollback.
4. Executar toda a CI, inclusive PostgreSQL, screenshots e build Windows.
5. Ensaiar backup/restauração e registrar RPO/RTO medidos.
6. Executar carga, concorrência, indisponibilidade parcial e recuperação de workers.
7. Realizar pentest e corrigir achados bloqueadores.
8. Homologar o instalador e o atualizador em máquinas Windows limpas.
9. Definir dashboards/alertas e responsáveis de plantão.
10. Fazer implantação piloto com grupo pequeno, rollback preparado e aceite formal.

## Próximo ciclo funcional

Com o núcleo protegido, a expansão dos departamentos deve reutilizar os mesmos casos de uso, eventos, permissões, filas e auditoria. A prioridade funcional sugerida é completar a jornada do colaborador (perfil com foto, documentos, ativos, tarefas, acessos e linha do tempo), seguida pelos fluxos ponta a ponta de admissão, compras/reposição, oportunidade/faturamento e atendimento/incidente. Novos caminhos de interface devem convergir no mesmo serviço, em vez de duplicar regras de negócio.
