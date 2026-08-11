"""Testes do agente distribuído de Tecnologia, sem rede ou alterações no SO."""

import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agente_ti import SCHEMA_PAYLOAD, VERSAO_AGENTE
from agente_ti.cli import main
from agente_ti.collector import coletar_payload
from agente_ti.config import (
    carregar_configuracao,
    criar_configuracao,
    salvar_configuracao,
)
from agente_ti.credentials import carregar_token
from agente_ti.runtime import InstanceLock, executar_uma_vez
from agente_ti.transport import enviar_heartbeat, assinatura_requisicao, serializar_payload
from agente_ti.windows import _comando_tarefa


class _Resposta:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limite):
        return b'{"aceito":true}'

    def getcode(self):
        return self.status


class _Opener:
    def __init__(self):
        self.requisicao = None
        self.timeout = None

    def open(self, requisicao, timeout):
        self.requisicao = requisicao
        self.timeout = timeout
        return _Resposta()


class AgenteTITests(unittest.TestCase):
    def test_configuracao_roundtrip_e_https_obrigatorio(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / "agent.json"
            config = criar_configuracao("https://ti.empresa.test", "TI-001", agent_id="agent-001")
            salvar_configuracao(config, caminho)
            carregada = carregar_configuracao(caminho)
            self.assertEqual(carregada, config)
            self.assertEqual(carregada.endpoint_heartbeat, "https://ti.empresa.test/api/v1/ti/agentes/heartbeat")
        with self.assertRaises(ValueError):
            criar_configuracao("http://ti.empresa.test", "TI-001")
        config_lan = criar_configuracao(
            "http://192.168.50.10:8765", "TI-001", agent_id="agent-lan-001",
            permitir_http_privado=True,
        )
        self.assertTrue(config_lan.permitir_http_privado)
        with self.assertRaises(ValueError):
            criar_configuracao("https://ti.empresa.test", "TI-001", verificar_tls=False)

    def test_token_pode_ser_injetado_sem_persistencia_em_desenvolvimento(self):
        token = "t" * 32
        with patch.dict(os.environ, {"DATA_TI_AGENT_TOKEN": token}):
            self.assertEqual(carregar_token(), token)

    def test_coleta_local_respeita_contrato_minimo(self):
        config = criar_configuracao("http://127.0.0.1:8000", "TI-DEV-001", agent_id="agent-local")
        payload = coletar_payload(config)
        self.assertEqual(payload["schema"], SCHEMA_PAYLOAD)
        self.assertEqual(payload["agente_versao"], VERSAO_AGENTE)
        self.assertEqual(payload["patrimonio"], "TI-DEV-001")
        self.assertTrue(payload["dispositivo"]["hostname"])
        self.assertIn("cpu_percentual", payload["metricas"])
        self.assertNotIn("processos", payload)
        self.assertNotIn("arquivos", payload)

    def test_anydesk_e_consultado_sem_shell_e_saida_e_validada(self):
        with tempfile.TemporaryDirectory() as temp:
            executavel = Path(temp) / "AnyDesk.exe"
            executavel.touch()
            config = criar_configuracao(
                "http://127.0.0.1:8000", "TI-002", agent_id="agent-anydesk",
                provedor_remoto="AnyDesk", executavel_remoto=str(executavel),
            )
            respostas = {
                "--get-id": "123456789", "--get-alias": "pc-fin@empresa",
                "--get-status": "online", "--version": "9.0.0",
            }
            with patch("agente_ti.collector._comando_curto", side_effect=lambda _e, p: respostas[p]):
                remoto = coletar_payload(config)["acesso_remoto"]
            self.assertTrue(remoto["instalado"])
            self.assertEqual(remoto["identificador"], "123456789")
            self.assertEqual(remoto["alias"], "pc-fin@empresa")

    def test_assinatura_hmac_possui_formato_deterministico(self):
        token = "segredo-de-teste-com-32-caracteres"
        corpo = b'{"ok":true}'
        chave = hashlib.sha256(token.encode()).digest()
        esperado = hmac.new(
            chave,
            f"1700000000\nnonce\n{hashlib.sha256(corpo).hexdigest()}".encode(),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(assinatura_requisicao(token, corpo, "1700000000", "nonce"), esperado)

    def test_transporte_envia_json_assinado_sem_token_no_payload(self):
        config = criar_configuracao("http://127.0.0.1:8000", "TI-003", agent_id="agent-transporte")
        payload = {"patrimonio": "TI-003", "metricas": {"cpu_percentual": 20}}
        opener = _Opener()
        with patch("agente_ti.transport._opener", return_value=opener):
            resultado = enviar_heartbeat(config, "x" * 32, payload)
        self.assertEqual(resultado.status, 202)
        self.assertEqual(resultado.corpo, {"aceito": True})
        self.assertEqual(opener.requisicao.data, serializar_payload(payload))
        headers = {k.lower(): v for k, v in opener.requisicao.header_items()}
        self.assertEqual(headers["x-agent-id"], "agent-transporte")
        self.assertIn("x-agent-signature", headers)
        self.assertNotIn(b"x" * 32, opener.requisicao.data)

    def test_dry_run_nao_exige_token_nem_envio(self):
        config = criar_configuracao("http://localhost:8000", "TI-004", agent_id="agent-dry")
        with patch("agente_ti.runtime.enviar_heartbeat") as enviar:
            payload, resposta = executar_uma_vez(config, dry_run=True)
        enviar.assert_not_called()
        self.assertEqual(payload["patrimonio"], "TI-004")
        self.assertIsNone(resposta)

    def test_lock_impede_segunda_instancia_e_remove_ao_sair(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / "agent.lock"
            with InstanceLock(caminho):
                self.assertTrue(caminho.exists())
                with self.assertRaises(RuntimeError):
                    with InstanceLock(caminho):
                        pass
            self.assertFalse(caminho.exists())

    def test_comando_de_tarefa_usa_caminhos_absolutos(self):
        with tempfile.TemporaryDirectory() as temp:
            pasta = Path(temp)
            exe = pasta / "DataIntelligenceTIAgent.exe"
            config = pasta / "agent.json"
            exe.touch(); config.write_text("{}", encoding="utf-8")
            comando = _comando_tarefa(exe, config)
            self.assertIn(str(exe.resolve()), comando)
            self.assertIn(str(config.resolve()), comando)
            self.assertIn(" run --config ", comando)

    def test_cli_collect_funciona_sem_token(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / "agent.json"
            salvar_configuracao(
                criar_configuracao("http://localhost:8000", "TI-005", agent_id="agent-cli"),
                caminho,
            )
            with patch("builtins.print") as imprimir:
                codigo = main(["collect", "--config", str(caminho)])
            self.assertEqual(codigo, 0)
            exibido = json.loads(imprimir.call_args.args[0])
            self.assertEqual(exibido["agent_id"], "agent-cli")

    def test_cli_once_dry_run_nao_carrega_credencial(self):
        with tempfile.TemporaryDirectory() as temp:
            caminho = Path(temp) / "agent.json"
            salvar_configuracao(
                criar_configuracao("http://localhost:8000", "TI-006", agent_id="agent-once"),
                caminho,
            )
            with patch("agente_ti.cli.carregar_token") as carregar, patch("builtins.print"):
                codigo = main(["once", "--config", str(caminho), "--dry-run"])
            self.assertEqual(codigo, 0)
            carregar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
