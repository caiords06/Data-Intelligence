"""Regressões funcionais da rodada V8.2.1 de navegação e organização."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.organizacao import (
    criar_empresa,
    listar_empresas,
    remover_empresa_criada_sessao,
)
from historico.repositorio import (
    excluir_analises,
    listar_historico,
    registrar_analise,
)
from interface.navegacao_analytics import MENU_ANALYTICS


class HotfixV821Tests(unittest.TestCase):
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
        obter_contexto()

    def tearDown(self):
        SESSAO.encerrar()
        self.patch_db.stop()
        self.patch_storage.stop()
        self.temporario.cleanup()

    def _resultado(self, nome):
        return {
            "dataframe": pd.DataFrame({"valor": [1, 2]}),
            "arquivos": [nome],
            "categoria": "vendas",
            "configuracao": {"fonte": "computador"},
            "indicadores": {},
            "qualidade": {"score_qualidade": 100.0, "nivel_qualidade": "Excelente"},
            "temporal": {},
        }

    def test_exclusao_multipla_historico_e_atomica(self):
        primeiro = registrar_analise(self._resultado("a.xlsx"), self.admin["id"])
        segundo = registrar_analise(self._resultado("b.xlsx"), self.admin["id"])
        quantidade = excluir_analises((primeiro, segundo), self.admin)
        self.assertEqual(quantidade, 2)
        ids_restantes = {item["id"] for item in listar_historico(self.admin)}
        self.assertNotIn(primeiro, ids_restantes)
        self.assertNotIn(segundo, ids_restantes)

        terceiro = registrar_analise(self._resultado("c.xlsx"), self.admin["id"])
        with self.assertRaises(ValueError):
            excluir_analises((terceiro, 999999), self.admin)
        ids_restantes = {item["id"] for item in listar_historico(self.admin)}
        self.assertIn(terceiro, ids_restantes)

    def test_empresa_criada_na_sessao_pode_ser_removida_com_seguranca(self):
        empresa_id = criar_empresa("Empresa temporária", ator=self.admin)
        self.assertTrue(SESSAO.empresa_criada_na_sessao(empresa_id))
        remover_empresa_criada_sessao(empresa_id, self.admin)
        self.assertFalse(SESSAO.empresa_criada_na_sessao(empresa_id))
        ativas = {item["id"] for item in listar_empresas() if item["ativo"]}
        self.assertNotIn(empresa_id, ativas)
        with banco.conectar() as conexao:
            empresa = conexao.execute(
                "SELECT ativo FROM empresas WHERE id=?", (empresa_id,)
            ).fetchone()
        self.assertEqual(empresa["ativo"], 0)

    def test_empresa_preexistente_ou_usuario_comum_nao_podem_usar_remocao_de_sessao(self):
        with banco.conectar() as conexao:
            cursor = conexao.execute(
                "INSERT INTO empresas (nome, ativo) VALUES ('Empresa antiga', 1)"
            )
            antiga = int(cursor.lastrowid)
        with self.assertRaises(ValueError):
            remover_empresa_criada_sessao(antiga, self.admin)

        temporaria = criar_empresa("Empresa para permissão", ator=self.admin)
        usuario = criar_usuario(
            "Usuário comum", "usuario.hotfix", "SenhaUsuario#123", ator=self.admin
        )
        with self.assertRaises(PermissionError):
            remover_empresa_criada_sessao(temporaria, usuario)

    def test_rotulos_analytics_sao_canonicos(self):
        menu = {chave: titulo for chave, _icone, titulo in MENU_ANALYTICS}
        self.assertEqual(menu["visao"], "Visão executiva")
        self.assertEqual(menu["insights"], "Insights")
        self.assertEqual(menu["conjuntos"], "Explorar dados")
        self.assertEqual(menu["relatorios"], "Relatórios")
        self.assertEqual(menu["visualizacoes"], "Visualizações")
        self.assertEqual(menu["regras"], "Regras analíticas")
        self.assertNotIn("modelos", menu)
        self.assertNotIn("assistente", menu)


if __name__ == "__main__":
    unittest.main()
