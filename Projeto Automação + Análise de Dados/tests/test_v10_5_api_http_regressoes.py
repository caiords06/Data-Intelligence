from __future__ import annotations

from email.message import Message
from http.server import ThreadingHTTPServer
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import patch

import enterprise.servidor_cliente as cliente
from servidor_corporativo.app import CorporateRequestHandler


class APIHttpV105RegressoesTests(unittest.TestCase):
    def _servidor(self, *, cors_origins=()):
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), CorporateRequestHandler)
        servidor.config = SimpleNamespace(cors_origins=tuple(cors_origins), max_upload_mb=10)
        servidor.observabilidade = None
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()

        def encerrar():
            servidor.shutdown()
            thread.join(2)
            servidor.server_close()

        self.addCleanup(encerrar)
        host, porta = servidor.server_address[:2]
        return f"http://{host}:{porta}"

    def _request(self, url, *, method="GET", headers=None):
        req = urllib.request.Request(url, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw = resp.read()
                payload = json.loads(raw.decode("utf-8")) if raw else None
                return resp.status, payload, resp.headers
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            payload = json.loads(raw.decode("utf-8")) if raw else None
            return exc.code, payload, exc.headers

    def test_bearer_ausente_ou_expirado_retorna_401_padronizado(self):
        base = self._servidor()
        status, payload, _ = self._request(base + "/api/v1/crm/leads")
        self.assertEqual(status, 401)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "unauthorized")
        self.assertTrue(payload["request_id"])

    def test_bearer_expirado_com_header_tambem_retorna_401(self):
        base = self._servidor()
        # obter_sessao(None/token desconhecido) representa token expirado/revogado.
        status, payload, _ = self._request(
            base + "/api/v1/crm/leads", headers={"Authorization": "Bearer token-expirado"}
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "unauthorized")

    def test_usuario_autenticado_sem_permissao_retorna_403(self):
        base = self._servidor()
        sessao = SimpleNamespace(ator=lambda: {"id": 1})
        with patch("servidor_corporativo.app.obter_sessao", return_value=sessao), patch(
            "servidor_corporativo.app.dispatch_api_get", side_effect=PermissionError("Sem permissão")
        ):
            status, payload, _ = self._request(
                base + "/api/v1/crm/leads", headers={"Authorization": "Bearer token-valido"}
            )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "forbidden")
        self.assertEqual(payload["error"]["message"], "Sem permissão")

    def test_cors_preflight_permite_apenas_origem_configurada(self):
        base = self._servidor(cors_origins=("https://app.empresa.local",))
        status, _, headers = self._request(
            base + "/api/v1/crm/leads",
            method="OPTIONS",
            headers={"Origin": "https://app.empresa.local", "Access-Control-Request-Method": "GET"},
        )
        self.assertEqual(status, 204)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://app.empresa.local")
        self.assertIn("GET", headers.get("Access-Control-Allow-Methods", ""))
        status, payload, headers = self._request(
            base + "/api/v1/crm/leads",
            method="OPTIONS",
            headers={"Origin": "https://hostil.example"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "cors_forbidden")
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))

    def test_500_de_endpoint_publico_mantem_envelope_api(self):
        base = self._servidor()
        sessao = SimpleNamespace(ator=lambda: {"id": 1})
        with patch("servidor_corporativo.app.obter_sessao", return_value=sessao), patch(
            "servidor_corporativo.app.dispatch_api_get", side_effect=RuntimeError("falha simulada")
        ):
            status, payload, _ = self._request(
                base + "/api/v1/crm/leads", headers={"Authorization": "Bearer token-valido"}
            )
        self.assertEqual(status, 500)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "internal_error")
        self.assertEqual(payload["error"]["message"], "Falha interna do servidor.")
        self.assertTrue(payload["request_id"])

    def test_cliente_entende_novo_envelope_e_descarta_token_em_401(self):
        headers = Message(); headers["Content-Type"] = "application/json"; headers["X-Request-ID"] = "req-401"
        corpo = io.BytesIO(json.dumps({
            "ok": False,
            "error": {"code": "unauthorized", "message": "Sessão expirada"},
            "request_id": "req-401",
        }).encode("utf-8"))
        erro = urllib.error.HTTPError("https://servidor/api/v1/crm/leads", 401, "Unauthorized", headers, corpo)
        anterior_token, anterior_bootstrap = cliente._TOKEN, dict(cliente._BOOTSTRAP_MEMORIA)
        self.addCleanup(setattr, cliente, "_TOKEN", anterior_token)
        self.addCleanup(setattr, cliente, "_BOOTSTRAP_MEMORIA", anterior_bootstrap)
        cliente._TOKEN = "expirado"
        cliente._BOOTSTRAP_MEMORIA = {"usuario": {"id": 1}}
        cfg = SimpleNamespace(servidor_url="https://servidor", permitir_http_privado=False)
        with patch.object(cliente, "_cfg", return_value=cfg), patch.object(cliente.urllib.request, "urlopen", side_effect=erro):
            with self.assertRaisesRegex(PermissionError, r"Sessão expirada.*req-401"):
                cliente._request("/api/v1/crm/leads")
        self.assertIsNone(cliente._TOKEN)
        self.assertEqual(cliente._BOOTSTRAP_MEMORIA, {})

    def test_cliente_converte_timeout_em_erro_operacional_exibivel(self):
        anterior_token = cliente._TOKEN
        self.addCleanup(setattr, cliente, "_TOKEN", anterior_token)
        cliente._TOKEN = "token"
        cfg = SimpleNamespace(servidor_url="https://servidor", permitir_http_privado=False)
        with patch.object(cliente, "_cfg", return_value=cfg), patch.object(
            cliente.urllib.request, "urlopen", side_effect=TimeoutError("timed out")
        ) as abrir:
            with self.assertRaisesRegex(ValueError, "Servidor corporativo indisponível"):
                cliente._request("/api/v1/crm/leads", timeout=0.25)
        self.assertEqual(abrir.call_args.kwargs["timeout"], 0.25)

    def test_cliente_preserva_mensagem_legada_de_erro(self):
        headers = Message(); headers["Content-Type"] = "application/json"
        corpo = io.BytesIO(json.dumps({"erro": "Permissão negada"}).encode("utf-8"))
        erro = urllib.error.HTTPError("https://servidor/api/v1/rpc", 403, "Forbidden", headers, corpo)
        anterior_token = cliente._TOKEN
        self.addCleanup(setattr, cliente, "_TOKEN", anterior_token)
        cliente._TOKEN = "token"
        cfg = SimpleNamespace(servidor_url="https://servidor", permitir_http_privado=False)
        with patch.object(cliente, "_cfg", return_value=cfg), patch.object(cliente.urllib.request, "urlopen", side_effect=erro):
            with self.assertRaisesRegex(PermissionError, "Permissão negada"):
                cliente._request("/api/v1/rpc")


if __name__ == "__main__":
    unittest.main()
