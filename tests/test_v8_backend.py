"""Contratos funcionais acrescentados pela V8."""

from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from dados.fontes import importar_sqlite
from dados.leitor import carregar_planilha
from enterprise.banco import inicializar_enterprise
from enterprise.central import listar_notificacoes
from enterprise.contexto import obter_contexto
from enterprise.ferramentas import (
    arquivar_tarefa,
    atualizar_status_tarefa,
    criar_tarefa,
    gerar_relatorio,
    listar_documentos,
    listar_relatorios,
    listar_tarefas,
    obter_arquivo_relatorio,
    registrar_documento,
    verificar_documento,
)
from enterprise.integracoes import (
    definir_integracao_ativa,
    listar_integracoes,
    registrar_integracao,
)
from enterprise.modulos import criar_registro
from enterprise.recursos import (
    alterar_estado_recurso,
    atualizar_recurso,
    criar_recurso,
    listar_recursos,
    obter_recurso,
)
from enterprise.workflows import (
    criar_workflow,
    definir_workflow_ativo,
    listar_workflows,
)


class BackendV8Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
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
        return admin, pasta

    def test_crud_especializado_tem_filial_ciclo_de_vida_e_auditoria(self):
        admin, _ = self._ambiente()
        recurso_id = criar_recurso(
            "rh",
            "admissoes",
            {
                "identificacao": "Admissão de Ana Silva",
                "descricao": "Documentação inicial",
                "responsavel": "Equipe de RH",
                "status": "Pendente",
                "prioridade": "Alta",
                "valor": "1.234,56",
                "data_referencia": "12/08/2026",
            },
            admin,
        )
        registro = obter_recurso("rh", "admissoes", recurso_id, admin)
        self.assertEqual(registro["valor_centavos"], 123456)
        self.assertEqual(registro["filial_id"], SESSAO.filial_id)

        atualizar_recurso(
            "rh",
            "admissoes",
            recurso_id,
            {
                "identificacao": "Admissão de Ana Silva",
                "descricao": "Documentos conferidos",
                "responsavel": "Equipe de RH",
                "status": "Em andamento",
                "prioridade": "Média",
                "valor": "1.234,56",
                "data_referencia": "12/08/2026",
            },
            admin,
        )
        self.assertEqual(
            listar_recursos("rh", "admissoes", admin, pesquisa="conferidos")["total"],
            1,
        )
        alterar_estado_recurso("rh", "admissoes", recurso_id, "Arquivado", admin)
        self.assertEqual(
            listar_recursos("rh", "admissoes", admin, estado="Ativo")["total"],
            0,
        )
        self.assertEqual(
            listar_recursos("rh", "admissoes", admin, estado="Arquivado")["total"],
            1,
        )
        with banco.conectar() as conexao:
            eventos = conexao.execute(
                "SELECT acao FROM historico_alteracoes "
                "WHERE entidade = 'recursos_departamentais' AND entidade_id = ? "
                "ORDER BY id",
                (recurso_id,),
            ).fetchall()
        self.assertEqual([item["acao"] for item in eventos], ["Criado", "Atualizado", "Arquivado"])

    def test_workflow_e_integracao_possuem_controle_de_estado(self):
        admin, _ = self._ambiente()
        workflow_id = criar_workflow(
            "Avisar nova admissão",
            "rh",
            "registro_criado",
            {"todos": []},
            [
                {
                    "tipo": "notificar",
                    "titulo": "Nova admissão registrada",
                    "mensagem": "{identificacao}",
                    "nivel": "info",
                }
            ],
            admin,
        )
        criar_recurso(
            "rh",
            "admissoes",
            {"identificacao": "Admissão de Beatriz", "prioridade": "Média"},
            admin,
        )
        self.assertTrue(
            any(
                item["titulo"] == "Nova admissão registrada"
                for item in listar_notificacoes(admin)
            )
        )
        definir_workflow_ativo(workflow_id, False, admin)
        self.assertFalse(bool(listar_workflows(admin)[0]["ativo"]))

        integracao_id = registrar_integracao(
            "google",
            "Google Workspace",
            "cofre://empresa/google",
            {"dominio": "empresa.com", "escopos": ["drive.readonly"]},
            admin,
        )
        definir_integracao_ativa(integracao_id, True, admin)
        self.assertTrue(bool(listar_integracoes(admin)[0]["ativo"]))

    def test_tarefas_documentos_relatorios_e_importacao_sqlite(self):
        admin, pasta = self._ambiente()
        tarefa_id = criar_tarefa(
            {
                "modulo": "financeiro",
                "titulo": "Revisar fechamento mensal",
                "descricao": "Conferir lançamentos",
                "responsavel_id": admin["id"],
                "prioridade": "Alta",
                "vencimento": "15/08/2026",
            },
            admin,
        )
        atualizar_status_tarefa(tarefa_id, "Concluída", admin)
        self.assertEqual(listar_tarefas(admin)[0]["status"], "Concluída")
        arquivar_tarefa(tarefa_id, admin)
        self.assertEqual(listar_tarefas(admin), [])

        origem = pasta / "politica.txt"
        origem.write_text("Política corporativa V8", encoding="utf-8")
        documento_id = registrar_documento(
            str(origem),
            "Política corporativa",
            "financeiro",
            "Interno",
            admin,
        )
        self.assertEqual(len(listar_documentos(admin)), 1)
        verificacao = verificar_documento(documento_id, admin)
        self.assertTrue(verificacao["integro"])
        Path(verificacao["caminho"]).write_text("conteúdo alterado", encoding="utf-8")
        self.assertFalse(verificar_documento(documento_id, admin)["integro"])

        criar_registro(
            "financeiro",
            {
                "descricao": "Receita de serviços",
                "tipo": "Receita",
                "categoria": "Serviços",
                "centro_custo_id": "",
                "valor": "7250,40",
                "vencimento": "20/08/2026",
                "status": "Recebido",
            },
            admin,
        )
        relatorio = gerar_relatorio(
            "Fechamento <Agosto>", "financeiro", "HTML", admin
        )
        self.assertTrue(Path(relatorio["arquivo"]).is_file())
        conteudo = Path(relatorio["arquivo"]).read_text(encoding="utf-8")
        self.assertIn("Fechamento &lt;Agosto&gt;", conteudo)
        self.assertEqual(len(listar_relatorios(admin)), 1)
        self.assertEqual(
            Path(obter_arquivo_relatorio(relatorio["id"], admin)),
            Path(relatorio["arquivo"]),
        )

        banco_externo = pasta / "origem.sqlite"
        with closing(sqlite3.connect(banco_externo)) as conexao, conexao:
            conexao.execute("CREATE TABLE vendas (produto TEXT, valor REAL)")
            conexao.execute("INSERT INTO vendas VALUES ('Produto A', 10.5)")
        arquivo_csv = Path(importar_sqlite(str(banco_externo), "vendas"))
        self.assertTrue(arquivo_csv.is_file())
        self.assertIn("Produto A", arquivo_csv.read_text(encoding="utf-8-sig"))

    def test_admissao_cria_tarefas_visiveis_na_filial_atual(self):
        admin, _ = self._ambiente()
        criar_registro(
            "rh",
            {
                "nome": "Carla Souza",
                "email": "carla@empresa.com",
                "cargo": "Analista",
                "departamento_id": "",
                "centro_custo_id": "",
                "salario": "5000,00",
                "admissao": "10/08/2026",
                "status": "Ativo",
            },
            admin,
        )
        tarefas = listar_tarefas(admin)
        self.assertEqual(len(tarefas), 3)
        self.assertTrue(all(item["filial_id"] == SESSAO.filial_id for item in tarefas))

    def test_fontes_preparadas_e_formatos_adicionais_chegam_ao_motor(self):
        _admin, pasta = self._ambiente()
        json_path = pasta / "vendas.json"
        json_path.write_text(
            '[{"produto":"A","valor":10},{"produto":"B","valor":20}]',
            encoding="utf-8",
        )
        txt_path = pasta / "vendas.txt"
        txt_path.write_text("produto;valor\nA;10\nB;20\n", encoding="utf-8")
        self.assertEqual(len(carregar_planilha(json_path)), 2)
        self.assertEqual(len(carregar_planilha(txt_path)), 2)

        from core.orquestrador import OrquestradorAnalise

        resultado = OrquestradorAnalise().processar(
            [str(txt_path)],
            {"fonte": "url", "categoria": "cadastro"},
        )
        self.assertEqual(resultado["estrutural"]["total_registros"], 2)


if __name__ == "__main__":
    unittest.main()
