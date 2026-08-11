"""Ciclo de vida, multifilial, auditoria, dinheiro exato e jobs."""

from __future__ import annotations


TABELAS_OPERACIONAIS = (
    "colaboradores",
    "lancamentos_financeiros",
    "itens_estoque",
    "solicitacoes_compra",
    "chamados_ti",
    "ativos_ti",
    "campanhas_marketing",
    "solicitacoes_administrativas",
    "contratos_juridicos",
    "oportunidades_comerciais",
)

COLUNAS_MONETARIAS = {
    "colaboradores": ("salario", "salario_centavos"),
    "lancamentos_financeiros": ("valor", "valor_centavos"),
    "itens_estoque": ("custo", "custo_centavos"),
    "solicitacoes_compra": ("valor_estimado", "valor_estimado_centavos"),
    "campanhas_marketing": (
        "investimento",
        "investimento_centavos",
        "receita",
        "receita_centavos",
    ),
    "solicitacoes_administrativas": ("valor", "valor_centavos"),
    "contratos_juridicos": ("valor", "valor_centavos"),
    "oportunidades_comerciais": ("valor", "valor_centavos"),
    "aprovacoes": ("valor", "valor_centavos"),
}


def _colunas(conexao, tabela: str) -> set[str]:
    return {
        str(item["name"])
        for item in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
    }


def _adicionar_coluna(conexao, tabela: str, nome: str, definicao: str) -> None:
    if nome not in _colunas(conexao, tabela):
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}")


def _migrar_centavos(conexao, tabela: str, pares: tuple[str, ...]) -> None:
    for indice in range(0, len(pares), 2):
        origem = pares[indice]
        destino = pares[indice + 1]
        _adicionar_coluna(conexao, tabela, destino, "INTEGER NOT NULL DEFAULT 0")
        conexao.execute(
            f"UPDATE {tabela} SET {destino} = ROUND(COALESCE({origem}, 0) * 100)"
        )


def upgrade(conexao) -> None:
    for tabela in TABELAS_OPERACIONAIS:
        _adicionar_coluna(conexao, tabela, "filial_id", "INTEGER")
        _adicionar_coluna(
            conexao,
            tabela,
            "estado_registro",
            "TEXT NOT NULL DEFAULT 'Ativo'",
        )
        _adicionar_coluna(conexao, tabela, "arquivado_em", "TEXT")
        _adicionar_coluna(conexao, tabela, "arquivado_por", "INTEGER")
        _adicionar_coluna(conexao, tabela, "atualizado_em", "TEXT")
        conexao.execute(
            f"""
            UPDATE {tabela}
            SET filial_id = (
                SELECT f.id FROM filiais f
                WHERE f.empresa_id = {tabela}.empresa_id AND f.ativo = 1
                ORDER BY f.id LIMIT 1
            )
            WHERE filial_id IS NULL
            """
        )
        conexao.execute(
            f"UPDATE {tabela} SET atualizado_em = COALESCE(atualizado_em, criado_em)"
        )
        conexao.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{tabela}_escopo_estado "
            f"ON {tabela} (empresa_id, filial_id, estado_registro, id DESC)"
        )

    for tabela, pares in COLUNAS_MONETARIAS.items():
        _migrar_centavos(conexao, tabela, pares)

    _adicionar_coluna(conexao, "aprovacoes", "filial_id", "INTEGER")
    _adicionar_coluna(conexao, "aprovacoes", "excluido_em", "TEXT")
    _adicionar_coluna(conexao, "aprovacoes", "excluido_por", "INTEGER")
    conexao.execute(
        """
        UPDATE aprovacoes
        SET filial_id = (
            SELECT f.id FROM filiais f
            WHERE f.empresa_id = aprovacoes.empresa_id AND f.ativo = 1
            ORDER BY f.id LIMIT 1
        )
        WHERE filial_id IS NULL
        """
    )

    for coluna, definicao in (
        ("empresa_id", "INTEGER"),
        ("filial_id", "INTEGER"),
        ("modulo", "TEXT"),
        ("entidade", "TEXT"),
        ("entidade_id", "INTEGER"),
        ("dados_antes", "TEXT"),
        ("dados_depois", "TEXT"),
        ("operacao_id", "TEXT"),
        ("versao_aplicacao", "TEXT"),
        ("maquina", "TEXT"),
    ):
        _adicionar_coluna(conexao, "auditoria", coluna, definicao)

    for coluna, definicao in (
        ("mfa_habilitado", "INTEGER NOT NULL DEFAULT 0"),
        ("mfa_secret_ref", "TEXT"),
        ("sessao_epoch", "INTEGER NOT NULL DEFAULT 0"),
    ):
        _adicionar_coluna(conexao, "usuarios", coluna, definicao)

    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS historico_alteracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operacao_id TEXT NOT NULL,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            modulo TEXT NOT NULL,
            entidade TEXT NOT NULL,
            entidade_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            dados_antes TEXT,
            dados_depois TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_historico_alteracoes_recurso
            ON historico_alteracoes (
                empresa_id, modulo, entidade, entidade_id, criado_em DESC
            );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN (
                    'Pendente', 'Executando', 'Concluído',
                    'Falhou', 'Cancelamento solicitado', 'Cancelado'
                )),
            progresso INTEGER NOT NULL DEFAULT 0
                CHECK (progresso BETWEEN 0 AND 100),
            mensagem TEXT,
            resultado_json TEXT,
            erro TEXT,
            cancelamento_solicitado INTEGER NOT NULL DEFAULT 0
                CHECK (cancelamento_solicitado IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            iniciado_em TEXT,
            concluido_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_empresa_status
            ON jobs (empresa_id, status, criado_em DESC);

        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            usuario_id INTEGER,
            arquivo TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Válido',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
        """
    )
