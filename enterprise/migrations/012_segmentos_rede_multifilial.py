"""Tecnologia 3.0.1: corrige unicidade de segmentos por empresa/filial/CIDR.

A versão anterior usava UNIQUE(empresa_id, cidr), o que impedia duas filiais da
mesma empresa de usarem o mesmo bloco privado. Esta migração preserva os IDs e
as referências existentes e passa a considerar a filial no escopo de unicidade.
"""

from __future__ import annotations


def upgrade(conexao) -> None:
    # A reconstrução precisa ocorrer com FKs temporariamente desligadas para que
    # ti_dispositivos_rede continue referenciando o nome final da tabela pai.
    conexao.commit()
    foreign_keys = int(conexao.execute("PRAGMA foreign_keys").fetchone()[0])
    conexao.execute("PRAGMA foreign_keys = OFF")

    try:
        conexao.execute("BEGIN IMMEDIATE")
        conexao.execute("DROP TABLE IF EXISTS ti_segmentos_rede_novo")
        conexao.execute(
            """
            CREATE TABLE ti_segmentos_rede_novo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                nome TEXT NOT NULL,
                cidr TEXT NOT NULL,
                vlan TEXT,
                gateway TEXT,
                dns TEXT,
                departamento_id INTEGER,
                autorizado INTEGER NOT NULL DEFAULT 0 CHECK (autorizado IN (0, 1)),
                justificativa_autorizacao TEXT,
                autorizado_por INTEGER,
                autorizado_em TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                firewall_status TEXT,
                firewall_regra TEXT,
                ultima_varredura_em TEXT,
                ultima_varredura_total INTEGER NOT NULL DEFAULT 0,
                ultima_varredura_online INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
                FOREIGN KEY (autorizado_por) REFERENCES usuarios(id)
            )
            """
        )
        conexao.execute(
            """
            INSERT INTO ti_segmentos_rede_novo (
                id, empresa_id, filial_id, nome, cidr, vlan, gateway, dns,
                departamento_id, autorizado, justificativa_autorizacao,
                autorizado_por, autorizado_em, ativo, firewall_status,
                firewall_regra, ultima_varredura_em, ultima_varredura_total,
                ultima_varredura_online
            )
            SELECT
                id, empresa_id, filial_id, nome, cidr, vlan, gateway, dns,
                departamento_id, autorizado, justificativa_autorizacao,
                autorizado_por, autorizado_em, ativo, firewall_status,
                firewall_regra, ultima_varredura_em, ultima_varredura_total,
                ultima_varredura_online
            FROM ti_segmentos_rede
            """
        )
        conexao.execute("DROP TABLE ti_segmentos_rede")
        conexao.execute("ALTER TABLE ti_segmentos_rede_novo RENAME TO ti_segmentos_rede")

        # IFNULL evita que duas linhas corporativas (filial NULL) com o mesmo CIDR
        # escapem da regra de unicidade devido à semântica de NULL do SQLite.
        conexao.execute(
            """
            CREATE UNIQUE INDEX uq_ti_segmentos_empresa_filial_cidr
            ON ti_segmentos_rede (empresa_id, IFNULL(filial_id, 0), cidr)
            """
        )
        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ti_segmentos_escopo_ativo
            ON ti_segmentos_rede (empresa_id, filial_id, ativo, nome)
            """
        )
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        if foreign_keys:
            conexao.execute("PRAGMA foreign_keys = ON")

    violacoes = list(conexao.execute("PRAGMA foreign_key_check"))
    if violacoes:
        raise RuntimeError(
            "A migração de segmentos de rede gerou inconsistências de chave estrangeira."
        )
