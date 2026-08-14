"""Regressões de ciclo de vida e observabilidade da V9.9."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import io
import json
import logging
from pathlib import Path
import tempfile
import time
import unittest
from urllib.request import urlopen

from agente_ti.runtime import atualizar_status
from core.ciclo_vida import encerrar_servidor, iniciar_servidor_em_thread
from core.observabilidade import JsonLineFormatter, RegistroSaude
from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA
from servidor_corporativo.app import CorporateRequestHandler, CorporateServer
from servidor_corporativo.config import ConfigServidor
from servidor_ti.app import TIRequestHandler, TIServer

RAIZ = Path(__file__).resolve().parents[1]


class RobustezOperacionalV99Tests(unittest.TestCase):
    def test_versao_canonica(self):
        self.assertEqual(VERSAO_PLATAFORMA, "11.1.0")
        self.assertEqual(VERSAO_INTERFACE, "V11.1.0")

    def test_registro_saude_contabiliza_status_e_latencia(self):
        registro = RegistroSaude("teste")
        registro.registrar_requisicao(200, 10.5)
        registro.registrar_requisicao(503, 25.0)
        dados = registro.snapshot()
        self.assertEqual(dados["requisicoes"], 2)
        self.assertEqual(dados["erros_5xx"], 1)
        self.assertEqual(dados["status_http"], {"200": 1, "503": 1})
        self.assertGreaterEqual(dados["latencia_max_ms"], 25.0)
        self.assertIn("uptime_segundos", dados)

    def test_formatter_json_lines_e_parseavel(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonLineFormatter())
        logger = logging.getLogger("teste.v99.json")
        logger.handlers[:] = [handler]
        logger.propagate = False
        logger.setLevel(logging.INFO)
        logger.info("evento operacional", extra={"evento": "teste", "request_id": "abc123"})
        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["mensagem"], "evento operacional")
        self.assertEqual(payload["evento"], "teste")
        self.assertEqual(payload["request_id"], "abc123")

    def test_ciclo_vida_encerra_thread_http(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(204); self.end_headers()
            def log_message(self, *_args):
                return
        servidor = TIServer(("127.0.0.1", 0), Handler)
        thread = iniciar_servidor_em_thread(servidor, nome="v99-lifecycle-test")
        try:
            with urlopen(f"http://127.0.0.1:{servidor.server_address[1]}/", timeout=2) as resposta:
                self.assertEqual(resposta.status, 204)
        finally:
            concluido = encerrar_servidor(servidor, thread, timeout=2)
        self.assertTrue(concluido)
        self.assertFalse(thread.is_alive())

    def test_health_ti_adiciona_request_id_e_metricas(self):
        servidor = TIServer(("127.0.0.1", 0), TIRequestHandler)
        thread = iniciar_servidor_em_thread(servidor, nome="v99-ti-health")
        try:
            with urlopen(f"http://127.0.0.1:{servidor.server_address[1]}/api/v1/ti/health/live", timeout=2) as resposta:
                corpo = json.loads(resposta.read().decode("utf-8"))
                request_id = resposta.headers.get("X-Request-ID")
            self.assertTrue(corpo["ok"])
            self.assertTrue(request_id)
            self.assertEqual(servidor.observabilidade.snapshot()["requisicoes"], 1)
        finally:
            encerrar_servidor(servidor, thread, timeout=2)

    def test_health_corporativo_e_monitor_encerram(self):
        cfg = ConfigServidor(host="127.0.0.1", porta=8770, ambiente="desenvolvimento")
        servidor = CorporateServer(("127.0.0.1", 0), CorporateRequestHandler, cfg)
        monitor = servidor._monitor_thread
        thread = iniciar_servidor_em_thread(servidor, nome="v99-corporate-health")
        try:
            with urlopen(f"http://127.0.0.1:{servidor.server_address[1]}/api/v1/health/live", timeout=2) as resposta:
                corpo = json.loads(resposta.read().decode("utf-8"))
                self.assertTrue(resposta.headers.get("X-Request-ID"))
            self.assertTrue(corpo["ok"])
        finally:
            encerrar_servidor(servidor, thread, timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertFalse(monitor.is_alive())

    def test_status_agente_e_incremental(self):
        with tempfile.TemporaryDirectory() as tmp:
            atualizar_status(tmp, {"estado": "online", "ultimo_envio": "2026-08-12T12:00:00+00:00", "falhas_consecutivas": 0})
            atualizar_status(tmp, {"estado": "degradado", "erro": "rede", "falhas_consecutivas": 1})
            dados = json.loads((Path(tmp) / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(dados["estado"], "degradado")
            self.assertEqual(dados["ultimo_envio"], "2026-08-12T12:00:00+00:00")
            self.assertEqual(dados["falhas_consecutivas"], 1)
            self.assertGreater(int(dados["pid"]), 0)
            self.assertTrue(dados["agente_versao"])

    def test_runner_mata_arvore_de_processos(self):
        texto = (RAIZ / "scripts" / "executar_grupo_testes.py").read_text(encoding="utf-8")
        self.assertIn("start_new_session", texto)
        self.assertIn("os.killpg", texto)
        self.assertIn("taskkill", texto)
        self.assertIn("_encerrar_arvore", texto)

    def test_release_exige_nucleo_operacional_v99(self):
        empacotador = (RAIZ / "scripts" / "empacotar_fonte_limpa.py").read_text(encoding="utf-8")
        workflow = (RAIZ / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
        for item in ("core/ciclo_vida.py", "core/observabilidade.py", "README_V9_9_ROBUSTEZ_OPERACIONAL.md"):
            self.assertIn(item, empacotador)
        self.assertIn("Qualidade V11", workflow)
        self.assertIn("DataIntelligence-Source-V11.1.0", workflow)


if __name__ == "__main__":
    unittest.main()
