"""Regressões dos bugs corrigidos na rodada de estabilização V8.2."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.central import listar_atividades, listar_notificacoes
from enterprise.contexto import obter_contexto, obter_permissoes_usuario
from enterprise.ferramentas import criar_tarefa
from enterprise.jobs import cancelar_job, criar_job, iniciar_job, listar_jobs
from enterprise.modulos import calcular_resumo_modulo, criar_registro, movimentar_estoque
from enterprise.organizacao import criar_empresa, criar_filial, definir_contexto_empresa


class CorrecoesV82Tests(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        pasta = Path(self.temporario.name)
        self.patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        self.patch_storage = patch.object(banco, "STORAGE_DIR", pasta)
        self.patch_db.start()
        self.patch_storage.start()
        banco.inicializar_banco()
        self.admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(self.admin)
        inicializar_enterprise()
        contexto = obter_contexto()
        self.empresa_id = contexto["empresa_id"]
        self.filial_id = contexto["filial_id"]

    def tearDown(self):
        SESSAO.encerrar()
        self.patch_db.stop()
        self.patch_storage.stop()
        self.temporario.cleanup()

    def _ator(self, empresa_id=None, filial_id=None):
        ator = dict(self.admin)
        ator["_empresa_id"] = int(empresa_id or self.empresa_id)
        ator["_filial_id"] = int(filial_id or self.filial_id)
        return ator

    def test_eventos_e_movimentacoes_ficam_na_filial_correta(self):
        filial_2 = criar_filial("Filial 2", "F2", ator=self.admin)
        ator_1 = self._ator()
        criar_registro(
            "ti",
            {
                "titulo": "Servidor indisponível",
                "categoria": "Infraestrutura",
                "prioridade": "Crítica",
                "status": "Aberto",
                "responsavel": "",
            },
            ator_1,
        )
        self.assertTrue(
            any("Servidor indisponível" in item["descricao"] for item in listar_atividades(ator_1))
        )
        ator_2 = self._ator(filial_id=filial_2)
        self.assertFalse(
            any("Servidor indisponível" in item["descricao"] for item in listar_atividades(ator_2))
        )
        self.assertFalse(
            any("Servidor indisponível" in item["mensagem"] for item in listar_notificacoes(ator_2))
        )

        item_id = criar_registro(
            "estoque",
            {
                "codigo": "NOTE-82",
                "descricao": "Notebook",
                "categoria": "TI",
                "quantidade": "1",
                "estoque_minimo": "1",
                "custo": "2500",
                "localizacao": "TI",
                "status": "Ativo",
            },
            ator_1,
        )
        movimentar_estoque(item_id, "Entrada", 2, ator_1)
        with banco.conectar() as conexao:
            movimento = conexao.execute(
                "SELECT filial_id FROM movimentos_estoque WHERE item_id=? ORDER BY id DESC LIMIT 1",
                (item_id,),
            ).fetchone()
        self.assertEqual(movimento["filial_id"], self.filial_id)
        with self.assertRaises(sqlite3.IntegrityError):
            with banco.conectar() as conexao:
                conexao.execute(
                    """
                    INSERT INTO movimentos_estoque (
                        empresa_id, filial_id, item_id, tipo, quantidade, criado_por
                    ) VALUES (?, ?, ?, 'Entrada', 1, ?)
                    """,
                    (self.empresa_id, filial_2, item_id, self.admin["id"]),
                )

        # O SKU é único por filial, não pela empresa inteira.
        item_filial_2 = criar_registro(
            "estoque",
            {
                "codigo": "NOTE-82",
                "descricao": "Notebook filial 2",
                "categoria": "TI",
                "quantidade": "1",
                "estoque_minimo": "1",
                "custo": "2500",
                "localizacao": "TI",
                "status": "Ativo",
            },
            ator_2,
        )
        self.assertNotEqual(item_filial_2, item_id)

    def test_usuario_restrito_nao_pode_trocar_de_filial(self):
        filial_2 = criar_filial("Filial 2", "F2", ator=self.admin)
        usuario = criar_usuario(
            "Analista filial", "analista.filial", "SenhaAnalista#123", ator=self.admin
        )
        SESSAO.encerrar()
        SESSAO.iniciar(usuario)
        with self.assertRaises(PermissionError):
            definir_contexto_empresa(self.empresa_id, filial_2)

    def test_responsavel_de_outra_empresa_e_rejeitado(self):
        ator_empresa_1 = self._ator()
        empresa_2 = criar_empresa("Empresa 2", ator=self.admin)
        definir_contexto_empresa(empresa_2)
        filial_2 = criar_filial("Matriz E2", "M2", ator=self.admin)
        definir_contexto_empresa(empresa_2, filial_2)
        usuario_2 = criar_usuario(
            "Usuário empresa 2", "usuario.e2", "SenhaUsuario#123", ator=self.admin
        )
        definir_contexto_empresa(self.empresa_id, self.filial_id)
        with self.assertRaises(ValueError):
            criar_tarefa(
                {
                    "modulo": "ti",
                    "titulo": "Tarefa fora do escopo",
                    "responsavel_id": usuario_2["id"],
                },
                ator_empresa_1,
            )


    def test_permissoes_nao_podem_ser_consultadas_fora_da_empresa(self):
        empresa_2 = criar_empresa("Empresa permissões", ator=self.admin)
        definir_contexto_empresa(empresa_2)
        filial_2 = criar_filial("Matriz permissões", "MP", ator=self.admin)
        definir_contexto_empresa(empresa_2, filial_2)
        usuario_2 = criar_usuario(
            "Usuário permissões", "usuario.permissoes", "SenhaUsuario#123", ator=self.admin
        )
        definir_contexto_empresa(self.empresa_id, self.filial_id)
        with self.assertRaises(PermissionError):
            obter_permissoes_usuario(usuario_2["id"], self.admin)

    def test_cancelamento_e_estado_terminal_e_nao_falha(self):
        ator = self._ator()
        job = criar_job("analise", "Teste de cancelamento", ator)
        iniciar_job(job["id"], ator)
        cancelar_job(job["id"], ator, "Cancelado no teste.")
        registro = next(item for item in listar_jobs(ator) if item["id"] == job["id"])
        self.assertEqual(registro["status"], "Cancelado")
        self.assertEqual(registro["cancelamento_solicitado"], 1)

    def test_regras_de_negocio_rejeitam_dados_inconsistentes(self):
        ator = self._ator()
        with self.assertRaises(ValueError):
            criar_registro(
                "marketing",
                {
                    "nome": "Campanha inválida",
                    "canal": "Meta Ads",
                    "investimento": "100",
                    "leads": "2",
                    "conversoes": "3",
                    "receita": "1000",
                    "status": "Ativa",
                },
                ator,
            )
        with self.assertRaises(ValueError):
            criar_registro(
                "comercial",
                {
                    "cliente": "Cliente X",
                    "etapa": "Ganho",
                    "valor": "1000",
                    "responsavel": "Ana",
                    "status": "Aberto",
                },
                ator,
            )
        with self.assertRaises(ValueError):
            criar_registro(
                "marketing",
                {
                    "nome": "Campanha decimal",
                    "canal": "Meta Ads",
                    "investimento": "100",
                    "leads": "2,5",
                    "conversoes": "1",
                    "receita": "1000",
                    "status": "Ativa",
                },
                ator,
            )

    def test_juridico_nao_conta_contrato_vencido_como_vencendo(self):
        ator = self._ator()
        criar_registro(
            "juridico",
            {
                "titulo": "Contrato vencido",
                "parte": "Fornecedor A",
                "valor": "1000",
                "risco": "Baixo",
                "vencimento": (date.today() - timedelta(days=5)).isoformat(),
                "status": "Ativo",
            },
            ator,
        )
        criar_registro(
            "juridico",
            {
                "titulo": "Contrato a vencer",
                "parte": "Fornecedor B",
                "valor": "2000",
                "risco": "Médio",
                "vencimento": (date.today() + timedelta(days=5)).isoformat(),
                "status": "Ativo",
            },
            ator,
        )
        resumo = calcular_resumo_modulo("juridico", ator)
        cards = {titulo: valor for titulo, valor, _tipo in resumo["cards"]}
        self.assertEqual(cards["VENCEM EM 30 DIAS"], 1)


if __name__ == "__main__":
    unittest.main()
