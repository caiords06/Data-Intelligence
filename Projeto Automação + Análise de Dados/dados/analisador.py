"""Análise descritiva genérica de DataFrames."""

from __future__ import annotations

import pandas as pd


def analisar_planilha(df: pd.DataFrame) -> dict:
    """Retorna informações estruturais e estatísticas básicas da planilha.

    A função não altera o DataFrame recebido e serve como base para módulos
    universais, independentemente da categoria de negócio da planilha.
    """
    if df is None:
        raise ValueError("DataFrame não informado para análise.")
    if not isinstance(df, pd.DataFrame):
        raise TypeError("A análise exige um pandas.DataFrame.")

    colunas = list(df.columns)
    tipos = {coluna: str(df[coluna].dtype) for coluna in colunas}
    valores_ausentes = {
        coluna: int(df[coluna].isna().sum())
        for coluna in colunas
    }

    colunas_numericas = list(df.select_dtypes(include="number").columns)
    colunas_texto = list(df.select_dtypes(include=["object", "string"]).columns)

    colunas_data = [
        coluna
        for coluna in colunas
        if pd.api.types.is_datetime64_any_dtype(df[coluna])
        or any(
            termo in str(coluna).lower()
            for termo in ("data", "date", "dia", "mês", "mes")
        )
    ]

    estatisticas: dict = {}
    for coluna in colunas_numericas:
        serie = pd.to_numeric(df[coluna], errors="coerce")
        valores_validos = serie.dropna()

        if valores_validos.empty:
            estatisticas[coluna] = {
                "soma": 0.0,
                "media": 0.0,
                "mediana": 0.0,
                "minimo": 0.0,
                "maximo": 0.0,
                "desvio_padrao": 0.0,
            }
            continue

        desvio = valores_validos.std()
        estatisticas[coluna] = {
            "soma": float(valores_validos.sum()),
            "media": float(valores_validos.mean()),
            "mediana": float(valores_validos.median()),
            "minimo": float(valores_validos.min()),
            "maximo": float(valores_validos.max()),
            "desvio_padrao": float(desvio) if pd.notna(desvio) else 0.0,
        }

    return {
        "total_registros": int(len(df)),
        "total_colunas": int(len(colunas)),
        "colunas": colunas,
        "tipos": tipos,
        "valores_ausentes": valores_ausentes,
        "total_valores_ausentes": int(sum(valores_ausentes.values())),
        "linhas_duplicadas": int(df.duplicated().sum()),
        "colunas_numericas": colunas_numericas,
        "colunas_texto": colunas_texto,
        "colunas_data": colunas_data,
        "estatisticas": estatisticas,
    }
