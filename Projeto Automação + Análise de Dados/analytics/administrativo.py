"""Indicadores de solicitações administrativas."""

import pandas as pd

from analytics.base import numerica, percentual, ranking_contagem, seguro, status_normalizado, texto


def calcular_indicadores_administrativo(df: pd.DataFrame, _campos: dict) -> dict:
    valores = numerica(df, "valor", "valor_estimado")
    status = status_normalizado(df)
    categorias = texto(df, "categoria")
    pendentes = status.str.contains("pendente|analise", regex=True, na=False)
    aprovadas = status.str.contains("aprovado|concluido", regex=True, na=False)
    ranking = ranking_contagem(categorias)
    return {
        "total_solicitacoes": int(len(df)),
        "solicitacoes_pendentes": int(pendentes.sum()),
        "solicitacoes_aprovadas": int(aprovadas.sum()),
        "taxa_aprovacao": percentual(aprovadas.sum(), len(df)),
        "valor_total": seguro(valores.sum()),
        "valor_pendente": seguro(valores.where(pendentes).sum()),
        "categoria_principal": next(iter(ranking), None),
        "solicitacoes_por_categoria": ranking,
    }

