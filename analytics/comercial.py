"""Indicadores de pipeline e conversão Comercial."""

import pandas as pd

from analytics.base import numerica, percentual, ranking_contagem, seguro, status_normalizado, texto


def calcular_indicadores_comercial(df: pd.DataFrame, _campos: dict) -> dict:
    valores = numerica(df, "valor", "valor_estimado")
    status = status_normalizado(df)
    etapas = texto(df, "etapa")
    abertas = status.str.contains("aberto", regex=True, na=False)
    ganhas = status.str.contains("ganho", regex=True, na=False)
    perdidas = status.str.contains("perdido", regex=True, na=False)
    ranking = ranking_contagem(etapas)
    total_decididas = int(ganhas.sum() + perdidas.sum())
    return {
        "total_oportunidades": int(len(df)),
        "oportunidades_abertas": int(abertas.sum()),
        "oportunidades_ganhas": int(ganhas.sum()),
        "oportunidades_perdidas": int(perdidas.sum()),
        "pipeline_aberto": seguro(valores.where(abertas).sum()),
        "receita_ganha": seguro(valores.where(ganhas).sum()),
        "ticket_medio_ganho": seguro(valores.where(ganhas).mean()),
        "taxa_conversao": percentual(ganhas.sum(), total_decididas),
        "etapa_principal": next(iter(ranking), None),
        "oportunidades_por_etapa": ranking,
    }

