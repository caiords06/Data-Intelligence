"""Indicadores operacionais de Compras."""

import pandas as pd

from analytics.base import (
    numerica,
    percentual,
    ranking_contagem,
    ranking_soma,
    seguro,
    status_normalizado,
    texto,
)


def calcular_indicadores_compras(df: pd.DataFrame, _campos: dict) -> dict:
    valores = numerica(df, "valor_estimado", "estimativa", "valor")
    quantidades = numerica(df, "quantidade", "qtd")
    status = status_normalizado(df)
    fornecedores = texto(df, "fornecedor", "fornecedor sugerido")
    pendentes = status.str.contains("pendente|cotacao", regex=True, na=False)
    aprovadas = status.str.contains("aprovado", regex=True, na=False)
    ranking_fornecedores = ranking_contagem(fornecedores)
    ranking_valor = ranking_soma(fornecedores, valores)
    return {
        "total_solicitacoes": int(len(df)),
        "solicitacoes_pendentes": int(pendentes.sum()),
        "solicitacoes_aprovadas": int(aprovadas.sum()),
        "taxa_aprovacao": percentual(aprovadas.sum(), len(df)),
        "valor_solicitado": seguro(valores.sum()),
        "valor_pendente": seguro(valores.where(pendentes).sum()),
        "quantidade_solicitada": seguro(quantidades.sum()),
        "total_fornecedores": int(fornecedores.nunique(dropna=True)),
        "fornecedor_mais_utilizado": next(iter(ranking_fornecedores), None),
        "fornecedor_maior_valor": next(iter(ranking_valor), None),
        "ranking_fornecedores": ranking_fornecedores,
        "valor_por_fornecedor": ranking_valor,
    }

