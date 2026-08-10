"""Migrações versionadas e idempotentes do banco empresarial."""

from __future__ import annotations

from importlib import import_module


MIGRACOES = (
    "001_v6_estabilizacao",
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

