from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.crm import criar_contato, criar_empresa_crm, criar_lead
from enterprise.rh import criar_colaborador
from enterprise.orquestracao import (
    converter_lead_em_oportunidade, criar_fluxo_admissao, listar_etapas_orquestracao, listar_orquestracoes,
)

class OrquestracaoV1041Tests(unittest.TestCase):
    def tearDown(self): SESSAO.encerrar()
    def ambiente(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); pasta=Path(tmp.name)
        p1=patch.object(banco,"DB_PATH",pasta/"teste.db"); p2=patch.object(banco,"STORAGE_DIR",pasta)
        p1.start(); p2.start(); self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        banco.inicializar_banco(); admin=criar_admin_inicial("Admin Fluxos","adminfluxos","Fluxos#123456")
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto(); return admin

    def test_marketing_comercial_reutiliza_lead_e_e_idempotente(self):
        admin=self.ambiente(); emp=criar_empresa_crm({"nome":"Conta Orion"},admin); contato=criar_contato({"nome":"Ana","crm_empresa_id":emp},admin)
        lead=criar_lead({"crm_empresa_id":emp,"contato_id":contato,"score":90,"status":"MQL"},admin)
        a=converter_lead_em_oportunidade(lead,{"titulo":"Expansão Orion","valor":"50000"},admin)
        b=converter_lead_em_oportunidade(lead,{"titulo":"Não deve duplicar"},admin)
        self.assertTrue(a["criada"]); self.assertFalse(b["criada"]); self.assertEqual(a["oportunidade_id"],b["oportunidade_id"])
        fluxos=listar_orquestracoes(admin,tipo="marketing_comercial")
        self.assertEqual(len(fluxos),1)

    def test_admissao_tem_etapas_rh_ti_estoque_administrativo(self):
        admin=self.ambiente()
        cid=criar_colaborador({"nome_completo":"Colaborador Teste","cpf":"12345678909","data_admissao":"2026-08-20","cargo_texto":"Analista"},admin)
        oid=criar_fluxo_admissao(cid,admin); etapas=listar_etapas_orquestracao(oid,admin)
        self.assertEqual([x["modulo"] for x in etapas],["rh","ti","ti","estoque","administrativo","rh"])

if __name__ == "__main__": unittest.main()
