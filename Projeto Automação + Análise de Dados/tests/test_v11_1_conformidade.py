"""Regressões funcionais da V11.1: legal, transporte e governança remota."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from enterprise.banco import inicializar_enterprise
from enterprise.organizacao import criar_empresa


CHAVE = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


class ConformidadeV111Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.raiz = Path(self.tmp.name)
        self.ambiente = patch.dict(os.environ, {
            "DATA_INTELLIGENCE_DB_BACKEND": "sqlite", "DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE": "1",
            "DATA_INTELLIGENCE_ALLOW_STANDALONE": "1", "DATA_INTELLIGENCE_NODE_ROLE": "servidor",
            "DATA_INTELLIGENCE_PII_MASTER_KEY": CHAVE, "DATA_INTELLIGENCE_MEDIA_MASTER_KEY": CHAVE,
            "DATA_INTELLIGENCE_MFA_MASTER_KEY": CHAVE, "DATA_INTELLIGENCE_WEBHOOK_MASTER_KEY": CHAVE,
        })
        self.ambiente.start()
        self.p_storage = patch.object(banco, "STORAGE_DIR", self.raiz / "storage")
        self.p_db = patch.object(banco, "DB_PATH", self.raiz / "app.db")
        self.p_storage.start(); self.p_db.start(); banco.inicializar_banco(); inicializar_enterprise()
        self.admin = criar_admin_inicial("Administrador V11.1", "adminv111", "SenhaForte#V11-2026")
        self.empresa_id = criar_empresa("Empresa V11.1", "11111111000199", ator=self.admin)
        self.ator = {**self.admin, "_empresa_id": self.empresa_id, "_filial_id": None}

    def tearDown(self):
        self.p_db.stop(); self.p_storage.stop(); self.ambiente.stop(); self.tmp.cleanup()

    def test_migracao_e_central_de_conformidade(self):
        from services.compliance import (
            abrir_incidente_privacidade, avaliar_incidente_privacidade, criar_solicitacao_titular,
            listar_incidentes_privacidade, listar_ripd, resumo_conformidade, salvar_decisao_analitica,
            salvar_ripd, salvar_tratamento,
        )
        tratamento = salvar_tratamento({
            "codigo": "RH-01", "nome": "Gestão de colaboradores", "controlador": "Empresa V11.1",
            "finalidade": "Administrar o vínculo profissional", "base_legal": "Obrigação legal e contrato",
            "categorias_titulares": "Colaboradores", "categorias_dados": "Cadastrais e profissionais",
            "prazo_retencao": "Conforme tabela validada pelo Jurídico", "medidas_seguranca": "RBAC, TLS e auditoria",
        }, self.ator)
        criar_solicitacao_titular({"tipo": "Acesso", "titular_nome": "Titular Teste", "canal": "Portal"}, self.ator)
        incidente = abrir_incidente_privacidade({
            "titulo": "Exposição em teste", "descricao": "Incidente simulado para validar o fluxo.",
            "titulares_afetados": "", "risco_dano": "Em avaliação",
        }, self.ator)
        avaliar_incidente_privacidade(incidente, {
            "status": "Em comunicação", "titulares_afetados": "12", "comunicar_anpd": True,
            "comunicar_titulares": True, "justificativa_decisao": "Risco relevante confirmado pelo encarregado.",
        }, self.ator, versao=0)
        ripd = salvar_ripd({
            "tratamento_id": tratamento, "codigo": "RIPD-RH", "titulo": "RIPD do ciclo de pessoas",
            "necessidade_proporcionalidade": "O tratamento é necessário e limitado à gestão do contrato.",
            "riscos": "Acesso indevido\nRetenção excessiva", "salvaguardas": "RBAC\nRevisão anual",
            "risco_residual": "Baixo", "status": "Aprovado",
        }, self.ator)
        decisao = salvar_decisao_analitica({
            "codigo": "ALERTA-RH", "nome": "Alerta de jornada", "finalidade": "Priorizar revisão gerencial",
            "dados_entrada": "Marcações de jornada", "logica_resumo": "Sinaliza desvios; não decide automaticamente",
            "impacto_pessoas": "Pode priorizar revisão de colaborador", "revisao_humana": True, "status": "Ativo",
        }, self.ator)
        self.assertGreater(ripd, 0); self.assertGreater(decisao, 0)
        self.assertEqual(listar_ripd(self.ator)[0]["riscos"][0], "Acesso indevido")
        self.assertEqual(listar_incidentes_privacidade(self.ator)[0]["titulares_afetados"], 12)
        self.assertEqual(resumo_conformidade(self.ator)["incidentes_abertos"], 1)
        with self.assertRaisesRegex(ValueError, "revisão humana"):
            salvar_decisao_analitica({
                "codigo": "AUTO-RH", "nome": "Decisão automática", "finalidade": "Decidir sobre pessoa",
                "dados_entrada": "Perfil", "logica_resumo": "Classificação automatizada",
                "impacto_pessoas": "Alto", "revisao_humana": False,
            }, self.ator)

    def test_bloqueio_legal_exclui_registro_da_retencao(self):
        from enterprise.compliance import definir_bloqueio_retencao
        from enterprise.privacidade import definir_politica_retencao, executar_retencao_rh
        from enterprise.rh import criar_colaborador
        colaborador = criar_colaborador({
            "nome_completo": "Pessoa sob retenção", "cargo_texto": "Analista", "cpf": "12345678901",
            "admissao": "01/01/2020",
        }, self.ator)
        with banco.conectar() as con:
            con.execute("UPDATE rh_colaboradores SET desligamento='2020-12-31',status='Desligado' WHERE id=?", (colaborador,))
        definir_politica_retencao("RH", "colaborador", 365, self.ator, acao="Anonimizar")
        self.assertEqual(executar_retencao_rh(self.ator, simular=True)["candidatos"], 1)
        definir_bloqueio_retencao("rh_colaboradores", colaborador, "Litígio em curso", "Defesa de direito", self.ator)
        self.assertEqual(executar_retencao_rh(self.ator, simular=True)["candidatos"], 0)

    def test_token_remoto_e_unico_e_nao_e_persistido_em_claro(self):
        from enterprise.remote_governanca import (
            consumir_autorizacao_remota, emitir_autorizacao_remota, salvar_politica_remota,
        )
        from enterprise.tecnologia import criar_ativo, criar_chamado
        ativo = criar_ativo({"patrimonio": "TI-111", "nome": "Notebook controlado"}, self.ator)
        chamado = criar_chamado({
            "titulo": "Suporte autorizado", "descricao": "Usuário solicitou suporte remoto.", "ativo_id": ativo,
        }, self.ator)
        salvar_politica_remota({
            "nome": "Política assistida", "exige_chamado": True, "exige_consentimento": True,
            "permite_clipboard": False, "permite_transferencia": False, "permite_terminal": False,
        }, self.ator)
        emissao = emitir_autorizacao_remota(
            ativo, chamado, "Diagnóstico solicitado e acompanhado pelo usuário.",
            {"visualizar": True, "controlar": True, "terminal": True}, self.ator, consentimento=True,
        )
        with banco.conectar() as con:
            registro = con.execute("SELECT token_hash,permissoes_json FROM ti_remote_autorizacoes WHERE id=?", (emissao["autorizacao_id"],)).fetchone()
        self.assertEqual(registro["token_hash"], hashlib.sha256(emissao["token"].encode()).hexdigest())
        self.assertNotEqual(registro["token_hash"], emissao["token"]); self.assertFalse(emissao["permissoes"]["terminal"])
        consumir_autorizacao_remota(emissao["token"], ativo)
        with self.assertRaises(PermissionError): consumir_autorizacao_remota(emissao["token"], ativo)

    def test_transporte_externo_sem_tls_falha_fechado(self):
        from servidor_corporativo.config import ConfigServidor
        with self.assertRaisesRegex(ValueError, "produção ou LAN"):
            ConfigServidor(host="0.0.0.0", tls=False, ambiente="lan", postgres_segredo="env:TESTE").validar()
        seguro_local = ConfigServidor(
            host="127.0.0.1", tls=False, ambiente="producao", postgres_host="127.0.0.1",
            postgres_segredo="env:TESTE",
        ).validar()
        self.assertEqual(seguro_local.host, "127.0.0.1")

    def test_correcoes_exatas_dos_logs_permanecem_no_codigo(self):
        raiz = Path(__file__).resolve().parents[1]
        rh = (raiz / "enterprise" / "rh.py").read_text(encoding="utf-8")
        estoque = (raiz / "enterprise" / "estoque.py").read_text(encoding="utf-8")
        self.assertNotIn("pd.read_sql_query(sql, conexao", rh)
        self.assertNotRegex(estoque, r"\bdepartamentos\s+do\b")
        self.assertIn("dep_origem.nome AS deposito_origem", estoque)


if __name__ == "__main__":
    unittest.main()
