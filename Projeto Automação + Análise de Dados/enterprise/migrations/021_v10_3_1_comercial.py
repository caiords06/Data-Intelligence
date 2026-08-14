"""V10.3.1 — Comercial especializado sobre CRM compartilhado."""
from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS comercial_pipeline_etapas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 0,
            probabilidade INTEGER NOT NULL DEFAULT 0,
            cor TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            UNIQUE(empresa_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );
        CREATE TABLE IF NOT EXISTS comercial_oportunidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            crm_empresa_id INTEGER,
            contato_id INTEGER,
            lead_id INTEGER,
            titulo TEXT NOT NULL,
            responsavel_id INTEGER,
            etapa_id INTEGER,
            valor_centavos INTEGER NOT NULL DEFAULT 0,
            probabilidade INTEGER NOT NULL DEFAULT 0,
            fechamento_previsto TEXT,
            status TEXT NOT NULL DEFAULT 'Aberta',
            motivo_perda TEXT,
            proxima_acao TEXT,
            legacy_oportunidade_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (crm_empresa_id) REFERENCES crm_empresas(id),
            FOREIGN KEY (contato_id) REFERENCES crm_contatos(id),
            FOREIGN KEY (lead_id) REFERENCES crm_leads(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (etapa_id) REFERENCES comercial_pipeline_etapas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_comercial_oportunidade_legacy ON comercial_oportunidades(legacy_oportunidade_id) WHERE legacy_oportunidade_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_comercial_oportunidades_escopo ON comercial_oportunidades(empresa_id, filial_id, status, etapa_id, id DESC);
        CREATE TABLE IF NOT EXISTS comercial_atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            oportunidade_id INTEGER NOT NULL, tipo TEXT NOT NULL, descricao TEXT, realizada_em TEXT,
            proxima_acao TEXT, responsavel_id INTEGER, criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (oportunidade_id) REFERENCES comercial_oportunidades(id)
        );
        CREATE TABLE IF NOT EXISTS comercial_propostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            oportunidade_id INTEGER NOT NULL, numero TEXT NOT NULL, validade TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0,
            desconto_centavos INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Rascunho', observacoes TEXT,
            criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, numero), FOREIGN KEY (oportunidade_id) REFERENCES comercial_oportunidades(id)
        );
        CREATE TABLE IF NOT EXISTS comercial_proposta_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT, proposta_id INTEGER NOT NULL, descricao TEXT NOT NULL,
            quantidade REAL NOT NULL DEFAULT 1, valor_unitario_centavos INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (proposta_id) REFERENCES comercial_propostas(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS comercial_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            responsavel_id INTEGER, referencia TEXT NOT NULL, valor_centavos INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, filial_id, responsavel_id, referencia)
        );
        CREATE TABLE IF NOT EXISTS comercial_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            referencia TEXT NOT NULL, pipeline_centavos INTEGER NOT NULL DEFAULT 0, ponderado_centavos INTEGER NOT NULL DEFAULT 0,
            comprometido_centavos INTEGER NOT NULL DEFAULT 0, meta_centavos INTEGER NOT NULL DEFAULT 0,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(empresa_id, filial_id, referencia)
        );
        """
    )
    # Etapas padrão por empresa existente.
    for nome, ordem, prob in (("Novo",10,10),("Qualificação",20,25),("Proposta",30,50),("Negociação",40,70),("Fechamento",50,90)):
        conexao.execute(
            "INSERT OR IGNORE INTO comercial_pipeline_etapas (empresa_id,nome,ordem,probabilidade) SELECT id,?,?,? FROM empresas",
            (nome, ordem, prob),
        )
    # Preserva a carteira legada sem apagar a origem.
    conexao.execute(
        """
        INSERT OR IGNORE INTO comercial_oportunidades (
            empresa_id, filial_id, titulo, etapa_id, valor_centavos, probabilidade, status,
            legacy_oportunidade_id, criado_por, criado_em
        )
        SELECT o.empresa_id, o.filial_id, o.cliente,
               (SELECT e.id FROM comercial_pipeline_etapas e WHERE e.empresa_id=o.empresa_id AND e.nome=
                    CASE WHEN o.etapa='Qualificado' THEN 'Qualificação' WHEN o.etapa IN ('Ganho','Perdido') THEN 'Fechamento' ELSE o.etapa END LIMIT 1),
               COALESCE(o.valor_centavos, CAST(ROUND(COALESCE(o.valor,0)*100) AS INTEGER)),
               CASE WHEN o.status='Ganho' THEN 100 WHEN o.status='Perdido' THEN 0 ELSE 25 END,
               CASE WHEN o.status='Ganho' THEN 'Ganha' WHEN o.status='Perdido' THEN 'Perdida' ELSE 'Aberta' END,
               o.id, o.criado_por, o.criado_em
        FROM oportunidades_comerciais o
        WHERE NOT EXISTS (SELECT 1 FROM comercial_oportunidades n WHERE n.legacy_oportunidade_id=o.id)
        """
    )
