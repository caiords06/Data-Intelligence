"""Fachada estável das orquestrações transversais V10.4.1."""
from enterprise.orquestracao import (
    concluir_etapa, converter_lead_em_oportunidade, criar_fluxo_admissao,
    criar_fluxo_desligamento, criar_fluxo_reposicao, encaminhar_provisao_financeiro,
    listar_etapas_orquestracao, listar_orquestracoes, contar_orquestracoes, resumo_orquestracoes,
)
__all__=("concluir_etapa","converter_lead_em_oportunidade","criar_fluxo_admissao","criar_fluxo_desligamento",
         "criar_fluxo_reposicao","encaminhar_provisao_financeiro","listar_etapas_orquestracao",
         "listar_orquestracoes","contar_orquestracoes","resumo_orquestracoes")
