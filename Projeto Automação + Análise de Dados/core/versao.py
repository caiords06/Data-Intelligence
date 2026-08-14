"""Versão canônica da plataforma e requisitos de release."""

from __future__ import annotations

VERSAO_PLATAFORMA = "11.1.0"
VERSAO_INTERFACE = "V11.1.0"
PYTHON_RELEASE = (3, 14)
PYTHON_RELEASE_TEXTO = "3.14"


def versao_completa() -> str:
    return f"Data Intelligence Enterprise Platform {VERSAO_INTERFACE}"
