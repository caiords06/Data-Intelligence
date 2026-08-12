"""Análise temporal independente da interface."""

from __future__ import annotations

import pandas as pd

from dados.classificador import criar_mapa_campos

GRANULARIDADES = {"automatico", "mensal", "trimestral", "semestral", "anual", "personalizado"}


def _identificar_coluna_data(df: pd.DataFrame, campos: dict) -> object | None:
    mapa = criar_mapa_campos(campos)
    coluna = mapa.get("data") or mapa.get("admissao")
    if coluna in df.columns:
        return coluna

    candidatas = [
        coluna
        for coluna in df.columns
        if any(termo in str(coluna).lower() for termo in ("data", "date"))
    ]
    return candidatas[0] if candidatas else None


def _identificar_coluna_valor(
    df: pd.DataFrame,
    campos: dict,
) -> tuple[object | None, str | None]:
    mapa = criar_mapa_campos(campos)
    for campo in (
        "valor",
        "receita",
        "despesa",
        "saldo_financeiro",
        "salario",
        "custo",
        "quantidade",
    ):
        coluna = mapa.get(campo)
        if coluna in df.columns:
            return coluna, campo

    candidatas = [
        coluna
        for coluna in df.columns
        if any(
            termo in str(coluna).lower()
            for termo in ("valor", "faturamento", "receita", "venda", "total")
        )
    ]
    return (candidatas[-1], "valor") if candidatas else (None, None)


def _agrupar(dados: pd.DataFrame, granularidade: str) -> pd.Series:
    if granularidade in {"automatico", "mensal", "personalizado"}:
        chave = dados["_data"].dt.to_period("M")
    elif granularidade == "trimestral":
        chave = dados["_data"].dt.to_period("Q")
    elif granularidade == "anual":
        chave = dados["_data"].dt.year.astype(str)
    elif granularidade == "semestral":
        chave = (
            dados["_data"].dt.year.astype(str)
            + "-S"
            + ((dados["_data"].dt.month.sub(1).floordiv(6)) + 1).astype(str)
        )
    else:
        chave = dados["_data"].dt.to_period("M")

    return dados.groupby(chave)["_valor"].sum().sort_index()


def analisar_periodos(
    df: pd.DataFrame,
    campos: dict,
    granularidade: str = "automatico",
) -> dict:
    """Agrupa uma métrica numérica ao longo do tempo e compara períodos.

    ``personalizado`` ainda não recebe datas inicial/final pela interface; por
    isso, nesta versão, usa granularidade mensal e sinaliza um aviso no retorno.
    """
    resultado = {
        "periodos": [],
        "comparacoes": [],
        "granularidade_solicitada": granularidade,
        "granularidade_aplicada": granularidade,
        "aviso": None,
        "metrica": None,
        "formato": "numero",
    }

    if df is None or df.empty:
        return resultado

    granularidade = str(granularidade or "automatico").lower()
    if granularidade not in GRANULARIDADES:
        granularidade = "automatico"

    if granularidade == "personalizado":
        resultado["granularidade_aplicada"] = "mensal"
        resultado["aviso"] = (
            "Período personalizado ainda não possui intervalo de datas na interface; "
            "foi aplicada análise mensal."
        )
    elif granularidade == "automatico":
        resultado["granularidade_aplicada"] = "mensal"
    else:
        resultado["granularidade_aplicada"] = granularidade

    coluna_data = _identificar_coluna_data(df, campos)
    coluna_valor, campo_metrica = _identificar_coluna_valor(df, campos)
    if coluna_data is None or coluna_valor is None:
        return resultado

    resultado["metrica"] = campo_metrica
    resultado["formato"] = (
        "moeda"
        if campo_metrica in {
            "valor",
            "receita",
            "despesa",
            "saldo_financeiro",
            "salario",
            "custo",
        }
        else "numero"
    )

    dados = pd.DataFrame(
        {
            "_data": pd.to_datetime(df[coluna_data], errors="coerce", dayfirst=True),
            "_valor": pd.to_numeric(df[coluna_valor], errors="coerce"),
        }
    ).dropna(subset=["_data", "_valor"])
    if dados.empty:
        return resultado

    agrupado = _agrupar(dados, resultado["granularidade_aplicada"])

    for periodo, valor in agrupado.items():
        valor_float = float(valor)
        if isinstance(periodo, pd.Period) and periodo.freqstr.startswith("Q"):
            periodo_texto = f"{periodo.year}-T{periodo.quarter}"
        else:
            periodo_texto = str(periodo)
        resultado["periodos"].append(
            {
                "periodo": periodo_texto,
                "valor": valor_float,
                # Alias mantido por compatibilidade com a interface atual.
                "faturamento": valor_float,
            }
        )

    periodos = resultado["periodos"]
    for indice in range(1, len(periodos)):
        anterior = periodos[indice - 1]
        atual = periodos[indice]
        valor_anterior = anterior["valor"]
        valor_atual = atual["valor"]
        variacao = (
            ((valor_atual - valor_anterior) / valor_anterior) * 100
            if valor_anterior != 0
            else None
        )
        resultado["comparacoes"].append(
            {
                "periodo_anterior": anterior["periodo"],
                "periodo_atual": atual["periodo"],
                "valor_anterior": valor_anterior,
                "valor_atual": valor_atual,
                "variacao_percentual": variacao,
            }
        )

    return resultado
