"""Ciclo de execução, status e logs do agente."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import random
import signal
import threading
import time
from typing import Any

from agente_ti import VERSAO_AGENTE
from agente_ti.collector import coletar_payload
from agente_ti.config import AgentConfig
from agente_ti.transport import TransportResult, enviar_heartbeat
from core.observabilidade import configurar_logger_rotativo


LOG_NAME = "ti-agent.log"
STATUS_NAME = "status.json"
LOCK_NAME = "agent.lock"


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pid_ativo(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        import psutil  # type: ignore
        return bool(psutil.pid_exists(pid))
    except ImportError:
        pass
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def configurar_log(diretorio: str | Path) -> logging.Logger:
    pasta = Path(diretorio)
    pasta.mkdir(parents=True, exist_ok=True)
    return configurar_logger_rotativo(
        "data_intelligence.ti_agent",
        pasta / LOG_NAME,
        max_bytes=2 * 1024 * 1024,
        backups=4,
    )


def salvar_status(diretorio: str | Path, dados: dict[str, Any]) -> Path:
    destino = Path(diretorio) / STATUS_NAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporario, destino)
    return destino


def atualizar_status(diretorio: str | Path, dados: dict[str, Any]) -> Path:
    """Mescla o estado novo preservando a última telemetria útil do agente."""
    destino = Path(diretorio) / STATUS_NAME
    atual: dict[str, Any] = {}
    if destino.is_file():
        try:
            bruto = json.loads(destino.read_text(encoding="utf-8-sig"))
            if isinstance(bruto, dict):
                atual = bruto
        except (OSError, json.JSONDecodeError):
            atual = {}
    atual.update({
        "pid": os.getpid(),
        "agente_versao": VERSAO_AGENTE,
        "atualizado_em": _agora(),
    })
    atual.update(dados)
    return salvar_status(diretorio, atual)


class InstanceLock(AbstractContextManager):
    """Evita duas instâncias do agente usando criação atômica de arquivo."""

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)
        self._adquirido = False

    def __enter__(self):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        for tentativa in range(2):
            try:
                descritor = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                break
            except FileExistsError:
                try:
                    pid = int(self.caminho.read_text(encoding="ascii").strip())
                except (OSError, ValueError):
                    pid = -1
                if tentativa == 0 and not _pid_ativo(pid):
                    self.caminho.unlink(missing_ok=True)
                    continue
                raise RuntimeError("Já existe uma instância do agente em execução.") from None
        with os.fdopen(descritor, "w", encoding="ascii") as arquivo:
            arquivo.write(str(os.getpid()))
        self._adquirido = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self._adquirido:
            try:
                self.caminho.unlink()
            except FileNotFoundError:
                pass
        self._adquirido = False
        return False


def executar_uma_vez(
    config: AgentConfig,
    *,
    token: str | None = None,
    dry_run: bool = False,
) -> tuple[dict[str, Any], TransportResult | None]:
    payload = coletar_payload(config)
    if dry_run:
        return payload, None
    if not token:
        raise ValueError("Token obrigatório para enviar o heartbeat.")
    return payload, enviar_heartbeat(config, token, payload)


class AgentRuntime:
    def __init__(self, config: AgentConfig, token: str, diretorio: str | Path):
        self.config = config.validar()
        self.token = token
        self.diretorio = Path(diretorio)
        self.logger = configurar_log(self.diretorio)
        self.parar = threading.Event()
        self._falhas = 0

    def solicitar_parada(self, *_args):
        self.parar.set()

    def _instalar_sinais(self):
        for nome in ("SIGINT", "SIGTERM"):
            sinal = getattr(signal, nome, None)
            if sinal is not None:
                try:
                    signal.signal(sinal, self.solicitar_parada)
                except (ValueError, OSError):
                    pass

    def _espera(self) -> float:
        if self._falhas == 0:
            return float(self.config.intervalo_segundos)
        base = min(900, max(15, 15 * (2 ** min(self._falhas - 1, 6))))
        return float(base + random.uniform(0, min(10, base * 0.1)))

    def executar(self) -> None:
        self._instalar_sinais()
        lock = self.diretorio / LOCK_NAME
        with InstanceLock(lock):
            self.logger.info("Agente iniciado; patrimônio=%s", self.config.patrimonio)
            atualizar_status(self.diretorio, {"estado": "iniciando", "iniciado_em": _agora(), "falhas_consecutivas": 0})
            while not self.parar.is_set():
                try:
                    _payload, resposta = executar_uma_vez(self.config, token=self.token)
                    self._falhas = 0
                    atualizar_status(self.diretorio, {
                        "estado": "online",
                        "ultimo_envio": _agora(),
                        "http_status": resposta.status if resposta else None,
                        "latencia_ms": resposta.latencia_ms if resposta else None,
                        "falhas_consecutivas": 0,
                    })
                    self.logger.info(
                        "Heartbeat confirmado; http=%s latencia_ms=%s",
                        resposta.status if resposta else "-",
                        resposta.latencia_ms if resposta else "-",
                    )
                except Exception as erro:  # o agente precisa continuar após falhas transitórias
                    self._falhas += 1
                    atualizar_status(self.diretorio, {
                        "estado": "degradado",
                        "ultima_falha": _agora(),
                        "erro": str(erro)[:500],
                        "falhas_consecutivas": self._falhas,
                    })
                    self.logger.warning("Falha no heartbeat: %s", str(erro)[:500])
                self.parar.wait(self._espera())
            atualizar_status(self.diretorio, {"estado": "parado", "encerrado_em": _agora()})
            self.logger.info("Agente encerrado")
