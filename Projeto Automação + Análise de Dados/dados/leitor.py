"""Leitura, validação e consolidação de planilhas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.api import types as tipos_pd

from dados.periodos import identificar_periodo

EXTENSOES_PERMITIDAS = {".xlsx", ".xls", ".csv", ".json", ".parquet", ".txt"}
LIMITE_ARQUIVO_LOCAL_BYTES = 100 * 1024 * 1024
COLUNAS_ORIGEM = (
    "arquivo_origem",
    "periodo_origem",
    "ano_origem",
    "mes_origem",
    "trimestre_origem",
    "semestre_origem",
)


def validar_arquivo(caminho: str | Path) -> Path:
    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    if not caminho.is_file():
        raise ValueError("O caminho informado não corresponde a um arquivo.")
    if caminho.suffix.lower() not in EXTENSOES_PERMITIDAS:
        raise ValueError(
            "Formato não suportado. Utilize XLSX, XLS, CSV, JSON, Parquet ou TXT."
        )
    tamanho = caminho.stat().st_size
    if tamanho > LIMITE_ARQUIVO_LOCAL_BYTES:
        raise ValueError(
            f"O arquivo local possui {tamanho / (1024*1024):.1f} MB e excede o limite de 100 MB. "
            "Divida a base ou use uma fonte administrada/importação em partes."
        )

    return caminho


def _carregar_csv(caminho: Path) -> pd.DataFrame:
    ultimo_erro: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            # sep=None permite detectar vírgula, ponto-e-vírgula e tabulação.
            return pd.read_csv(
                caminho,
                sep=None,
                engine="python",
                encoding=encoding,
            )
        except UnicodeDecodeError as erro:
            ultimo_erro = erro

    if ultimo_erro:
        raise ultimo_erro
    raise ValueError(f"Não foi possível ler o CSV: {caminho}")


def carregar_planilha(caminho: str | Path) -> pd.DataFrame:
    caminho = validar_arquivo(caminho)
    extensao = caminho.suffix.lower()

    if extensao in {".csv", ".txt"}:
        return _carregar_csv(caminho)
    if extensao in {".xlsx", ".xls"}:
        return pd.read_excel(caminho)
    if extensao == ".json":
        try:
            return pd.read_json(caminho)
        except ValueError:
            return pd.read_json(caminho, lines=True)
    if extensao == ".parquet":
        try:
            return pd.read_parquet(caminho)
        except ImportError as erro:
            raise RuntimeError(
                "A leitura de Parquet requer a dependência pyarrow. "
                "Execute: pip install -r requirements.txt"
            ) from erro

    raise ValueError(f"Extensão não suportada: {extensao}")


def carregar_multiplas_planilhas(caminhos) -> list[dict]:
    caminhos = list(caminhos or [])
    if not caminhos:
        raise ValueError("Nenhum arquivo foi selecionado.")

    resultados = []
    for caminho in caminhos:
        caminho_path = validar_arquivo(caminho)
        df = carregar_planilha(caminho_path)
        resultados.append(
            {
                "caminho": str(caminho_path),
                "nome_arquivo": caminho_path.name,
                "dataframe": df,
                "periodo": identificar_periodo(df, caminho_path.name),
            }
        )

    return resultados


def verificar_compatibilidade(resultados: list[dict]) -> dict:
    if not resultados:
        raise ValueError("Nenhum arquivo foi carregado.")

    colunas_referencia = list(resultados[0]["dataframe"].columns)
    conjunto_referencia = set(colunas_referencia)
    incompatibilidades = []

    def familia(serie):
        if serie.dropna().empty:
            return "vazio"
        if tipos_pd.is_bool_dtype(serie.dtype):
            return "booleano"
        if tipos_pd.is_numeric_dtype(serie.dtype):
            return "numerico"
        if tipos_pd.is_datetime64_any_dtype(serie.dtype):
            return "data"
        return "texto"

    tipos_referencia = {
        coluna: familia(resultados[0]["dataframe"][coluna])
        for coluna in colunas_referencia
    }

    for item in resultados[1:]:
        colunas_atual = list(item["dataframe"].columns)
        conjunto_atual = set(colunas_atual)

        conflitos_tipos = {}
        if conjunto_atual == conjunto_referencia:
            for coluna in colunas_referencia:
                tipo_atual = familia(item["dataframe"][coluna])
                tipo_referencia = tipos_referencia[coluna]
                if (
                    tipo_atual != tipo_referencia
                    and "vazio" not in {tipo_atual, tipo_referencia}
                ):
                    conflitos_tipos[coluna] = {
                        "esperado": tipo_referencia,
                        "encontrado": tipo_atual,
                    }

        if conjunto_atual != conjunto_referencia or conflitos_tipos:
            incompatibilidades.append(
                {
                    "arquivo": item["nome_arquivo"],
                    "colunas": colunas_atual,
                    "faltando": sorted(conjunto_referencia - conjunto_atual),
                    "extras": sorted(conjunto_atual - conjunto_referencia),
                    "tipos": conflitos_tipos,
                }
            )

    return {
        "compativel": not incompatibilidades,
        "colunas_referencia": colunas_referencia,
        "tipos_referencia": tipos_referencia,
        "incompatibilidades": incompatibilidades,
    }


def _adicionar_colunas_periodo(df: pd.DataFrame, item: dict) -> pd.DataFrame:
    df = df.copy()
    periodo = item.get("periodo") or {}
    df["arquivo_origem"] = item["nome_arquivo"]

    if periodo.get("origem_identificacao") == "coluna_data":
        coluna_data = periodo.get("coluna_data")
        if coluna_data in df.columns:
            datas = pd.to_datetime(df[coluna_data], errors="coerce", dayfirst=True)
            df["periodo_origem"] = datas.dt.strftime("%m/%Y")
            df["ano_origem"] = datas.dt.year.astype("Int64")
            df["mes_origem"] = datas.dt.month.astype("Int64")
            df["trimestre_origem"] = datas.dt.quarter.map(
                lambda valor: f"T{valor}" if pd.notna(valor) else None
            )
            df["semestre_origem"] = datas.dt.month.map(
                lambda mes: f"S{1 if mes <= 6 else 2}" if pd.notna(mes) else None
            )
            return df

    df["periodo_origem"] = periodo.get("periodo")
    df["ano_origem"] = periodo.get("ano")
    df["mes_origem"] = periodo.get("mes")
    df["trimestre_origem"] = periodo.get("trimestre")
    df["semestre_origem"] = periodo.get("semestre")
    return df


def consolidar_planilhas(resultados: list[dict]) -> pd.DataFrame:
    if not resultados:
        raise ValueError("Nenhum arquivo disponível para consolidação.")

    compatibilidade = verificar_compatibilidade(resultados)
    if not compatibilidade["compativel"]:
        raise ValueError("Não é possível consolidar arquivos incompatíveis.")

    ordem_colunas = compatibilidade["colunas_referencia"]
    tabelas = []

    for item in resultados:
        df = item["dataframe"].copy()
        # Arquivos com as mesmas colunas em ordem diferente são alinhados.
        df = df.reindex(columns=ordem_colunas)
        tabelas.append(_adicionar_colunas_periodo(df, item))

    return pd.concat(tabelas, ignore_index=True)
