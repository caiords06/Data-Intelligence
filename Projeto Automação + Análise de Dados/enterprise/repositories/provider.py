"""Registro do provider de persistência da plataforma.

PostgreSQL é a autoridade transacional em produção. O provider SQLite permanece
apenas como compatibilidade de testes/migração quando habilitado explicitamente.
"""
from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from auth import banco as _banco_local

Provider = Callable[[], Any]
_provider: Provider | None = None
_provider_nome: str | None = None


def provider_sqlite():
    """Compatibilidade histórica: retorna o provider canônico do processo.

    O nome é mantido por compatibilidade; em produção retorna PostgreSQL.
    """
    return _banco_local.conectar()


def configurar_provider(provider: Provider | None, *, nome: str | None = None) -> None:
    """Define um provider alternativo; ``None`` restaura o backend canônico."""
    global _provider, _provider_nome
    if provider is not None and not callable(provider):
        raise TypeError("O provider de persistência precisa ser chamável.")
    _provider = provider
    _provider_nome = (str(nome).strip().lower() or "custom") if provider is not None else None


def obter_provider() -> Provider:
    return _provider or provider_sqlite


def backend_atual() -> str:
    """Identificador diagnóstico do backend em uso."""
    return _provider_nome or _banco_local.backend_banco()


def conectar():
    return obter_provider()()


@contextmanager
def provider_temporario(provider: Provider, *, nome: str = "teste"):
    """Troca o provider apenas dentro do bloco e restaura o estado anterior."""
    global _provider, _provider_nome
    anterior, nome_anterior = _provider, _provider_nome
    configurar_provider(provider, nome=nome)
    try:
        yield
    finally:
        _provider, _provider_nome = anterior, nome_anterior
