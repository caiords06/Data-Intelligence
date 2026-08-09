import pandas as pd
import numpy as np


def analisar_planilha(df):

    resultado = {}

    # =========================================================
    # INFORMAÇÕES BÁSICAS
    # =========================================================

    resultado["total_registros"] = len(df)

    resultado["total_colunas"] = len(df.columns)

    resultado["colunas"] = list(df.columns)

    # =========================================================
    # TIPOS DAS COLUNAS
    # =========================================================

    tipos = {}

    for coluna in df.columns:

        tipos[coluna] = str(
            df[coluna].dtype
        )

    resultado["tipos"] = tipos

    # =========================================================
    # VALORES AUSENTES
    # =========================================================

    valores_ausentes = {}

    for coluna in df.columns:

        quantidade = int(
            df[coluna].isna().sum()
        )

        valores_ausentes[coluna] = quantidade

    resultado["valores_ausentes"] = valores_ausentes

    resultado["total_valores_ausentes"] = sum(
        valores_ausentes.values()
    )

    # =========================================================
    # DUPLICIDADES
    # =========================================================

    resultado["linhas_duplicadas"] = int(
        df.duplicated().sum()
    )

    # =========================================================
    # COLUNAS NUMÉRICAS
    # =========================================================

    colunas_numericas = list(
        df.select_dtypes(
            include=np.number
        ).columns
    )

    resultado["colunas_numericas"] = (
        colunas_numericas
    )

    # =========================================================
    # COLUNAS DE TEXTO
    # =========================================================

    colunas_texto = list(
        df.select_dtypes(
            include=["object", "string"]
        ).columns
    )

    resultado["colunas_texto"] = colunas_texto

    # =========================================================
    # COLUNAS DE DATA
    # =========================================================

    colunas_data = []

    for coluna in df.columns:

        nome = str(coluna).lower()

        if any(
            palavra in nome
            for palavra in [
                "data",
                "date",
                "dia",
                "mês",
                "mes"
            ]
        ):

            colunas_data.append(
                coluna
            )

    resultado["colunas_data"] = colunas_data

    # =========================================================
    # ESTATÍSTICAS NUMÉRICAS
    # =========================================================

    estatisticas = {}

    for coluna in colunas_numericas:

        serie = pd.to_numeric(
            df[coluna],
            errors="coerce"
        )

        estatisticas[coluna] = {

            "soma": float(
                serie.sum()
            ),

            "media": float(
                serie.mean()
            ) if serie.notna().any() else 0,

            "mediana": float(
                serie.median()
            ) if serie.notna().any() else 0,

            "minimo": float(
                serie.min()
            ) if serie.notna().any() else 0,

            "maximo": float(
                serie.max()
            ) if serie.notna().any() else 0,

        }

    resultado["estatisticas"] = estatisticas

    return resultado