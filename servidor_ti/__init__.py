"""Servidor central do agente de Tecnologia."""

VERSAO_SERVIDOR_TI = "1.0.0"

from servidor_ti.runtime import (
    iniciar_servidor_embutido,
    parar_servidor_embutido,
    status_servidor,
)

__all__ = ["VERSAO_SERVIDOR_TI", "iniciar_servidor_embutido", "parar_servidor_embutido", "status_servidor"]
