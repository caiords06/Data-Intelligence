"""Motores de indicadores específicos por categoria."""

from __future__ import annotations

import math

import pandas as pd

from dados.classificador import criar_mapa_campos


def _float_seguro(valor, padrao: float = 0.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if math.isfinite(numero) else padrao


def _serie_numerica(df: pd.DataFrame, coluna: object | None) -> pd.Series:
    if coluna is None or coluna not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[coluna], errors="coerce")


def _ranking(
    df: pd.DataFrame,
    coluna_dimensao: object | None,
    coluna_valor: object | None,
) -> pd.Series:
    if (
        coluna_dimensao is None
        or coluna_valor is None
        or coluna_dimensao not in df.columns
        or coluna_valor not in df.columns
    ):
        return pd.Series(dtype="float64")

    dados = pd.DataFrame(
        {
            "dimensao": df[coluna_dimensao],
            "valor": pd.to_numeric(df[coluna_valor], errors="coerce"),
        }
    ).dropna(subset=["dimensao", "valor"])

    if dados.empty:
        return pd.Series(dtype="float64")

    return dados.groupby("dimensao", dropna=True)["valor"].sum().sort_values(ascending=False)


def calcular_indicadores_vendas(df: pd.DataFrame, campos: dict) -> dict:
    """Calcula KPIs de vendas apenas quando as colunas necessárias existem."""
    if df is None:
        raise ValueError("DataFrame não informado para indicadores de vendas.")

    resultado: dict = {}
    mapa = criar_mapa_campos(campos)

    coluna_valor = mapa.get("valor")
    coluna_quantidade = mapa.get("quantidade")
    coluna_produto = mapa.get("produto")
    coluna_loja = mapa.get("loja")
    coluna_data = mapa.get("data")
    coluna_venda = mapa.get("id_venda")

    valores = _serie_numerica(df, coluna_valor)
    valores_validos = valores.dropna()
    if not valores_validos.empty:
        desvio = valores_validos.std()
        resultado.update(
            {
                "faturamento_total": _float_seguro(valores_validos.sum()),
                "valor_medio_venda": _float_seguro(valores_validos.mean()),
                "maior_venda": _float_seguro(valores_validos.max()),
                "menor_venda": _float_seguro(valores_validos.min()),
                "mediana_venda": _float_seguro(valores_validos.median()),
                "desvio_padrao_venda": _float_seguro(desvio),
            }
        )

    quantidades = _serie_numerica(df, coluna_quantidade)
    quantidades_validas = quantidades.dropna()
    if not quantidades_validas.empty:
        resultado.update(
            {
                "quantidade_total": _float_seguro(quantidades_validas.sum()),
                "quantidade_media": _float_seguro(quantidades_validas.mean()),
                "maior_quantidade": _float_seguro(quantidades_validas.max()),
                "menor_quantidade": _float_seguro(quantidades_validas.min()),
            }
        )

    if coluna_venda is not None and coluna_venda in df.columns and not valores_validos.empty:
        vendas_unicas = int(df[coluna_venda].nunique(dropna=True))
        if vendas_unicas > 0:
            faturamento = _float_seguro(valores_validos.sum())
            resultado["total_vendas"] = vendas_unicas
            resultado["ticket_medio"] = faturamento / vendas_unicas

    if not valores_validos.empty and not quantidades_validas.empty:
        quantidade_total = _float_seguro(quantidades_validas.sum())
        if quantidade_total:
            resultado["preco_medio_unidade"] = (
                _float_seguro(valores_validos.sum()) / quantidade_total
            )

    ranking_produtos = _ranking(df, coluna_produto, coluna_valor)
    if not ranking_produtos.empty:
        resultado["produto_maior_faturamento"] = str(ranking_produtos.index[0])
        resultado["valor_produto_lider"] = _float_seguro(ranking_produtos.iloc[0])
        resultado["ranking_produtos"] = {
            str(chave): _float_seguro(valor)
            for chave, valor in ranking_produtos.head(10).items()
        }

    ranking_lojas = _ranking(df, coluna_loja, coluna_valor)
    if not ranking_lojas.empty:
        resultado["loja_maior_faturamento"] = str(ranking_lojas.index[0])
        resultado["valor_loja_lider"] = _float_seguro(ranking_lojas.iloc[0])
        resultado["ranking_lojas"] = {
            str(chave): _float_seguro(valor)
            for chave, valor in ranking_lojas.head(10).items()
        }

    if (
        coluna_data is not None
        and coluna_data in df.columns
        and coluna_valor is not None
        and coluna_valor in df.columns
    ):
        dados_temporais = pd.DataFrame(
            {
                "data": pd.to_datetime(df[coluna_data], errors="coerce", dayfirst=True),
                "valor": pd.to_numeric(df[coluna_valor], errors="coerce"),
            }
        ).dropna()
        if not dados_temporais.empty:
            mensal = (
                dados_temporais.groupby(dados_temporais["data"].dt.to_period("M"))["valor"]
                .sum()
                .sort_index()
            )
            resultado["faturamento_mensal"] = {
                str(periodo): _float_seguro(valor)
                for periodo, valor in mensal.items()
            }

    return resultado


def calcular_indicadores(categoria: str, df: pd.DataFrame, campos: dict) -> dict:
    """Despacha o cálculo para o motor disponível da categoria."""
    motores = {"vendas": calcular_indicadores_vendas}
    motor = motores.get(categoria)
    return motor(df, campos) if motor else {}
