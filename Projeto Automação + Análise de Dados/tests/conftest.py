"""Isolamento da suíte legada.

Produção é PostgreSQL-only. A suíte antiga ainda exercita SQLite em diretórios
temporários para testes unitários rápidos e migração; essa liberação existe
somente dentro do processo de pytest.
"""
import os

os.environ.setdefault("DATA_INTELLIGENCE_ALLOW_STANDALONE", "1")
os.environ.setdefault("DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE", "1")
os.environ.setdefault("DATA_INTELLIGENCE_DB_BACKEND", "sqlite")


def _limpar_estado_global_pos_teste() -> None:
    """Evita que sessões, pools e caches sobrevivam entre testes no mesmo pytest.

    O runner oficial ainda isola cada arquivo em processo próprio (defesa em
    profundidade), mas esta limpeza torna a execução monolítica bem menos
    sensível à ordem dos testes.
    """
    try:
        from auth.sessao import SESSAO
        SESSAO.encerrar()
    except Exception:
        pass
    try:
        from enterprise.servidor_cliente import encerrar_sessao_remota, _limpar_arquivos_temporarios
        encerrar_sessao_remota()
        _limpar_arquivos_temporarios()
    except Exception:
        pass
    try:
        from enterprise.postgresql.adapter import fechar_pool
        fechar_pool()
    except Exception:
        pass


import gc
import pytest


@pytest.fixture(autouse=True)
def _isolamento_global_por_teste():
    yield
    _limpar_estado_global_pos_teste()
    gc.collect()
