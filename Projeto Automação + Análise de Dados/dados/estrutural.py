"""Análise estrutural universal de bases tabulares."""

from __future__ import annotations

import pandas as pd

from dados.analisador import analisar_planilha


def _parece_temporal(serie: pd.Series, nome_coluna: object) -> bool:
    if pd.api.types.is_datetime64_any_dtype(serie):
        return True

    nome = str(nome_coluna).lower()
    if not any(termo in nome for termo in ("data", "date", "dt_", "dt ")):
        return False

    amostra = serie.dropna().head(200)
    if amostra.empty:
        return False

    convertida = pd.to_datetime(amostra, errors="coerce", dayfirst=True)
    return float(convertida.notna().mean()) >= 0.8


def analisar_estrutura(df: pd.DataFrame) -> dict:
    """Descreve forma, tipos, cardinalidade e estatísticas de um DataFrame."""
    if df is None:
        raise ValueError("DataFrame não informado para análise estrutural.")
    if not isinstance(df, pd.DataFrame):
        raise TypeError("A análise estrutural exige um pandas.DataFrame.")

    resultado_base = analisar_planilha(df)
    colunas_numericas = list(df.select_dtypes(include="number").columns)
    colunas_temporais = [
        coluna
        for coluna in df.columns
        if _parece_temporal(df[coluna], coluna)
    ]
    colunas_textuais = [
        coluna
        for coluna in df.columns
        if coluna not in colunas_numericas and coluna not in colunas_temporais
    ]

    cardinalidade = {
        str(coluna): int(df[coluna].nunique(dropna=True))
        for coluna in df.columns
    }

    return {
        "total_registros": int(len(df)),
        "total_colunas": int(len(df.columns)),
        "quantidade_numericas": len(colunas_numericas),
        "quantidade_textuais": len(colunas_textuais),
        "quantidade_temporais": len(colunas_temporais),
        "colunas_numericas": [str(c) for c in colunas_numericas],
        "colunas_textuais": [str(c) for c in colunas_textuais],
        "colunas_temporais": [str(c) for c in colunas_temporais],
        "tipos": resultado_base.get("tipos", {}),
        "estatisticas": resultado_base.get("estatisticas", {}),
        "cardinalidade": cardinalidade,
    }
