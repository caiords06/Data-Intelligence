from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from dados.indicadores import calcular_indicadores
from enterprise.banco import inicializar_enterprise
from enterprise.backups import criar_backup, verificar_backup
from enterprise.central import listar_aprovacoes, remover_aprovacao_da_fila
from enterprise.contexto import obter_contexto
from enterprise.jobs import (
    atualizar_job,
    concluir_job,
    criar_job,
    iniciar_job,
    listar_jobs,
)
from enterprise.modulos import (
    alterar_estado_registro,
    criar_registro,
    exportar_dataframe_modulo,
    listar_historico_registro,
    listar_registros_paginados,
)


class EstabilizacaoV6Tests(unittest.TestCase):
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

    def test_toda_conexao_ativa_integridade_referencial(self):
        self._ambiente()
        with banco.conectar() as conexao:
            self.assertEqual(conexao.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                conexao.execute(
                    """
                    INSERT INTO movimentos_estoque (
                        empresa_id, item_id, tipo, quantidade
                    ) VALUES (?, 999999, 'Entrada', 1)
                    """,
                    (SESSAO.empresa_id,),
                )

    def test_analytics_nao_trunca_em_mil_registros(self):
        admin = self._ambiente()
        with banco.conectar() as conexao:
            conexao.executemany(
                """
                INSERT INTO lancamentos_financeiros (
                    empresa_id, filial_id, tipo, descricao, valor,
                    valor_centavos, status, estado_registro
                ) VALUES (?, ?, 'Receita', ?, 1.25, 125, 'Recebido', 'Ativo')
                """,
                [
                    (SESSAO.empresa_id, SESSAO.filial_id, f"Lançamento {indice}")
                    for indice in range(1005)
                ],
            )
        dataframe = exportar_dataframe_modulo("financeiro", admin)
        self.assertEqual(len(dataframe), 1005)

    def test_ciclo_de_vida_paginacao_e_auditoria(self):
        admin = self._ambiente()
        registro_id = criar_registro(
            "financeiro",
            {
                "descricao": "Contrato de suporte",
                "tipo": "Despesa",
                "categoria": "Tecnologia",
                "centro_custo_id": "",
                "valor": "10,235",
                "vencimento": "20/08/2026",
                "status": "Pendente",
            },
            admin,
        )
        with banco.conectar() as conexao:
            registro = conexao.execute(
                "SELECT valor_centavos FROM lancamentos_financeiros WHERE id = ?",
                (registro_id,),
            ).fetchone()
        self.assertEqual(registro["valor_centavos"], 1024)

        ativos = listar_registros_paginados(
            "financeiro", admin, pagina=1, tamanho=25, pesquisa="suporte"
        )
        self.assertEqual(ativos["total"], 1)

        alterar_estado_registro("financeiro", registro_id, "Arquivado", admin)
        self.assertEqual(
            listar_registros_paginados("financeiro", admin, estado="Ativo")["total"],
            0,
        )
        self.assertEqual(
            listar_registros_paginados("financeiro", admin, estado="Arquivado")["total"],
            1,
        )
        historico = listar_historico_registro("financeiro", registro_id, admin)
        self.assertEqual(historico[0]["acao"], "Arquivado")

    def test_aprovacao_e_removida_sem_exclusao_fisica(self):
        admin = self._ambiente()
        criar_registro(
            "compras",
            {
                "item": "Notebook",
                "quantidade": "1",
                "fornecedor": "Fornecedor A",
                "valor_estimado": "4999,90",
                "centro_custo_id": "",
                "status": "Pendente",
            },
            admin,
        )
        aprovacao_id = listar_aprovacoes(admin)[0]["id"]
        remover_aprovacao_da_fila(aprovacao_id, admin)
        self.assertEqual(listar_aprovacoes(admin), [])
        with banco.conectar() as conexao:
            registro = conexao.execute(
                "SELECT excluido_em FROM aprovacoes WHERE id = ?",
                (aprovacao_id,),
            ).fetchone()
        self.assertIsNotNone(registro["excluido_em"])

    def test_motores_departamentais(self):
        casos = {
            "compras": pd.DataFrame(
                {"fornecedor": ["A", "A"], "valor_estimado": [100, 50], "status": ["Aprovado", "Pendente"]}
            ),
            "ti": pd.DataFrame(
                {"titulo": ["Erro", "Erro"], "prioridade": ["Crítica", "Baixa"], "status": ["Aberto", "Concluído"]}
            ),
            "marketing": pd.DataFrame(
                {"investimento": [100], "leads": [10], "conversoes": [2], "receita": [500], "canal": ["Ads"]}
            ),
            "administrativo": pd.DataFrame(
                {"valor": [100, 50], "categoria": ["Viagem", "Viagem"], "status": ["Pendente", "Aprovado"]}
            ),
            "juridico": pd.DataFrame(
                {"valor": [1000], "risco": ["Alto"], "status": ["Ativo"], "vencimento": [pd.Timestamp.now()]}
            ),
            "comercial": pd.DataFrame(
                {"valor": [1000, 500], "etapa": ["Proposta", "Ganho"], "status": ["Aberto", "Ganho"]}
            ),
        }
        chaves = {
            "compras": "valor_solicitado",
            "ti": "total_chamados",
            "marketing": "roas",
            "administrativo": "valor_total",
            "juridico": "valor_em_risco",
            "comercial": "pipeline_aberto",
        }
        for categoria, dataframe in casos.items():
            with self.subTest(categoria=categoria):
                resultado = calcular_indicadores(categoria, dataframe, {})
                self.assertIn(chaves[categoria], resultado)
                self.assertEqual(resultado["categoria_motor"], categoria)

    def test_job_manager_e_backup_verificado(self):
        admin = self._ambiente()
        job = criar_job("analise", "Análise financeira", admin)
        iniciar_job(job["id"], admin)
        atualizar_job(job["id"], 63, "Calculando indicadores", admin)
        concluir_job(job["id"], admin, {"categoria": "financeiro"})
        registro = listar_jobs(admin)[0]
        self.assertEqual(registro["status"], "Concluído")
        self.assertEqual(registro["progresso"], 100)

        with tempfile.TemporaryDirectory() as pasta:
            backup = criar_backup(admin, pasta)
            verificacao = verificar_backup(
                backup["arquivo"],
                backup["hash_sha256"],
            )
        self.assertTrue(verificacao["integro"])
        self.assertTrue(verificacao["hash_valido"])


if __name__ == "__main__":
    unittest.main()
