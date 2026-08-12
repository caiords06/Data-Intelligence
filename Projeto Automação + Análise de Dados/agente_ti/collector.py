"""Coleta local e minimizada de inventário e saúde do equipamento.

Não há descoberta de rede, captura de tela, leitura de documentos, histórico de
navegação ou inventário de conteúdo do usuário. O agente observa somente a
máquina em que está instalado.
"""

from __future__ import annotations

from datetime import datetime, timezone
import getpass
import os
import platform
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
from typing import Any
from uuid import getnode

from agente_ti import SCHEMA_PAYLOAD, VERSAO_AGENTE
from agente_ti.config import AgentConfig

try:
    import psutil  # type: ignore
except ImportError:  # cobertura pelo fallback nos ambientes mínimos
    psutil = None


GIB = 1024 ** 3
LIMITE_SAIDA_COMANDO = 256


def _arredondar(valor: float | int | None, casas=2):
    return round(float(valor), casas) if valor is not None else None


def _mac_texto(numero: int) -> str:
    return ":".join(f"{(numero >> deslocamento) & 0xff:02X}" for deslocamento in range(40, -1, -8))


def _raiz_disco() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("SystemDrive", "C:") + "\\")
    return Path("/")


def _enderecos_rede() -> tuple[list[str], list[str]]:
    ips: set[str] = set()
    macs: set[str] = set()
    if psutil is not None:
        for enderecos in psutil.net_if_addrs().values():
            for endereco in enderecos:
                if endereco.family == socket.AF_INET and not endereco.address.startswith("127."):
                    ips.add(endereco.address)
                elif endereco.family == socket.AF_INET6:
                    valor = endereco.address.split("%", 1)[0]
                    if valor != "::1" and not valor.lower().startswith("fe80:"):
                        ips.add(valor)
                elif endereco.family == getattr(psutil, "AF_LINK", object()):
                    texto = str(endereco.address or "").upper().replace("-", ":")
                    if texto and texto != "00:00:00:00:00:00":
                        macs.add(texto)
    else:
        try:
            for resultado in socket.getaddrinfo(socket.gethostname(), None):
                endereco = resultado[4][0].split("%", 1)[0]
                if endereco not in {"127.0.0.1", "::1"} and not endereco.lower().startswith("fe80:"):
                    ips.add(endereco)
        except OSError:
            pass
        macs.add(_mac_texto(getnode()))
    return sorted(ips), sorted(macs)


def _memoria_fallback() -> tuple[float | None, float | None]:
    if os.name != "nt":
        return None, None

    import ctypes

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None, None
    return status.ullTotalPhys / GIB, float(status.dwMemoryLoad)


def _uptime_fallback() -> int | None:
    if os.name != "nt":
        return None
    import ctypes
    return int(ctypes.windll.kernel32.GetTickCount64() // 1000)


def _metricas_sistema() -> dict[str, Any]:
    raiz = _raiz_disco()
    disco = shutil.disk_usage(raiz)
    if psutil is not None:
        memoria = psutil.virtual_memory()
        cpu_percentual = psutil.cpu_percent(interval=0.2)
        memoria_total = memoria.total / GIB
        memoria_percentual = memoria.percent
        uptime = max(0, int(time.time() - psutil.boot_time()))
    else:
        memoria_total, memoria_percentual = _memoria_fallback()
        cpu_percentual = None
        uptime = _uptime_fallback()
    return {
        "cpu_percentual": _arredondar(cpu_percentual),
        "memoria_percentual": _arredondar(memoria_percentual),
        "disco_percentual": _arredondar((disco.used / disco.total) * 100 if disco.total else 0),
        "espaco_livre_gb": _arredondar(disco.free / GIB),
        "uptime_segundos": uptime,
        "latencia_ms": None,
        "memoria_total_gb": _arredondar(memoria_total),
        "armazenamento_total_gb": _arredondar(disco.total / GIB),
    }


def _executavel_anydesk(configurado: str | None = None) -> Path | None:
    candidatos: list[Path] = []
    if configurado:
        candidatos.append(Path(configurado))
    local = os.environ.get("LOCALAPPDATA")
    program_files = os.environ.get("ProgramFiles")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    for base in (program_files_x86, program_files, local):
        if base:
            candidatos.append(Path(base) / "AnyDesk" / "AnyDesk.exe")
    localizado = shutil.which("AnyDesk.exe") or shutil.which("anydesk")
    if localizado:
        candidatos.append(Path(localizado))
    return next((caminho for caminho in candidatos if caminho.is_file()), None)


def _comando_curto(executavel: Path, parametro: str) -> str | None:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        resultado = subprocess.run(
            [str(executavel), parametro],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
            shell=False,
            creationflags=flags,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    texto = (resultado.stdout or "").strip()[:LIMITE_SAIDA_COMANDO]
    return texto if resultado.returncode == 0 and texto else None


def _identidade_remota(config: AgentConfig) -> dict[str, Any]:
    provedor = config.provedor_remoto or None
    resultado: dict[str, Any] = {
        "provedor": provedor,
        "instalado": False,
        "identificador": None,
        "alias": None,
        "status": None,
        "versao": None,
    }
    if provedor != "AnyDesk":
        if config.executavel_remoto:
            resultado["instalado"] = Path(config.executavel_remoto).is_file()
        return resultado
    executavel = _executavel_anydesk(config.executavel_remoto)
    if executavel is None:
        return resultado
    resultado["instalado"] = True
    identificador = _comando_curto(executavel, "--get-id")
    alias = _comando_curto(executavel, "--get-alias")
    padrao = re.compile(r"^[A-Za-z0-9@._ -]{3,120}$")
    resultado["identificador"] = identificador if identificador and padrao.fullmatch(identificador) else None
    resultado["alias"] = alias if alias and padrao.fullmatch(alias) else None
    resultado["status"] = _comando_curto(executavel, "--get-status")
    resultado["versao"] = _comando_curto(executavel, "--version")
    return resultado


def coletar_payload(config: AgentConfig) -> dict[str, Any]:
    """Produz um heartbeat autocontido, serializável e sem dados pessoais amplos."""
    config.validar()
    ips, macs = _enderecos_rede()
    metricas = _metricas_sistema()
    return {
        "schema": SCHEMA_PAYLOAD,
        "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent_id": config.agent_id,
        "agente_versao": VERSAO_AGENTE,
        "patrimonio": config.patrimonio,
        "dispositivo": {
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "sistema_operacional": platform.system(),
            "versao_sistema": platform.version(),
            "release_sistema": platform.release(),
            "arquitetura": platform.machine(),
            "processador": platform.processor() or None,
            "executado_como": getpass.getuser(),
            "enderecos_ip": ips,
            "enderecos_mac": macs,
            "endereco_ip": ips[0] if ips else None,
            "endereco_mac": macs[0] if macs else None,
            "memoria_total_gb": metricas.pop("memoria_total_gb"),
            "armazenamento_total_gb": metricas.pop("armazenamento_total_gb"),
        },
        "metricas": metricas,
        "acesso_remoto": _identidade_remota(config),
    }
