"""V10.3.2 — Administrativo especializado e central de serviços internos."""
from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS administrativo_solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            numero TEXT NOT NULL, solicitante_id INTEGER, solicitante_nome TEXT, categoria TEXT NOT NULL,
            titulo TEXT NOT NULL, descricao TEXT, prioridade TEXT NOT NULL DEFAULT 'Média', responsavel_id INTEGER,
            sla_horas INTEGER NOT NULL DEFAULT 48, prazo TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Aberta', centro_custo_id INTEGER, legacy_solicitacao_id INTEGER,
            criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, numero)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_adm_solicitacao_legacy ON administrativo_solicitacoes(legacy_solicitacao_id) WHERE legacy_solicitacao_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_adm_solicitacoes_fila ON administrativo_solicitacoes(empresa_id, filial_id, status, prioridade, id DESC);
        CREATE TABLE IF NOT EXISTS administrativo_recursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            tipo TEXT NOT NULL, nome TEXT NOT NULL, localizacao TEXT, capacidade INTEGER, status TEXT NOT NULL DEFAULT 'Disponível',
            observacoes TEXT, criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS administrativo_reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            recurso_id INTEGER NOT NULL, titulo TEXT NOT NULL, inicio TEXT NOT NULL, fim TEXT NOT NULL,
            responsavel_id INTEGER, status TEXT NOT NULL DEFAULT 'Confirmada', observacoes TEXT, criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (recurso_id) REFERENCES administrativo_recursos(id)
        );
        CREATE INDEX IF NOT EXISTS idx_adm_reservas_recurso ON administrativo_reservas(recurso_id, inicio, fim, status);
        CREATE TABLE IF NOT EXISTS administrativo_viagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            viajante TEXT NOT NULL, destino TEXT NOT NULL, inicio TEXT, fim TEXT, motivo TEXT,
            custo_estimado_centavos INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Solicitada', criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS administrativo_reembolsos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            solicitante TEXT NOT NULL, categoria TEXT NOT NULL, descricao TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0,
            centro_custo_id INTEGER, status TEXT NOT NULL DEFAULT 'Pendente', aprovado_por INTEGER, pago_em TEXT,
            criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS administrativo_manutencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, filial_id INTEGER,
            recurso_id INTEGER, titulo TEXT NOT NULL, descricao TEXT, prioridade TEXT NOT NULL DEFAULT 'Média',
            fornecedor TEXT, custo_centavos INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Aberta',
            prazo TEXT, criado_por INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conexao.execute(
        """
        INSERT OR IGNORE INTO administrativo_solicitacoes (
            empresa_id, filial_id, numero, solicitante_nome, categoria, titulo, prioridade,
            valor_centavos, status, centro_custo_id, legacy_solicitacao_id, criado_por, criado_em
        )
        SELECT s.empresa_id, s.filial_id, 'LEG-' || s.id, s.solicitante, s.categoria, s.titulo, 'Média',
               COALESCE(s.valor_centavos, CAST(ROUND(COALESCE(s.valor,0)*100) AS INTEGER)),
               CASE WHEN s.status='Pendente' THEN 'Aberta' WHEN s.status='Em análise' THEN 'Triagem' ELSE s.status END,
               s.centro_custo_id, s.id, s.criado_por, s.criado_em
        FROM solicitacoes_administrativas s
        WHERE NOT EXISTS (SELECT 1 FROM administrativo_solicitacoes n WHERE n.legacy_solicitacao_id=s.id)
        """
    )
