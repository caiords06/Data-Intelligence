"""Inicialização automática do Servidor Corporativo no Windows."""
from __future__ import annotations

from pathlib import Path
import sys

from core.windows_tasks import (
    consultar_tarefa as _consultar,
    eh_administrador,
    exigir_windows,
    iniciar_tarefa as _iniciar,
    registrar_tarefa_boot_system,
    remover_tarefa as _remover,
)

NOME_TAREFA = "DataIntelligenceCorporateServer"


def _comando_tarefa(executavel: str | Path) -> str:
    """Representação humana do comando; o registro real separa EXE/argumentos."""
    exe = Path(executavel).resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"Executável do servidor não encontrado: {exe}")
    return f'"{exe}" run'


def instalar_tarefa(executavel: str | Path) -> None:
    exe = Path(executavel).resolve()
    registrar_tarefa_boot_system(
        NOME_TAREFA,
        exe,
        "run",
        descricao="Data Intelligence Corporate Server",
    )


def iniciar_tarefa() -> None:
    _iniciar(NOME_TAREFA)


def remover_tarefa(*, ignorar_ausente: bool = True) -> None:
    _remover(NOME_TAREFA, ignorar_ausente=ignorar_ausente)


def consultar_tarefa() -> str:
    resultado = _consultar(NOME_TAREFA)
    return resultado or "Tarefa do Servidor Corporativo não instalada."


def executavel_atual() -> Path:
    if not getattr(sys, "frozen", False):
        raise RuntimeError("A instalação automática exige o executável gerado pelo build.")
    return Path(sys.executable)
