"""Detecção explicável de inconsistências e valores atípicos."""

from __future__ import annotations

import pandas as pd

from dados.classificador import identificar_campo, normalizar_texto
from dados.qualidade_base import COLUNAS_TECNICAS_PADRAO

CAMPOS_NAO_NEGATIVOS = {
    "quantidade",
    "valor_unitario",
    "valor",
    "estoque",
    "salario",
}
CAMPOS_ID = {"id_venda"}


def detectar_outliers(
    df: pd.DataFrame,
    *,
    fator_iqr: float = 1.5,
    minimo_valores: int = 8,
) -> dict:
    """Sinaliza outliers pelo IQR sem removê-los da base."""
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("A detecção de outliers exige um pandas.DataFrame.")

    por_coluna: dict[str, dict] = {}
    total = 0
    numericas = df.select_dtypes(include="number").columns
    for coluna in numericas:
        if str(coluna) in COLUNAS_TECNICAS_PADRAO:
            continue
        if identificar_campo(coluna) in CAMPOS_ID:
            continue

        serie = pd.to_numeric(df[coluna], errors="coerce").dropna()
        if len(serie) < minimo_valores:
            continue
        q1 = float(serie.quantile(0.25))
        q3 = float(serie.quantile(0.75))
        iqr = q3 - q1
        if iqr <= 0:
            continue

        limite_inferior = q1 - fator_iqr * iqr
        limite_superior = q3 + fator_iqr * iqr
        mascara = (serie < limite_inferior) | (serie > limite_superior)
        quantidade = int(mascara.sum())
        if not quantidade:
            continue

        total += quantidade
        por_coluna[str(coluna)] = {
            "quantidade": quantidade,
            "percentual": round(quantidade / len(serie) * 100, 2),
            "limite_inferior": round(limite_inferior, 4),
            "limite_superior": round(limite_superior, 4),
            "menor_outlier": float(serie[mascara].min()),
            "maior_outlier": float(serie[mascara].max()),
        }

    return {
        "metodo": "IQR",
        "fator_iqr": fator_iqr,
        "total_outliers": total,
        "quantidade_colunas_com_outliers": len(por_coluna),
        "por_coluna": por_coluna,
    }


def _variacoes_textuais(df: pd.DataFrame) -> dict[str, list[dict]]:
    resultado: dict[str, list[dict]] = {}
    for coluna in df.select_dtypes(include=["object", "string"]).columns:
        if str(coluna) in COLUNAS_TECNICAS_PADRAO:
            continue
        serie = df[coluna].dropna().astype("string").str.strip()
        cardinalidade = int(serie.nunique())
        if cardinalidade < 2 or cardinalidade > 100:
            continue

        grupos: dict[str, set[str]] = {}
        for valor in serie.unique():
            grupos.setdefault(normalizar_texto(valor), set()).add(str(valor))
        divergentes = [
            {"forma_normalizada": chave, "variacoes": sorted(valores)}
            for chave, valores in grupos.items()
            if chave and len(valores) > 1
        ]
        if divergentes:
            resultado[str(coluna)] = divergentes[:20]
    return resultado


def analisar_inconsistencias(df: pd.DataFrame) -> dict:
    """Procura negativos improváveis, datas futuras e variações textuais."""
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("A análise de inconsistências exige um pandas.DataFrame.")

    negativos: dict[str, int] = {}
    datas_futuras: dict[str, int] = {}
    hoje = pd.Timestamp.now().normalize()

    for coluna in df.columns:
        campo = identificar_campo(coluna)
        if campo in CAMPOS_NAO_NEGATIVOS:
            serie = pd.to_numeric(df[coluna], errors="coerce")
            quantidade = int((serie < 0).sum())
            if quantidade:
                negativos[str(coluna)] = quantidade
        if campo in {"data", "admissao", "desligamento"}:
            serie_data = pd.to_datetime(df[coluna], errors="coerce", dayfirst=True)
            quantidade = int((serie_data > hoje).sum())
            if quantidade:
                datas_futuras[str(coluna)] = quantidade

    mapa_temporal = {
        identificar_campo(coluna): coluna
        for coluna in df.columns
        if identificar_campo(coluna) in {"admissao", "desligamento"}
    }
    ordens_invalidas = 0
    if {"admissao", "desligamento"}.issubset(mapa_temporal):
        admissao = pd.to_datetime(df[mapa_temporal["admissao"]], errors="coerce", dayfirst=True)
        desligamento = pd.to_datetime(
            df[mapa_temporal["desligamento"]], errors="coerce", dayfirst=True
        )
        ordens_invalidas = int((desligamento < admissao).sum())

    variacoes = _variacoes_textuais(df)
    total_variacoes = sum(len(grupos) for grupos in variacoes.values())
    total = (
        sum(negativos.values())
        + sum(datas_futuras.values())
        + ordens_invalidas
        + total_variacoes
    )
    return {
        "valores_negativos": negativos,
        "total_valores_negativos": sum(negativos.values()),
        "datas_futuras": datas_futuras,
        "total_datas_futuras": sum(datas_futuras.values()),
        "ordens_temporais_invalidas": ordens_invalidas,
        "variacoes_textuais": variacoes,
        "total_grupos_textuais_inconsistentes": total_variacoes,
        "total_inconsistencias": total,
    }
