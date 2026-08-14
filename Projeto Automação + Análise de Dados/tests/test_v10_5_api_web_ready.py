from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from servidor_corporativo.api_v1 import PUBLIC_ENDPOINTS, dispatch_get, dispatch_post

class _Sessao:
    def __init__(self, ator): self._ator=ator
    def ator(self): return self._ator

class APIWebReadyV105Tests(unittest.TestCase):
    def tearDown(self): SESSAO.encerrar()
    def ambiente(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); pasta=Path(tmp.name)
        p1=patch.object(banco,"DB_PATH",pasta/"teste.db"); p2=patch.object(banco,"STORAGE_DIR",pasta)
        p1.start(); p2.start(); self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        banco.inicializar_banco(); admin=criar_admin_inicial("Admin API","adminapi","ApiWeb#123456")
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto(); return admin

    def test_contratos_publicos_existem_e_paginam(self):
        admin=self.ambiente(); sessao=_Sessao(admin)
        status,payload=dispatch_post("/api/v1/crm/leads",{"score":40,"status":"Novo"},sessao,"req-1")
        self.assertEqual(int(status),201); self.assertTrue(payload["ok"])
        status,payload=dispatch_get("/api/v1/crm/leads",{"page":["1"],"page_size":["10"]},sessao,"req-2")
        self.assertEqual(int(status),200); self.assertTrue(payload["ok"]); self.assertEqual(payload["pagination"]["total"],1)
        self.assertIn("/api/v1/analytics/insights",PUBLIC_ENDPOINTS)
        self.assertIn("/api/v1/comercial/oportunidades",PUBLIC_ENDPOINTS)

    def test_paginacao_real_ultrapassa_limite_legado_de_2000(self):
        admin = self.ambiente(); sessao = _Sessao(admin)
        contexto = obter_contexto()
        empresa_id = int(contexto["empresa_id"])
        filial_id = contexto.get("filial_id")
        usuario_id = int(admin["id"])
        # Volume suficiente para provar que LIMIT/OFFSET ocorre no SQL e não
        # depois de uma lista previamente truncada em 2.000 itens.
        with banco.conectar() as con:
            con.executemany(
                "INSERT INTO crm_leads (empresa_id,filial_id,score,status,criado_por) VALUES (?,?,?,?,?)",
                [(empresa_id, filial_id, i % 101, "Novo", usuario_id) for i in range(2105)],
            )
        status, payload = dispatch_get(
            "/api/v1/crm/leads", {"page": ["21"], "page_size": ["100"]}, sessao, "req-volume"
        )
        self.assertEqual(int(status), 200)
        self.assertEqual(payload["pagination"]["total"], 2105)
        self.assertEqual(len(payload["data"]), 100)
        self.assertTrue(payload["pagination"]["has_next"])
        _, ultima = dispatch_get(
            "/api/v1/crm/leads", {"page": ["22"], "page_size": ["100"]}, sessao, "req-last"
        )
        self.assertEqual(len(ultima["data"]), 5)
        self.assertFalse(ultima["pagination"]["has_next"])

    def test_todos_endpoints_paginados_delegam_limit_offset_e_count(self):
        casos = (
            ("/api/v1/crm/leads", "services.crm.listar_leads", "services.crm.contar_leads"),
            ("/api/v1/comercial/oportunidades", "services.departamentos.comercial.listar_oportunidades", "services.departamentos.comercial.contar_oportunidades"),
            ("/api/v1/marketing/campanhas", "services.departamentos.marketing.listar_campanhas", "services.departamentos.marketing.contar_campanhas"),
            ("/api/v1/juridico/processos", "services.departamentos.juridico.listar_processos", "services.departamentos.juridico.contar_processos"),
            ("/api/v1/administrativo/solicitacoes", "services.departamentos.administrativo.listar_solicitacoes", "services.departamentos.administrativo.contar_solicitacoes"),
            ("/api/v1/analytics/insights", "services.analytics.listar_insights", "services.analytics.contar_insights"),
            ("/api/v1/orquestracoes", "services.orquestracao.listar_orquestracoes", "services.orquestracao.contar_orquestracoes"),
        )
        sessao = _Sessao({"id": 99})
        for path, listar_target, contar_target in casos:
            with self.subTest(path=path), patch(listar_target, return_value=[]) as listar, patch(contar_target, return_value=123) as contar:
                status, payload = dispatch_get(path, {"page": ["3"], "page_size": ["25"]}, sessao, "req-page")
                self.assertEqual(int(status), 200)
                self.assertEqual(payload["pagination"]["total"], 123)
                self.assertEqual(payload["pagination"]["page"], 3)
                self.assertEqual(listar.call_args.kwargs["limite"], 25)
                self.assertEqual(listar.call_args.kwargs["offset"], 50)
                self.assertEqual(contar.call_count, 1)

    def test_api_analytics_executiva_usa_mesmo_servico(self):
        admin=self.ambiente(); status,payload=dispatch_get("/api/v1/analytics/executive",{},_Sessao(admin),"req-x")
        self.assertEqual(int(status),200); self.assertEqual(payload["request_id"],"req-x"); self.assertIn("modulos",payload["data"])

if __name__ == "__main__": unittest.main()
