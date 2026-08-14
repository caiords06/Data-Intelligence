from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.administrativo import criar_solicitacao
from enterprise.analytics_inteligencia import (
    alterar_status_insight, gerar_insights, listar_insights, listar_regras, salvar_regra,
)


class AnalyticsEmpresarialV104Tests(unittest.TestCase):
    def tearDown(self): SESSAO.encerrar()
    def ambiente(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); pasta=Path(tmp.name)
        p1=patch.object(banco,"DB_PATH",pasta/"teste.db"); p2=patch.object(banco,"STORAGE_DIR",pasta)
        p1.start(); p2.start(); self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        banco.inicializar_banco(); admin=criar_admin_inicial("Admin Analytics","adminanalytics","Analytics#123456")
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto(); return admin

    def test_gera_insight_acionavel_e_persistente(self):
        admin=self.ambiente()
        criar_solicitacao({"titulo":"Interdição elétrica","categoria":"Facilities","prioridade":"Crítica","valor":"1000"},admin)
        r=gerar_insights(admin,persistir=True)
        encontrados=[x for x in r["insights"] if x.get("codigo")=="solicitacoes_criticas"]
        self.assertTrue(encontrados)
        item=encontrados[0]
        self.assertEqual(item["acao_modulo"],"administrativo")
        self.assertEqual(item["acao_secao"],"solicitacoes")
        alterar_status_insight(item["id"],"Ignorado",admin)
        self.assertFalse(any(x["id"]==item["id"] for x in listar_insights(admin,status="Ativo")))

    def test_regra_personalizada_complementa_detectores_nativos(self):
        admin=self.ambiente()
        criar_solicitacao({"titulo":"Solicitação 1","categoria":"Facilities","prioridade":"Média"},admin)
        rid=salvar_regra({"codigo":"backlog_admin","nome":"Qualquer backlog administrativo","modulo":"administrativo",
                          "metrica":"abertas","operador":">=","limite":1,"severidade":"Atenção",
                          "acao_modulo":"administrativo","acao_secao":"solicitacoes"},admin)
        self.assertGreater(rid,0); self.assertEqual(len(listar_regras(admin)),1)
        r=gerar_insights(admin,persistir=False)
        self.assertTrue(any(str(x.get("codigo","")).startswith("custom_") for x in r["insights"]))

if __name__ == "__main__": unittest.main()
