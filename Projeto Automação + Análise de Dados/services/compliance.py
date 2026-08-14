"""Fachada dos casos de uso de conformidade para Desktop, API e integrações."""
from enterprise.compliance import (
    abrir_incidente_privacidade, atualizar_solicitacao_titular, avaliar_incidente_privacidade,
    criar_solicitacao_titular, definir_bloqueio_retencao, encerrar_bloqueio_retencao,
    listar_bloqueios_retencao, listar_incidentes_privacidade, listar_solicitacoes_titulares,
    listar_decisoes_analiticas, listar_ripd, listar_terceiros, listar_tratamentos, resumo_conformidade,
    salvar_decisao_analitica, salvar_ripd, salvar_terceiro, salvar_tratamento,
)

__all__ = tuple(nome for nome in globals() if not nome.startswith("_"))
