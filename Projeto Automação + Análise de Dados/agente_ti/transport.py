"""Transporte HTTPS autenticado para o futuro coletor central de Tecnologia."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPHandler,
    HTTPSHandler,
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from agente_ti import VERSAO_AGENTE
from agente_ti.config import AgentConfig


MAX_RESPOSTA_BYTES = 64 * 1024


class TransportError(RuntimeError):
    """Erro normalizado de comunicação, sem vazar a credencial."""


@dataclass(frozen=True, slots=True)
class TransportResult:
    status: int
    corpo: dict[str, Any]
    latencia_ms: float


class _SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Redirecionamento recusado", headers, fp)


def serializar_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def assinatura_requisicao(
    token: str,
    corpo: bytes,
    timestamp: str,
    nonce: str,
) -> str:
    resumo = hashlib.sha256(corpo).hexdigest()
    mensagem = f"{timestamp}\n{nonce}\n{resumo}".encode("utf-8")
    chave = hashlib.sha256(token.encode("utf-8")).digest()
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()


def _opener(config: AgentConfig):
    if config.verificar_tls:
        contexto = ssl.create_default_context(cafile=config.ca_bundle)
    else:
        contexto = ssl._create_unverified_context()  # permitido somente em localhost pela configuração
    return build_opener(
        _SemRedirecionamento(),
        HTTPHandler(),
        HTTPSHandler(context=contexto),
    )


def enviar_heartbeat(
    config: AgentConfig,
    token: str,
    payload: dict[str, Any],
) -> TransportResult:
    config.validar()
    if len(str(token or "")) < 24:
        raise ValueError("Token de autenticação do agente inválido.")
    corpo = serializar_payload(payload)
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    assinatura = assinatura_requisicao(token, corpo, timestamp, nonce)
    requisicao = Request(
        config.endpoint_heartbeat,
        data=corpo,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": f"DataIntelligence-TIAgent/{VERSAO_AGENTE}",
            "X-Agent-ID": config.agent_id,
            "X-Agent-Timestamp": timestamp,
            "X-Agent-Nonce": nonce,
            "X-Agent-Signature": assinatura,
        },
    )
    inicio = time.monotonic()
    try:
        with _opener(config).open(requisicao, timeout=config.timeout_segundos) as resposta:
            bruto = resposta.read(MAX_RESPOSTA_BYTES + 1)
            if len(bruto) > MAX_RESPOSTA_BYTES:
                raise TransportError("A resposta do servidor excedeu o limite permitido.")
            status = int(getattr(resposta, "status", resposta.getcode()))
    except HTTPError as erro:
        detalhe = ""
        try:
            detalhe = erro.read(2048).decode("utf-8", errors="replace")
        except OSError:
            pass
        raise TransportError(f"Servidor recusou o heartbeat (HTTP {erro.code}). {detalhe}".strip()) from None
    except (URLError, TimeoutError, OSError) as erro:
        raise TransportError(f"Não foi possível alcançar o servidor: {erro}") from None
    latencia = (time.monotonic() - inicio) * 1000
    if not 200 <= status < 300:
        raise TransportError(f"Resposta inesperada do servidor: HTTP {status}.")
    if not bruto:
        resposta_json: dict[str, Any] = {}
    else:
        try:
            decodificado = json.loads(bruto.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise TransportError("O servidor retornou uma resposta JSON inválida.") from None
        if not isinstance(decodificado, dict):
            raise TransportError("O servidor retornou um formato de resposta inválido.")
        resposta_json = decodificado
    return TransportResult(status=status, corpo=resposta_json, latencia_ms=round(latencia, 2))
