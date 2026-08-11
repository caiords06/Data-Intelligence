"""Migrações versionadas e idempotentes do banco empresarial."""

from __future__ import annotations

from importlib import import_module


MIGRACOES = (
    "001_v6_estabilizacao",
    "002_v8_recursos_departamentais",
    "003_v8_1_integridade",
    "004_v8_2_estabilizacao",
    "005_financeiro_departamental",
    "006_rh_departamental",
    "007_rh_2_0_complementos",
    "008_estoque_departamental",
    "009_compras_departamental",
    "010_tecnologia_departamental",
    "011_tecnologia_operacoes_rede",
    "012_segmentos_rede_multifilial",
    "013_agentes_ti_api",
    "014_colaboracao_email_sessoes",
    "015_aprovacoes_compras",
    "016_relatorios_formatos",
    "017_consistencia_monetaria_aprovacoes",
    "018_caminhos_rh_portaveis",
)


def aplicar_migracoes(conexao) -> None:
    """Aplica, em ordem, somente migrações ainda não registradas."""
    for nome in MIGRACOES:
        chave = f"enterprise_{nome}"
        aplicada = conexao.execute(
            "SELECT 1 FROM migracoes_sistema WHERE chave = ?",
            (chave,),
        ).fetchone()
        if aplicada is not None:
            continue

        modulo = import_module(f"enterprise.migrations.{nome}")
        modulo.upgrade(conexao)
        conexao.execute(
            "INSERT INTO migracoes_sistema (chave) VALUES (?)",
            (chave,),
        )
