"""Indicadores de contratos, vencimentos e risco jurídico."""

from datetime import datetime

import pandas as pd

from analytics.base import datas, numerica, ranking_contagem, seguro, status_normalizado, texto


def calcular_indicadores_juridico(df: pd.DataFrame, _campos: dict) -> dict:
    valores = numerica(df, "valor")
    riscos = texto(df, "risco").str.lower()
    status = status_normalizado(df)
    vencimentos = datas(df, "vencimento")
    agora = pd.Timestamp(datetime.now().date())
    limite = agora + pd.Timedelta(days=30)
    ativos = status.str.contains("ativo|revisao|elaboracao", regex=True, na=False)
    alto_risco = riscos.str.contains("alto|critico|crítico", regex=True, na=False)
    vencendo = vencimentos.between(agora, limite, inclusive="both") & ativos
    ranking = ranking_contagem(riscos)
    return {
        "total_contratos": int(len(df)),
        "contratos_ativos": int(ativos.sum()),
        "contratos_vencendo_30_dias": int(vencendo.sum()),
        "contratos_alto_risco": int(alto_risco.sum()),
        "valor_total_contratos": seguro(valores.sum()),
        "valor_em_risco": seguro(valores.where(alto_risco).sum()),
        "risco_predominante": next(iter(ranking), None),
        "contratos_por_risco": ranking,
    }

