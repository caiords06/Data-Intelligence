"""V10.3.0 — CRM compartilhado e Marketing especializado."""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS crm_empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            nome_fantasia TEXT,
            cnpj TEXT,
            segmento TEXT,
            porte TEXT,
            site TEXT,
            cidade TEXT,
            estado TEXT,
            proprietario_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Ativo',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (proprietario_id) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_crm_empresas_escopo ON crm_empresas(empresa_id, status, id DESC);

        CREATE TABLE IF NOT EXISTS crm_contatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            crm_empresa_id INTEGER,
            nome TEXT NOT NULL,
            cargo TEXT,
            email TEXT,
            telefone TEXT,
            linkedin TEXT,
            responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Ativo',
            origem TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (crm_empresa_id) REFERENCES crm_empresas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_crm_contatos_escopo ON crm_contatos(empresa_id, status, id DESC);

        CREATE TABLE IF NOT EXISTS marketing_canais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Outro',
            custo_mensal_centavos INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Ativo',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS marketing_campanhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            objetivo TEXT,
            canal_id INTEGER,
            publico TEXT,
            orcamento_centavos INTEGER NOT NULL DEFAULT 0,
            investimento_centavos INTEGER NOT NULL DEFAULT 0,
            receita_atribuida_centavos INTEGER NOT NULL DEFAULT 0,
            inicio TEXT,
            fim TEXT,
            responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Planejada',
            legacy_campanha_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (canal_id) REFERENCES marketing_canais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_marketing_campanha_legacy ON marketing_campanhas(legacy_campanha_id) WHERE legacy_campanha_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_marketing_campanhas_escopo ON marketing_campanhas(empresa_id, filial_id, status, id DESC);

        CREATE TABLE IF NOT EXISTS crm_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            contato_id INTEGER,
            crm_empresa_id INTEGER,
            origem TEXT,
            campanha_id INTEGER,
            score INTEGER NOT NULL DEFAULT 0,
            temperatura TEXT NOT NULL DEFAULT 'Frio',
            responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Novo',
            data_qualificacao TEXT,
            convertido_em TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (contato_id) REFERENCES crm_contatos(id),
            FOREIGN KEY (crm_empresa_id) REFERENCES crm_empresas(id),
            FOREIGN KEY (campanha_id) REFERENCES marketing_campanhas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_crm_leads_escopo ON crm_leads(empresa_id, filial_id, status, score DESC, id DESC);

        CREATE TABLE IF NOT EXISTS crm_atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            lead_id INTEGER,
            oportunidade_id INTEGER,
            tipo TEXT NOT NULL,
            descricao TEXT,
            realizada_em TEXT,
            proxima_acao TEXT,
            responsavel_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (lead_id) REFERENCES crm_leads(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS marketing_conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            campanha_id INTEGER,
            titulo TEXT NOT NULL,
            formato TEXT NOT NULL DEFAULT 'Post',
            canal TEXT,
            etapa TEXT NOT NULL DEFAULT 'Pauta',
            responsavel_id INTEGER,
            data_publicacao TEXT,
            observacoes TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (campanha_id) REFERENCES marketing_campanhas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS marketing_automacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            gatilho TEXT NOT NULL,
            acao TEXT NOT NULL,
            campanha_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (campanha_id) REFERENCES marketing_campanhas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS marketing_metricas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            campanha_id INTEGER NOT NULL,
            referencia TEXT NOT NULL,
            impressoes INTEGER NOT NULL DEFAULT 0,
            cliques INTEGER NOT NULL DEFAULT 0,
            leads INTEGER NOT NULL DEFAULT 0,
            mqls INTEGER NOT NULL DEFAULT 0,
            conversoes INTEGER NOT NULL DEFAULT 0,
            investimento_centavos INTEGER NOT NULL DEFAULT 0,
            receita_centavos INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(campanha_id, referencia),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (campanha_id) REFERENCES marketing_campanhas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        """
    )
    # Migração segura do cadastro antigo de campanhas. Não remove a tabela legada.
    conexao.execute(
        """
        INSERT OR IGNORE INTO marketing_canais (empresa_id, nome, tipo, status)
        SELECT DISTINCT empresa_id, canal, 'Legado', 'Ativo'
        FROM campanhas_marketing
        WHERE TRIM(COALESCE(canal,'')) <> ''
        """
    )
    conexao.execute(
        """
        INSERT OR IGNORE INTO marketing_campanhas (
            empresa_id, filial_id, nome, canal_id, investimento_centavos,
            receita_atribuida_centavos, status, legacy_campanha_id, criado_por, criado_em
        )
        SELECT c.empresa_id, c.filial_id, c.nome, mc.id,
               COALESCE(c.investimento_centavos, CAST(ROUND(COALESCE(c.investimento,0)*100) AS INTEGER)),
               COALESCE(c.receita_centavos, CAST(ROUND(COALESCE(c.receita,0)*100) AS INTEGER)),
               c.status, c.id, c.criado_por, c.criado_em
        FROM campanhas_marketing c
        LEFT JOIN marketing_canais mc ON mc.empresa_id=c.empresa_id AND mc.nome=c.canal
        WHERE NOT EXISTS (
            SELECT 1 FROM marketing_campanhas nova WHERE nova.legacy_campanha_id=c.id
        )
        """
    )
