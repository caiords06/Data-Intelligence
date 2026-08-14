"""Casos de uso de comunicação corporativa."""
from enterprise.correio import (
    atualizar_estado, contagem_nao_lidas, enviar_mensagem, listar_caixa,
    listar_contatos, obter_mensagem, salvar_rascunho,
)

__all__ = (
    "atualizar_estado", "contagem_nao_lidas", "enviar_mensagem", "listar_caixa",
    "listar_contatos", "obter_mensagem", "salvar_rascunho",
)
