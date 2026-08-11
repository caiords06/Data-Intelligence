"""Correções de integridade e escopo introduzidas na estabilização V8.2."""

from __future__ import annotations


def _tabela_existe(conexao, tabela: str) -> bool:
    return conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
    ).fetchone() is not None


def _colunas(conexao, tabela: str) -> set[str]:
    if not _tabela_existe(conexao, tabela):
        return set()
    return {str(item["name"]) for item in conexao.execute(f"PRAGMA table_info({tabela})")}


def _adicionar_coluna(conexao, tabela: str, nome: str, definicao: str) -> None:
    if _tabela_existe(conexao, tabela) and nome not in _colunas(conexao, tabela):
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}")


def _tem_unicidade_antiga_estoque(conexao) -> bool:
    if not _tabela_existe(conexao, "itens_estoque"):
        return False
    for indice in conexao.execute("PRAGMA index_list(itens_estoque)").fetchall():
        # PRAGMA index_list: seq, name, unique, origin, partial
        if not bool(indice["unique"]):
            continue
        colunas = [
            str(item["name"])
            for item in conexao.execute(
                f"PRAGMA index_info({indice['name']})"
            ).fetchall()
        ]
        if colunas == ["empresa_id", "codigo"]:
            return True
    return False


def _reconstruir_itens_estoque(conexao) -> None:
    """Troca a unicidade antiga empresa+SKU por empresa+filial+SKU.

    A V8.1 já tratava o item como recurso de filial, mas bases atualizadas de
    versões antigas ainda conservavam o UNIQUE(empresa_id, codigo), impedindo
    o mesmo SKU em duas unidades. A reconstrução preserva IDs para não quebrar
    as movimentações existentes.
    """
    if not _tem_unicidade_antiga_estoque(conexao):
        return

    colunas_origem = _colunas(conexao, "itens_estoque")
    conexao.execute("PRAGMA defer_foreign_keys = ON")
    conexao.execute("DROP TABLE IF EXISTS itens_estoque_v82_novo")
    conexao.execute(
        """
        CREATE TABLE itens_estoque_v82_novo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            codigo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            categoria TEXT,
            quantidade REAL NOT NULL DEFAULT 0,
            estoque_minimo REAL NOT NULL DEFAULT 0,
            custo REAL NOT NULL DEFAULT 0,
            custo_centavos INTEGER NOT NULL DEFAULT 0,
            localizacao TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            estado_registro TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (estado_registro IN ('Ativo', 'Arquivado', 'Lixeira')),
            arquivado_em TEXT,
            arquivado_por INTEGER,
            atualizado_em TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, filial_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (arquivado_por) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        )
        """
    )

    destinos = (
        "id", "empresa_id", "filial_id", "codigo", "descricao", "categoria",
        "quantidade", "estoque_minimo", "custo", "custo_centavos",
        "localizacao", "status", "estado_registro", "arquivado_em",
        "arquivado_por", "atualizado_em", "criado_por", "criado_em",
    )
    expressoes = []
    for coluna in destinos:
        if coluna in colunas_origem:
            expressoes.append(coluna)
        elif coluna == "filial_id":
            expressoes.append(
                "(SELECT f.id FROM filiais f "
                "WHERE f.empresa_id=itens_estoque.empresa_id AND f.ativo=1 "
                "ORDER BY f.id LIMIT 1)"
            )
        elif coluna == "custo_centavos":
            expressoes.append("ROUND(COALESCE(custo, 0) * 100)")
        elif coluna == "estado_registro":
            expressoes.append("'Ativo'")
        elif coluna == "atualizado_em":
            expressoes.append("criado_em")
        else:
            expressoes.append("NULL")

    conexao.execute(
        f"INSERT INTO itens_estoque_v82_novo ({', '.join(destinos)}) "
        f"SELECT {', '.join(expressoes)} FROM itens_estoque"
    )
    conexao.execute("DROP TABLE itens_estoque")
    conexao.execute("ALTER TABLE itens_estoque_v82_novo RENAME TO itens_estoque")
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS idx_itens_estoque_escopo_estado "
        "ON itens_estoque (empresa_id, filial_id, estado_registro, id DESC)"
    )


def _normalizar_filial_por_empresa(conexao, tabela: str) -> None:
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
    conexao.executescript(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{tabela}_filial_insert_v82
        BEFORE INSERT ON {tabela}
        WHEN NEW.filial_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM filiais
            WHERE id = NEW.filial_id AND empresa_id = NEW.empresa_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'filial não pertence à empresa');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_{tabela}_filial_update_v82
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


def upgrade(conexao) -> None:
    _reconstruir_itens_estoque(conexao)
    _normalizar_filial_por_empresa(conexao, "itens_estoque")

    # Movimentações de estoque eram a última entidade operacional sem filial.
    _adicionar_coluna(conexao, "movimentos_estoque", "filial_id", "INTEGER")
    if _tabela_existe(conexao, "movimentos_estoque"):
        conexao.execute(
            """
            UPDATE movimentos_estoque
            SET filial_id = COALESCE(
                (SELECT i.filial_id FROM itens_estoque i
                 WHERE i.id = movimentos_estoque.item_id
                   AND i.empresa_id = movimentos_estoque.empresa_id),
                (SELECT f.id FROM filiais f
                 WHERE f.empresa_id = movimentos_estoque.empresa_id AND f.ativo = 1
                 ORDER BY f.id LIMIT 1)
            )
            WHERE filial_id IS NULL
            """
        )

    if _tabela_existe(conexao, "movimentos_estoque"):
        # A movimentação deve apontar para um item do mesmo escopo; validar
        # empresa e filial separadamente não impediria cruzar itens entre
        # unidades da mesma organização.
        conexao.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS trg_movimentos_item_escopo_insert_v82
            BEFORE INSERT ON movimentos_estoque
            WHEN NOT EXISTS (
                SELECT 1 FROM itens_estoque i
                WHERE i.id = NEW.item_id
                  AND i.empresa_id = NEW.empresa_id
                  AND (
                      (i.filial_id IS NULL AND NEW.filial_id IS NULL) OR
                      i.filial_id = NEW.filial_id
                  )
            )
            BEGIN
                SELECT RAISE(ABORT, 'item não pertence ao escopo da movimentação');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_movimentos_item_escopo_update_v82
            BEFORE UPDATE OF item_id, empresa_id, filial_id ON movimentos_estoque
            WHEN NOT EXISTS (
                SELECT 1 FROM itens_estoque i
                WHERE i.id = NEW.item_id
                  AND i.empresa_id = NEW.empresa_id
                  AND (
                      (i.filial_id IS NULL AND NEW.filial_id IS NULL) OR
                      i.filial_id = NEW.filial_id
                  )
            )
            BEGIN
                SELECT RAISE(ABORT, 'item não pertence ao escopo da movimentação');
            END;
            """
        )

    # Eventos antigos da V8.1 eram gravados sem filial por omissão. Como o
    # produto não possuía uma API explícita de evento corporativo, os registros
    # nulos existentes são associados à filial válida da própria empresa.
    for tabela in ("atividades", "notificacoes", "movimentos_estoque"):
        _normalizar_filial_por_empresa(conexao, tabela)
        if _tabela_existe(conexao, tabela) and {"empresa_id", "filial_id"}.issubset(_colunas(conexao, tabela)):
            conexao.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{tabela}_escopo_v82 "
                f"ON {tabela} (empresa_id, filial_id, id DESC)"
            )
