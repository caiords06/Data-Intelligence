"""Valida o pacote-fonte V9.3 a partir de uma extração limpa.

A validação estrutural compila o código e analisa os três .spec. Para testes,
use ``--grupo 1``, ``--grupo 2`` ou ``--grupo 3``. Cada invocação usa uma
extração própria; o CI executa os grupos em jobs independentes para isolamento
real de sockets, SQLite e estado temporário.
"""
from __future__ import annotations

import argparse
import ast
import compileall
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

RAIZ_SCRIPT = Path(__file__).resolve().parents[1]
if str(RAIZ_SCRIPT) not in sys.path:
    sys.path.insert(0, str(RAIZ_SCRIPT))

from scripts.empacotar_fonte_limpa import ARQUIVOS_OBRIGATORIOS, empacotar, validar_zip

SPECS = ("DataIntelligencePlatform.spec", "DataIntelligenceServer.spec", "agente_ti.spec")


def _extrair(caminho_zip: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(caminho_zip) as zf:
        zf.extractall(destino)


def _selecionar_testes(raiz: Path, grupo: int, total: int = 3) -> list[str]:
    arquivos = sorted((raiz / "tests").glob("test_*.py"))
    tamanho = math.ceil(len(arquivos) / total)
    inicio = (grupo - 1) * tamanho
    return [str(x.relative_to(raiz)) for x in arquivos[inicio : inicio + tamanho]]


def validar(caminho_zip: Path, grupo_testes: int | None = None) -> None:
    caminho_zip = caminho_zip.resolve()
    validar_zip(caminho_zip)
    if grupo_testes is not None and grupo_testes not in (1, 2, 3):
        raise ValueError("Grupo deve ser 1, 2 ou 3.")

    with tempfile.TemporaryDirectory(prefix="di-v93-source-") as tmp:
        raiz = Path(tmp) / "fonte"
        _extrair(caminho_zip, raiz)

        faltando = [x for x in sorted(ARQUIVOS_OBRIGATORIOS) if not (raiz / x).is_file()]
        if faltando:
            raise RuntimeError("ZIP extraído perdeu arquivos obrigatórios: " + ", ".join(faltando))

        for spec in SPECS:
            ast.parse((raiz / spec).read_text(encoding="utf-8"), filename=spec)

        if not compileall.compile_dir(
            raiz,
            quiet=1,
            rx=__import__("re").compile(r"/(?:docs|dados_exemplo)/"),
        ):
            raise RuntimeError("Falha ao compilar o código Python do pacote extraído.")

        if grupo_testes is not None:
            relativos = _selecionar_testes(raiz, grupo_testes)
            ambiente = os.environ.copy()
            ambiente.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", *relativos],
                cwd=raiz,
                env=ambiente,
                check=False,
                timeout=150,
            )
            if proc.returncode:
                raise RuntimeError(f"Grupo de testes {grupo_testes}/3 falhou no pacote extraído.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", nargs="?", help="ZIP a validar; se omitido, gera um temporário.")
    parser.add_argument("--grupo", type=int, choices=(1, 2, 3), help="Executa um grupo isolado de testes no ZIP extraído.")
    args = parser.parse_args()

    if args.zip:
        caminho = Path(args.zip).expanduser().resolve()
        validar(caminho, grupo_testes=args.grupo)
    else:
        with tempfile.TemporaryDirectory(prefix="di-v93-package-") as tmp:
            caminho, _ = empacotar(Path(tmp) / "source.zip")
            validar(caminho, grupo_testes=args.grupo)
    sufixo = f" + grupo {args.grupo}/3" if args.grupo else ""
    print(f"Pacote-fonte V9.3 validado a partir de extração limpa{sufixo}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
