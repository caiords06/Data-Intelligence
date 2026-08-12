"""Motores analíticos empresariais especializados."""

from analytics.administrativo import calcular_indicadores_administrativo
from analytics.comercial import calcular_indicadores_comercial
from analytics.compras import calcular_indicadores_compras
from analytics.juridico import calcular_indicadores_juridico
from analytics.marketing import calcular_indicadores_marketing
from analytics.ti import calcular_indicadores_ti

__all__ = (
    "calcular_indicadores_administrativo",
    "calcular_indicadores_comercial",
    "calcular_indicadores_compras",
    "calcular_indicadores_juridico",
    "calcular_indicadores_marketing",
    "calcular_indicadores_ti",
)

