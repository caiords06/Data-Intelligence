"""Hardening de produção: MFA, sessões, filas, privacidade e API."""
from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    return {str(item["name"]) for item in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()}


def upgrade(conexao) -> None:
    colunas = _colunas(conexao, "usuarios")
    for nome, definicao in (
        ("mfa_pendente", "INTEGER NOT NULL DEFAULT 0"),
        ("mfa_confirmado_em", "TEXT"),
        ("mfa_ultimo_passo", "INTEGER"),
    ):
        if nome not in colunas:
            conexao.execute(f"ALTER TABLE usuarios ADD COLUMN {nome} {definicao}")

    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS mfa_codigos_recuperacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            salt TEXT NOT NULL,
            codigo_hash TEXT NOT NULL,
            usado_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_mfa_recuperacao_usuario
            ON mfa_codigos_recuperacao(usuario_id, usado_em, id);

        CREATE TABLE IF NOT EXISTS sessoes_servidor (
            token_hash TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            sessao_epoch INTEGER NOT NULL,
            criado_em TEXT NOT NULL,
            ultima_atividade_em TEXT NOT NULL,
            expira_em TEXT NOT NULL,
            revogado_em TEXT,
            ip_hash TEXT,
            cliente TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id)
        );
        CREATE INDEX IF NOT EXISTS idx_sessoes_usuario_ativas
            ON sessoes_servidor(usuario_id, revogado_em, expira_em);

        CREATE TABLE IF NOT EXISTS api_rate_limits (
            chave_hash TEXT NOT NULL,
            janela_inicio INTEGER NOT NULL,
            contador INTEGER NOT NULL DEFAULT 0,
            expira_em INTEGER NOT NULL,
            PRIMARY KEY (chave_hash, janela_inicio)
        );
        CREATE INDEX IF NOT EXISTS idx_api_rate_expira ON api_rate_limits(expira_em);

        CREATE TABLE IF NOT EXISTS api_idempotencia (
            chave_hash TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            metodo TEXT NOT NULL,
            caminho TEXT NOT NULL,
            requisicao_hash TEXT NOT NULL,
            status_http INTEGER,
            resposta_json TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expira_em TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS automacao_fila (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER NOT NULL,
            handler TEXT NOT NULL,
            titulo TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'Pendente',
            prioridade INTEGER NOT NULL DEFAULT 100,
            idempotency_key TEXT,
            tentativa_atual INTEGER NOT NULL DEFAULT 0,
            max_tentativas INTEGER NOT NULL DEFAULT 3,
            disponivel_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            lease_token TEXT,
            lease_expira_em TEXT,
            heartbeat_em TEXT,
            cancelamento_solicitado INTEGER NOT NULL DEFAULT 0,
            requer_aprovacao INTEGER NOT NULL DEFAULT 0,
            aprovado_em TEXT,
            aprovado_por INTEGER,
            resultado_json TEXT,
            erro TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            iniciado_em TEXT,
            concluido_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (aprovado_por) REFERENCES usuarios(id),
            UNIQUE (empresa_id, idempotency_key)
        );
        CREATE INDEX IF NOT EXISTS idx_automacao_fila_disponivel
            ON automacao_fila(status, disponivel_em, prioridade, id);

        CREATE TABLE IF NOT EXISTS automacao_agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            referencia_tipo TEXT,
            referencia_id INTEGER,
            handler TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            frequencia TEXT NOT NULL,
            proxima_execucao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            ultima_execucao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            UNIQUE (empresa_id, modulo, referencia_tipo, referencia_id)
        );
        CREATE INDEX IF NOT EXISTS idx_automacao_agenda
            ON automacao_agendamentos(ativo, proxima_execucao, id);

        CREATE TABLE IF NOT EXISTS auditoria_leituras_sensiveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            entidade TEXT NOT NULL,
            entidade_id INTEGER,
            campos TEXT NOT NULL,
            finalidade TEXT,
            request_id TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_auditoria_leitura_sensivel
            ON auditoria_leituras_sensiveis(empresa_id, entidade, entidade_id, criado_em DESC);

        CREATE TABLE IF NOT EXISTS politicas_retencao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            entidade TEXT NOT NULL,
            dias_retencao INTEGER NOT NULL,
            acao TEXT NOT NULL DEFAULT 'Anonimizar',
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, modulo, entidade),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS webhook_endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            url TEXT NOT NULL,
            eventos_json TEXT NOT NULL DEFAULT '[]',
            segredo_ref TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS webhook_entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_id INTEGER NOT NULL,
            evento_id TEXT NOT NULL,
            evento_tipo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente',
            tentativa INTEGER NOT NULL DEFAULT 0,
            status_http INTEGER,
            resposta_resumo TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TEXT,
            UNIQUE(endpoint_id, evento_id),
            FOREIGN KEY (endpoint_id) REFERENCES webhook_endpoints(id) ON DELETE CASCADE
        );
        """
    )
