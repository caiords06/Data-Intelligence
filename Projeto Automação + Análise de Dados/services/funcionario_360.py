"""Fachada do Funcionário 360° independente da interface."""
from enterprise.core_v11.funcionarios import (
    carregar_avatar, garantir_vinculo, obter_funcionario_360, obter_meu_funcionario_360,
    registrar_acesso, registrar_avatar, registrar_avatar_bytes, registrar_custo,
    registrar_feedback, registrar_ocorrencia,
)

__all__ = tuple(nome for nome in globals() if not nome.startswith("_"))
