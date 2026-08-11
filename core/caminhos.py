"""Resolução de caminhos para desenvolvimento e executáveis PyInstaller.

Recursos empacotados são lidos do bundle; dados persistentes nunca são gravados
na pasta temporária do PyInstaller. Em builds Windows, o banco e arquivos gerados
ficam em ProgramData, salvo quando DATA_INTELLIGENCE_DATA_DIR for definido.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys


def executando_empacotado() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def raiz_projeto() -> Path:
    return Path(__file__).resolve().parents[1]


def raiz_recursos() -> Path:
    if executando_empacotado():
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return raiz_projeto()


def pasta_dados() -> Path:
    override = str(os.environ.get("DATA_INTELLIGENCE_DATA_DIR", "")).strip()
    if override:
        return Path(override).expanduser().resolve()
    if executando_empacotado():
        if os.name == "nt":
            base = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
            return base / "DataIntelligence" / "Platform"
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
        return base / "data-intelligence-platform"
    return raiz_projeto() / "storage"


def caminho_recurso(*partes: str | Path) -> Path:
    return raiz_recursos().joinpath(*map(Path, partes))


__all__ = [
    "executando_empacotado",
    "raiz_projeto",
    "raiz_recursos",
    "pasta_dados",
    "caminho_recurso",
]
