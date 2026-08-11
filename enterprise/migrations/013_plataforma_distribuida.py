"""Base V9 para comunicação, sincronização e operação distribuída.

A migração é idempotente e preserva instalações anteriores. Dados binários
continuam fora do SQLite; o banco registra identidade, integridade e localização.
"""

from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    existe = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
    ).fetchone()
    if existe is None:
        return set()
    return {str(item["name"]) for item in conexao.execute(f"PRAGMA table_info({tabela})")}


def _adicionar(conexao, tabela: str, coluna: str, definicao: str) -> None:
    if coluna not in _colunas(conexao, tabela):
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def upgrade(conexao) -> None:
    _adicionar(conexao, "usuarios", "email_corporativo", "TEXT")
    _adicionar(conexao, "backups", "manifesto_json", "TEXT NOT NULL DEFAULT '{}'")
    _adicionar(conexao, "backups", "tipo", "TEXT NOT NULL DEFAULT 'Completo'")
    _adicionar(conexao, "backups", "armazenamento_remoto", "TEXT")
    _adicionar(conexao, "relatorios_corporativos", "formato_arquivo", "TEXT")

    # Compatibilidade com uma prévia interna que usou o prefixo ``cmp_``.
    # A migração oficial preserva os dados caso essa prévia tenha sido aberta.
    antiga = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cmp_aprovacoes_etapas'"
    ).fetchone()
    nova = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='aprovacoes_compras_etapas'"
    ).fetchone()
    if antiga is not None and nova is None:
        conexao.execute(
            "ALTER TABLE cmp_aprovacoes_etapas RENAME TO aprovacoes_compras_etapas"
        )

    conexao.executescript(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email_corporativo
            ON usuarios (email_corporativo COLLATE NOCASE)
            WHERE email_corporativo IS NOT NULL;

        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            remetente_id INTEGER NOT NULL,
            assunto TEXT NOT NULL,
            corpo TEXT NOT NULL,
            prioridade TEXT NOT NULL DEFAULT 'Normal'
                CHECK (prioridade IN ('Baixa', 'Normal', 'Alta', 'Urgente')),
            status TEXT NOT NULL DEFAULT 'Enviada'
                CHECK (status IN ('Rascunho', 'Enviada', 'Cancelada')),
            resposta_de_id INTEGER,
            conversa_id TEXT NOT NULL,
            enviada_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (remetente_id) REFERENCES usuarios(id),
            FOREIGN KEY (resposta_de_id) REFERENCES mensagens(id)
        );

        CREATE TABLE IF NOT EXISTS mensagem_destinatarios (
            mensagem_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Para'
                CHECK (tipo IN ('Para', 'Cc', 'Cco')),
            lida INTEGER NOT NULL DEFAULT 0 CHECK (lida IN (0, 1)),
            lida_em TEXT,
            arquivada INTEGER NOT NULL DEFAULT 0 CHECK (arquivada IN (0, 1)),
            excluida INTEGER NOT NULL DEFAULT 0 CHECK (excluida IN (0, 1)),
            PRIMARY KEY (mensagem_id, usuario_id, tipo),
            FOREIGN KEY (mensagem_id) REFERENCES mensagens(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS mensagem_anexos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem_id INTEGER NOT NULL,
            nome_original TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL,
            hash_sha256 TEXT NOT NULL,
            mime_type TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mensagem_id) REFERENCES mensagens(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_mensagens_empresa_data
            ON mensagens (empresa_id, criado_em DESC);
        CREATE INDEX IF NOT EXISTS idx_destinatarios_usuario_caixa
            ON mensagem_destinatarios (usuario_id, excluida, arquivada, lida);

        CREATE TABLE IF NOT EXISTS nos_plataforma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            identificador TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('Servidor', 'Central', 'Agente')),
            versao TEXT,
            sistema TEXT,
            endereco_ip TEXT,
            chave_publica TEXT,
            token_hash TEXT,
            segredo_ref TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente', 'Ativo', 'Bloqueado', 'Revogado', 'Offline')),
            ultimo_heartbeat TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS tokens_api (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            usuario_id INTEGER,
            no_id INTEGER,
            nome TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            escopos TEXT NOT NULL DEFAULT '[]',
            expira_em TEXT,
            revogado_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (no_id) REFERENCES nos_plataforma(id)
        );

        CREATE TABLE IF NOT EXISTS nonces_agente (
            agent_id TEXT NOT NULL,
            nonce TEXT NOT NULL,
            usado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (agent_id, nonce)
        );
        CREATE INDEX IF NOT EXISTS idx_nonces_agente_data
            ON nonces_agente (usado_em);

        CREATE TABLE IF NOT EXISTS arquivos_corporativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            recurso_tipo TEXT,
            recurso_id INTEGER,
            nome_original TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL,
            versao INTEGER NOT NULL DEFAULT 1,
            armazenamento TEXT NOT NULL DEFAULT 'Local'
                CHECK (armazenamento IN ('Local', 'Servidor', 'Local+Servidor')),
            estado TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (estado IN ('Ativo', 'Arquivado', 'Lixeira')),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fila_sincronizacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            no_id INTEGER,
            direcao TEXT NOT NULL CHECK (direcao IN ('Upload', 'Download', 'Evento')),
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER,
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente', 'Executando', 'Concluído', 'Erro', 'Cancelado')),
            tentativas INTEGER NOT NULL DEFAULT 0,
            proxima_tentativa TEXT,
            erro TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (no_id) REFERENCES nos_plataforma(id)
        );

        CREATE INDEX IF NOT EXISTS idx_fila_sync_status
            ON fila_sincronizacao (status, proxima_tentativa, id);
        CREATE INDEX IF NOT EXISTS idx_arquivos_corporativos_escopo
            ON arquivos_corporativos (empresa_id, filial_id, modulo, estado);

        CREATE TABLE IF NOT EXISTS aprovacoes_compras_etapas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            nivel INTEGER NOT NULL,
            papel_aprovador TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente', 'Aprovado', 'Rejeitado', 'Alteração solicitada')),
            aprovador_id INTEGER,
            comentario TEXT,
            decidido_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (recurso_tipo, recurso_id, nivel, papel_aprovador),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (aprovador_id) REFERENCES usuarios(id)
        );
        """
    )

    # Endereços internos determinísticos para usuários existentes.
    conexao.execute(
        """
        UPDATE usuarios
        SET email_corporativo = lower(usuario) || '@empresa.local'
        WHERE email_corporativo IS NULL OR trim(email_corporativo)=''
        """
    )
