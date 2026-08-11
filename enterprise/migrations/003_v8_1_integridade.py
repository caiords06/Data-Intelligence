"""Integridade multiempresa, histórico seguro e biblioteca de dados V8.1."""

from __future__ import annotations


TABELAS_COM_ESCOPO = (
    "colaboradores",
    "lancamentos_financeiros",
    "itens_estoque",
    "movimentos_estoque",
    "solicitacoes_compra",
    "chamados_ti",
    "ativos_ti",
    "campanhas_marketing",
    "solicitacoes_administrativas",
    "contratos_juridicos",
    "oportunidades_comerciais",
    "aprovacoes",
    "tarefas",
    "documentos",
    "integracoes",
    "workflows",
    "recursos_departamentais",
    "relatorios_corporativos",
    "jobs",
)


def _tabela_existe(conexao, tabela):
    return conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
    ).fetchone() is not None


def _colunas(conexao, tabela):
    if not _tabela_existe(conexao, tabela):
        return set()
    return {item["name"] for item in conexao.execute(f"PRAGMA table_info({tabela})")}


def _adicionar_coluna(conexao, tabela, nome, definicao):
    if _tabela_existe(conexao, tabela) and nome not in _colunas(conexao, tabela):
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}")


def _normalizar_filiais(conexao, tabela):
    colunas = _colunas(conexao, tabela)
    if not {"empresa_id", "filial_id"}.issubset(colunas):
        return
    conexao.execute(
        f"""
        UPDATE {tabela}
        SET filial_id = (
            SELECT f.id FROM filiais f
            WHERE f.empresa_id = {tabela}.empresa_id AND f.ativo = 1
            ORDER BY f.id LIMIT 1
        )
        WHERE filial_id IS NULL
           OR NOT EXISTS (
               SELECT 1 FROM filiais f
               WHERE f.id = {tabela}.filial_id
                 AND f.empresa_id = {tabela}.empresa_id
           )
        """
    )
    # Triggers garantem a integridade do par empresa/filial sem depender de
    # duas foreign keys independentes.
    conexao.executescript(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{tabela}_filial_insert
        BEFORE INSERT ON {tabela}
        WHEN NEW.filial_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM filiais
            WHERE id = NEW.filial_id AND empresa_id = NEW.empresa_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'filial não pertence à empresa');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_{tabela}_filial_update
        BEFORE UPDATE OF empresa_id, filial_id ON {tabela}
        WHEN NEW.filial_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM filiais
            WHERE id = NEW.filial_id AND empresa_id = NEW.empresa_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'filial não pertence à empresa');
        END;
        """
    )


def upgrade(conexao):
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios_empresas (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (usuario_id, empresa_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (filial_id) REFERENCES filiais(id)
        );

        CREATE TABLE IF NOT EXISTS conjuntos_dados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            descricao TEXT,
            origem TEXT NOT NULL,
            nome_original TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            extensao TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            total_registros INTEGER NOT NULL DEFAULT 0,
            total_colunas INTEGER NOT NULL DEFAULT 0,
            categoria TEXT NOT NULL DEFAULT 'automatica',
            data_inicial TEXT,
            data_final TEXT,
            status TEXT NOT NULL DEFAULT 'Pronto',
            hash_sha256 TEXT NOT NULL,
            versao INTEGER NOT NULL DEFAULT 1,
            tags TEXT NOT NULL DEFAULT '',
            responsavel_id INTEGER,
            estado_registro TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (estado_registro IN ('Ativo', 'Arquivado', 'Lixeira')),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, filial_id, hash_sha256, estado_registro),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_conjuntos_dados_escopo
            ON conjuntos_dados (
                empresa_id, filial_id, estado_registro, atualizado_em DESC
            );
        """
    )

    # Na atualização, administradores recebem todas as empresas; demais
    # usuários permanecem na empresa principal até concessão explícita.
    conexao.execute(
        """
        INSERT OR IGNORE INTO usuarios_empresas (usuario_id, empresa_id, filial_id)
        SELECT u.id, e.id,
               (SELECT f.id FROM filiais f
                WHERE f.empresa_id=e.id AND f.ativo=1 ORDER BY f.id LIMIT 1)
        FROM usuarios u CROSS JOIN empresas e
        WHERE u.perfil='admin' AND e.ativo=1
        """
    )
    conexao.execute(
        """
        INSERT OR IGNORE INTO usuarios_empresas (usuario_id, empresa_id, filial_id)
        SELECT u.id, e.id,
               (SELECT f.id FROM filiais f
                WHERE f.empresa_id=e.id AND f.ativo=1 ORDER BY f.id LIMIT 1)
        FROM usuarios u
        JOIN empresas e ON e.id=(SELECT id FROM empresas WHERE ativo=1 ORDER BY id LIMIT 1)
        WHERE u.perfil!='admin'
        """
    )

    _normalizar_filiais(conexao, "usuarios_empresas")
    _normalizar_filiais(conexao, "conjuntos_dados")

    for tabela in ("notificacoes", "atividades"):
        _adicionar_coluna(conexao, tabela, "filial_id", "INTEGER")
        _normalizar_filiais(conexao, tabela)

    for tabela in TABELAS_COM_ESCOPO:
        _normalizar_filiais(conexao, tabela)

    if _tabela_existe(conexao, "historico_analises"):
        for nome, definicao in (
            ("empresa_id", "INTEGER"),
            ("filial_id", "INTEGER"),
            ("estado_registro", "TEXT NOT NULL DEFAULT 'Ativo'"),
            ("excluido_em", "TEXT"),
            ("excluido_por", "INTEGER"),
        ):
            _adicionar_coluna(conexao, "historico_analises", nome, definicao)
        conexao.execute(
            """
            UPDATE historico_analises
            SET empresa_id=COALESCE(
                    empresa_id,
                    (SELECT empresa_id FROM usuarios_empresas ue
                     WHERE ue.usuario_id=historico_analises.usuario_id
                       AND ue.ativo=1 ORDER BY ue.empresa_id LIMIT 1),
                    (SELECT id FROM empresas WHERE ativo=1 ORDER BY id LIMIT 1)
                )
            WHERE empresa_id IS NULL
            """
        )
        _normalizar_filiais(conexao, "historico_analises")
