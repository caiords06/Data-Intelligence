"""Utilitários pequenos compartilhados pelos motores departamentais."""

from __future__ import annotations

import math

import pandas as pd

from dados.classificador import normalizar_texto


def coluna(df: pd.DataFrame, *nomes: str):
    candidatos = {normalizar_texto(nome) for nome in nomes}
    for atual in df.columns:
        if normalizar_texto(atual) in candidatos:
            return atual
    return None


def numerica(df: pd.DataFrame, *nomes: str) -> pd.Series:
    encontrada = coluna(df, *nomes)
    if encontrada is None:
        return pd.Series(index=df.index, dtype="float64")
    return pd.to_numeric(df[encontrada], errors="coerce")


def texto(df: pd.DataFrame, *nomes: str) -> pd.Series:
    encontrada = coluna(df, *nomes)
    if encontrada is None:
        return pd.Series(index=df.index, dtype="string")
    return df[encontrada].astype("string").str.strip()


def datas(df: pd.DataFrame, *nomes: str) -> pd.Series:
    encontrada = coluna(df, *nomes)
    if encontrada is None:
        return pd.Series(index=df.index, dtype="datetime64[ns]")
    return pd.to_datetime(df[encontrada], errors="coerce", dayfirst=True)


def seguro(valor, padrao=0.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return float(padrao)
    return numero if math.isfinite(numero) else float(padrao)


def percentual(parte, total) -> float:
    total = seguro(total)
    return round(seguro(parte) / total * 100, 2) if total else 0.0


def ranking_contagem(serie: pd.Series, limite=10) -> dict:
    if serie.empty:
        return {}
    contagem = serie.dropna().astype("string").value_counts().head(limite)
    return {str(chave): int(valor) for chave, valor in contagem.items()}


def ranking_soma(dimensao: pd.Series, valores: pd.Series, limite=10) -> dict:
    if dimensao.empty or valores.empty:
        return {}
    base = pd.DataFrame({"dimensao": dimensao, "valor": valores}).dropna()
    if base.empty:
        return {}
    ranking = (
        base.groupby("dimensao", dropna=True)["valor"]
        .sum()
        .sort_values(ascending=False)
        .head(limite)
    )
    return {str(chave): seguro(valor) for chave, valor in ranking.items()}


def status_normalizado(df: pd.DataFrame) -> pd.Series:
    return texto(df, "status", "situação").map(normalizar_texto)

