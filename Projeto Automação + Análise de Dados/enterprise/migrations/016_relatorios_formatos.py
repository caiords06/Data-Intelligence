"""Amplia formatos do catálogo corporativo de relatórios.

A tabela V8 original aceitava apenas HTML/CSV/JSON, mas os motores
departamentais geram também XLSX e PDF. A migração reconstrói a tabela de
forma idempotente preservando dados e chaves estrangeiras.
"""

from __future__ import annotations


def upgrade(conexao) -> None:
    sql = conexao.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='relatorios_corporativos'"
    ).fetchone()
    if sql is None:
        return
    definicao = str(sql[0] or "").upper()
    if "'XLSX'" in definicao and "'PDF'" in definicao:
        return

    conexao.execute("PRAGMA foreign_keys=OFF")
    try:
        conexao.executescript(
            """
            CREATE TABLE relatorios_corporativos_novo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT NOT NULL DEFAULT 'analytics',
                titulo TEXT NOT NULL,
                descricao TEXT,
                formato TEXT NOT NULL DEFAULT 'HTML'
                    CHECK (formato IN ('HTML','CSV','JSON','XLSX','PDF')),
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

            INSERT INTO relatorios_corporativos_novo (
                id,empresa_id,filial_id,modulo,titulo,descricao,formato,
                filtros_json,arquivo,status,criado_por,criado_em,atualizado_em
            )
            SELECT id,empresa_id,filial_id,modulo,titulo,descricao,
                   CASE UPPER(formato)
                       WHEN 'EXCEL' THEN 'XLSX'
                       ELSE UPPER(formato)
                   END,
                   filtros_json,arquivo,status,criado_por,criado_em,atualizado_em
            FROM relatorios_corporativos;

            DROP TABLE relatorios_corporativos;
            ALTER TABLE relatorios_corporativos_novo RENAME TO relatorios_corporativos;

            CREATE INDEX IF NOT EXISTS idx_relatorios_corporativos_escopo
                ON relatorios_corporativos (
                    empresa_id, filial_id, modulo, criado_em DESC
                );
            """
        )
    finally:
        conexao.execute("PRAGMA foreign_keys=ON")
