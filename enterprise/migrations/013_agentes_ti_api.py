"""API central do agente TI: credenciais, estado e proteção contra replay."""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS ti_agentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo_id INTEGER NOT NULL,
            agent_id TEXT NOT NULL UNIQUE,
            token_hash TEXT NOT NULL,
            patrimonio TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Provisionado'
                CHECK (status IN ('Provisionado','Online','Degradado','Revogado')),
            ultimo_ip TEXT,
            ultima_versao TEXT,
            ultimo_heartbeat TEXT,
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            UNIQUE (ativo_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_ti_agentes_escopo
            ON ti_agentes (empresa_id, filial_id, ativo, status);

        CREATE TABLE IF NOT EXISTS ti_agente_nonces (
            agente_id INTEGER NOT NULL,
            nonce TEXT NOT NULL,
            recebido_em INTEGER NOT NULL,
            PRIMARY KEY (agente_id, nonce),
            FOREIGN KEY (agente_id) REFERENCES ti_agentes(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ti_agente_nonces_tempo
            ON ti_agente_nonces (recebido_em);
        """
    )
