"""Instalação operacional do executável do agente pelo Agendador do Windows."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import subprocess
import sys


NOME_TAREFA = "DataIntelligence-TIAgent"


def exigir_windows() -> None:
    if os.name != "nt":
        raise OSError("Esta operação está disponível apenas no Windows.")


def eh_administrador() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def proteger_diretorio(caminho: str | Path) -> None:
    """Restringe configuração e segredo a SYSTEM e administradores locais."""
    exigir_windows()
    pasta = Path(caminho).resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "icacls.exe", str(pasta), "/inheritance:r",
            "/grant:r", "*S-1-5-18:(OI)(CI)F",
            "/grant:r", "*S-1-5-32-544:(OI)(CI)F",
        ],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )


def _comando_tarefa(executavel: str | Path, config_path: str | Path) -> str:
    exe = Path(executavel).resolve()
    config = Path(config_path).resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"Executável do agente não encontrado: {exe}")
    if not config.is_file():
        raise FileNotFoundError(f"Configuração do agente não encontrada: {config}")
    return f'"{exe}" run --config "{config}"'


def instalar_tarefa(executavel: str | Path, config_path: str | Path) -> None:
    exigir_windows()
    if not eh_administrador():
        raise PermissionError("Execute o instalador do agente como administrador.")
    comando = _comando_tarefa(executavel, config_path)
    subprocess.run(
        [
            "schtasks.exe", "/Create", "/TN", NOME_TAREFA,
            "/SC", "ONSTART", "/RU", "SYSTEM", "/RL", "HIGHEST",
            "/TR", comando, "/F",
        ],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )


def remover_tarefa() -> None:
    exigir_windows()
    if not eh_administrador():
        raise PermissionError("Execute a remoção do agente como administrador.")
    subprocess.run(
        ["schtasks.exe", "/Delete", "/TN", NOME_TAREFA, "/F"],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )


def consultar_tarefa() -> str:
    exigir_windows()
    resultado = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", NOME_TAREFA, "/FO", "LIST", "/V"],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    if resultado.returncode != 0:
        return "Tarefa do agente não instalada."
    return resultado.stdout.strip()


def executavel_atual() -> Path:
    if not getattr(sys, "frozen", False):
        raise RuntimeError(
            "A instalação automática exige o executável gerado pelo script de build."
        )
    return Path(sys.executable)
