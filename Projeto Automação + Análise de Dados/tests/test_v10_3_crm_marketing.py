from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.crm import (
    criar_contato, criar_empresa_crm, criar_lead, listar_leads, resumo_crm,
    atualizar_lead_status,
)
from enterprise.marketing import (
    criar_canal, criar_campanha, criar_conteudo, criar_automacao,
    registrar_metricas, resumo_marketing, exportar_dataframe_marketing,
)
from interface.navegacao_modulos import tipo_tela_modulo, normalizar_secao_modulo


class CRMMarketingV103Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        pasta = Path(tmp.name)
        p1=patch.object(banco,"DB_PATH",pasta/"teste.db"); p2=patch.object(banco,"STORAGE_DIR",pasta)
        p1.start(); p2.start(); self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        banco.inicializar_banco()
        admin=criar_admin_inicial("Admin Marketing","adminmkt","SenhaMarketing#123")
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto()
        return admin

    def test_marketing_e_promovido_a_modulo_especializado(self):
        self.assertEqual(tipo_tela_modulo("marketing","visao"),"marketing")
        self.assertEqual(normalizar_secao_modulo("marketing","registros"),"campanhas")

    def test_fluxo_crm_campanha_lead_metricas(self):
        admin=self._ambiente()
        empresa_id=criar_empresa_crm({"nome":"Cliente Alpha","segmento":"Tecnologia"},admin)
        contato_id=criar_contato({"nome":"Ana Compras","email":"ana@alpha.com","crm_empresa_id":empresa_id,"origem":"Evento"},admin)
        canal_id=criar_canal({"nome":"LinkedIn","tipo":"Social"},admin)
        campanha_id=criar_campanha({"nome":"ABM Alpha","canal_id":canal_id,"orcamento":"10000","investimento":"2500","status":"Ativa"},admin)
        lead_id=criar_lead({"contato_id":contato_id,"crm_empresa_id":empresa_id,"campanha_id":campanha_id,"origem":"LinkedIn","score":82,"status":"MQL"},admin)
        leads=listar_leads(admin)
        self.assertEqual(leads[0]["id"],lead_id)
        self.assertEqual(leads[0]["contato_nome"],"Ana Compras")
        self.assertEqual(resumo_crm(admin)["mql"],1)
        atualizar_lead_status(lead_id,"SQL",admin)
        self.assertEqual(listar_leads(admin)[0]["status"],"SQL")
        registrar_metricas(campanha_id,"2026-08",{"impressoes":10000,"cliques":700,"leads":20,"mqls":7,"conversoes":2,"investimento":"2500","receita":"12000"},admin)
        resumo=resumo_marketing(admin)
        self.assertEqual(resumo["leads"],20)
        self.assertEqual(resumo["mqls"],7)
        self.assertEqual(resumo["conversoes"],2)
        self.assertEqual(resumo["roas"],4.8)
        df=exportar_dataframe_marketing(admin)
        self.assertEqual(len(df),1)
        self.assertEqual(df.iloc[0]["nome"],"ABM Alpha")

    def test_conteudo_e_automacao_usam_tabelas_especializadas(self):
        admin=self._ambiente()
        campanha=criar_campanha({"nome":"Inbound Agosto","status":"Planejada"},admin)
        conteudo=criar_conteudo({"titulo":"Guia de automação","formato":"Artigo","campanha_id":campanha,"etapa":"Produção","data_publicacao":"2026-08-30"},admin)
        automacao=criar_automacao({"nome":"Nutrição MQL","gatilho":"Lead virou MQL","acao":"Criar tarefa de revisão comercial"},admin)
        self.assertGreater(conteudo,0); self.assertGreater(automacao,0)


if __name__ == "__main__":
    unittest.main()
