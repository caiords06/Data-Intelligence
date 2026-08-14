"""V10.4.1 — Orquestrações transversais entre departamentos."""
from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS orquestracoes_empresariais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            referencia_tipo TEXT,
            referencia_id INTEGER,
            titulo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Aberta',
            responsavel_id INTEGER,
            dados_json TEXT NOT NULL DEFAULT '{}',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_orquestracoes_contexto
            ON orquestracoes_empresariais(empresa_id, filial_id, tipo, status);

        CREATE TABLE IF NOT EXISTS orquestracao_etapas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orquestracao_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            modulo TEXT NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Pendente',
            responsavel_id INTEGER,
            dados_json TEXT NOT NULL DEFAULT '{}',
            concluido_em TEXT,
            concluido_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(orquestracao_id, codigo)
        );
        CREATE INDEX IF NOT EXISTS idx_orquestracao_etapas_status
            ON orquestracao_etapas(orquestracao_id, status, ordem);
        """
    )
