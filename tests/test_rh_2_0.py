"""Regressões do domínio especializado de Recursos Humanos 2.0."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto, salvar_permissoes_usuario
from enterprise.rh import (
    abrir_folha,
    adicionar_evento_folha,
    concluir_desligamento,
    criar_solicitacao,
    criar_vaga,
    decidir_ferias_ausencia,
    exportar_dataframe_rh,
    fechar_folha,
    gerar_contracheque,
    gerar_relatorio_rh,
    iniciar_admissao,
    iniciar_desligamento,
    listar_admissoes,
    listar_auditoria_rh,
    listar_colaboradores,
    listar_secao,
    obter_colaborador,
    registrar_documento,
    registrar_ponto,
    resumo_rh,
    salvar_avaliacao,
    salvar_beneficio,
    salvar_cargo,
    salvar_pdi,
    salvar_permissao_acao,
    salvar_treinamento,
    solicitar_ferias_ausencia,
    vincular_beneficio,
    vincular_equipamento,
)


class RecursosHumanos20Tests(unittest.TestCase):
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
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto()
        return admin, pasta

    def _admissao(self, admin, nome="Ana Silva"):
        return iniciar_admissao(
            {
                "nome_completo": nome,
                "cargo_texto": "Analista de Pessoas",
                "cpf": {
                    "Ana Silva": "12345678901",
                    "Bruno Lima": "98765432100",
                    "Carla Souza": "45678912300",
                }.get(nome, "11122233344"),
                "email_corporativo": f"{nome.split()[0].lower()}@empresa.com",
                "admissao": "10/08/2026",
                "salario": "5.300,00",
                "tipo_contrato": "CLT",
            },
            admin,
        )

    def test_migracao_cria_dominio_e_cadastro_mestre(self):
        admin, _ = self._ambiente()
        admissao_id = self._admissao(admin)
        admissao = listar_admissoes(admin)[0]
        self.assertEqual(admissao["id"], admissao_id)
        pagina = listar_colaboradores(admin)
        self.assertEqual(pagina["total"], 1)
        colaborador = obter_colaborador(pagina["registros"][0]["id"], admin)
        self.assertEqual(colaborador["salario_centavos"], 530_000)
        with banco.conectar() as conexao:
            tabelas = {x["name"] for x in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'rh_%'"
            ).fetchall()}
        self.assertTrue({"rh_colaboradores", "rh_admissoes", "rh_folhas", "rh_vagas"} <= tabelas)

    def test_admissao_distribui_tarefas_interdepartamentais(self):
        admin, _ = self._ambiente()
        admissao_id = self._admissao(admin)
        with banco.conectar() as conexao:
            tarefas = conexao.execute(
                "SELECT modulo FROM tarefas WHERE recurso_tipo='rh_admissoes' AND recurso_id=?",
                (admissao_id,),
            ).fetchall()
        self.assertEqual({x["modulo"] for x in tarefas}, {"rh", "ti", "estoque", "administrativo"})

    def test_desligamento_exige_conclusao_das_tarefas(self):
        admin, _ = self._ambiente()
        self._admissao(admin)
        colaborador_id = listar_colaboradores(admin)["registros"][0]["id"]
        desligamento_id = iniciar_desligamento(
            colaborador_id,
            {"tipo": "Sem justa causa", "motivo": "Reestruturação", "data_prevista": "31/08/2026"},
            admin,
        )
        with self.assertRaisesRegex(ValueError, "tarefa"):
            concluir_desligamento(desligamento_id, admin)
        with banco.conectar() as conexao:
            conexao.execute(
                "UPDATE tarefas SET status='Concluída' WHERE recurso_tipo='rh_desligamentos' AND recurso_id=?",
                (desligamento_id,),
            )
        concluir_desligamento(desligamento_id, admin)
        self.assertEqual(obter_colaborador(colaborador_id, admin)["status"], "Desligado")

    def test_ferias_impedem_conflito_e_usam_aprovacao_central(self):
        admin, _ = self._ambiente(); self._admissao(admin)
        colaborador_id = listar_colaboradores(admin)["registros"][0]["id"]
        registro_id = solicitar_ferias_ausencia(
            {"colaborador_id": colaborador_id, "tipo": "Férias", "inicio": "01/09/2026", "fim": "10/09/2026", "saldo_antes": 30},
            admin,
        )
        with self.assertRaisesRegex(ValueError, "conflita"):
            solicitar_ferias_ausencia(
                {"colaborador_id": colaborador_id, "tipo": "Férias", "inicio": "05/09/2026", "fim": "15/09/2026"},
                admin,
            )
        decidir_ferias_ausencia(registro_id, True, "Planejamento aprovado", admin)
        self.assertEqual(listar_secao("ferias", admin)[0]["status"], "Aprovado")

    def test_beneficios_folha_contracheque_e_integracao_financeira(self):
        admin, pasta = self._ambiente(); self._admissao(admin)
        colaborador_id = listar_colaboradores(admin)["registros"][0]["id"]
        beneficio = salvar_beneficio(
            {"nome": "Gympass", "tipo": "Bem-estar", "custo_empresa": "120,00", "desconto_colaborador": "30,00"},
            admin,
        )
        vincular_beneficio(colaborador_id, beneficio, "10/08/2026", admin)
        folha = abrir_folha("2026-08", admin)
        adicionar_evento_folha(folha, colaborador_id, {"codigo": "VT", "descricao": "Vale-transporte", "natureza": "Desconto", "valor": "220,00"}, admin)
        fechar_folha(folha, admin)
        contracheque = Path(gerar_contracheque(folha, colaborador_id, admin))
        self.assertTrue(contracheque.is_file())
        self.assertGreater(contracheque.stat().st_size, 500)
        with banco.conectar() as conexao:
            tarefa = conexao.execute("SELECT * FROM tarefas WHERE modulo='financeiro' AND recurso_tipo='rh_folhas' AND recurso_id=?", (folha,)).fetchone()
        self.assertIsNotNone(tarefa)
        relatorio = pasta / "folha.xlsx"
        gerar_relatorio_rh("Folha", "XLSX", relatorio, admin)
        self.assertTrue(relatorio.is_file())

    def test_talentos_documentos_solicitacoes_e_analytics(self):
        admin, pasta = self._ambiente(); self._admissao(admin)
        colaborador_id = listar_colaboradores(admin)["registros"][0]["id"]
        cargo = salvar_cargo({"codigo": "RH-SR", "titulo": "Analista RH Sênior", "nivel": "Sênior", "salario_minimo": "7000", "salario_maximo": "9500"}, admin)
        vaga = criar_vaga({"titulo": "Analista RH", "cargo_id": cargo, "quantidade": 1, "motivo": "Expansão"}, admin)
        salvar_avaliacao({"colaborador_id": colaborador_id, "ciclo": "2026-S2", "tipo": "Gestor", "nota": 8.5, "feedback": "Bom desempenho", "status": "Concluída"}, admin)
        salvar_pdi({"colaborador_id": colaborador_id, "titulo": "Liderança", "objetivo": "Preparar para liderança", "inicio": "10/08/2026", "prazo": "10/02/2027", "progresso": 20}, admin)
        treinamento = salvar_treinamento({"titulo": "LGPD para RH", "tipo": "Interno", "carga_horaria": 4, "obrigatorio": True}, admin)
        registrar_ponto(colaborador_id, {"data": "10/08/2026", "entrada": "08:00", "intervalo_inicio": "12:00", "intervalo_fim": "13:00", "saida": "17:00"}, admin)
        arquivo = pasta / "contrato.txt"; arquivo.write_text("contrato de trabalho", encoding="utf-8")
        documento = registrar_documento(colaborador_id, {"categoria": "Contratual", "titulo": "Contrato", "classificacao": "Restrito"}, arquivo, admin)
        equipamento = vincular_equipamento(colaborador_id, {"patrimonio": "TI-0001", "descricao": "Notebook corporativo", "origem_modulo": "ti", "entregue_em": "10/08/2026"}, admin)
        solicitacao = criar_solicitacao({"colaborador_id": colaborador_id, "tipo": "Documento", "titulo": "Declaração de vínculo"}, admin)
        self.assertGreater(vaga, 0); self.assertGreater(treinamento, 0)
        self.assertGreater(documento, 0); self.assertGreater(equipamento, 0); self.assertGreater(solicitacao, 0)
        self.assertEqual(len(exportar_dataframe_rh(admin)), 1)
        self.assertGreaterEqual(len(listar_auditoria_rh(admin)), 8)

    def test_permissao_granular_pode_ocultar_remuneracao(self):
        admin, _ = self._ambiente(); self._admissao(admin)
        usuario = criar_usuario("Gestor", "gestor", "SenhaGestor#123", ator=admin, perfil_acesso="analista")
        salvar_permissoes_usuario(usuario["id"], {"rh": {"ler": True, "escrever": False, "aprovar": False}}, admin)
        salvar_permissao_acao(usuario["id"], "visualizar_remuneracao", False, admin)
        ator = {**usuario, "_empresa_id": SESSAO.empresa_id, "_filial_id": SESSAO.filial_id}
        pagina = listar_colaboradores(ator)
        self.assertIsNone(pagina["registros"][0]["salario_centavos"])
        self.assertNotIn("salario_centavos", exportar_dataframe_rh(ator).columns)

    def test_portal_pessoal_e_gestor_enxergam_apenas_escopo_autorizado(self):
        admin, _ = self._ambiente()
        self._admissao(admin, "Ana Silva")
        self._admissao(admin, "Bruno Lima")
        self._admissao(admin, "Carla Souza")
        gestor = criar_usuario("Gestor", "gestor.equipe", "SenhaGestor#123", ator=admin, perfil_acesso="gestor_pessoas")
        colaborador = criar_usuario("Bruno", "bruno.portal", "SenhaPortal#123", ator=admin, perfil_acesso="colaborador")
        with banco.conectar() as conexao:
            ana = conexao.execute("SELECT id FROM rh_colaboradores WHERE nome_completo='Ana Silva'").fetchone()["id"]
            bruno = conexao.execute("SELECT id FROM rh_colaboradores WHERE nome_completo='Bruno Lima'").fetchone()["id"]
            carla = conexao.execute("SELECT id FROM rh_colaboradores WHERE nome_completo='Carla Souza'").fetchone()["id"]
            conexao.execute("UPDATE rh_colaboradores SET usuario_id=? WHERE id=?", (gestor["id"], ana))
            conexao.execute("UPDATE rh_colaboradores SET usuario_id=?, gestor_id=? WHERE id=?", (colaborador["id"], ana, bruno))
        escopo = {"_empresa_id": SESSAO.empresa_id, "_filial_id": SESSAO.filial_id}
        visao_gestor = listar_colaboradores({**gestor, **escopo})["registros"]
        visao_pessoal = listar_colaboradores({**colaborador, **escopo})["registros"]
        self.assertEqual({x["id"] for x in visao_gestor}, {ana, bruno})
        self.assertEqual([x["id"] for x in visao_pessoal], [bruno])
        self.assertNotIn(carla, {x["id"] for x in visao_gestor})


if __name__ == "__main__":
    unittest.main()
