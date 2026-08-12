"""Identificação de períodos em nomes de arquivos e colunas de data."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

ABREVIACOES_MESES = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}


def normalizar_texto(texto: object) -> str:
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )


def identificar_mes_nome(nome: str) -> int | None:
    nome_normalizado = normalizar_texto(nome)

    for mes, numero in MESES.items():
        if mes in nome_normalizado:
            return numero

    for abreviacao, numero in ABREVIACOES_MESES.items():
        if re.search(rf"\b{re.escape(abreviacao)}\b", nome_normalizado):
            return numero

    return None


def identificar_ano_nome(nome: str) -> int | None:
    resultado = re.search(r"\b(20\d{2})\b", str(nome))
    return int(resultado.group(1)) if resultado else None


def _dados_calendario(mes: int, ano: int | None) -> dict:
    trimestre = f"T{((mes - 1) // 3) + 1}"
    semestre = f"S{((mes - 1) // 6) + 1}"

    if ano is None:
        return {
            "mes": mes,
            "ano": None,
            "data_referencia": None,
            "periodo": f"{mes:02d}/????",
            "trimestre": trimestre,
            "semestre": semestre,
        }

    data_referencia = pd.Timestamp(year=ano, month=mes, day=1)
    return {
        "mes": mes,
        "ano": ano,
        "data_referencia": data_referencia,
        "periodo": data_referencia.strftime("%m/%Y"),
        "trimestre": trimestre,
        "semestre": semestre,
    }


def identificar_periodo_nome(nome_arquivo: str) -> dict | None:
    nome = Path(nome_arquivo).stem
    mes = identificar_mes_nome(nome)
    if mes is None:
        return None

    # Não inventa o ano atual. Se não estiver no nome, o resultado informa
    # explicitamente que o ano é desconhecido.
    return _dados_calendario(mes, identificar_ano_nome(nome))


def encontrar_coluna_data(df: pd.DataFrame) -> object | None:
    candidatos = (
        "data",
        "date",
        "data venda",
        "data_venda",
        "data da venda",
        "data cadastro",
        "data_cadastro",
        "data pedido",
        "data_pedido",
    )
    colunas_normalizadas = {
        normalizar_texto(coluna): coluna for coluna in df.columns
    }

    for candidato in candidatos:
        encontrado = colunas_normalizadas.get(normalizar_texto(candidato))
        if encontrado is not None:
            return encontrado

    # Fallback conservador para nomes que contenham a palavra "data"/"date".
    for coluna in df.columns:
        nome = normalizar_texto(coluna)
        if "data" in nome or "date" in nome:
            return coluna

    return None


def identificar_periodo_dataframe(df: pd.DataFrame) -> dict | None:
    coluna_data = encontrar_coluna_data(df)
    if coluna_data is None:
        return None

    datas = pd.to_datetime(df[coluna_data], errors="coerce", dayfirst=True)
    datas_validas = datas.dropna()
    if datas_validas.empty:
        return None

    data_minima = datas_validas.min()
    data_maxima = datas_validas.max()
    mesmo_mes = (
        data_minima.year == data_maxima.year
        and data_minima.month == data_maxima.month
    )

    periodo = (
        data_minima.strftime("%m/%Y")
        if mesmo_mes
        else f"{data_minima.strftime('%m/%Y')} a {data_maxima.strftime('%m/%Y')}"
    )

    return {
        "coluna_data": coluna_data,
        "data_inicial": data_minima,
        "data_final": data_maxima,
        "ano": int(data_minima.year) if mesmo_mes else None,
        "mes": int(data_minima.month) if mesmo_mes else None,
        "periodo": periodo,
        "trimestre": f"T{((data_minima.month - 1) // 3) + 1}" if mesmo_mes else None,
        "semestre": f"S{((data_minima.month - 1) // 6) + 1}" if mesmo_mes else None,
        "multiplos_periodos": not mesmo_mes,
    }


def identificar_periodo(df: pd.DataFrame, nome_arquivo: str) -> dict:
    periodo_dataframe = identificar_periodo_dataframe(df)
    if periodo_dataframe is not None:
        periodo_dataframe["origem_identificacao"] = "coluna_data"
        return periodo_dataframe

    periodo_nome = identificar_periodo_nome(nome_arquivo)
    if periodo_nome is not None:
        periodo_nome["origem_identificacao"] = "nome_arquivo"
        return periodo_nome

    return {"origem_identificacao": "nao_identificado"}
