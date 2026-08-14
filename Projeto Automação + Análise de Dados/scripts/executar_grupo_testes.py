"""Executa uma fração determinística da suíte com isolamento por arquivo.

V9.9: cada pytest roda em um grupo de processo próprio. Em timeout, todo o
process tree é encerrado, evitando que filhos (servidores, Tk, workers) fiquem
órfãos e contaminem o job seguinte.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

RAIZ = Path(__file__).resolve().parents[1]
PASTA_TESTES = RAIZ / "tests"


def selecionar(grupo: int, total: int) -> list[Path]:
    arquivos = sorted(PASTA_TESTES.glob("test_*.py"))
    if total < 1 or grupo < 1 or grupo > total:
        raise ValueError("Grupo inválido.")
    tamanho = math.ceil(len(arquivos) / total)
    inicio = (grupo - 1) * tamanho
    return arquivos[inicio : inicio + tamanho]


def _encerrar_arvore(processo: subprocess.Popen, *, espera: float = 5.0) -> None:
    if processo.poll() is not None:
        return
    if os.name == "nt":
        # taskkill /T encerra também processos filhos criados pelo pytest.
        subprocess.run(
            ["taskkill", "/PID", str(processo.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=max(1.0, espera),
        )
    else:
        try:
            os.killpg(processo.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            processo.wait(timeout=max(0.5, espera / 2))
            return
        except subprocess.TimeoutExpired:
            try:
                os.killpg(processo.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        processo.wait(timeout=max(0.5, espera / 2))
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(timeout=2)


def _encerrar_residuos_grupo(pid: int) -> None:
    """Encerra netos que tenham sobrevivido ao pytest já finalizado.

    No POSIX, filhos herdam o process group criado para o arquivo. Isso evita
    servidores/Tk/workers órfãos sem depender de um PIPE de stdout permanecer
    aberto. No Windows, o timeout continua usando taskkill /T.
    """
    if os.name == "nt":
        return
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def executar_arquivo(arquivo: Path, ambiente: dict[str, str], timeout_segundos: int = 90) -> int:
    relativo = str(arquivo.relative_to(RAIZ))
    print(f"\n[pytest isolado] {relativo}", flush=True)
    # Arquivo temporário, não PIPE: processos netos podem herdar o descritor
    # sem impedir o runner de detectar o término do pytest principal.
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as saida:
        kwargs = {
            "cwd": RAIZ,
            "env": ambiente,
            "stdout": saida,
            "stderr": subprocess.STDOUT,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        processo = subprocess.Popen([sys.executable, "-m", "pytest", "-q", relativo], **kwargs)
        try:
            codigo = processo.wait(timeout=timeout_segundos)
            _encerrar_residuos_grupo(processo.pid)
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {relativo} excedeu {timeout_segundos}s; encerrando árvore do processo", flush=True)
            _encerrar_arvore(processo)
            codigo = 124
        except KeyboardInterrupt:
            _encerrar_arvore(processo)
            raise
        finally:
            saida.flush()
            saida.seek(0)
            conteudo = saida.read()
            if conteudo:
                print(conteudo, end="" if conteudo.endswith("\n") else "\n", flush=True)
        return int(codigo or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grupo", type=int, required=True)
    parser.add_argument("--total", type=int, default=6)
    parser.add_argument("--timeout-arquivo", type=int, default=90)
    args = parser.parse_args()

    arquivos = selecionar(args.grupo, args.total)
    if not arquivos:
        print(f"Grupo {args.grupo}/{args.total}: nenhum teste.")
        return 0

    print(f"Grupo {args.grupo}/{args.total}: {len(arquivos)} arquivos em processos independentes", flush=True)
    ambiente = os.environ.copy()
    ambiente["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    falhas: list[str] = []
    for arquivo in arquivos:
        if executar_arquivo(arquivo, ambiente, args.timeout_arquivo) != 0:
            falhas.append(str(arquivo.relative_to(RAIZ)))

    if falhas:
        print("\nArquivos com falha:", flush=True)
        for item in falhas:
            print(f"  - {item}", flush=True)
        return 1

    print(f"\nGrupo {args.grupo}/{args.total}: todos os arquivos concluídos com sucesso.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
