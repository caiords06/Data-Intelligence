"""Registro confiável de tarefas de inicialização no Windows.

O caminho do executável e os argumentos são entregues ao PowerShell por
variáveis de ambiente, não interpolados em uma linha ``cmd.exe``/``schtasks``.
Isso evita a quebra de caminhos sob ``C:\\Program Files\\...`` observada no
Setup V10.1.0 durante a homologação; V10.1.1 elimina esse caminho frágil.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import subprocess


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


def _powershell(script: str, *, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    exigir_windows()
    ambiente = os.environ.copy()
    if env_extra:
        ambiente.update({str(k): str(v) for k, v in env_extra.items()})
    return subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-Command", script,
        ],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
        env=ambiente,
    )


def registrar_tarefa_boot_system(
    nome: str,
    executavel: str | Path,
    argumentos: str,
    *,
    descricao: str = "Data Intelligence",
) -> None:
    exigir_windows()
    if not eh_administrador():
        raise PermissionError("Execute a instalação como administrador.")
    exe = Path(executavel).resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"Executável não encontrado: {exe}")
    nome = str(nome or "").strip()
    if not nome:
        raise ValueError("Nome da tarefa vazio.")
    script = r"""
$ErrorActionPreference = 'Stop'
$action = New-ScheduledTaskAction -Execute $env:DI_TASK_EXE -Argument $env:DI_TASK_ARGS
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $env:DI_TASK_NAME -Action $action -Trigger $trigger -Principal $principal -Description $env:DI_TASK_DESCRIPTION -Force | Out-Null
"""
    _powershell(
        script,
        env_extra={
            "DI_TASK_EXE": str(exe),
            "DI_TASK_ARGS": str(argumentos or ""),
            "DI_TASK_NAME": nome,
            "DI_TASK_DESCRIPTION": str(descricao or "Data Intelligence"),
        },
    )


def iniciar_tarefa(nome: str) -> None:
    exigir_windows()
    subprocess.run(
        ["schtasks.exe", "/Run", "/TN", str(nome)],
        check=True, capture_output=True, text=True, shell=False,
    )


def remover_tarefa(nome: str, *, ignorar_ausente: bool = True) -> None:
    exigir_windows()
    resultado = subprocess.run(
        ["schtasks.exe", "/Delete", "/TN", str(nome), "/F"],
        check=False, capture_output=True, text=True, shell=False,
    )
    if resultado.returncode != 0 and not ignorar_ausente:
        raise RuntimeError(
            resultado.stderr.strip() or resultado.stdout.strip() or "Falha ao remover tarefa."
        )


def consultar_tarefa(nome: str) -> str:
    exigir_windows()
    resultado = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", str(nome), "/FO", "LIST", "/V"],
        check=False, capture_output=True, text=True, shell=False,
    )
    if resultado.returncode != 0:
        return ""
    return resultado.stdout.strip()
