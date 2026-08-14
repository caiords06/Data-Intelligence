from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.central import (
    busca_universal,
    decidir_aprovacao,
    listar_aprovacoes,
    listar_atividades,
    listar_notificacoes,
)
from enterprise.contexto import (
    obter_contexto,
    salvar_permissoes_usuario,
    tem_permissao,
)
from enterprise.modulos import (
    calcular_resumo_modulo,
    criar_registro,
    exportar_dataframe_modulo,
    listar_registros,
    movimentar_estoque,
)
from core.orquestrador import OrquestradorAnalise
from enterprise.integracoes import listar_integracoes, registrar_integracao
from enterprise.organizacao import (
    criar_empresa,
    definir_contexto_empresa,
    listar_departamentos,
    listar_empresas,
)
from enterprise.workflows import criar_workflow, listar_workflows


class EnterpriseV5Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta)
        patch_db.start()
        patch_storage.start()
        self.addCleanup(patch_db.stop)
        self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        obter_contexto()
        return admin

    def test_estrutura_multiempresa_e_contexto(self):
        admin = self._ambiente()
        self.assertGreaterEqual(len(listar_departamentos()), 8)
        empresa_id = criar_empresa("Empresa secundária", ator=admin)
        definir_contexto_empresa(empresa_id)
        self.assertEqual(obter_contexto()["empresa_nome"], "Empresa secundária")
        self.assertEqual(len(listar_empresas()), 2)

    def test_permissoes_por_modulo(self):
        admin = self._ambiente()
        usuario = criar_usuario(
            "Analista RH", "analistarh", "SenhaAnalista#123", ator=admin
        )
        salvar_permissoes_usuario(
            usuario["id"],
            {"rh": {"ler": True, "escrever": True, "aprovar": False}},
            admin,
        )
        self.assertTrue(tem_permissao(usuario, "rh", "escrever"))
        self.assertFalse(tem_permissao(usuario, "financeiro", "ler"))
        self.assertFalse(tem_permissao(usuario, "analytics", "ler"))

    def test_modulos_geram_indicadores_atividades_e_alertas(self):
        admin = self._ambiente()
        criar_registro(
            "rh",
            {
                "nome": "Ana Silva",
                "email": "ana@empresa.com",
                "cargo": "Analista",
                "departamento_id": "",
                "centro_custo_id": "",
                "salario": "5000,00",
                "admissao": "09/08/2026",
                "status": "Ativo",
            },
            admin,
        )
        estoque_id = criar_registro(
            "estoque",
            {
                "codigo": "NOTE-01",
                "descricao": "Notebook Dell",
                "categoria": "TI",
                "quantidade": "3",
                "estoque_minimo": "5",
                "custo": "4500",
                "localizacao": "Estoque TI",
                "status": "Ativo",
            },
            admin,
        )
        movimentar_estoque(estoque_id, "Entrada", 4, admin)
        self.assertEqual(
            calcular_resumo_modulo("rh", admin)["cards"][1][1],
            1,
        )
        self.assertEqual(
            calcular_resumo_modulo("estoque", admin)["cards"][1][1],
            7.0,
        )
        self.assertGreaterEqual(len(listar_atividades(admin)), 3)
        self.assertGreaterEqual(len(listar_notificacoes(admin)), 1)
        self.assertEqual(len(busca_universal("Notebook", admin)), 1)

    def test_aprovacao_humana_atualiza_solicitacao(self):
        admin = self._ambiente()
        criar_registro(
            "compras",
            {
                "item": "Cadeira ergonômica",
                "quantidade": "2",
                "fornecedor": "Fornecedor A",
                "valor_estimado": "2400",
                "centro_custo_id": "",
                "status": "Pendente",
            },
            admin,
        )
        aprovacao = listar_aprovacoes(admin)[0]
        self.assertEqual(aprovacao["status"], "Pendente")
        decidir_aprovacao(aprovacao["id"], "Aprovado", "Orçamento validado", admin)
        self.assertEqual(listar_aprovacoes(admin)[0]["status"], "Aprovado")
        registro = listar_registros("compras", admin)[0]
        self.assertEqual(registro["status"], "Aprovado")

    def test_workflow_seguro_gera_alerta_sem_executar_acao_sensivel(self):
        admin = self._ambiente()
        criar_workflow(
            "Alertar despesa relevante",
            "financeiro",
            "registro_criado",
            {
                "todos": [
                    {"campo": "tipo", "operador": "igual", "valor": "Despesa"},
                    {"campo": "valor", "operador": "maior", "valor": 1000},
                ]
            },
            [
                {
                    "tipo": "notificar",
                    "titulo": "Despesa relevante",
                    "mensagem": "{descricao}: R$ {valor}",
                    "nivel": "aviso",
                }
            ],
            admin,
        )
        criar_registro(
            "financeiro",
            {
                "descricao": "Serviço de nuvem",
                "tipo": "Despesa",
                "categoria": "Tecnologia",
                "centro_custo_id": "",
                "valor": "2500",
                "vencimento": "20/08/2026",
                "status": "Pendente",
            },
            admin,
        )
        alertas = listar_notificacoes(admin)
        self.assertTrue(any(item["titulo"] == "Despesa relevante" for item in alertas))
        self.assertEqual(len(listar_workflows(admin)), 1)

    def test_integration_hub_rejeita_segredos_em_texto_aberto(self):
        admin = self._ambiente()
        registrar_integracao(
            "google",
            "Google Workspace",
            "cofre://google/empresa-principal",
            {"dominio": "empresa.com", "escopos": ["drive.readonly"]},
            admin,
        )
        self.assertEqual(len(listar_integracoes(admin)), 1)
        with self.assertRaises(ValueError):
            registrar_integracao(
                "api_http",
                "API insegura",
                "",
                {"access_token": "segredo"},
                admin,
            )

    def test_dados_do_modulo_alimentam_o_mesmo_motor_analitico(self):
        admin = self._ambiente()
        for tipo, valor in (("Receita", "5000"), ("Despesa", "1200")):
            criar_registro(
                "financeiro",
                {
                    "descricao": f"Lançamento {tipo}",
                    "tipo": tipo,
                    "categoria": "Operacional",
                    "centro_custo_id": "",
                    "valor": valor,
                    "vencimento": "20/08/2026",
                    "status": "Pendente",
                },
                admin,
            )
        dataframe = exportar_dataframe_modulo("financeiro", admin)
        resultado = OrquestradorAnalise().processar_dataframe(
            dataframe,
            {"categoria": "financeiro", "fonte": "sistema"},
            nome_fonte="Módulo Financeiro",
        )
        self.assertEqual(resultado["categoria"], "financeiro")
        self.assertEqual(resultado["indicadores"]["receita_total"], 5000.0)
        self.assertEqual(resultado["indicadores"]["despesa_total"], 1200.0)


if __name__ == "__main__":
    unittest.main()
