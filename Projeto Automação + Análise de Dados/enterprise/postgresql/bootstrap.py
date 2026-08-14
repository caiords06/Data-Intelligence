"""Bootstrap e health do schema PostgreSQL V10.1."""
from __future__ import annotations

from pathlib import Path
import logging
import re
import threading

from .adapter import obter_pool

_SCHEMA = Path(__file__).with_name("schema_v10_1.sql")
_HARDENING = Path(__file__).with_name("schema_hardening.sql")
_V11 = Path(__file__).with_name("schema_v11.sql")
_V11_1 = Path(__file__).with_name("schema_v11_1.sql")
_LOCK = threading.RLock()
_PRONTO = False


def _garantir_extensoes_runtime(raw) -> None:
    """Aplica tabelas idempotentes adicionadas após o baseline V10.1 inicial."""
    raw.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_analises (
            id BIGSERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            empresa_id INTEGER REFERENCES empresas(id),
            filial_id INTEGER,
            categoria TEXT NOT NULL,
            fonte TEXT NOT NULL,
            quantidade_arquivos INTEGER NOT NULL,
            total_registros INTEGER NOT NULL,
            total_colunas INTEGER NOT NULL,
            score_qualidade DOUBLE PRECISION,
            nivel_qualidade TEXT,
            status TEXT NOT NULL DEFAULT 'concluida',
            resumo_json TEXT NOT NULL,
            estado_registro TEXT NOT NULL DEFAULT 'Ativo',
            excluido_em TEXT,
            excluido_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id)
        );
        CREATE INDEX IF NOT EXISTS idx_historico_analises_escopo
            ON historico_analises (empresa_id, filial_id, usuario_id, estado_registro, id DESC);
        CREATE TABLE IF NOT EXISTS preferencias_usuarios (
            usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
            preferencias_json TEXT NOT NULL,
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

        CREATE TABLE IF NOT EXISTS crm_empresas (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            nome TEXT NOT NULL, nome_fantasia TEXT, cnpj TEXT, segmento TEXT, porte TEXT, site TEXT,
            cidade TEXT, estado TEXT, proprietario_id INTEGER REFERENCES usuarios(id), status TEXT NOT NULL DEFAULT 'Ativo',
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE INDEX IF NOT EXISTS idx_crm_empresas_escopo ON crm_empresas(empresa_id, status, id DESC);
        CREATE TABLE IF NOT EXISTS crm_contatos (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), crm_empresa_id BIGINT REFERENCES crm_empresas(id),
            nome TEXT NOT NULL, cargo TEXT, email TEXT, telefone TEXT, linkedin TEXT, responsavel_id INTEGER REFERENCES usuarios(id),
            status TEXT NOT NULL DEFAULT 'Ativo', origem TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE INDEX IF NOT EXISTS idx_crm_contatos_escopo ON crm_contatos(empresa_id, status, id DESC);
        CREATE TABLE IF NOT EXISTS marketing_canais (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Outro', custo_mensal_centavos BIGINT NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Ativo',
            criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE(empresa_id,nome)
        );
        CREATE TABLE IF NOT EXISTS marketing_campanhas (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, nome TEXT NOT NULL, objetivo TEXT,
            canal_id BIGINT REFERENCES marketing_canais(id), publico TEXT, orcamento_centavos BIGINT NOT NULL DEFAULT 0,
            investimento_centavos BIGINT NOT NULL DEFAULT 0, receita_atribuida_centavos BIGINT NOT NULL DEFAULT 0, inicio TEXT, fim TEXT,
            responsavel_id INTEGER REFERENCES usuarios(id), status TEXT NOT NULL DEFAULT 'Planejada', legacy_campanha_id INTEGER,
            criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_marketing_campanha_legacy ON marketing_campanhas(legacy_campanha_id) WHERE legacy_campanha_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_marketing_campanhas_escopo ON marketing_campanhas(empresa_id, filial_id, status, id DESC);
        CREATE TABLE IF NOT EXISTS crm_leads (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, contato_id BIGINT REFERENCES crm_contatos(id),
            crm_empresa_id BIGINT REFERENCES crm_empresas(id), origem TEXT, campanha_id BIGINT REFERENCES marketing_campanhas(id),
            score INTEGER NOT NULL DEFAULT 0, temperatura TEXT NOT NULL DEFAULT 'Frio', responsavel_id INTEGER REFERENCES usuarios(id),
            status TEXT NOT NULL DEFAULT 'Novo', data_qualificacao TEXT, convertido_em TEXT, criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE INDEX IF NOT EXISTS idx_crm_leads_escopo ON crm_leads(empresa_id, filial_id, status, score DESC, id DESC);
        CREATE TABLE IF NOT EXISTS crm_atividades (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, lead_id BIGINT REFERENCES crm_leads(id),
            oportunidade_id INTEGER, tipo TEXT NOT NULL, descricao TEXT, realizada_em TEXT, proxima_acao TEXT, responsavel_id INTEGER REFERENCES usuarios(id),
            criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE TABLE IF NOT EXISTS marketing_conteudos (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, campanha_id BIGINT REFERENCES marketing_campanhas(id),
            titulo TEXT NOT NULL, formato TEXT NOT NULL DEFAULT 'Post', canal TEXT, etapa TEXT NOT NULL DEFAULT 'Pauta',
            responsavel_id INTEGER REFERENCES usuarios(id), data_publicacao TEXT, observacoes TEXT, criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE TABLE IF NOT EXISTS marketing_automacoes (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, nome TEXT NOT NULL, gatilho TEXT NOT NULL,
            acao TEXT NOT NULL, campanha_id BIGINT REFERENCES marketing_campanhas(id), ativo INTEGER NOT NULL DEFAULT 1, criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE TABLE IF NOT EXISTS marketing_metricas (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, campanha_id BIGINT NOT NULL REFERENCES marketing_campanhas(id),
            referencia TEXT NOT NULL, impressoes INTEGER NOT NULL DEFAULT 0, cliques INTEGER NOT NULL DEFAULT 0, leads INTEGER NOT NULL DEFAULT 0,
            mqls INTEGER NOT NULL DEFAULT 0, conversoes INTEGER NOT NULL DEFAULT 0, investimento_centavos BIGINT NOT NULL DEFAULT 0,
            receita_centavos BIGINT NOT NULL DEFAULT 0, criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(campanha_id, referencia)
        );
        INSERT INTO marketing_canais (empresa_id,nome,tipo,status)
        SELECT DISTINCT empresa_id, canal, 'Legado', 'Ativo' FROM campanhas_marketing c
        WHERE COALESCE(TRIM(c.canal),'')<>'' AND NOT EXISTS (SELECT 1 FROM marketing_canais m WHERE m.empresa_id=c.empresa_id AND m.nome=c.canal);
        INSERT INTO marketing_campanhas (empresa_id,filial_id,nome,canal_id,investimento_centavos,receita_atribuida_centavos,status,legacy_campanha_id,criado_por,criado_em)
        SELECT c.empresa_id,c.filial_id,c.nome,m.id,c.investimento_centavos,c.receita_centavos,c.status,c.id,c.criado_por,c.criado_em
        FROM campanhas_marketing c LEFT JOIN marketing_canais m ON m.empresa_id=c.empresa_id AND m.nome=c.canal
        WHERE NOT EXISTS (SELECT 1 FROM marketing_campanhas x WHERE x.legacy_campanha_id=c.id);

        CREATE TABLE IF NOT EXISTS comercial_pipeline_etapas (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), nome TEXT NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 0, probabilidade INTEGER NOT NULL DEFAULT 0, cor TEXT, ativo INTEGER NOT NULL DEFAULT 1,
            UNIQUE(empresa_id,nome)
        );
        CREATE TABLE IF NOT EXISTS comercial_oportunidades (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER,
            crm_empresa_id BIGINT REFERENCES crm_empresas(id), contato_id BIGINT REFERENCES crm_contatos(id), lead_id BIGINT REFERENCES crm_leads(id),
            titulo TEXT NOT NULL, responsavel_id INTEGER REFERENCES usuarios(id), etapa_id BIGINT REFERENCES comercial_pipeline_etapas(id),
            valor_centavos BIGINT NOT NULL DEFAULT 0, probabilidade INTEGER NOT NULL DEFAULT 0, fechamento_previsto TEXT,
            status TEXT NOT NULL DEFAULT 'Aberta', motivo_perda TEXT, proxima_acao TEXT, legacy_oportunidade_id INTEGER,
            criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_comercial_oportunidade_legacy ON comercial_oportunidades(legacy_oportunidade_id) WHERE legacy_oportunidade_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_comercial_oportunidades_escopo ON comercial_oportunidades(empresa_id,filial_id,status,etapa_id,id DESC);
        CREATE TABLE IF NOT EXISTS comercial_atividades (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, oportunidade_id BIGINT NOT NULL REFERENCES comercial_oportunidades(id),
            tipo TEXT NOT NULL, descricao TEXT, realizada_em TEXT, proxima_acao TEXT, responsavel_id INTEGER REFERENCES usuarios(id), criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE TABLE IF NOT EXISTS comercial_propostas (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, oportunidade_id BIGINT NOT NULL REFERENCES comercial_oportunidades(id),
            numero TEXT NOT NULL, validade TEXT, valor_centavos BIGINT NOT NULL DEFAULT 0, desconto_centavos BIGINT NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Rascunho',
            observacoes TEXT, criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(empresa_id,numero)
        );
        CREATE TABLE IF NOT EXISTS comercial_proposta_itens (
            id BIGSERIAL PRIMARY KEY, proposta_id BIGINT NOT NULL REFERENCES comercial_propostas(id) ON DELETE CASCADE, descricao TEXT NOT NULL, quantidade DOUBLE PRECISION NOT NULL DEFAULT 1, valor_unitario_centavos BIGINT NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS comercial_metas (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, responsavel_id INTEGER REFERENCES usuarios(id), referencia TEXT NOT NULL, valor_centavos BIGINT NOT NULL DEFAULT 0,
            criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(empresa_id,filial_id,responsavel_id,referencia)
        );
        CREATE TABLE IF NOT EXISTS comercial_forecasts (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, referencia TEXT NOT NULL, pipeline_centavos BIGINT NOT NULL DEFAULT 0, ponderado_centavos BIGINT NOT NULL DEFAULT 0,
            comprometido_centavos BIGINT NOT NULL DEFAULT 0, meta_centavos BIGINT NOT NULL DEFAULT 0, atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(empresa_id,filial_id,referencia)
        );
        INSERT INTO comercial_pipeline_etapas (empresa_id,nome,ordem,probabilidade)
        SELECT e.id,x.nome,x.ordem,x.prob FROM empresas e CROSS JOIN (VALUES ('Novo',10,10),('Qualificação',20,25),('Proposta',30,50),('Negociação',40,70),('Fechamento',50,90)) x(nome,ordem,prob)
        ON CONFLICT(empresa_id,nome) DO NOTHING;
        INSERT INTO comercial_oportunidades (empresa_id,filial_id,titulo,etapa_id,valor_centavos,probabilidade,status,legacy_oportunidade_id,criado_por,criado_em)
        SELECT o.empresa_id,o.filial_id,o.cliente,(SELECT e.id FROM comercial_pipeline_etapas e WHERE e.empresa_id=o.empresa_id AND e.nome=CASE WHEN o.etapa='Qualificado' THEN 'Qualificação' WHEN o.etapa IN ('Ganho','Perdido') THEN 'Fechamento' ELSE o.etapa END LIMIT 1),
               COALESCE(o.valor_centavos,CAST(ROUND(COALESCE(o.valor,0)*100) AS BIGINT)),CASE WHEN o.status='Ganho' THEN 100 WHEN o.status='Perdido' THEN 0 ELSE 25 END,
               CASE WHEN o.status='Ganho' THEN 'Ganha' WHEN o.status='Perdido' THEN 'Perdida' ELSE 'Aberta' END,o.id,o.criado_por,o.criado_em
        FROM oportunidades_comerciais o WHERE NOT EXISTS (SELECT 1 FROM comercial_oportunidades n WHERE n.legacy_oportunidade_id=o.id);

        CREATE TABLE IF NOT EXISTS administrativo_solicitacoes (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, numero TEXT NOT NULL, solicitante_id INTEGER REFERENCES usuarios(id), solicitante_nome TEXT, categoria TEXT NOT NULL, titulo TEXT NOT NULL,
            descricao TEXT, prioridade TEXT NOT NULL DEFAULT 'Média', responsavel_id INTEGER REFERENCES usuarios(id), sla_horas INTEGER NOT NULL DEFAULT 48, prazo TEXT, valor_centavos BIGINT NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Aberta', centro_custo_id INTEGER REFERENCES centros_custo(id), legacy_solicitacao_id INTEGER, criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(empresa_id,numero)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_adm_solicitacao_legacy ON administrativo_solicitacoes(legacy_solicitacao_id) WHERE legacy_solicitacao_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_adm_solicitacoes_fila ON administrativo_solicitacoes(empresa_id,filial_id,status,prioridade,id DESC);
        CREATE TABLE IF NOT EXISTS administrativo_recursos (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,tipo TEXT NOT NULL,nome TEXT NOT NULL,localizacao TEXT,capacidade INTEGER,status TEXT NOT NULL DEFAULT 'Disponível',observacoes TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE TABLE IF NOT EXISTS administrativo_reservas (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,recurso_id BIGINT NOT NULL REFERENCES administrativo_recursos(id),titulo TEXT NOT NULL,inicio TEXT NOT NULL,fim TEXT NOT NULL,responsavel_id INTEGER REFERENCES usuarios(id),status TEXT NOT NULL DEFAULT 'Confirmada',observacoes TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE INDEX IF NOT EXISTS idx_adm_reservas_recurso ON administrativo_reservas(recurso_id,inicio,fim,status);
        CREATE TABLE IF NOT EXISTS administrativo_viagens (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,viajante TEXT NOT NULL,destino TEXT NOT NULL,inicio TEXT,fim TEXT,motivo TEXT,custo_estimado_centavos BIGINT NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'Solicitada',criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE TABLE IF NOT EXISTS administrativo_reembolsos (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,solicitante TEXT NOT NULL,categoria TEXT NOT NULL,descricao TEXT,valor_centavos BIGINT NOT NULL DEFAULT 0,centro_custo_id INTEGER REFERENCES centros_custo(id),status TEXT NOT NULL DEFAULT 'Pendente',aprovado_por INTEGER REFERENCES usuarios(id),pago_em TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE TABLE IF NOT EXISTS administrativo_manutencoes (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,recurso_id BIGINT REFERENCES administrativo_recursos(id),titulo TEXT NOT NULL,descricao TEXT,prioridade TEXT NOT NULL DEFAULT 'Média',fornecedor TEXT,custo_centavos BIGINT NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'Aberta',prazo TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        INSERT INTO administrativo_solicitacoes (empresa_id,filial_id,numero,solicitante_nome,categoria,titulo,prioridade,valor_centavos,status,centro_custo_id,legacy_solicitacao_id,criado_por,criado_em)
        SELECT s.empresa_id,s.filial_id,'LEG-'||s.id,s.solicitante,s.categoria,s.titulo,'Média',COALESCE(s.valor_centavos,CAST(ROUND(COALESCE(s.valor,0)*100) AS BIGINT)),CASE WHEN s.status='Pendente' THEN 'Aberta' WHEN s.status='Em análise' THEN 'Triagem' ELSE s.status END,s.centro_custo_id,s.id,s.criado_por,s.criado_em
        FROM solicitacoes_administrativas s WHERE NOT EXISTS (SELECT 1 FROM administrativo_solicitacoes n WHERE n.legacy_solicitacao_id=s.id);

        CREATE TABLE IF NOT EXISTS juridico_contratos (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,numero TEXT,titulo TEXT NOT NULL,parte TEXT NOT NULL,objeto TEXT,valor_centavos BIGINT NOT NULL DEFAULT 0,risco TEXT NOT NULL DEFAULT 'Baixo',inicio TEXT,vencimento TEXT,responsavel_id INTEGER REFERENCES usuarios(id),status TEXT NOT NULL DEFAULT 'Elaboração',legacy_contrato_id INTEGER,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE UNIQUE INDEX IF NOT EXISTS ux_juridico_contrato_legacy ON juridico_contratos(legacy_contrato_id) WHERE legacy_contrato_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS juridico_processos (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,numero TEXT NOT NULL,titulo TEXT NOT NULL,tribunal TEXT,parte_contraria TEXT,advogado_responsavel TEXT,tipo TEXT,fase TEXT,valor_causa_centavos BIGINT NOT NULL DEFAULT 0,probabilidade TEXT NOT NULL DEFAULT 'Possível',risco TEXT NOT NULL DEFAULT 'Médio',status TEXT NOT NULL DEFAULT 'Ativo',criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),UNIQUE(empresa_id,numero));
        CREATE TABLE IF NOT EXISTS juridico_prazos (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,processo_id BIGINT REFERENCES juridico_processos(id),contrato_id BIGINT REFERENCES juridico_contratos(id),titulo TEXT NOT NULL,vencimento TEXT NOT NULL,tipo TEXT,prioridade TEXT NOT NULL DEFAULT 'Alta',responsavel_id INTEGER REFERENCES usuarios(id),status TEXT NOT NULL DEFAULT 'Pendente',observacoes TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE INDEX IF NOT EXISTS idx_juridico_prazos_agenda ON juridico_prazos(empresa_id,status,vencimento);
        CREATE TABLE IF NOT EXISTS juridico_audiencias (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,processo_id BIGINT NOT NULL REFERENCES juridico_processos(id),data_hora TEXT NOT NULL,local TEXT,tipo TEXT,responsavel TEXT,status TEXT NOT NULL DEFAULT 'Agendada',observacoes TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE TABLE IF NOT EXISTS juridico_riscos (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,processo_id BIGINT REFERENCES juridico_processos(id),contrato_id BIGINT REFERENCES juridico_contratos(id),titulo TEXT NOT NULL,probabilidade TEXT NOT NULL,impacto TEXT NOT NULL,exposicao_centavos BIGINT NOT NULL DEFAULT 0,justificativa TEXT,responsavel_id INTEGER REFERENCES usuarios(id),status TEXT NOT NULL DEFAULT 'Aberto',revisado_em TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        CREATE TABLE IF NOT EXISTS juridico_provisoes (id BIGSERIAL PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),filial_id INTEGER,processo_id BIGINT REFERENCES juridico_processos(id),risco_id BIGINT REFERENCES juridico_riscos(id),referencia TEXT NOT NULL,valor_centavos BIGINT NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'Proposta',observacoes TEXT,criado_por INTEGER REFERENCES usuarios(id),criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')));
        INSERT INTO juridico_contratos (empresa_id,filial_id,titulo,parte,valor_centavos,risco,vencimento,status,legacy_contrato_id,criado_por,criado_em)
        SELECT c.empresa_id,c.filial_id,c.titulo,c.parte,COALESCE(c.valor_centavos,CAST(ROUND(COALESCE(c.valor,0)*100) AS BIGINT)),c.risco,c.vencimento,c.status,c.id,c.criado_por,c.criado_em
        FROM contratos_juridicos c WHERE NOT EXISTS (SELECT 1 FROM juridico_contratos n WHERE n.legacy_contrato_id=c.id);

        CREATE TABLE IF NOT EXISTS analytics_insights (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER,
            modulo TEXT NOT NULL, codigo TEXT NOT NULL, titulo TEXT NOT NULL, descricao TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Informativa', prioridade INTEGER NOT NULL DEFAULT 50, tipo TEXT NOT NULL DEFAULT 'Regra',
            metrica_chave TEXT, metrica_valor DOUBLE PRECISION, unidade TEXT, acao_tipo TEXT NOT NULL DEFAULT 'navegar',
            acao_modulo TEXT, acao_secao TEXT, acao_rotulo TEXT, fingerprint TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'Ativo',
            detectado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            resolvido_em TEXT, resolvido_por INTEGER REFERENCES usuarios(id), criado_por INTEGER REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_insights_contexto ON analytics_insights(empresa_id,filial_id,status,prioridade);
        CREATE INDEX IF NOT EXISTS idx_analytics_insights_modulo ON analytics_insights(empresa_id,modulo,status);
        CREATE TABLE IF NOT EXISTS analytics_regras (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, codigo TEXT NOT NULL,
            nome TEXT NOT NULL, modulo TEXT NOT NULL, metrica TEXT NOT NULL, operador TEXT NOT NULL DEFAULT '>', limite DOUBLE PRECISION,
            severidade TEXT NOT NULL DEFAULT 'Atenção', acao_modulo TEXT, acao_secao TEXT, ativo INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE(empresa_id,filial_id,codigo)
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_regras_contexto ON analytics_regras(empresa_id,filial_id,ativo,modulo);
        CREATE TABLE IF NOT EXISTS analytics_execucoes (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, origem TEXT NOT NULL DEFAULT 'empresarial',
            modulos_processados INTEGER NOT NULL DEFAULT 0, insights_gerados INTEGER NOT NULL DEFAULT 0, erros INTEGER NOT NULL DEFAULT 0,
            duracao_ms INTEGER NOT NULL DEFAULT 0, criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );
        CREATE TABLE IF NOT EXISTS orquestracoes_empresariais (
            id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER, tipo TEXT NOT NULL,
            referencia_tipo TEXT, referencia_id BIGINT, titulo TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Aberta',
            responsavel_id INTEGER REFERENCES usuarios(id), dados_json TEXT NOT NULL DEFAULT '{}', criado_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), concluido_em TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_orquestracoes_contexto ON orquestracoes_empresariais(empresa_id,filial_id,tipo,status);
        CREATE TABLE IF NOT EXISTS orquestracao_etapas (
            id BIGSERIAL PRIMARY KEY, orquestracao_id BIGINT NOT NULL REFERENCES orquestracoes_empresariais(id) ON DELETE CASCADE,
            codigo TEXT NOT NULL, titulo TEXT NOT NULL, modulo TEXT NOT NULL, ordem INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Pendente', responsavel_id INTEGER REFERENCES usuarios(id), dados_json TEXT NOT NULL DEFAULT '{}',
            concluido_em TEXT, concluido_por INTEGER REFERENCES usuarios(id),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(orquestracao_id,codigo)
        );
        CREATE INDEX IF NOT EXISTS idx_orquestracao_etapas_status ON orquestracao_etapas(orquestracao_id,status,ordem);
        """,
        prepare=False,
    )
    raw.execute(_HARDENING.read_text(encoding="utf-8"), prepare=False)
    raw.execute(_V11.read_text(encoding="utf-8"), prepare=False)
    raw.execute(_V11_1.read_text(encoding="utf-8"), prepare=False)


def _existe_baseline(raw) -> bool:
    row=raw.execute("SELECT to_regclass('public.migracoes_sistema')", prepare=False).fetchone()
    if not row or row[0] is None: return False
    row=raw.execute("SELECT 1 FROM migracoes_sistema WHERE chave='postgresql_baseline_v10_1'", prepare=False).fetchone()
    return row is not None


def _tabelas_esperadas() -> tuple[str, ...]:
    """Extrai as tabelas do baseline para detectar instalação parcial/corrompida."""
    sql = "\n".join(
        arquivo.read_text(encoding="utf-8") for arquivo in (_SCHEMA, _HARDENING, _V11, _V11_1)
    )
    nomes = {
        match.group(1).lower()
        for match in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)",
            sql,
            flags=re.I,
        )
    }
    nomes.update({"historico_analises", "preferencias_usuarios", "crm_empresas", "crm_contatos", "crm_leads", "crm_atividades", "marketing_canais", "marketing_campanhas", "marketing_conteudos", "marketing_automacoes", "marketing_metricas", "comercial_pipeline_etapas", "comercial_oportunidades", "comercial_atividades", "comercial_propostas", "comercial_proposta_itens", "comercial_metas", "comercial_forecasts", "administrativo_solicitacoes", "administrativo_recursos", "administrativo_reservas", "administrativo_viagens", "administrativo_reembolsos", "administrativo_manutencoes", "juridico_contratos", "juridico_processos", "juridico_prazos", "juridico_audiencias", "juridico_riscos", "juridico_provisoes", "analytics_insights", "analytics_regras", "analytics_execucoes", "orquestracoes_empresariais", "orquestracao_etapas"})
    return tuple(sorted(nomes))


def validar_schema_runtime() -> dict:
    """Confirma que o PostgreSQL contém todas as tabelas esperadas pela build."""
    esperadas = _tabelas_esperadas()
    pool = obter_pool()
    with pool.connection() as raw:
        rows = raw.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public'",
            prepare=False,
        ).fetchall()
        raw.commit()
    existentes = {str(row[0]).lower() for row in rows}
    ausentes = [nome for nome in esperadas if nome not in existentes]
    if ausentes:
        raise RuntimeError(
            "Schema PostgreSQL incompleto para esta versão. Tabelas ausentes: "
            + ", ".join(ausentes[:40])
            + (" ..." if len(ausentes) > 40 else "")
        )
    return {"ok": True, "tabelas_esperadas": len(esperadas), "tabelas_encontradas": len(existentes)}


def inicializar_schema_postgresql(*, forcar: bool=False) -> None:
    """Cria o baseline PostgreSQL e preserva o erro SQL original em caso de falha.

    O schema V10.1 possui BEGIN/COMMIT próprios. Por isso ele é executado com
    autocommit habilitado somente enquanto a conexão está IDLE. Se algum comando
    do lote falhar, fazemos rollback ANTES de restaurar o modo de autocommit.
    """
    global _PRONTO
    with _LOCK:
        if _PRONTO and not forcar:
            return

        pool = obter_pool()
        with pool.connection() as raw:
            if _existe_baseline(raw):
                _garantir_extensoes_runtime(raw)
                raw.commit()
                _PRONTO = True
                return

            sql = _SCHEMA.read_text(encoding="utf-8")

            # SELECTs anteriores podem ter iniciado uma transação implícita.
            raw.rollback()
            anterior = raw.autocommit

            try:
                raw.autocommit = True
                try:
                    raw.execute(sql, prepare=False)
                except Exception:
                    # Uma falha no lote pode deixar a sessão em INERROR,
                    # especialmente porque o próprio schema contém BEGIN/COMMIT.
                    # É obrigatório sair desse estado antes de alterar autocommit.
                    try:
                        raw.rollback()
                    except Exception:
                        logging.getLogger(__name__).exception("Rollback PostgreSQL após falha de bootstrap também falhou")
                    raise
            finally:
                # Nunca tente alterar autocommit enquanto a conexão estiver
                # dentro de uma transação/estado de erro.
                try:
                    raw.rollback()
                except Exception:
                    logging.getLogger(__name__).exception("Rollback final do bootstrap PostgreSQL falhou")
                raw.autocommit = anterior

            # Confirma que o lote realmente chegou ao baseline.
            if not _existe_baseline(raw):
                raw.rollback()
                raise RuntimeError(
                    "O schema PostgreSQL foi executado, mas o baseline "
                    "'postgresql_baseline_v10_1' não foi criado."
                )

            _garantir_extensoes_runtime(raw)
            raw.commit()
            _PRONTO = True


def health_postgresql() -> dict:
    pool=obter_pool()
    with pool.connection() as raw:
        banco, usuario, versao = raw.execute(
            "SELECT current_database(), current_user, current_setting('server_version')", prepare=False
        ).fetchone()
        baseline=_existe_baseline(raw); raw.commit()
    stats={}
    try:
        stats=dict(pool.get_stats())
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível coletar estatísticas do pool PostgreSQL")
    schema = validar_schema_runtime() if baseline else {"ok": False}
    return {
        "backend":"postgresql","banco":banco,"usuario":usuario,"versao":versao,
        "schema_pronto":baseline and bool(schema.get("ok")),"schema":schema,"pool":stats
    }
