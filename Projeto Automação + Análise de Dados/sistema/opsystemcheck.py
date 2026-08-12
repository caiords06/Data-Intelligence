"""Validações relacionadas ao sistema operacional."""

import platform


def verificar_sistema_operacional():
    sistema = platform.system()
    if sistema != "Windows":
        raise OSError("A automação web desta versão requer Windows.")
    return sistema
