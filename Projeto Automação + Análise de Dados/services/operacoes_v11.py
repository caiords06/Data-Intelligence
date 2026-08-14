"""Fachada dos casos de uso operacionais configuráveis da V11."""
from enterprise.core_v11.registros import (
    alterar_estado_registro, avancar_fluxo, atualizar_registro, criar_registro, listar_registros,
    listar_tipos, obter_registro, resumo_operacional, salvar_tipo,
    relacionar_registros,
)

__all__ = tuple(nome for nome in globals() if not nome.startswith("_"))
