ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS mfa_pendente INTEGER NOT NULL DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS mfa_confirmado_em TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS mfa_ultimo_passo BIGINT;

CREATE TABLE IF NOT EXISTS mfa_codigos_recuperacao (
    id BIGSERIAL PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    salt TEXT NOT NULL, codigo_hash TEXT NOT NULL, usado_em TEXT,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS idx_mfa_recuperacao_usuario ON mfa_codigos_recuperacao(usuario_id,usado_em,id);

CREATE TABLE IF NOT EXISTS sessoes_servidor (
    token_hash TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    sessao_epoch INTEGER NOT NULL, criado_em TEXT NOT NULL, ultima_atividade_em TEXT NOT NULL,
    expira_em TEXT NOT NULL, revogado_em TEXT, ip_hash TEXT, cliente TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessoes_usuario_ativas ON sessoes_servidor(usuario_id,revogado_em,expira_em);

CREATE TABLE IF NOT EXISTS api_rate_limits (
    chave_hash TEXT NOT NULL, janela_inicio BIGINT NOT NULL, contador INTEGER NOT NULL DEFAULT 0,
    expira_em BIGINT NOT NULL, PRIMARY KEY(chave_hash,janela_inicio)
);
CREATE INDEX IF NOT EXISTS idx_api_rate_expira ON api_rate_limits(expira_em);

CREATE TABLE IF NOT EXISTS api_idempotencia (
    chave_hash TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    metodo TEXT NOT NULL, caminho TEXT NOT NULL, requisicao_hash TEXT NOT NULL,
    status_http INTEGER, resposta_json TEXT, criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    expira_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS automacao_fila (
    id BIGSERIAL PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    filial_id INTEGER REFERENCES filiais(id), usuario_id INTEGER NOT NULL REFERENCES usuarios(id), handler TEXT NOT NULL,
    titulo TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'Pendente',
    prioridade INTEGER NOT NULL DEFAULT 100, idempotency_key TEXT, tentativa_atual INTEGER NOT NULL DEFAULT 0,
    max_tentativas INTEGER NOT NULL DEFAULT 3, disponivel_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    lease_token TEXT, lease_expira_em TEXT, heartbeat_em TEXT, cancelamento_solicitado INTEGER NOT NULL DEFAULT 0,
    requer_aprovacao INTEGER NOT NULL DEFAULT 0, aprovado_em TEXT, aprovado_por INTEGER REFERENCES usuarios(id),
    resultado_json TEXT, erro TEXT, criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    iniciado_em TEXT, concluido_em TEXT, UNIQUE(empresa_id,idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_automacao_fila_disponivel ON automacao_fila(status,disponivel_em,prioridade,id);

CREATE TABLE IF NOT EXISTS automacao_agendamentos (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id), modulo TEXT NOT NULL, referencia_tipo TEXT, referencia_id BIGINT,
    handler TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', frequencia TEXT NOT NULL, proxima_execucao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1, ultima_execucao TEXT,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,modulo,referencia_tipo,referencia_id)
);
CREATE INDEX IF NOT EXISTS idx_automacao_agenda ON automacao_agendamentos(ativo,proxima_execucao,id);

CREATE TABLE IF NOT EXISTS auditoria_leituras_sensiveis (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id), modulo TEXT NOT NULL, entidade TEXT NOT NULL, entidade_id BIGINT,
    campos TEXT NOT NULL, finalidade TEXT, request_id TEXT,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS idx_auditoria_leitura_sensivel ON auditoria_leituras_sensiveis(empresa_id,entidade,entidade_id,criado_em DESC);

CREATE TABLE IF NOT EXISTS politicas_retencao (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), modulo TEXT NOT NULL, entidade TEXT NOT NULL,
    dias_retencao INTEGER NOT NULL, acao TEXT NOT NULL DEFAULT 'Anonimizar', ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,modulo,entidade)
);

CREATE TABLE IF NOT EXISTS webhook_endpoints (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), nome TEXT NOT NULL, url TEXT NOT NULL,
    eventos_json TEXT NOT NULL DEFAULT '[]', segredo_ref TEXT NOT NULL, ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,nome)
);
CREATE TABLE IF NOT EXISTS webhook_entregas (
    id BIGSERIAL PRIMARY KEY, endpoint_id BIGINT NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    evento_id TEXT NOT NULL, evento_tipo TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pendente', tentativa INTEGER NOT NULL DEFAULT 0,
    status_http INTEGER, resposta_resumo TEXT,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    concluido_em TEXT, UNIQUE(endpoint_id,evento_id)
);

INSERT INTO migracoes_sistema(chave) VALUES ('enterprise_026_hardening_producao') ON CONFLICT(chave) DO NOTHING;
