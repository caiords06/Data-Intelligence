"""Contrato explícito do cliente do Servidor Corporativo."""
from enterprise.servidor_cliente import (
    baixar_conjunto_remoto, enviar_bytes_servidor, excluir_item_servidor,
    listar_arquivos_servidor, testar_servidor,
)

__all__ = (
    "baixar_conjunto_remoto", "enviar_bytes_servidor", "excluir_item_servidor",
    "listar_arquivos_servidor", "testar_servidor",
)
