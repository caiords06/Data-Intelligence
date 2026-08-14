"""Regressões da autoridade transacional remota V9.1."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from servidor_corporativo.app import CorporateRequestHandler, CorporateServer
from servidor_corporativo.config import ConfigServidor
from servidor_corporativo import sessoes as sessoes_servidor


class AutoridadeCentralV91Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()
        sessoes_servidor._SESSOES.clear()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "server.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
        patch_db.start(); patch_storage.start()
        self.addCleanup(patch_db.stop); self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123", email_corporativo="admin@empresa.local")
        SESSAO.iniciar(admin)
        inicializar_enterprise(); obter_contexto()
        return admin

    @staticmethod
    def _json(url, *, metodo="GET", dados=None, token=None):
        corpo = None
        headers = {"Accept": "application/json"}
        if dados is not None:
            corpo = json.dumps(dados).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=corpo, headers=headers, method=metodo)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def test_rpc_http_grava_e_le_no_mesmo_banco_do_servidor(self):
        self._ambiente()
        cfg = ConfigServidor(host="127.0.0.1", porta=8770)
        servidor = CorporateServer(("127.0.0.1", 0), CorporateRequestHandler, cfg)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True); thread.start()
        self.addCleanup(servidor.server_close); self.addCleanup(servidor.shutdown)
        base = f"http://127.0.0.1:{servidor.server_address[1]}"
        status, login = self._json(base + "/api/v1/auth/login", metodo="POST", dados={"usuario":"admin","senha":"SenhaAdmin#123"})
        self.assertEqual(status, 200)
        token = login["token"]

        status, criado = self._json(
            base + "/api/v1/rpc", metodo="POST", token=token,
            dados={"modulo":"enterprise.financeiro","funcao":"criar_conta","args":[{"nome":"Conta RPC","saldo_inicial":"123.45"},{"id":999,"perfil":"admin"}],"kwargs":{}},
        )
        self.assertEqual(status, 200)
        conta_id = int(criado["resultado"])
        with banco.conectar() as con:
            row = con.execute("SELECT nome FROM fin_contas WHERE id=?", (conta_id,)).fetchone()
        self.assertEqual(row["nome"], "Conta RPC")

        status, listado = self._json(
            base + "/api/v1/rpc", metodo="POST", token=token,
            dados={"modulo":"enterprise.financeiro","funcao":"listar_contas_com_saldo","args":[{"id":999,"perfil":"usuario"}],"kwargs":{}},
        )
        self.assertEqual(status, 200)
        self.assertTrue(any(x["nome"] == "Conta RPC" for x in listado["resultado"]))

    def test_rpc_rejeita_funcao_fora_da_allowlist(self):
        self._ambiente()
        cfg = ConfigServidor(host="127.0.0.1", porta=8770)
        servidor = CorporateServer(("127.0.0.1", 0), CorporateRequestHandler, cfg)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True); thread.start()
        self.addCleanup(servidor.server_close); self.addCleanup(servidor.shutdown)
        base = f"http://127.0.0.1:{servidor.server_address[1]}"
        _, login = self._json(base + "/api/v1/auth/login", metodo="POST", dados={"usuario":"admin","senha":"SenhaAdmin#123"})
        req = urllib.request.Request(
            base + "/api/v1/rpc",
            data=json.dumps({"modulo":"os","funcao":"system","args":["whoami"],"kwargs":{}}).encode(),
            headers={"Authorization":f"Bearer {login['token']}","Content-Type":"application/json"},
            method="POST",
        )
        with self.assertRaises(Exception):
            urllib.request.urlopen(req, timeout=5)

    def test_proxy_em_estacao_remota_nao_executa_funcao_local(self):
        import enterprise.financeiro as financeiro
        with patch("core.nodo.usa_servidor_remoto", return_value=True), \
             patch("enterprise.servidor_cliente.executar_rpc_remoto", return_value=321) as rpc:
            resultado = financeiro.criar_conta({"nome":"Nunca local"}, {"id":1})
        self.assertEqual(resultado, 321)
        rpc.assert_called_once()
        self.assertEqual(rpc.call_args.args[0:2], ("enterprise.financeiro", "criar_conta"))


    def test_servidor_corporativo_recebe_heartbeat_do_agente_ti(self):
        admin = self._ambiente()
        from agente_ti import SCHEMA_PAYLOAD
        from agente_ti.config import criar_configuracao
        from agente_ti.transport import enviar_heartbeat
        from enterprise.tecnologia import criar_ativo, criar_credencial_agente
        ativo_id = criar_ativo({
            "patrimonio": "TI-RPC-AG-001", "nome": "Notebook remoto",
            "tipo": "Notebook", "status": "Em uso",
        }, admin)
        cred = criar_credencial_agente(ativo_id, admin)
        cfg = ConfigServidor(host="127.0.0.1", porta=8770)
        servidor = CorporateServer(("127.0.0.1", 0), CorporateRequestHandler, cfg)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True); thread.start()
        self.addCleanup(servidor.server_close); self.addCleanup(servidor.shutdown)
        base = f"http://127.0.0.1:{servidor.server_address[1]}"
        agent_cfg = criar_configuracao(
            base, cred["patrimonio"], agent_id=cred["agent_id"], permitir_http_privado=True
        )
        payload = {
            "schema": SCHEMA_PAYLOAD, "agent_id": cred["agent_id"],
            "agente_versao": "1.2.0", "patrimonio": cred["patrimonio"],
            "dispositivo": {
                "hostname": "NOTE-RPC-01", "fqdn": "NOTE-RPC-01.local",
                "sistema_operacional": "Windows", "versao_sistema": "Windows 11",
                "arquitetura": "AMD64", "processador": "CPU Teste",
                "executado_como": "usuario.remoto",
                "enderecos_ip": ["192.168.1.22"],
                "enderecos_mac": ["00:11:22:33:44:66"],
                "memoria_total_gb": 16, "armazenamento_total_gb": 512,
            },
            "metricas": {
                "cpu_percentual": 10, "memoria_percentual": 40,
                "disco_percentual": 50, "espaco_livre_gb": 200,
                "uptime_segundos": 1000, "latencia_ms": 3,
            },
            "acesso_remoto": {"provedor": "AnyDesk", "instalado": True, "identificador": "123456789"},
        }
        resposta = enviar_heartbeat(agent_cfg, cred["token"], payload)
        self.assertEqual(resposta.status, 202)
        with banco.conectar() as con:
            row = con.execute("SELECT hostname,remote_id FROM ti_ativos WHERE id=?", (ativo_id,)).fetchone()
        self.assertEqual(row["hostname"], "NOTE-RPC-01")
        self.assertEqual(row["remote_id"], "123456789")

    def test_allowlist_rpc_aponta_apenas_para_funcoes_existentes(self):
        import importlib
        from core.rpc_central import RPC_ALLOWLIST
        faltantes=[]
        for modulo, funcoes in RPC_ALLOWLIST.items():
            mod=importlib.import_module(modulo)
            for nome in funcoes:
                if not callable(getattr(mod,nome,None)):
                    faltantes.append(f"{modulo}.{nome}")
        self.assertEqual(faltantes, [])

    def test_interface_nao_possui_sql_direto_de_estoque(self):
        raiz = Path(__file__).parents[1] / "interface"
        arquivos = [raiz / "estoque.py", raiz / "estoque_shared.py", raiz / "estoque_views.py", raiz / "estoque_acoes.py"]
        texto = "\n".join(x.read_text(encoding="utf-8") for x in arquivos if x.is_file())
        self.assertNotIn("from auth.banco import conectar", texto)
        self.assertIn("obter_primeiro_item_operacao", texto)


if __name__ == "__main__":
    unittest.main()
