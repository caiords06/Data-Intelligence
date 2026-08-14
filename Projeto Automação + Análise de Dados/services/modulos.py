"""Casos de uso dos registros modulares genéricos."""
from enterprise.modulos import (
    alterar_estado_registro, atualizar_registro, calcular_resumo_modulo,
    criar_registro, listar_registros_paginados, movimentar_estoque, obter_registro,
)

__all__ = (
    "alterar_estado_registro", "atualizar_registro", "calcular_resumo_modulo",
    "criar_registro", "listar_registros_paginados", "movimentar_estoque", "obter_registro",
)
