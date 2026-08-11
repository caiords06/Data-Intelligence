"""Tecnologia 3.0: operação de rede, inventário gerenciado e metadados do agente."""

from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    return {linha["name"] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}


def _adicionar_coluna(conexao, tabela: str, definicao: str) -> None:
    nome = definicao.split()[0]
    if nome not in _colunas(conexao, tabela):
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {definicao}")


def upgrade(conexao) -> None:
    # Segmentos passam a registrar o estado operacional da última descoberta e
    # a regra de firewall local criada de forma restrita ao CIDR autorizado.
    for definicao in (
        "firewall_status TEXT",
        "firewall_regra TEXT",
        "ultima_varredura_em TEXT",
        "ultima_varredura_total INTEGER NOT NULL DEFAULT 0",
        "ultima_varredura_online INTEGER NOT NULL DEFAULT 0",
    ):
        _adicionar_coluna(conexao, "ti_segmentos_rede", definicao)

    # Dispositivos de descoberta podem ser arquivados sem apagar a trilha.
    for definicao in (
        "ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))",
        "ultimo_ping_ms REAL",
        "observacao TEXT",
    ):
        _adicionar_coluna(conexao, "ti_dispositivos_rede", definicao)

    # Campos produzidos pelo agente distribuído / acesso remoto. Mantê-los no
    # ativo permite que o painel detalhe a máquina sem acoplar a interface ao
    # formato de transporte do agente.
    for definicao in (
        "agent_id TEXT",
        "fqdn TEXT",
        "versao_sistema TEXT",
        "arquitetura TEXT",
        "usuario_sessao TEXT",
        "remote_alias TEXT",
        "remote_status TEXT",
        "remote_versao TEXT",
    ):
        _adicionar_coluna(conexao, "ti_ativos", definicao)

    conexao.execute(
        "CREATE INDEX IF NOT EXISTS idx_ti_dispositivos_rede_ativos ON ti_dispositivos_rede (segmento_id, ativo, ultima_deteccao DESC)"
    )
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS idx_ti_ativos_agent_id ON ti_ativos (empresa_id, agent_id)"
    )
