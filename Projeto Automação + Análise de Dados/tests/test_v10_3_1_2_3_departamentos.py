from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.crm import criar_empresa_crm, criar_contato, criar_lead
from enterprise.comercial import criar_oportunidade, listar_etapas, criar_proposta, registrar_atividade, salvar_meta, resumo_comercial, exportar_dataframe_comercial
from enterprise.administrativo import criar_solicitacao, criar_recurso, criar_reserva, criar_viagem, criar_reembolso, criar_manutencao, resumo_administrativo, exportar_dataframe_administrativo
from enterprise.juridico import criar_contrato, criar_processo, criar_prazo, criar_audiencia, registrar_risco, criar_provisao, resumo_juridico, exportar_dataframe_juridico
from interface.navegacao_modulos import tipo_tela_modulo, normalizar_secao_modulo, MODULOS_VISUAIS
from core.versao import VERSAO_PLATAFORMA


class DepartamentosEspecializadosV1033Tests(unittest.TestCase):
    def tearDown(self): SESSAO.encerrar()
    def ambiente(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); pasta=Path(tmp.name)
        p1=patch.object(banco,"DB_PATH",pasta/"teste.db"); p2=patch.object(banco,"STORAGE_DIR",pasta)
        p1.start(); p2.start(); self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        banco.inicializar_banco(); admin=criar_admin_inicial("Admin Empresa","adminv1033","SenhaEmpresa#123")
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto(); return admin

    def test_roteamento_dos_tres_modulos_e_especializado(self):
        self.assertEqual(VERSAO_PLATAFORMA,"11.1.0")
        self.assertEqual(MODULOS_VISUAIS,frozenset())
        self.assertEqual(tipo_tela_modulo("comercial","visao"),"comercial")
        self.assertEqual(tipo_tela_modulo("administrativo","visao"),"administrativo")
        self.assertEqual(tipo_tela_modulo("juridico","visao"),"juridico")
        self.assertEqual(normalizar_secao_modulo("comercial","registros"),"oportunidades")
        self.assertEqual(normalizar_secao_modulo("administrativo","salas"),"reservas")
        self.assertEqual(normalizar_secao_modulo("juridico","registros"),"contratos")

    def test_comercial_compartilha_crm_e_calcula_forecast(self):
        admin=self.ambiente(); emp=criar_empresa_crm({"nome":"Cliente Beta"},admin); contato=criar_contato({"nome":"Bruno","crm_empresa_id":emp},admin); lead=criar_lead({"crm_empresa_id":emp,"contato_id":contato,"score":90,"status":"MQL"},admin)
        etapa=listar_etapas(admin)[1]
        op=criar_oportunidade({"titulo":"Contrato anual","crm_empresa_id":emp,"contato_id":contato,"lead_id":lead,"etapa_id":etapa["id"],"valor":"100000","probabilidade":40,"proxima_acao":"Demo executiva"},admin)
        registrar_atividade(op,{"tipo":"Reunião","descricao":"Discovery","proxima_acao":"Enviar proposta"},admin)
        criar_proposta({"oportunidade_id":op,"valor":"100000","desconto":"5000"},admin); salvar_meta("2026-08","150000",admin)
        r=resumo_comercial(admin); self.assertEqual(r["oportunidades"],1); self.assertEqual(r["pipeline_centavos"],10000000); self.assertEqual(r["ponderado_centavos"],4000000); self.assertEqual(r["meta_centavos"],15000000)
        self.assertEqual(len(exportar_dataframe_comercial(admin)),1)

    def test_administrativo_detecta_conflito_de_reserva_e_resume_operacao(self):
        admin=self.ambiente(); criar_solicitacao({"titulo":"Trocar iluminação","categoria":"Facilities","prioridade":"Alta","valor":"2500"},admin)
        recurso=criar_recurso({"nome":"Sala Azul","tipo":"Sala","capacidade":12},admin)
        criar_reserva({"recurso_id":recurso,"titulo":"Reunião A","inicio":"2026-08-20 10:00","fim":"2026-08-20 11:00"},admin)
        with self.assertRaises(ValueError): criar_reserva({"recurso_id":recurso,"titulo":"Conflito","inicio":"2026-08-20 10:30","fim":"2026-08-20 11:30"},admin)
        criar_viagem({"viajante":"Ana","destino":"São Paulo","custo_estimado":"1800"},admin); criar_reembolso({"solicitante":"Ana","categoria":"Transporte","valor":"150"},admin); criar_manutencao({"recurso_id":recurso,"titulo":"Revisar projetor","custo":"300"},admin)
        r=resumo_administrativo(admin); self.assertEqual(r["solicitacoes"],1); self.assertEqual(r["reservas"],1); self.assertEqual(r["reembolsos_pendentes"],1); self.assertEqual(len(exportar_dataframe_administrativo(admin)),1)

    def test_juridico_cobre_contrato_processo_prazo_risco_e_provisao(self):
        admin=self.ambiente(); contrato=criar_contrato({"titulo":"Contrato fornecedor","parte":"Fornecedor X","valor":"50000","risco":"Médio","status":"Ativo"},admin)
        processo=criar_processo({"numero":"0001234-56.2026.8.00.0001","titulo":"Cobrança","valor_causa":"80000","probabilidade":"Provável","risco":"Alto"},admin)
        criar_prazo({"processo_id":processo,"titulo":"Contestação","vencimento":"2026-08-25","prioridade":"Crítica"},admin); criar_audiencia({"processo_id":processo,"data_hora":"2026-09-10 14:00","local":"TJ"},admin)
        risco=registrar_risco({"processo_id":processo,"contrato_id":contrato,"titulo":"Perda provável","probabilidade":"Provável","impacto":"Alto","exposicao":"60000"},admin)
        criar_provisao({"processo_id":processo,"risco_id":risco,"referencia":"2026-08","valor":"60000"},admin)
        r=resumo_juridico(admin); self.assertEqual(r["contratos"],1); self.assertEqual(r["processos_ativos"],1); self.assertEqual(r["riscos_abertos"],1); self.assertEqual(r["exposicao_centavos"],6000000); self.assertEqual(r["provisoes_centavos"],6000000); self.assertEqual(len(exportar_dataframe_juridico(admin)),1)


if __name__ == "__main__": unittest.main()
