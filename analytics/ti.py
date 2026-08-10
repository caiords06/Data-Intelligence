"""Indicadores operacionais de Tecnologia e Help Desk."""

import pandas as pd

from analytics.base import percentual, ranking_contagem, status_normalizado, texto


def calcular_indicadores_ti(df: pd.DataFrame, _campos: dict) -> dict:
    status = status_normalizado(df)
    prioridade = texto(df, "prioridade").str.lower()
    categorias = texto(df, "categoria")
    titulos = texto(df, "titulo", "chamado")
    concluidos = status.str.contains("concluido|resolvido|fechado", regex=True, na=False)
    abertos = ~concluidos
    criticos = prioridade.str.contains("critica|crítica", regex=True, na=False) & abertos
    ranking = ranking_contagem(categorias)
    repetidos = titulos.dropna().duplicated(keep=False)
    return {
        "total_chamados": int(len(df)),
        "chamados_abertos": int(abertos.sum()),
        "chamados_concluidos": int(concluidos.sum()),
        "chamados_criticos": int(criticos.sum()),
        "taxa_resolucao": percentual(concluidos.sum(), len(df)),
        "chamados_reincidentes": int(repetidos.sum()),
        "categoria_mais_frequente": next(iter(ranking), None),
        "chamados_por_categoria": ranking,
    }

