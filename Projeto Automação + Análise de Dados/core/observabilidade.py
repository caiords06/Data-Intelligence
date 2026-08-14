"""Observabilidade operacional leve e sem dependências externas.

Fornece métricas em memória, logs JSON Lines e IDs de correlação para os
servidores/serviços da plataforma. Não substitui uma stack externa de
monitoramento; cria uma base estável para exportação futura.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import tempfile
import threading
import time
from typing import Any
from uuid import uuid4


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def novo_request_id() -> str:
    return uuid4().hex[:16]


class JsonLineFormatter(logging.Formatter):
    """Formata um evento por linha, adequado a coleta por agentes externos."""

    CAMPOS_EXTRA = (
        "evento", "request_id", "metodo", "caminho", "status",
        "duracao_ms", "bytes", "componente", "empresa_id", "filial_id",
        "erro_operacional", "modulo", "funcao",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        for campo in self.CAMPOS_EXTRA:
            valor = getattr(record, campo, None)
            if valor is not None:
                payload[campo] = valor
        if record.exc_info:
            payload["excecao"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def configurar_logger_rotativo(
    nome: str,
    destino: str | Path,
    *,
    max_bytes: int = 4 * 1024 * 1024,
    backups: int = 5,
    nivel: int = logging.INFO,
) -> logging.Logger:
    """Configura logger idempotente sem impedir a inicialização do processo."""
    logger = logging.getLogger(nome)
    logger.setLevel(nivel)
    logger.propagate = False
    preferido = Path(destino).expanduser().resolve()
    candidatos = (
        preferido,
        Path(tempfile.gettempdir()).resolve() / "DataIntelligence" / "logs" / preferido.name,
    )
    caminho = None
    handler_novo = None
    for candidato in candidatos:
        try:
            candidato.parent.mkdir(parents=True, exist_ok=True)
            handler_novo = RotatingFileHandler(
                str(candidato), maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
            )
            caminho = candidato
            break
        except OSError:
            continue
    if caminho is None or handler_novo is None:
        if not any(getattr(h, "_di_fallback_stderr", False) for h in logger.handlers):
            handler_novo = logging.StreamHandler()
            handler_novo._di_fallback_stderr = True
            handler_novo.setFormatter(JsonLineFormatter())
            logger.addHandler(handler_novo)
        logger.arquivo_log = None
        return logger
    alvo = str(caminho)
    existente = next(
        (h for h in logger.handlers if isinstance(h, RotatingFileHandler) and h.baseFilename == alvo),
        None,
    )
    if existente is None:
        handler_novo.setFormatter(JsonLineFormatter())
        logger.addHandler(handler_novo)
    else:
        handler_novo.close()
    logger.arquivo_log = caminho
    return logger


class RegistroSaude:
    """Métricas thread-safe de um processo HTTP/serviço."""

    def __init__(self, componente: str):
        self.componente = str(componente)
        self._inicio_monotonic = time.monotonic()
        self._inicio_iso = agora_iso()
        self._lock = threading.RLock()
        self._requisicoes = 0
        self._erros = 0
        self._latencia_total_ms = 0.0
        self._latencia_max_ms = 0.0
        self._status = Counter()
        self._ultima_requisicao_em: str | None = None
        self._ultimo_erro_em: str | None = None

    def registrar_requisicao(self, status: int, duracao_ms: float) -> None:
        codigo = int(status)
        latencia = max(0.0, float(duracao_ms))
        with self._lock:
            self._requisicoes += 1
            self._status[str(codigo)] += 1
            self._latencia_total_ms += latencia
            self._latencia_max_ms = max(self._latencia_max_ms, latencia)
            self._ultima_requisicao_em = agora_iso()
            if codigo >= 500:
                self._erros += 1
                self._ultimo_erro_em = self._ultima_requisicao_em

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            media = self._latencia_total_ms / self._requisicoes if self._requisicoes else 0.0
            return {
                "componente": self.componente,
                "iniciado_em": self._inicio_iso,
                "uptime_segundos": round(max(0.0, time.monotonic() - self._inicio_monotonic), 3),
                "requisicoes": self._requisicoes,
                "erros_5xx": self._erros,
                "latencia_media_ms": round(media, 3),
                "latencia_max_ms": round(self._latencia_max_ms, 3),
                "status_http": dict(self._status),
                "ultima_requisicao_em": self._ultima_requisicao_em,
                "ultimo_erro_em": self._ultimo_erro_em,
            }

    def prometheus(self, extras: dict[str, float | int] | None = None) -> str:
        """Exporta o estado em formato Prometheus sem dependência adicional."""
        snap = self.snapshot()
        componente = self.componente.replace("\\", "\\\\").replace('"', '\\"')
        rotulo = f'componente="{componente}"'
        linhas = [
            "# HELP data_intelligence_uptime_seconds Tempo ativo do processo.",
            "# TYPE data_intelligence_uptime_seconds gauge",
            f"data_intelligence_uptime_seconds{{{rotulo}}} {snap['uptime_segundos']}",
            "# HELP data_intelligence_http_requests_total Requisições HTTP processadas.",
            "# TYPE data_intelligence_http_requests_total counter",
            f"data_intelligence_http_requests_total{{{rotulo}}} {snap['requisicoes']}",
            "# HELP data_intelligence_http_errors_total Respostas HTTP 5xx.",
            "# TYPE data_intelligence_http_errors_total counter",
            f"data_intelligence_http_errors_total{{{rotulo}}} {snap['erros_5xx']}",
            "# TYPE data_intelligence_http_latency_average_ms gauge",
            f"data_intelligence_http_latency_average_ms{{{rotulo}}} {snap['latencia_media_ms']}",
            "# TYPE data_intelligence_http_latency_max_ms gauge",
            f"data_intelligence_http_latency_max_ms{{{rotulo}}} {snap['latencia_max_ms']}",
        ]
        for status, quantidade in sorted(snap["status_http"].items()):
            linhas.append(f'data_intelligence_http_status_total{{{rotulo},status="{status}"}} {quantidade}')
        for nome, valor in sorted((extras or {}).items()):
            seguro = "".join(c if c.isalnum() or c == "_" else "_" for c in str(nome).lower())
            linhas.append(f"data_intelligence_{seguro}{{{rotulo}}} {float(valor)}")
        return "\n".join(linhas) + "\n"
