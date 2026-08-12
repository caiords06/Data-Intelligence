"""Testes end-to-end da API central do agente TI em localhost."""

from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from agente_ti import SCHEMA_PAYLOAD
from agente_ti.config import criar_configuracao
from agente_ti.transport import TransportError, enviar_heartbeat
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.tecnologia import criar_ativo, criar_credencial_agente
from servidor_ti.app import TIServer, TIRequestHandler


class ServidorTITests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
        patch_db.start(); patch_storage.start()
        self.addCleanup(patch_db.stop); self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(admin)
        inicializar_enterprise(); obter_contexto()
        ativo = criar_ativo({
            "patrimonio": "TI-API-001",
            "nome": "Notebook API",
            "tipo": "Notebook",
            "status": "Em uso",
        }, admin)
        credencial = criar_credencial_agente(ativo, admin)
        return admin, ativo, credencial

    @staticmethod
    def _payload(credencial):
        return {
            "schema": SCHEMA_PAYLOAD,
            "agent_id": credencial["agent_id"],
            "agente_versao": "1.1.0",
            "patrimonio": credencial["patrimonio"],
            "dispositivo": {
                "hostname": "NOTE-API-01",
                "fqdn": "NOTE-API-01.local",
                "sistema_operacional": "Windows",
                "versao_sistema": "Windows 11",
                "arquitetura": "AMD64",
                "processador": "CPU Teste",
                "executado_como": "usuario.teste",
                "enderecos_ip": ["192.168.50.20"],
                "enderecos_mac": ["00:11:22:33:44:55"],
                "memoria_total_gb": 16,
                "armazenamento_total_gb": 512,
            },
            "metricas": {
                "cpu_percentual": 20,
                "memoria_percentual": 45,
                "disco_percentual": 60,
                "espaco_livre_gb": 180,
                "uptime_segundos": 3600,
                "latencia_ms": 2,
            },
            "acesso_remoto": {
                "provedor": "AnyDesk",
                "instalado": True,
                "identificador": "123456789",
                "alias": "note-api@empresa",
                "status": "online",
                "versao": "9.0",
            },
        }

    def test_heartbeat_real_localhost_atualiza_ativo(self):
        _admin, ativo, credencial = self._ambiente()
        servidor = TIServer(("127.0.0.1", 0), TIRequestHandler)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        porta = servidor.server_address[1]
        config = criar_configuracao(
            f"http://127.0.0.1:{porta}",
            credencial["patrimonio"],
            agent_id=credencial["agent_id"],
        )
        resposta = enviar_heartbeat(config, credencial["token"], self._payload(credencial))
        self.assertEqual(resposta.status, 202)
        self.assertTrue(resposta.corpo["aceito"])
        with banco.conectar() as conexao:
            ativo_db = conexao.execute("SELECT * FROM ti_ativos WHERE id=?", (ativo,)).fetchone()
            agente_db = conexao.execute("SELECT * FROM ti_agentes WHERE ativo_id=?", (ativo,)).fetchone()
            telemetria = conexao.execute("SELECT COUNT(*) FROM ti_telemetria WHERE ativo_id=?", (ativo,)).fetchone()[0]
        self.assertEqual(ativo_db["hostname"], "NOTE-API-01")
        self.assertEqual(ativo_db["remote_id"], "123456789")
        self.assertEqual(agente_db["status"], "Online")
        self.assertEqual(telemetria, 1)

    def test_token_incorreto_e_recusado(self):
        _admin, _ativo, credencial = self._ambiente()
        servidor = TIServer(("127.0.0.1", 0), TIRequestHandler)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        config = criar_configuracao(
            f"http://127.0.0.1:{servidor.server_address[1]}",
            credencial["patrimonio"],
            agent_id=credencial["agent_id"],
        )
        with self.assertRaises(TransportError):
            enviar_heartbeat(config, "token-incorreto-xxxxxxxxxxxxxxxxxxxxxxxx", self._payload(credencial))


if __name__ == "__main__":
    unittest.main()
