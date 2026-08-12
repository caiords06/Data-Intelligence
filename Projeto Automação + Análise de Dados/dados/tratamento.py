"""Tratamento seguro e auditável de bases tabulares.

O módulo nunca altera o DataFrame recebido. As correções são aplicadas em uma
cópia e todas as mudanças relevantes são descritas no relatório retornado.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

from dados.classificador import identificar_campo

CAMPOS_NUMERICOS = {
    "quantidade",
    "valor_unitario",
    "valor",
    "custo",
    "meta",
    "estoque",
    "salario",
    "receita",
    "despesa",
    "saldo_financeiro",
    "estoque_minimo",
}
CAMPOS_TEMPORAIS = {"data", "admissao", "desligamento"}
MARCADORES_AUSENTES = {"", "-", "n/a", "na", "null", "none", "nan"}


def normalizar_nome_coluna(nome: object) -> str:
    """Converte o nome para ``snake_case`` sem acentos ou símbolos."""
    texto = unicodedata.normalize("NFKD", str(nome).strip())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower()
    return texto or "coluna_sem_nome"


def normalizar_colunas(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Normaliza rótulos e resolve colisões sem descartar nenhuma coluna."""
    resultado = df.copy()
    usados: set[str] = set()
    novos_nomes: list[str] = []
    alteracoes: list[dict] = []
    colisoes: list[dict] = []

    for coluna in resultado.columns:
        base = normalizar_nome_coluna(coluna)
        novo_nome = base
        sufixo = 2
        while novo_nome in usados:
            novo_nome = f"{base}_{sufixo}"
            sufixo += 1

        usados.add(novo_nome)
        novos_nomes.append(novo_nome)
        if str(coluna) != novo_nome:
            alteracoes.append({"original": str(coluna), "normalizada": novo_nome})
        if novo_nome != base:
            colisoes.append(
                {
                    "original": str(coluna),
                    "nome_base": base,
                    "nome_aplicado": novo_nome,
                }
            )

    resultado.columns = novos_nomes
    return resultado, {
        "colunas_renomeadas": alteracoes,
        "quantidade_colunas_renomeadas": len(alteracoes),
        "colisoes_colunas": colisoes,
        "quantidade_colisoes_colunas": len(colisoes),
    }


def _numero_br(valor: object) -> float | None:
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)

    texto = str(valor).strip()
    if texto.casefold() in MARCADORES_AUSENTES:
        return None

    negativo_parenteses = texto.startswith("(") and texto.endswith(")")
    texto = re.sub(r"[^0-9,\.\-+]", "", texto)
    if not texto or texto in {"-", "+", ".", ","}:
        return None

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")

    try:
        numero = float(texto)
    except ValueError:
        return None
    return -abs(numero) if negativo_parenteses else numero


def converter_serie_numerica(serie: pd.Series) -> tuple[pd.Series, dict]:
    """Converte números comuns no Brasil e contabiliza valores inválidos."""
    ausentes_originais = serie.isna() | serie.astype("string").str.strip().str.casefold().isin(
        MARCADORES_AUSENTES
    )
    convertida = serie.map(_numero_br).astype("Float64")
    invalidos = (~ausentes_originais) & convertida.isna()
    return convertida, {
        "valores_validos": int(convertida.notna().sum()),
        "valores_invalidos": int(invalidos.sum()),
        "percentual_sucesso": round(
            float(convertida.notna().sum() / max(1, (~ausentes_originais).sum()) * 100),
            2,
        ),
    }


def converter_serie_data(serie: pd.Series) -> tuple[pd.Series, dict]:
    """Converte datas com preferência para o padrão brasileiro dia/mês/ano."""
    textos = serie.astype("string").str.strip()
    ausentes_originais = serie.isna() | textos.str.casefold().isin(MARCADORES_AUSENTES)
    convertida = pd.to_datetime(serie, errors="coerce", dayfirst=True, format="mixed")
    invalidos = (~ausentes_originais) & convertida.isna()
    return convertida, {
        "valores_validos": int(convertida.notna().sum()),
        "valores_invalidos": int(invalidos.sum()),
        "percentual_sucesso": round(
            float(convertida.notna().sum() / max(1, (~ausentes_originais).sum()) * 100),
            2,
        ),
    }


def _limpar_textos(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    resultado = df.copy()
    ajustes = 0
    for coluna in resultado.select_dtypes(include=["object", "string"]).columns:
        original = resultado[coluna].astype("string")
        limpa = original.str.strip().str.replace(r"\s+", " ", regex=True)
        ausentes = limpa.str.casefold().isin(MARCADORES_AUSENTES)
        limpa = limpa.mask(ausentes, pd.NA)
        ajustes += int((original.fillna("<NA>") != limpa.fillna("<NA>")).sum())
        resultado[coluna] = limpa
    return resultado, ajustes


def tratar_dataframe(
    df: pd.DataFrame,
    *,
    normalizar_nomes: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Aplica limpeza conservadora e devolve dados tratados mais auditoria."""
    if df is None:
        raise ValueError("DataFrame não informado para tratamento.")
    if not isinstance(df, pd.DataFrame):
        raise TypeError("O tratamento exige um pandas.DataFrame.")

    if normalizar_nomes:
        resultado, relatorio_colunas = normalizar_colunas(df)
    else:
        resultado = df.copy()
        relatorio_colunas = {
            "colunas_renomeadas": [],
            "quantidade_colunas_renomeadas": 0,
            "colisoes_colunas": [],
            "quantidade_colisoes_colunas": 0,
        }

    resultado, textos_ajustados = _limpar_textos(resultado)
    conversoes: dict[str, dict] = {}
    total_invalidos = 0

    for coluna in list(resultado.columns):
        campo = identificar_campo(coluna)
        if campo in CAMPOS_NUMERICOS:
            convertida, diagnostico = converter_serie_numerica(resultado[coluna])
            resultado[coluna] = convertida
            diagnostico["tipo_destino"] = "numero"
        elif campo in CAMPOS_TEMPORAIS:
            convertida, diagnostico = converter_serie_data(resultado[coluna])
            resultado[coluna] = convertida
            diagnostico["tipo_destino"] = "data"
        else:
            continue

        conversoes[str(coluna)] = diagnostico
        total_invalidos += diagnostico["valores_invalidos"]

    total_ajustes = (
        relatorio_colunas["quantidade_colunas_renomeadas"]
        + textos_ajustados
        + len(conversoes)
    )
    relatorio = {
        **relatorio_colunas,
        "textos_ajustados": textos_ajustados,
        "conversoes": conversoes,
        "quantidade_colunas_convertidas": len(conversoes),
        "total_valores_invalidos": total_invalidos,
        "total_ajustes": int(total_ajustes),
        "linhas_antes": int(len(df)),
        "linhas_depois": int(len(resultado)),
        "linhas_removidas": 0,
    }
    return resultado, relatorio
