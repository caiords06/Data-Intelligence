"""Instalação operacional do executável do agente pelo Agendador do Windows."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from core.windows_tasks import (
    consultar_tarefa as _consultar,
    eh_administrador,
    exigir_windows,
    iniciar_tarefa as _iniciar,
    registrar_tarefa_boot_system,
    remover_tarefa as _remover,
)

NOME_TAREFA = "DataIntelligence-TIAgent"


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
    exe = Path(executavel).resolve()
    config = Path(config_path).resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"Executável do agente não encontrado: {exe}")
    if not config.is_file():
        raise FileNotFoundError(f"Configuração do agente não encontrada: {config}")
    # New-ScheduledTaskAction recebe o caminho e os argumentos separadamente;
    # nenhum nível de cmd.exe precisa re-interpretar Program Files.
    registrar_tarefa_boot_system(
        NOME_TAREFA,
        exe,
        f'run --config "{config}"',
        descricao="Data Intelligence TI Agent",
    )


def iniciar_tarefa() -> None:
    _iniciar(NOME_TAREFA)


def remover_tarefa() -> None:
    exigir_windows()
    if not eh_administrador():
        raise PermissionError("Execute a remoção do agente como administrador.")
    _remover(NOME_TAREFA, ignorar_ausente=True)


def consultar_tarefa() -> str:
    resultado = _consultar(NOME_TAREFA)
    return resultado or "Tarefa do agente não instalada."


def executavel_atual() -> Path:
    if not getattr(sys, "frozen", False):
        raise RuntimeError(
            "A instalação automática exige o executável gerado pelo script de build."
        )
    return Path(sys.executable)
