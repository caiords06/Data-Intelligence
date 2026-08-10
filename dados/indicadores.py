"""Indicadores universais e motores analíticos por categoria."""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

from analytics import (
    calcular_indicadores_administrativo,
    calcular_indicadores_comercial,
    calcular_indicadores_compras,
    calcular_indicadores_juridico,
    calcular_indicadores_marketing,
    calcular_indicadores_ti,
)
from dados.classificador import criar_mapa_campos, normalizar_texto
from dados.qualidade_base import COLUNAS_TECNICAS_PADRAO

STATUS_ATIVOS = {"ativo", "ativa", "sim", "1", "aberto", "vigente", "empregado"}
STATUS_INATIVOS = {
    "inativo",
    "inativa",
    "nao",
    "0",
    "fechado",
    "encerrado",
    "desligado",
    "demitido",
}


def _float_seguro(valor, padrao: float = 0.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if math.isfinite(numero) else padrao


def _serie_numerica(df: pd.DataFrame, coluna: object | None) -> pd.Series:
    if coluna is None or coluna not in df.columns:
        return pd.Series(index=df.index, dtype="float64")
    return pd.to_numeric(df[coluna], errors="coerce")


def _serie_data(df: pd.DataFrame, coluna: object | None) -> pd.Series:
    if coluna is None or coluna not in df.columns:
        return pd.Series(index=df.index, dtype="datetime64[ns]")
    return pd.to_datetime(df[coluna], errors="coerce", dayfirst=True)


def _serie_texto(df: pd.DataFrame, coluna: object | None) -> pd.Series:
    if coluna is None or coluna not in df.columns:
        return pd.Series(index=df.index, dtype="string")
    return df[coluna].astype("string").str.strip()


def _ranking(
    df: pd.DataFrame,
    coluna_dimensao: object | None,
    valores: pd.Series,
) -> pd.Series:
    if coluna_dimensao is None or coluna_dimensao not in df.columns:
        return pd.Series(dtype="float64")
    dados = pd.DataFrame(
        {"dimensao": df[coluna_dimensao], "valor": valores}
    ).dropna(subset=["dimensao", "valor"])
    if dados.empty:
        return pd.Series(dtype="float64")
    return (
        dados.groupby("dimensao", dropna=True)["valor"]
        .sum()
        .sort_values(ascending=False)
    )


def _ranking_contagem(
    df: pd.DataFrame,
    coluna: object | None,
) -> pd.Series:
    if coluna is None or coluna not in df.columns:
        return pd.Series(dtype="int64")
    return df[coluna].dropna().astype("string").value_counts()


def _dict_ranking(serie: pd.Series, limite: int = 10) -> dict[str, float]:
    return {
        str(chave): _float_seguro(valor)
        for chave, valor in serie.head(limite).items()
    }


def _contar_status(serie: pd.Series) -> tuple[int, int]:
    normalizada = serie.dropna().map(normalizar_texto)
    ativos = int(normalizada.isin(STATUS_ATIVOS).sum())
    inativos = int(normalizada.isin(STATUS_INATIVOS).sum())
    return ativos, inativos


def calcular_indicadores_universais(df: pd.DataFrame) -> dict:
    """Calcula métricas úteis para qualquer base tabular."""
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("Os indicadores universais exigem um pandas.DataFrame.")

    colunas_negocio = [
        coluna
        for coluna in df.columns
        if str(coluna) not in COLUNAS_TECNICAS_PADRAO
    ]
    base = df[colunas_negocio] if colunas_negocio else df
    total_celulas = int(base.shape[0] * base.shape[1])
    ausentes = int(base.isna().sum().sum())
    completude = 100.0 - (ausentes / total_celulas * 100 if total_celulas else 0.0)
    numericas = list(base.select_dtypes(include="number").columns)
    temporais = list(base.select_dtypes(include=["datetime", "datetimetz"]).columns)

    return {
        "total_registros": int(len(base)),
        "total_colunas": int(len(base.columns)),
        "colunas_numericas": len(numericas),
        "colunas_temporais": len(temporais),
        "colunas_textuais": int(len(base.columns) - len(numericas) - len(temporais)),
        "valores_ausentes": ausentes,
        "registros_duplicados": int(base.duplicated().sum()),
        "completude": round(completude, 2),
        "memoria_mb": round(float(base.memory_usage(deep=True).sum()) / 1024**2, 3),
    }


def calcular_indicadores_vendas(df: pd.DataFrame, campos: dict) -> dict:
    """Calcula KPIs de vendas apenas quando as colunas necessárias existem."""
    mapa = criar_mapa_campos(campos)
    coluna_valor = mapa.get("valor")
    coluna_quantidade = mapa.get("quantidade")
    coluna_produto = mapa.get("produto")
    coluna_loja = mapa.get("loja")
    coluna_data = mapa.get("data")
    coluna_venda = mapa.get("id_venda")

    valores = _serie_numerica(df, coluna_valor)
    quantidades = _serie_numerica(df, coluna_quantidade)
    valores_validos = valores.dropna()
    quantidades_validas = quantidades.dropna()
    resultado: dict = {}

    if not valores_validos.empty:
        desvio = valores_validos.std()
        resultado.update(
            {
                "faturamento_total": _float_seguro(valores_validos.sum()),
                "valor_medio_venda": _float_seguro(valores_validos.mean()),
                "maior_venda": _float_seguro(valores_validos.max()),
                "menor_venda": _float_seguro(valores_validos.min()),
                "mediana_venda": _float_seguro(valores_validos.median()),
                "desvio_padrao_venda": _float_seguro(desvio),
            }
        )

    if not quantidades_validas.empty:
        resultado.update(
            {
                "quantidade_total": _float_seguro(quantidades_validas.sum()),
                "quantidade_media": _float_seguro(quantidades_validas.mean()),
                "maior_quantidade": _float_seguro(quantidades_validas.max()),
                "menor_quantidade": _float_seguro(quantidades_validas.min()),
            }
        )

    if coluna_venda in df.columns and not valores_validos.empty:
        vendas_unicas = int(df[coluna_venda].nunique(dropna=True))
        if vendas_unicas:
            resultado["total_vendas"] = vendas_unicas
            resultado["ticket_medio"] = _float_seguro(valores_validos.sum()) / vendas_unicas

    quantidade_total = _float_seguro(quantidades_validas.sum())
    if not valores_validos.empty and quantidade_total:
        resultado["preco_medio_unidade"] = (
            _float_seguro(valores_validos.sum()) / quantidade_total
        )

    ranking_produtos = _ranking(df, coluna_produto, valores)
    if not ranking_produtos.empty:
        resultado["produto_maior_faturamento"] = str(ranking_produtos.index[0])
        resultado["valor_produto_lider"] = _float_seguro(ranking_produtos.iloc[0])
        resultado["ranking_produtos"] = _dict_ranking(ranking_produtos)

    ranking_lojas = _ranking(df, coluna_loja, valores)
    if not ranking_lojas.empty:
        resultado["loja_maior_faturamento"] = str(ranking_lojas.index[0])
        resultado["valor_loja_lider"] = _float_seguro(ranking_lojas.iloc[0])
        resultado["ranking_lojas"] = _dict_ranking(ranking_lojas)

    datas = _serie_data(df, coluna_data)
    dados_temporais = pd.DataFrame({"data": datas, "valor": valores}).dropna()
    if not dados_temporais.empty:
        mensal = (
            dados_temporais.groupby(dados_temporais["data"].dt.to_period("M"))["valor"]
            .sum()
            .sort_index()
        )
        resultado["faturamento_mensal"] = {
            str(periodo): _float_seguro(valor) for periodo, valor in mensal.items()
        }

    return resultado


def calcular_indicadores_financeiros(df: pd.DataFrame, campos: dict) -> dict:
    """Calcula receitas, despesas, saldo, médias e concentrações financeiras."""
    mapa = criar_mapa_campos(campos)
    receitas = _serie_numerica(df, mapa.get("receita"))
    despesas = _serie_numerica(df, mapa.get("despesa")).abs()
    valores = _serie_numerica(df, mapa.get("valor"))
    custos = _serie_numerica(df, mapa.get("custo")).abs()
    coluna_tipo = mapa.get("tipo_movimento")
    tipos = _serie_texto(df, coluna_tipo)
    if coluna_tipo is not None:
        tipos = tipos.dropna().map(normalizar_texto).reindex(df.index)

    if receitas.notna().sum() == 0 and valores.notna().sum():
        if tipos.notna().sum():
            mascara = tipos.str.contains(r"receita|entrada|credito", regex=True, na=False)
            receitas = valores.where(mascara)
        else:
            receitas = valores.where(valores >= 0)
    if despesas.notna().sum() == 0:
        if custos.notna().sum():
            despesas = custos
        elif valores.notna().sum():
            if tipos.notna().sum():
                mascara = tipos.str.contains(r"despesa|saida|debito|custo", regex=True, na=False)
                despesas = valores.where(mascara).abs()
            else:
                despesas = valores.where(valores < 0).abs()

    receita_total = _float_seguro(receitas.sum())
    despesa_total = _float_seguro(despesas.sum())
    saldo = receita_total - despesa_total
    movimentos = receitas.fillna(0) + despesas.fillna(0)
    total_lancamentos = int((receitas.notna() | despesas.notna()).sum())
    resultado = {
        "receita_total": receita_total,
        "despesa_total": despesa_total,
        "saldo": saldo,
        "total_lancamentos": total_lancamentos,
        "media_lancamento": _float_seguro(movimentos[movimentos != 0].mean()),
        "media_receitas": _float_seguro(receitas.mean()),
        "media_despesas": _float_seguro(despesas.mean()),
        "maior_receita": _float_seguro(receitas.max()),
        "maior_despesa": _float_seguro(despesas.max()),
        "margem_operacional": round(saldo / receita_total * 100, 2) if receita_total else 0.0,
    }

    ranking = _ranking(df, mapa.get("categoria"), movimentos)
    if not ranking.empty:
        resultado["categoria_maior_movimentacao"] = str(ranking.index[0])
        resultado["valor_categoria_lider"] = _float_seguro(ranking.iloc[0])
        resultado["ranking_categorias"] = _dict_ranking(ranking)
    return resultado


def calcular_indicadores_estoque(df: pd.DataFrame, campos: dict) -> dict:
    """Calcula posição, criticidade, valor e rankings de estoque."""
    mapa = criar_mapa_campos(campos)
    coluna_estoque = mapa.get("estoque") or mapa.get("quantidade")
    coluna_produto = mapa.get("produto")
    estoque = _serie_numerica(df, coluna_estoque)
    estoque_valido = estoque.dropna()
    produtos = _serie_texto(df, coluna_produto)
    custo = _serie_numerica(df, mapa.get("custo"))
    if custo.notna().sum() == 0:
        custo = _serie_numerica(df, mapa.get("valor_unitario"))

    total_produtos = int(produtos.nunique(dropna=True)) if coluna_produto in df.columns else int(len(df))
    resultado = {
        "estoque_total": _float_seguro(estoque_valido.sum()),
        "produtos_distintos": total_produtos,
        "produtos_baixo_estoque": int(((estoque > 0) & (estoque <= 5)).sum()),
        "produtos_sem_estoque": int((estoque <= 0).sum()),
        "estoque_medio": _float_seguro(estoque_valido.mean()),
        "valor_estoque": _float_seguro((estoque * custo).sum()),
    }

    ranking = _ranking(df, coluna_produto, estoque)
    if not ranking.empty:
        resultado["produto_maior_estoque"] = str(ranking.index[0])
        resultado["valor_maior_estoque"] = _float_seguro(ranking.iloc[0])
        resultado["produto_critico"] = str(ranking.index[-1])
        resultado["valor_produto_critico"] = _float_seguro(ranking.iloc[-1])
        resultado["ranking_estoque"] = _dict_ranking(ranking)

    movimentacao = _serie_numerica(df, mapa.get("quantidade"))
    if (
        mapa.get("estoque") is not None
        and mapa.get("quantidade") is not None
        and estoque_valido.mean()
    ):
        resultado["giro_estoque"] = _float_seguro(movimentacao.sum()) / _float_seguro(
            estoque_valido.mean(),
            1.0,
        )
    return resultado


def calcular_indicadores_cadastro(df: pd.DataFrame, campos: dict) -> dict:
    """Calcula volume, unicidade, completude, status e distribuição cadastral."""
    mapa = criar_mapa_campos(campos)
    coluna_identidade = mapa.get("cliente") or mapa.get("id_cadastro")
    coluna_status = mapa.get("status")
    total = int(len(df))
    unicos = (
        int(df[coluna_identidade].nunique(dropna=True))
        if coluna_identidade in df.columns
        else int(len(df.drop_duplicates()))
    )
    ativos, inativos = _contar_status(_serie_texto(df, coluna_status))
    total_celulas = int(df.shape[0] * df.shape[1])
    ausentes = int(df.isna().sum().sum())
    completude = 100.0 - (ausentes / total_celulas * 100 if total_celulas else 0.0)
    resultado = {
        "total_registros": total,
        "registros_unicos": unicos,
        "registros_duplicados": int(df.duplicated().sum()),
        "valores_ausentes": ausentes,
        "completude": round(completude, 2),
        "registros_ativos": ativos,
        "registros_inativos": inativos,
    }

    ranking = _ranking_contagem(df, mapa.get("categoria"))
    if not ranking.empty:
        resultado["maior_categoria"] = str(ranking.index[0])
        resultado["quantidade_categoria_lider"] = int(ranking.iloc[0])
        resultado["distribuicao_categorias"] = {
            str(chave): int(valor) for chave, valor in ranking.head(10).items()
        }
    return resultado


def calcular_indicadores_rh(df: pd.DataFrame, campos: dict) -> dict:
    """Calcula quadro, movimentação, folha, setores e rotatividade de RH."""
    mapa = criar_mapa_campos(campos)
    coluna_colaborador = mapa.get("colaborador") or mapa.get("id_cadastro")
    colaboradores = (
        int(df[coluna_colaborador].nunique(dropna=True))
        if coluna_colaborador in df.columns
        else int(len(df))
    )
    admissoes = _serie_data(df, mapa.get("admissao"))
    desligamentos = _serie_data(df, mapa.get("desligamento"))
    salarios = _serie_numerica(df, mapa.get("salario"))
    ativos, inativos = _contar_status(_serie_texto(df, mapa.get("status")))
    if ativos == 0 and inativos == 0 and mapa.get("desligamento") in df.columns:
        inativos = int(desligamentos.notna().sum())
        ativos = max(0, colaboradores - inativos)

    setores = _ranking_contagem(df, mapa.get("setor"))
    resultado = {
        "total_colaboradores": colaboradores,
        "total_setores": int(df[mapa["setor"]].nunique(dropna=True)) if mapa.get("setor") in df.columns else 0,
        "total_admissoes": int(admissoes.notna().sum()),
        "total_desligamentos": int(desligamentos.notna().sum()),
        "colaboradores_ativos": ativos,
        "colaboradores_inativos": inativos,
        "folha_total": _float_seguro(salarios.sum()),
        "salario_medio": _float_seguro(salarios.mean()),
        "turnover_percentual": round(
            int(desligamentos.notna().sum()) / colaboradores * 100,
            2,
        ) if colaboradores else 0.0,
    }
    if not setores.empty:
        resultado["maior_setor"] = str(setores.index[0])
        resultado["quantidade_maior_setor"] = int(setores.iloc[0])
        resultado["distribuicao_setores"] = {
            str(chave): int(valor) for chave, valor in setores.head(10).items()
        }

    if admissoes.notna().any():
        fim = desligamentos.fillna(pd.Timestamp(datetime.now().date()))
        anos = (fim - admissoes).dt.days / 365.25
        resultado["tempo_medio_empresa_anos"] = round(_float_seguro(anos.mean()), 2)
    return resultado


def calcular_indicadores(categoria: str, df: pd.DataFrame, campos: dict) -> dict:
    """Executa o motor da categoria e sempre inclui indicadores universais."""
    motores = {
        "vendas": calcular_indicadores_vendas,
        "financeiro": calcular_indicadores_financeiros,
        "estoque": calcular_indicadores_estoque,
        "cadastro": calcular_indicadores_cadastro,
        "recursos_humanos": calcular_indicadores_rh,
        "compras": calcular_indicadores_compras,
        "ti": calcular_indicadores_ti,
        "marketing": calcular_indicadores_marketing,
        "administrativo": calcular_indicadores_administrativo,
        "juridico": calcular_indicadores_juridico,
        "comercial": calcular_indicadores_comercial,
    }
    motor = motores.get(str(categoria).lower())
    especificos = motor(df, campos) if motor else {}
    return {
        **especificos,
        "universais": calcular_indicadores_universais(df),
        "categoria_motor": str(categoria).lower(),
    }
