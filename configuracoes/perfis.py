"""Perfis reutilizáveis de execução analítica."""

from copy import deepcopy

PERFIS_ANALISE = {
    "completa": {
        "nome": "Análise completa",
        "descricao": "Executa tratamento, estrutura, qualidade, indicadores e temporal.",
        "configuracao": {
            "categoria": "automatica",
            "periodo": "automatico",
            "modulos": {
                "tratamento": True,
                "estrutural": True,
                "indicadores": True,
                "temporal": True,
                "qualidade": True,
            },
        },
    },
    "executiva": {
        "nome": "Visão executiva",
        "descricao": "Prioriza indicadores, comparações temporais e qualidade.",
        "configuracao": {
            "categoria": "automatica",
            "periodo": "mensal",
            "modulos": {
                "tratamento": True,
                "estrutural": False,
                "indicadores": True,
                "temporal": True,
                "qualidade": True,
            },
        },
    },
    "qualidade": {
        "nome": "Auditoria de qualidade",
        "descricao": "Foca estrutura, tratamento, inconsistências e possíveis outliers.",
        "configuracao": {
            "categoria": "automatica",
            "periodo": "automatico",
            "modulos": {
                "tratamento": True,
                "estrutural": True,
                "indicadores": False,
                "temporal": False,
                "qualidade": True,
            },
        },
    },
    "rapida": {
        "nome": "Análise rápida",
        "descricao": "Executa tratamento e indicadores com menor quantidade de etapas.",
        "configuracao": {
            "categoria": "automatica",
            "periodo": "automatico",
            "modulos": {
                "tratamento": True,
                "estrutural": False,
                "indicadores": True,
                "temporal": False,
                "qualidade": False,
            },
        },
    },
}


def obter_perfis() -> dict:
    return deepcopy(PERFIS_ANALISE)


def obter_perfil(chave: str) -> dict:
    if chave not in PERFIS_ANALISE:
        raise ValueError("Perfil de análise não encontrado.")
    return deepcopy(PERFIS_ANALISE[chave])
