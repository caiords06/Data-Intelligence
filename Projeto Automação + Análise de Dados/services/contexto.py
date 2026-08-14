"""Casos de uso de contexto e autorização."""
from enterprise.contexto import (
    aplicar_perfil_padrao_usuario, listar_modulos_permitidos, obter_contexto,
    obter_permissoes_usuario, salvar_permissoes_usuario, tem_permissao,
)

__all__ = (
    "aplicar_perfil_padrao_usuario", "listar_modulos_permitidos", "obter_contexto",
    "obter_permissoes_usuario", "salvar_permissoes_usuario", "tem_permissao",
)
