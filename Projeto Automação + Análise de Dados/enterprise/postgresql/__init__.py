"""Backend PostgreSQL da autoridade corporativa V10.1."""
from .adapter import (
    ConfigPostgres,
    ConexaoCompat,
    CursorCompat,
    DependenciaPostgresAusente,
    HybridRow,
    conectar_postgresql,
    fechar_pool,
    obter_pool,
    testar_conexao,
    traduzir_sql,
)

__all__ = [
    "ConfigPostgres", "ConexaoCompat", "CursorCompat", "DependenciaPostgresAusente",
    "HybridRow", "conectar_postgresql", "fechar_pool", "obter_pool", "testar_conexao",
    "traduzir_sql",
]
