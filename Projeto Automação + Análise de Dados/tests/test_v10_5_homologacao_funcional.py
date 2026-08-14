from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from services.contexto import obter_contexto
from services.crm import criar_contato, criar_empresa_crm, criar_lead
from services.departamentos.administrativo import criar_recurso, criar_reserva, criar_solicitacao
from services.departamentos.juridico import criar_processo, registrar_risco, criar_provisao
from services.departamentos.marketing import criar_campanha
from services.departamentos.rh import criar_colaborador
from services.orquestracao import converter_lead_em_oportunidade, criar_fluxo_admissao, listar_orquestracoes
from services.analytics import gerar_insights, obter_painel_executivo


class HomologacaoFuncionalV105Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def ambiente(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); pasta = Path(tmp.name)
        p1 = patch.object(banco, "DB_PATH", pasta / "homologacao.db")
        p2 = patch.object(banco, "STORAGE_DIR", pasta)
        p1.start(); p2.start(); self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Admin Homologação", "adminrc", "Homologacao#123456")
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto()
        return admin

    def test_cenario_integrado_cobre_nove_modulos_e_fluxos_transversais(self):
        admin = self.ambiente()

        campanha = criar_campanha({"nome": "Campanha RC", "objetivo": "Pipeline", "orcamento": "10000", "status": "Ativa"}, admin)
        conta = criar_empresa_crm({"nome": "Empresa Demo"}, admin)
        contato = criar_contato({"nome": "Comprador Demo", "crm_empresa_id": conta, "email": "demo@example.com"}, admin)
        lead = criar_lead({"crm_empresa_id": conta, "contato_id": contato, "campanha_id": campanha, "score": 92, "status": "MQL"}, admin)
        conversao = converter_lead_em_oportunidade(lead, {"titulo": "Contrato Demo", "valor": "75000"}, admin)
        self.assertTrue(conversao["oportunidade_id"])

        criar_solicitacao({"titulo": "Adequar sala", "categoria": "Facilities", "prioridade": "Crítica"}, admin)
        recurso = criar_recurso({"nome": "Sala Demo", "tipo": "Sala", "capacidade": 8}, admin)
        criar_reserva({"recurso_id": recurso, "titulo": "Kickoff", "inicio": "2026-09-01 09:00", "fim": "2026-09-01 10:00"}, admin)

        processo = criar_processo({"numero": "RC-2026-0001", "titulo": "Processo Demo", "valor_causa": "50000", "probabilidade": "Provável", "risco": "Alto"}, admin)
        risco = registrar_risco({"processo_id": processo, "titulo": "Exposição Demo", "probabilidade": "Provável", "impacto": "Alto", "exposicao": "40000"}, admin)
        criar_provisao({"processo_id": processo, "risco_id": risco, "referencia": "2026-09", "valor": "10000"}, admin)

        colaborador = criar_colaborador({"nome_completo": "Pessoa Demo", "cpf": "12345678909", "data_admissao": "2026-09-01", "cargo_texto": "Analista"}, admin)
        self.assertGreater(criar_fluxo_admissao(colaborador, admin), 0)

        painel = obter_painel_executivo(admin)
        self.assertEqual(set(painel["modulos"]), {
            "financeiro", "rh", "compras", "estoque", "ti",
            "marketing", "comercial", "administrativo", "juridico",
        })
        self.assertEqual(painel["modulos_processados"], 9)

        insights = gerar_insights(admin, persistir=True)
        codigos = {x["codigo"] for x in insights["insights"]}
        self.assertIn("solicitacoes_criticas", codigos)
        self.assertIn("gap_provisao", codigos)
        self.assertGreaterEqual(len(listar_orquestracoes(admin)), 2)


if __name__ == "__main__":
    unittest.main()
