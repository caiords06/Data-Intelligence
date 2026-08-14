"""V10.4.0 — Analytics empresarial: insights persistentes e regras analíticas."""
from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS analytics_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            codigo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Informativa',
            prioridade INTEGER NOT NULL DEFAULT 50,
            tipo TEXT NOT NULL DEFAULT 'Regra',
            metrica_chave TEXT,
            metrica_valor REAL,
            unidade TEXT,
            acao_tipo TEXT NOT NULL DEFAULT 'navegar',
            acao_modulo TEXT,
            acao_secao TEXT,
            acao_rotulo TEXT,
            fingerprint TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'Ativo',
            detectado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolvido_em TEXT,
            resolvido_por INTEGER,
            criado_por INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_insights_contexto
            ON analytics_insights(empresa_id, filial_id, status, prioridade);
        CREATE INDEX IF NOT EXISTS idx_analytics_insights_modulo
            ON analytics_insights(empresa_id, modulo, status);

        CREATE TABLE IF NOT EXISTS analytics_regras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            modulo TEXT NOT NULL,
            metrica TEXT NOT NULL,
            operador TEXT NOT NULL DEFAULT '>',
            limite REAL,
            severidade TEXT NOT NULL DEFAULT 'Atenção',
            acao_modulo TEXT,
            acao_secao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, filial_id, codigo)
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_regras_contexto
            ON analytics_regras(empresa_id, filial_id, ativo, modulo);

        CREATE TABLE IF NOT EXISTS analytics_execucoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            origem TEXT NOT NULL DEFAULT 'empresarial',
            modulos_processados INTEGER NOT NULL DEFAULT 0,
            insights_gerados INTEGER NOT NULL DEFAULT 0,
            erros INTEGER NOT NULL DEFAULT 0,
            duracao_ms INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
