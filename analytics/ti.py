"""Indicadores operacionais de Tecnologia, ITSM e disponibilidade."""

import pandas as pd

from analytics.base import percentual, ranking_contagem, status_normalizado, texto


def calcular_indicadores_ti(df: pd.DataFrame, _campos: dict) -> dict:
    status = status_normalizado(df)
    prioridade = texto(df, "prioridade").str.lower()
    categorias = texto(df, "categoria")
    titulos = texto(df, "titulo", "chamado")
    concluidos = status.str.contains("concluido|resolvido|fechado", regex=True, na=False)
    abertos = ~concluidos
    criticos = prioridade.str.contains("critica|crítica", regex=True, na=False) & abertos
    ranking = ranking_contagem(categorias)
    repetidos = titulos.dropna().duplicated(keep=False)
    serie_vazia_data = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    serie_vazia_numero = pd.Series(float("nan"), index=df.index, dtype="float64")
    criado = pd.to_datetime(df["criado_em"], errors="coerce") if "criado_em" in df else serie_vazia_data
    primeira = pd.to_datetime(df["primeira_resposta_em"], errors="coerce") if "primeira_resposta_em" in df else serie_vazia_data
    resolvido_em = pd.to_datetime(df["resolvido_em"], errors="coerce") if "resolvido_em" in df else serie_vazia_data
    atendimento_minutos = (primeira - criado).dt.total_seconds().div(60)
    solucao_minutos = (resolvido_em - criado).dt.total_seconds().div(60)
    sla_atendimento = pd.to_numeric(df["sla_atendimento_minutos"], errors="coerce") if "sla_atendimento_minutos" in df else serie_vazia_numero
    sla_solucao = pd.to_numeric(df["sla_solucao_minutos"], errors="coerce") if "sla_solucao_minutos" in df else serie_vazia_numero
    dentro_sla = concluidos & solucao_minutos.notna() & (
        sla_solucao.isna() | (solucao_minutos <= sla_solucao)
    )
    resolvidos_validos = int((concluidos & solucao_minutos.notna()).sum())
    saude = pd.to_numeric(df["saude_percentual"], errors="coerce") if "saude_percentual" in df else serie_vazia_numero
    conectividade = texto(df, "estado_conectividade").str.lower()
    return {
        "total_chamados": int(len(df)),
        "chamados_abertos": int(abertos.sum()),
        "chamados_concluidos": int(concluidos.sum()),
        "chamados_criticos": int(criticos.sum()),
        "taxa_resolucao": percentual(concluidos.sum(), len(df)),
        "chamados_reincidentes": int(repetidos.sum()),
        "tempo_medio_primeira_resposta_minutos": round(float(atendimento_minutos.mean()), 2) if atendimento_minutos.notna().any() else None,
        "mttr_minutos": round(float(solucao_minutos.mean()), 2) if solucao_minutos.notna().any() else None,
        "sla_compliance": percentual(dentro_sla.sum(), resolvidos_validos),
        "primeiras_respostas_no_sla": percentual(
            (atendimento_minutos.notna() & (sla_atendimento.isna() | (atendimento_minutos <= sla_atendimento))).sum(),
            int(atendimento_minutos.notna().sum()),
        ),
        "saude_media_ativos": round(float(saude.mean()), 2) if saude.notna().any() else None,
        "ativos_offline_relacionados": int(conectividade.str.contains("offline", na=False).sum()),
        "categoria_mais_frequente": next(iter(ranking), None),
        "chamados_por_categoria": ranking,
    }
