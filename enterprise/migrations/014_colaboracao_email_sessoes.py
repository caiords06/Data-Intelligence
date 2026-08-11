"""Colaboração interna, email corporativo e revogação efetiva de sessão."""

from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    return {str(x["name"]) for x in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()}


def upgrade(conexao) -> None:
    colunas_usuarios = _colunas(conexao, "usuarios")
    if "email_corporativo" not in colunas_usuarios:
        conexao.execute("ALTER TABLE usuarios ADD COLUMN email_corporativo TEXT")
    if "sessao_epoch" not in colunas_usuarios:
        conexao.execute("ALTER TABLE usuarios ADD COLUMN sessao_epoch INTEGER NOT NULL DEFAULT 0")

    conexao.execute(
        """UPDATE usuarios
           SET email_corporativo = LOWER(usuario) || '@dataintelligence.local'
           WHERE email_corporativo IS NULL OR TRIM(email_corporativo)=''"""
    )
    conexao.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_email_corporativo
           ON usuarios(LOWER(email_corporativo))
           WHERE email_corporativo IS NOT NULL AND TRIM(email_corporativo)<>''"""
    )

    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS correio_mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            remetente_id INTEGER NOT NULL,
            assunto TEXT NOT NULL,
            corpo TEXT NOT NULL,
            modulo_origem TEXT,
            resposta_de_id INTEGER,
            encaminhada_de_id INTEGER,
            rascunho INTEGER NOT NULL DEFAULT 0 CHECK (rascunho IN (0,1)),
            excluida_remetente INTEGER NOT NULL DEFAULT 0 CHECK (excluida_remetente IN (0,1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            enviado_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (remetente_id) REFERENCES usuarios(id),
            FOREIGN KEY (resposta_de_id) REFERENCES correio_mensagens(id),
            FOREIGN KEY (encaminhada_de_id) REFERENCES correio_mensagens(id)
        );

        CREATE TABLE IF NOT EXISTS correio_destinatarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'PARA' CHECK (tipo IN ('PARA','CC','CCO')),
            lida_em TEXT,
            arquivada INTEGER NOT NULL DEFAULT 0 CHECK (arquivada IN (0,1)),
            excluida INTEGER NOT NULL DEFAULT 0 CHECK (excluida IN (0,1)),
            estrela INTEGER NOT NULL DEFAULT 0 CHECK (estrela IN (0,1)),
            FOREIGN KEY (mensagem_id) REFERENCES correio_mensagens(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            UNIQUE (mensagem_id, usuario_id, tipo)
        );

        CREATE TABLE IF NOT EXISTS correio_anexos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            arquivo_relativo TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mensagem_id) REFERENCES correio_mensagens(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_correio_destinatario_caixa
            ON correio_destinatarios(usuario_id, excluida, arquivada, mensagem_id);
        CREATE INDEX IF NOT EXISTS idx_correio_remetente
            ON correio_mensagens(remetente_id, excluida_remetente, id);

        CREATE TABLE IF NOT EXISTS arquivos_corporativos (
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

        CREATE TABLE IF NOT EXISTS backups_empresariais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            filial_id INTEGER,
            tipo TEXT NOT NULL DEFAULT 'Completo',
            arquivo_relativo TEXT NOT NULL,
            manifesto_relativo TEXT,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            restaurado_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        """
    )
