"""Fachada de persistência empresarial.

Os domínios dependem somente deste contrato. PostgreSQL é o backend canônico de
produção; SQLite só pode ser habilitado explicitamente para migração/testes.
"""
from .provider import (
    backend_atual,
    conectar,
    configurar_provider,
    obter_provider,
    provider_sqlite,
    provider_temporario,
)

__all__ = (
    "backend_atual",
    "conectar",
    "configurar_provider",
    "obter_provider",
    "provider_sqlite",
    "provider_temporario",
)
