"""Indicadores de investimento, conversão e retorno de Marketing."""

import pandas as pd

from analytics.base import numerica, percentual, ranking_soma, seguro, texto


def calcular_indicadores_marketing(df: pd.DataFrame, _campos: dict) -> dict:
    investimento = numerica(df, "investimento")
    leads = numerica(df, "leads")
    conversoes = numerica(df, "conversoes", "conversões")
    receita = numerica(df, "receita", "receita atribuida")
    canais = texto(df, "canal")
    campanhas = texto(df, "nome", "campanha")
    total_investimento = seguro(investimento.sum())
    total_leads = seguro(leads.sum())
    total_conversoes = seguro(conversoes.sum())
    total_receita = seguro(receita.sum())
    receita_por_canal = ranking_soma(canais, receita)
    receita_por_campanha = ranking_soma(campanhas, receita)
    return {
        "investimento_total": total_investimento,
        "leads_total": total_leads,
        "conversoes_total": total_conversoes,
        "receita_atribuida": total_receita,
        "cpl": total_investimento / total_leads if total_leads else 0.0,
        "cac": total_investimento / total_conversoes if total_conversoes else 0.0,
        "roas": total_receita / total_investimento if total_investimento else 0.0,
        "roi_percentual": percentual(total_receita - total_investimento, total_investimento),
        "taxa_conversao": percentual(total_conversoes, total_leads),
        "melhor_canal": next(iter(receita_por_canal), None),
        "melhor_campanha": next(iter(receita_por_campanha), None),
        "receita_por_canal": receita_por_canal,
        "receita_por_campanha": receita_por_campanha,
    }

