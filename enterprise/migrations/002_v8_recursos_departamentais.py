"""Recursos especializados, relatórios e ciclo de vida das ferramentas V8."""

from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    return {
        str(item["name"])
        for item in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
    }


def _adicionar_coluna(conexao, tabela: str, nome: str, definicao: str) -> None:
    if nome not in _colunas(conexao, tabela):
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}")


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS recursos_departamentais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            recurso TEXT NOT NULL,
            identificacao TEXT NOT NULL,
            descricao TEXT,
            responsavel TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente',
            prioridade TEXT NOT NULL DEFAULT 'Média',
            valor_centavos INTEGER NOT NULL DEFAULT 0
                CHECK (valor_centavos >= 0),
            data_referencia TEXT,
            dados_json TEXT NOT NULL DEFAULT '{}',
            estado_registro TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (estado_registro IN ('Ativo', 'Arquivado', 'Lixeira')),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            arquivado_em TEXT,
            arquivado_por INTEGER,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id),
            FOREIGN KEY (arquivado_por) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_recursos_departamentais_escopo
            ON recursos_departamentais (
                empresa_id, filial_id, modulo, recurso,
                estado_registro, atualizado_em DESC
            );

        CREATE INDEX IF NOT EXISTS idx_recursos_departamentais_status
            ON recursos_departamentais (
                empresa_id, filial_id, modulo, status
            );

        CREATE TABLE IF NOT EXISTS relatorios_corporativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL DEFAULT 'analytics',
            titulo TEXT NOT NULL,
            descricao TEXT,
            formato TEXT NOT NULL DEFAULT 'HTML'
                CHECK (formato IN ('HTML', 'CSV', 'JSON')),
            filtros_json TEXT NOT NULL DEFAULT '{}',
            arquivo TEXT,
            status TEXT NOT NULL DEFAULT 'Rascunho',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_relatorios_corporativos_escopo
            ON relatorios_corporativos (
                empresa_id, filial_id, modulo, criado_em DESC
            );
        """
    )

    for tabela in ("tarefas", "documentos", "integracoes", "workflows"):
        _adicionar_coluna(conexao, tabela, "filial_id", "INTEGER")
        _adicionar_coluna(
            conexao,
            tabela,
            "atualizado_em",
            "TEXT NOT NULL DEFAULT ''",
        )
        conexao.execute(
            f"UPDATE {tabela} SET atualizado_em = COALESCE(NULLIF(atualizado_em, ''), criado_em)"
        )

    for tabela in ("tarefas", "documentos"):
        _adicionar_coluna(
            conexao,
            tabela,
            "estado_registro",
            "TEXT NOT NULL DEFAULT 'Ativo'",
        )

    for tabela in ("tarefas", "documentos", "integracoes", "workflows"):
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
