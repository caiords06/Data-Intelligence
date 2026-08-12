"""V9 - etapas efetivas de aprovação de Compras."""

VERSAO = "015_aprovacoes_compras"


def upgrade(conexao):
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS cmp_aprovacoes_solicitacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            solicitacao_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            perfil_aprovador TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente','Aprovado','Rejeitado','Alteração solicitada')),
            aprovador_id INTEGER,
            comentario TEXT,
            decidido_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (solicitacao_id, ordem),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id) ON DELETE CASCADE,
            FOREIGN KEY (aprovador_id) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cmp_aprov_solicitacao_status
            ON cmp_aprovacoes_solicitacao(empresa_id, filial_id, solicitacao_id, status, ordem);
        """
    )
