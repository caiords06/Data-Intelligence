"""Compatibilidade segura com componentes V9 legados ainda suportados.

Esta migração substitui a antiga ``013_plataforma_distribuida`` que não fazia
parte do registry e confligia com o schema atual de ``arquivos_corporativos``.
Ela cria somente as estruturas ainda consumidas por adapters legados e também
normaliza instalações antigas para o schema canônico do Servidor Corporativo.
"""

from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    existe = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
    ).fetchone()
    if existe is None:
        return set()
    return {
        str(item["name"])
        for item in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
    }


def _normalizar_arquivos_corporativos(conexao) -> None:
    """Converte a prévia V9 para o schema usado pelo servidor atual.

    A versão interna antiga tinha ``nome_original/hash_sha256/estado``. O
    servidor atual usa ``nome/sha256/excluido_em``. A reconstrução preserva os
    IDs e os metadados úteis sem manter duas fontes de verdade.
    """
    colunas = _colunas(conexao, "arquivos_corporativos")
    if not colunas:
        return
    canonicas = {
        "id", "empresa_id", "filial_id", "modulo", "categoria", "nome",
        "caminho_relativo", "tamanho_bytes", "sha256", "origem",
        "criado_por", "criado_em", "excluido_em",
    }
    if canonicas.issubset(colunas):
        return
    antigas = {"nome_original", "hash_sha256", "estado"}
    if not antigas.issubset(colunas):
        # Um schema desconhecido não deve ser destruído silenciosamente.
        return

    conexao.execute("PRAGMA foreign_keys=OFF")
    try:
        conexao.executescript(
            """
            ALTER TABLE arquivos_corporativos RENAME TO arquivos_corporativos_v9_legado;

            CREATE TABLE arquivos_corporativos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT,
                categoria TEXT NOT NULL DEFAULT 'arquivo',
                nome TEXT NOT NULL,
                caminho_relativo TEXT NOT NULL,
                tamanho_bytes INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT,
                origem TEXT NOT NULL DEFAULT 'local',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                excluido_em TEXT,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            INSERT INTO arquivos_corporativos (
                id, empresa_id, filial_id, modulo, categoria, nome,
                caminho_relativo, tamanho_bytes, sha256, origem,
                criado_por, criado_em, excluido_em
            )
            SELECT
                id,
                empresa_id,
                filial_id,
                NULLIF(TRIM(modulo), ''),
                COALESCE(NULLIF(TRIM(recurso_tipo), ''), 'arquivo'),
                nome_original,
                caminho_relativo,
                tamanho_bytes,
                hash_sha256,
                CASE LOWER(COALESCE(armazenamento, 'local'))
                    WHEN 'servidor' THEN 'servidor'
                    WHEN 'local+servidor' THEN 'sincronizado'
                    ELSE 'local'
                END,
                criado_por,
                criado_em,
                CASE WHEN estado='Lixeira' THEN atualizado_em ELSE NULL END
            FROM arquivos_corporativos_v9_legado;

            DROP TABLE arquivos_corporativos_v9_legado;

            CREATE INDEX IF NOT EXISTS idx_arquivos_corporativos_escopo_atual
                ON arquivos_corporativos (empresa_id, filial_id, modulo, excluido_em);
            """
        )
    finally:
        conexao.execute("PRAGMA foreign_keys=ON")


def upgrade(conexao) -> None:
    _normalizar_arquivos_corporativos(conexao)
    conexao.executescript(
        """
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
        """
    )
