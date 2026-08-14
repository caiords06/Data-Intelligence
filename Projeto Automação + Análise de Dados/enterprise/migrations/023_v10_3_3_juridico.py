"""V10.3.3 — Jurídico especializado com contratos, processos, prazos e risco."""
from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS juridico_contratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            numero TEXT, titulo TEXT NOT NULL, parte TEXT NOT NULL, objeto TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0,
            risco TEXT NOT NULL DEFAULT 'Baixo', inicio TEXT, vencimento TEXT, responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Elaboração', legacy_contrato_id INTEGER, criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_juridico_contrato_legacy ON juridico_contratos(legacy_contrato_id) WHERE legacy_contrato_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS juridico_processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            numero TEXT NOT NULL, titulo TEXT NOT NULL, tribunal TEXT, parte_contraria TEXT, advogado_responsavel TEXT,
            tipo TEXT, fase TEXT, valor_causa_centavos INTEGER NOT NULL DEFAULT 0, probabilidade TEXT NOT NULL DEFAULT 'Possível',
            risco TEXT NOT NULL DEFAULT 'Médio', status TEXT NOT NULL DEFAULT 'Ativo', criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, numero)
        );
        CREATE TABLE IF NOT EXISTS juridico_prazos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            processo_id INTEGER, contrato_id INTEGER, titulo TEXT NOT NULL, vencimento TEXT NOT NULL,
            tipo TEXT, prioridade TEXT NOT NULL DEFAULT 'Alta', responsavel_id INTEGER, status TEXT NOT NULL DEFAULT 'Pendente',
            observacoes TEXT, criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_juridico_prazos_agenda ON juridico_prazos(empresa_id, status, vencimento);
        CREATE TABLE IF NOT EXISTS juridico_audiencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            processo_id INTEGER NOT NULL, data_hora TEXT NOT NULL, local TEXT, tipo TEXT, responsavel TEXT,
            status TEXT NOT NULL DEFAULT 'Agendada', observacoes TEXT, criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS juridico_riscos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            processo_id INTEGER, contrato_id INTEGER, titulo TEXT NOT NULL, probabilidade TEXT NOT NULL,
            impacto TEXT NOT NULL, exposicao_centavos INTEGER NOT NULL DEFAULT 0, justificativa TEXT,
            responsavel_id INTEGER, status TEXT NOT NULL DEFAULT 'Aberto', revisado_em TEXT,
            criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS juridico_provisoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            processo_id INTEGER, risco_id INTEGER, referencia TEXT NOT NULL, valor_centavos INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Proposta', observacoes TEXT, criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conexao.execute(
        """
        INSERT OR IGNORE INTO juridico_contratos (
            empresa_id, filial_id, titulo, parte, valor_centavos, risco, vencimento, status,
            legacy_contrato_id, criado_por, criado_em
        )
        SELECT c.empresa_id, c.filial_id, c.titulo, c.parte,
               COALESCE(c.valor_centavos, CAST(ROUND(COALESCE(c.valor,0)*100) AS INTEGER)),
               c.risco, c.vencimento, c.status, c.id, c.criado_por, c.criado_em
        FROM contratos_juridicos c
        WHERE NOT EXISTS (SELECT 1 FROM juridico_contratos n WHERE n.legacy_contrato_id=c.id)
        """
    )
