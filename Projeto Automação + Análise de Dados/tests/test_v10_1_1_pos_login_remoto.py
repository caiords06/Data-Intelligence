"""Regressões do fluxo Login -> contexto remoto -> tela principal V10.2.0."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch


class PosLoginRemotoTests(unittest.TestCase):
    def setUp(self):
        from auth.sessao import SESSAO
        from enterprise import servidor_cliente

        self._env = patch.dict(
            os.environ,
            {
                "DATA_INTELLIGENCE_NODE_ROLE": "central",
                "DATA_INTELLIGENCE_SERVER_URL": "http://127.0.0.1:8770",
            },
            clear=False,
        )
        self._env.start()
        SESSAO.encerrar()
        servidor_cliente._BOOTSTRAP_MEMORIA = {}
        servidor_cliente._TOKEN = "token-teste"

    def tearDown(self):
        from auth.sessao import SESSAO
        from enterprise import servidor_cliente

        SESSAO.encerrar()
        servidor_cliente._BOOTSTRAP_MEMORIA = {}
        servidor_cliente._TOKEN = None
        self._env.stop()

    @staticmethod
    def _bootstrap():
        return {
            "usuario": {
                "id": 41,
                "nome": "Usuário remoto",
                "usuario": "remoto",
                "perfil": "usuario",
                "perfil_acesso": "analista",
                "sessao_epoch": 2,
                "ativo": True,
            },
            "empresa": {"id": 3, "nome": "Empresa Remota"},
            "filial_id": 11,
            "filiais": [{"id": 11, "empresa_id": 3, "nome": "Matriz", "ativo": True}],
            "departamentos": [],
            "centros_custo": [],
            "permissoes": [
                {
                    "modulo": "financeiro",
                    "pode_ler": True,
                    "pode_escrever": False,
                    "pode_aprovar": False,
                }
            ],
        }

    def test_contexto_remoto_nao_abre_postgresql_na_estacao(self):
        from auth.sessao import SESSAO
        from enterprise import contexto, servidor_cliente

        servidor_cliente._BOOTSTRAP_MEMORIA = self._bootstrap()
        SESSAO.iniciar(dict(self._bootstrap()["usuario"]))

        with patch.object(
            contexto,
            "conectar",
            side_effect=AssertionError("Central/Cliente não pode abrir PostgreSQL diretamente."),
        ):
            self.assertEqual(contexto.garantir_contexto_sessao(), (3, 11))
            self.assertEqual(
                contexto.obter_contexto(),
                {
                    "empresa_id": 3,
                    "empresa_nome": "Empresa Remota",
                    "filial_id": 11,
                    "filial_nome": "Matriz",
                },
            )
            self.assertTrue(contexto.tem_permissao(SESSAO.usuario, "financeiro", "ler"))
            self.assertFalse(contexto.tem_permissao(SESSAO.usuario, "financeiro", "escrever"))
            self.assertIn("financeiro", contexto.listar_modulos_permitidos(SESSAO.usuario))

    def test_bootstrap_ausente_e_reobtido_do_servidor_sem_banco_local(self):
        from auth.sessao import SESSAO
        from enterprise import contexto

        SESSAO.iniciar(dict(self._bootstrap()["usuario"]))
        with patch.object(contexto, "conectar", side_effect=AssertionError("sem PostgreSQL local")), patch(
            "enterprise.servidor_cliente.validar_sessao_remota",
            return_value=self._bootstrap(),
        ) as validar:
            self.assertEqual(contexto.garantir_contexto_sessao(), (3, 11))
            validar.assert_called_once_with()

    def test_login_nao_destroi_tela_antes_da_navegacao(self):
        from pathlib import Path

        texto = Path("interface/login.py").read_text(encoding="utf-8")
        trecho = texto[texto.index("    def entrar(self):"):texto.index("    def destruir(self):")]
        self.assertIn("SESSAO.iniciar(usuario_autenticado)", trecho)
        self.assertIn("self.ao_entrar()", trecho)
        self.assertNotIn("self.destruir()", trecho)

    def test_tela_principal_renderiza_shell_antes_de_rpc_e_carrega_em_worker(self):
        from pathlib import Path

        texto = Path("interface/principal.py").read_text(encoding="utf-8")
        construtor = texto[texto.index("    def __init__(self, root, navegacao):"):texto.index("    @staticmethod", texto.index("    def __init__(self, root, navegacao):"))]
        self.assertLess(construtor.index("self.criar_interface()"), construtor.index("self._iniciar_carregamento()"))
        self.assertNotIn("resumo_cockpit(", construtor)
        self.assertNotIn("obter_contexto()", construtor)
        carregamento = texto[texto.index("    def _iniciar_carregamento(self):"):texto.index("    def _processar_carregamento", texto.index("    def _iniciar_carregamento(self):"))]
        self.assertIn("threading.Thread", carregamento)
        self.assertIn("daemon=True", carregamento)
        self.assertIn("resumo_cockpit(SESSAO.usuario)", carregamento)
        self.assertIn("obter_contexto()", carregamento)
        self.assertIn("self.root.after(", carregamento)

    def test_main_registra_excecoes_tk_e_oferece_recuperacao(self):
        from pathlib import Path

        texto = Path("main.py").read_text(encoding="utf-8")
        self.assertIn("report_callback_exception", texto)
        self.assertIn("desktop.jsonl", texto)
        self.assertIn("TENTAR NOVAMENTE", texto)
        self.assertIn("SAIR DA SESSÃO", texto)
        preparar = texto[texto.index("    def preparar_tela():"):texto.index("    def abrir_principal():")]
        self.assertLess(preparar.index("garantir_contexto_sessao()"), preparar.index("limpar_janela()"))
        limpar = texto[texto.index("    def limpar_janela():"):texto.index("    def _registrar_erro_interface") ]
        self.assertIn('janela.unbind("<Return>")', limpar)


if __name__ == "__main__":
    unittest.main()
