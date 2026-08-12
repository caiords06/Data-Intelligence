"""API HTTP mínima, segura e sem dependência externa para o servidor central."""

from __future__ import annotations

import json
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from auth.banco import buscar_usuario_por_id, conectar, inicializar_banco
from enterprise.banco import inicializar_enterprise
from enterprise.tecnologia import registrar_snapshot_agente
from servidor import VERSAO_SERVIDOR
from servidor.seguranca import autenticar_agente

MAX_JSON = 2 * 1024 * 1024


class ReceptorCentral(BaseHTTPRequestHandler):
    server_version = f"DataIntelligence/{VERSAO_SERVIDOR}"

    def log_message(self, formato, *args):
        # Evita registrar payloads, tokens ou cabeçalhos sensíveis.
        super().log_message("%s", formato % args)

    def _json(self, status: int, dados: dict):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo_json(self) -> tuple[bytes, dict]:
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Content-Length inválido.") from None
        if tamanho <= 0 or tamanho > MAX_JSON:
            raise ValueError("Corpo ausente ou maior que 2 MB.")
        corpo = self.rfile.read(tamanho)
        try:
            dados = json.loads(corpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("JSON inválido.") from None
        if not isinstance(dados, dict):
            raise ValueError("O corpo precisa ser um objeto JSON.")
        return corpo, dados

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "operacional", "versao": VERSAO_SERVIDOR})
            return
        self._json(404, {"erro": "Rota não encontrada."})

    def do_POST(self):
        if self.path != "/api/v1/ti/agentes/heartbeat":
            self._json(404, {"erro": "Rota não encontrada."})
            return
        try:
            corpo, payload = self._corpo_json()
            no = autenticar_agente(
                self.headers.get("X-Agent-ID", ""),
                self.headers.get("X-Agent-Timestamp", ""),
                self.headers.get("X-Agent-Nonce", ""),
                self.headers.get("X-Agent-Signature", ""),
                corpo,
            )
            if str(payload.get("agent_id") or "") != str(no["identificador"]):
                raise PermissionError("O identificador do payload não corresponde ao agente autenticado.")
            usuario = buscar_usuario_por_id(int(no["criado_por"]))
            if usuario is None or not bool(usuario["ativo"]):
                raise PermissionError("Responsável pelo agente não está ativo.")
            ator = {
                "id": int(usuario["id"]), "nome": usuario["nome"],
                "perfil": usuario["perfil"], "perfil_acesso": usuario["perfil_acesso"],
                "ativo": bool(usuario["ativo"]),
                "sessao_epoch": int(usuario["sessao_epoch"] or 0),
                "_empresa_id": int(no["empresa_id"]),
                "_filial_id": int(no["filial_id"]) if no["filial_id"] is not None else None,
            }
            ativo_id = registrar_snapshot_agente(payload, ator)
            with conectar() as conexao:
                conexao.execute(
                    "UPDATE nos_plataforma SET endereco_ip=?,ultimo_heartbeat=CURRENT_TIMESTAMP,"
                    "status='Ativo',atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                    (self.client_address[0], int(no["id"])),
                )
            self._json(202, {"aceito": True, "ativo_id": ativo_id})
        except PermissionError as erro:
            self._json(401, {"erro": str(erro)})
        except (ValueError, FileNotFoundError) as erro:
            self._json(400, {"erro": str(erro)})
        except Exception:
            self._json(500, {"erro": "Falha interna ao processar o heartbeat."})


def executar_servidor(
    host="127.0.0.1", porta=8765, *, certificado=None, chave_privada=None
):
    inicializar_banco()
    inicializar_enterprise()
    servidor = ThreadingHTTPServer((host, int(porta)), ReceptorCentral)
    if certificado or chave_privada:
        if not (certificado and chave_privada):
            raise ValueError("Informe certificado e chave privada em conjunto.")
        contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto.minimum_version = ssl.TLSVersion.TLSv1_2
        contexto.load_cert_chain(certificado, chave_privada)
        servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
    return servidor
