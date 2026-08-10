"""Diagnóstico de qualidade de dados."""

from __future__ import annotations

import pandas as pd

from dados.inconsistencias import analisar_inconsistencias, detectar_outliers
from dados.qualidade_base import COLUNAS_TECNICAS_PADRAO


def _mascara_ausentes(df: pd.DataFrame) -> pd.DataFrame:
    mascara = df.isna().copy()
    for coluna in df.select_dtypes(include=["object", "string"]).columns:
        vazios = df[coluna].astype("string").str.strip().eq("").fillna(False)
        mascara[coluna] = mascara[coluna] | vazios
    return mascara


def analisar_qualidade(
    df: pd.DataFrame,
    colunas_ignoradas: set[str] | None = None,
    relatorio_tratamento: dict | None = None,
) -> dict:
    """Calcula completude, unicidade, colunas vazias e um score explicável.

    As colunas técnicas adicionadas pela consolidação são excluídas do diagnóstico
    por padrão. Assim, metadados de origem não distorcem a qualidade dos dados de
    negócio e registros iguais em arquivos diferentes continuam sendo detectados.
    """
    if df is None:
        raise ValueError("DataFrame não informado para análise de qualidade.")
    if not isinstance(df, pd.DataFrame):
        raise TypeError("A análise de qualidade exige um pandas.DataFrame.")

    ignoradas = set(colunas_ignoradas or COLUNAS_TECNICAS_PADRAO)
    colunas_avaliadas = [
        coluna for coluna in df.columns if str(coluna) not in ignoradas
    ]
    df_avaliado = df[colunas_avaliadas] if colunas_avaliadas else df

    total_registros = int(len(df_avaliado))
    total_colunas = int(len(df_avaliado.columns))
    total_celulas = total_registros * total_colunas

    mascara_ausentes = _mascara_ausentes(df_avaliado)
    valores_ausentes = int(mascara_ausentes.sum().sum())
    linhas_com_ausentes = int(mascara_ausentes.any(axis=1).sum())
    ausentes_por_coluna = {
        str(coluna): int(quantidade)
        for coluna, quantidade in mascara_ausentes.sum().items()
        if int(quantidade) > 0
    }
    colunas_vazias = [
        str(coluna)
        for coluna in df_avaliado.columns
        if bool(mascara_ausentes[coluna].all())
    ]

    linhas_duplicadas = int(df_avaliado.duplicated().sum())
    percentual_ausentes = (
        (valores_ausentes / total_celulas) * 100 if total_celulas else 0.0
    )
    percentual_duplicados = (
        (linhas_duplicadas / total_registros) * 100 if total_registros else 0.0
    )
    completude = 100.0 - percentual_ausentes
    unicidade = 100.0 - percentual_duplicados
    percentual_colunas_validas = (
        ((total_colunas - len(colunas_vazias)) / total_colunas) * 100
        if total_colunas
        else 100.0
    )

    inconsistencias = analisar_inconsistencias(df_avaliado)
    outliers = detectar_outliers(df_avaliado)
    total_invalidos = int(
        (relatorio_tratamento or {}).get("total_valores_invalidos", 0)
    )
    validade = 100.0 - min(
        100.0,
        (total_invalidos / total_celulas) * 100 if total_celulas else 0.0,
    )
    consistencia = 100.0 - min(
        100.0,
        (inconsistencias["total_inconsistencias"] / total_registros) * 100
        if total_registros
        else 0.0,
    )

    score_qualidade = round(
        max(
            0.0,
            min(
                100.0,
                completude * 0.55
                + unicidade * 0.20
                + percentual_colunas_validas * 0.10
                + validade * 0.10
                + consistencia * 0.05,
            ),
        ),
        2,
    )

    if score_qualidade >= 95:
        nivel = "Excelente"
    elif score_qualidade >= 85:
        nivel = "Boa"
    elif score_qualidade >= 70:
        nivel = "Atenção"
    else:
        nivel = "Crítica"

    return {
        "total_registros": total_registros,
        "total_colunas": total_colunas,
        "total_colunas_dataframe": int(len(df.columns)),
        "colunas_avaliadas": [str(c) for c in df_avaliado.columns],
        "total_celulas": total_celulas,
        "valores_ausentes": valores_ausentes,
        "linhas_com_ausentes": linhas_com_ausentes,
        "percentual_ausentes": round(percentual_ausentes, 2),
        "linhas_duplicadas": linhas_duplicadas,
        "percentual_duplicados": round(percentual_duplicados, 2),
        "colunas_vazias": colunas_vazias,
        "quantidade_colunas_vazias": len(colunas_vazias),
        "ausentes_por_coluna": ausentes_por_coluna,
        "completude": round(completude, 2),
        "unicidade": round(unicidade, 2),
        "validade": round(validade, 2),
        "consistencia": round(consistencia, 2),
        "valores_invalidos": total_invalidos,
        "inconsistencias": inconsistencias,
        "outliers": outliers,
        "score_qualidade": score_qualidade,
        "nivel_qualidade": nivel,
    }
