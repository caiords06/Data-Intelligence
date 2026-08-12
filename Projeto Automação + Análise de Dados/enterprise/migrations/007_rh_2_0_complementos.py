"""Complementos de patrimônio e comprovantes do RH 2.0."""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS rh_equipamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            patrimonio TEXT NOT NULL,
            descricao TEXT NOT NULL,
            origem_modulo TEXT,
            origem_recurso_id INTEGER,
            entregue_em TEXT NOT NULL,
            devolvido_em TEXT,
            termo_documento_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Em uso',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, patrimonio, entregue_em),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (termo_documento_id) REFERENCES rh_documentos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_contracheques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            folha_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            caminho TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            gerado_por INTEGER,
            gerado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (folha_id, colaborador_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (folha_id) REFERENCES rh_folhas(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (gerado_por) REFERENCES usuarios(id)
        );
        """
    )
