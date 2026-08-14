"""Impede builds oficiais com versão de Python diferente da homologada."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.versao import PYTHON_RELEASE, PYTHON_RELEASE_TEXTO, VERSAO_INTERFACE


def main() -> int:
    atual = sys.version_info[:2]
    if atual != PYTHON_RELEASE:
        print(
            f"ERRO: release {VERSAO_INTERFACE} exige Python {PYTHON_RELEASE_TEXTO}; "
            f"interpretador atual é {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}."
        )
        return 2
    print(f"Python de release validado: {sys.version.split()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
