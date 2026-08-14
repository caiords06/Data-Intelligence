"""Serviço estável da Inteligência Empresarial.

A interface desktop e a futura API/Web usam este mesmo ponto de entrada.
"""
from enterprise.analytics_inteligencia import (
    SEVERIDADES,
    alterar_status_insight,
    definir_regra_ativa,
    gerar_insights,
    historico_execucoes,
    contar_insights,
    listar_insights,
    listar_regras,
    obter_painel_executivo,
    salvar_regra,
)

__all__ = (
    "SEVERIDADES", "alterar_status_insight", "definir_regra_ativa", "gerar_insights",
    "historico_execucoes", "contar_insights", "listar_insights", "listar_regras", "obter_painel_executivo", "salvar_regra",
)
