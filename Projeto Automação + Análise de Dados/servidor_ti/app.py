"""Servidor HTTP(S) mínimo e empacotável para heartbeats TI."""

from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import ssl
import time
from typing import Any

from auth.banco import conectar
from agente_ti import SCHEMA_PAYLOAD
from enterprise.tecnologia import registrar_snapshot_agente
from servidor_ti import VERSAO_SERVIDOR_TI
from servidor_ti.config import ServidorTIConfig
from servidor_ti.security import AgentAuthError, autenticar
from core.observabilidade import RegistroSaude, novo_request_id

MAX_BODY = 128 * 1024


def _json_bytes(dados: dict[str, Any]) -> bytes:
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _ator_servico(agente) -> dict:
    return {
        "id": agente.criado_por,
        "nome": "Agente TI",
        "perfil": "admin",
        "perfil_acesso": "administrador",
        "ativo": True,
        "_empresa_id": agente.empresa_id,
        "_filial_id": agente.filial_id,
    }


def processar_heartbeat(headers, corpo: bytes, endereco_remoto: str) -> dict[str, Any]:
    agente = autenticar(headers, corpo)
    try:
        payload = json.loads(corpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Payload JSON inválido.") from None
    if not isinstance(payload, dict):
        raise ValueError("O payload do agente precisa ser um objeto JSON.")
    if payload.get("schema") != SCHEMA_PAYLOAD:
        raise ValueError("Versão do contrato do agente não suportada.")
    if str(payload.get("agent_id") or "") != agente.agent_id:
        raise AgentAuthError("Agent ID do payload não corresponde à credencial.")
    if str(payload.get("patrimonio") or "") != agente.patrimonio:
        raise AgentAuthError("Patrimônio do payload não corresponde à credencial.")

    ator = _ator_servico(agente)
    ativo_id = registrar_snapshot_agente(payload, ator)
    if int(ativo_id) != agente.ativo_id:
        raise AgentAuthError("A credencial não corresponde ao ativo informado.")
    versao = str(payload.get("agente_versao") or "")[:40] or None
    with conectar() as conexao:
        conexao.execute(
            """UPDATE ti_agentes SET status='Online',ultimo_ip=?,ultima_versao=?,
               ultimo_heartbeat=CURRENT_TIMESTAMP,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (str(endereco_remoto or "")[:45] or None, versao, agente.id),
        )
    return {
        "aceito": True,
        "ativo_id": agente.ativo_id,
        "agent_id": agente.agent_id,
        "servidor_versao": VERSAO_SERVIDOR_TI,
        "recebido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


class TIRequestHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self._inicio_requisicao = time.perf_counter()
        self._request_id = novo_request_id()

    server_version = "DataIntelligenceTIServer/" + VERSAO_SERVIDOR_TI
    sys_version = ""

    def _responder(self, status: int, dados: dict[str, Any]):
        corpo = _json_bytes(dados)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Request-ID", self._request_id)
        observabilidade = getattr(self.server, "observabilidade", None)
        if observabilidade is not None:
            observabilidade.registrar_requisicao(int(status), (time.perf_counter() - self._inicio_requisicao) * 1000)
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        caminho = self.path.rstrip("/")
        if caminho in {"", "/health", "/api/v1/ti/health", "/api/v1/ti/health/live"}:
            self._responder(HTTPStatus.OK, {"ok": True, "servico": "ti-agent-api", "versao": VERSAO_SERVIDOR_TI})
            return
        if caminho == "/api/v1/ti/health/ready":
            try:
                with conectar() as conexao:
                    conexao.execute("SELECT 1").fetchone()
                pronto = True
            except Exception:
                pronto = False
            status = HTTPStatus.OK if pronto else HTTPStatus.SERVICE_UNAVAILABLE
            self._responder(status, {"ok": pronto, "pronto": pronto, "servico": "ti-agent-api"})
            return
        self._responder(HTTPStatus.NOT_FOUND, {"erro": "Rota não encontrada."})

    def do_POST(self):
        if self.path.rstrip("/") != "/api/v1/ti/agentes/heartbeat":
            self._responder(HTTPStatus.NOT_FOUND, {"erro": "Rota não encontrada."})
            return
        tipo = str(self.headers.get("Content-Type", "")).lower()
        if "application/json" not in tipo:
            self._responder(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"erro": "Use application/json."})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            tamanho = -1
        if tamanho <= 0 or tamanho > MAX_BODY:
            self._responder(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"erro": "Payload vazio ou acima do limite."})
            return
        corpo = self.rfile.read(tamanho)
        try:
            resultado = processar_heartbeat(self.headers, corpo, self.client_address[0])
        except AgentAuthError:
            self._responder(HTTPStatus.UNAUTHORIZED, {"erro": "Agente não autorizado."})
            return
        except (ValueError, PermissionError) as erro:
            self._responder(HTTPStatus.UNPROCESSABLE_ENTITY, {"erro": str(erro)[:300]})
            return
        except Exception:
            logging.getLogger("data_intelligence.ti_server").exception("Falha interna ao processar heartbeat")
            self._responder(HTTPStatus.INTERNAL_SERVER_ERROR, {"erro": "Falha interna do servidor."})
            return
        self._responder(HTTPStatus.ACCEPTED, resultado)

    def log_message(self, formato, *args):
        logging.getLogger("data_intelligence.ti_server").info(
            "%s %s - %s", self.client_address[0], self.path, formato % args
        )


class TIServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.observabilidade = RegistroSaude("ti-agent-api")


def criar_servidor(config: ServidorTIConfig) -> TIServer:
    config.validar()
    servidor = TIServer((config.host, int(config.porta)), TIRequestHandler)
    if config.tls:
        contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto.minimum_version = ssl.TLSVersion.TLSv1_2
        contexto.load_cert_chain(config.certificado, config.chave_privada)
        servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
    return servidor
