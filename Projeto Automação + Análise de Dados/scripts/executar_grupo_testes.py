"""Executa uma fração determinística da suíte em um único processo pytest.

O CI usa três jobs independentes para impedir que servidores HTTP, threads e
patches globais de banco/storage de um grupo contaminem os demais.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import subprocess
import sys

RAIZ = Path(__file__).resolve().parents[1]
PASTA_TESTES = RAIZ / "tests"


def selecionar(grupo: int, total: int) -> list[Path]:
    arquivos = sorted(PASTA_TESTES.glob("test_*.py"))
    if total < 1 or grupo < 1 or grupo > total:
        raise ValueError("Grupo inválido.")
    tamanho = math.ceil(len(arquivos) / total)
    inicio = (grupo - 1) * tamanho
    return arquivos[inicio : inicio + tamanho]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grupo", type=int, required=True)
    parser.add_argument("--total", type=int, default=3)
    args = parser.parse_args()

    arquivos = selecionar(args.grupo, args.total)
    if not arquivos:
        print(f"Grupo {args.grupo}/{args.total}: nenhum teste.")
        return 0
    relativos = [str(p.relative_to(RAIZ)) for p in arquivos]
    print(f"Grupo {args.grupo}/{args.total}: {len(relativos)} arquivos", flush=True)
    for item in relativos:
        print(f"  - {item}")

    ambiente = os.environ.copy()
    ambiente.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *relativos],
        cwd=RAIZ,
        env=ambiente,
        check=False,
    )
    return int(resultado.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
