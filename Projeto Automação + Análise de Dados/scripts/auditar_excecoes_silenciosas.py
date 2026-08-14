"""Bloqueia ``except Exception: pass`` fora da suíte de testes."""
from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IGNORADOS = {"tests", "build", "dist", "release", "storage", "artifacts"}


def main() -> int:
    problemas: list[str] = []
    for caminho in RAIZ.rglob("*.py"):
        relativo = caminho.relative_to(RAIZ)
        if any(parte in IGNORADOS for parte in relativo.parts):
            continue
        arvore = ast.parse(caminho.read_text(encoding="utf-8-sig"), filename=str(relativo))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.ExceptHandler):
                continue
            amplo = isinstance(no.type, ast.Name) and no.type.id in {"Exception", "BaseException"}
            silencioso = len(no.body) == 1 and isinstance(no.body[0], ast.Pass)
            if amplo and silencioso:
                problemas.append(f"{relativo.as_posix()}:{no.lineno}")
    if problemas:
        print("Tratamentos silenciosos proibidos:\n" + "\n".join(problemas))
        return 1
    print("OK: nenhum except Exception/BaseException silencioso fora de testes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
