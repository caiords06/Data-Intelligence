"""Smoke Tk real das experiências e workspaces introduzidos na V9.

Executar no build Windows com ``RUN_TK_SMOKE=1``. Em Linux/CI use xvfb-run.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto


@unittest.skipUnless(os.environ.get("RUN_TK_SMOKE") == "1", "Smoke Tk exige display gráfico.")
class InterfaceSmokeV9Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        pasta = Path(self.tmp.name)
        self.patch_db = patch.object(banco, "DB_PATH", pasta / "v9-ui.db")
        self.patch_storage = patch.object(banco, "STORAGE_DIR", pasta)
        self.patch_db.start(); self.patch_storage.start()
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "adminv9", "SenhaAdmin#123", "admin@empresa.local")
        SESSAO.iniciar(admin)
        inicializar_enterprise(); obter_contexto()
        chaves = (
            "inicio", "modulos", "modulo", "registros_modulo", "secao_modulo",
            "analisar_modulo", "analytics", "analytics_secao", "nova", "historico",
            "aprovacoes", "notificacoes", "correio", "configuracoes", "organizacao",
            "perfis", "usuarios", "busca", "ferramenta", "sair", "voltar",
        )
        self.nav = {k: (lambda *a, **kw: None) for k in chaves}

    def tearDown(self):
        SESSAO.encerrar()
        self.patch_db.stop(); self.patch_storage.stop(); self.tmp.cleanup()

    @staticmethod
    def _fechar(root):
        try:
            ids = root.tk.call("after", "info")
        except tk.TclError:
            ids = ()
        for ident in ids:
            try: root.after_cancel(ident)
            except tk.TclError: pass
        try: root.destroy()
        except tk.TclError: pass

    def _construir(self, fabrica):
        root = tk.Tk(); root.geometry("1440x900+0+0")
        try:
            fabrica(root)
            root.update_idletasks(); root.update()
            self.assertGreater(root.winfo_width(), 0)
        finally:
            self._fechar(root)

    def test_experiencias_departamentais_v9_constroem(self):
        from interface.experiencias_departamentais import TelaExperienciaDepartamental
        for modulo in ("rh", "financeiro", "estoque", "compras", "marketing", "administrativo", "juridico", "comercial"):
            with self.subTest(modulo=modulo):
                self._construir(lambda r, m=modulo: TelaExperienciaDepartamental(r, self.nav, m))

    def test_workspaces_visuais_v9_constroem(self):
        from interface.operacoes_visuais import TelaOperacaoVisual
        casos = (("marketing", "calendario"), ("administrativo", "facilities"), ("juridico", "processos"), ("comercial", "pipeline"))
        for modulo, secao in casos:
            with self.subTest(modulo=modulo, secao=secao):
                self._construir(lambda r, m=modulo, s=secao: TelaOperacaoVisual(r, self.nav, m, s))

    def test_correio_e_grades_especializadas_constroem(self):
        from interface.correio import TelaCorreio
        from interface.financeiro import TelaFinanceiro
        from interface.rh import TelaRH
        from interface.estoque import TelaEstoque
        from interface.compras import TelaCompras
        from interface.tecnologia import TelaTecnologia
        casos = (
            ("correio", lambda r: TelaCorreio(r, self.nav)),
            ("financeiro_lancamentos", lambda r: TelaFinanceiro(r, self.nav, "lancamentos")),
            ("rh_colaboradores", lambda r: TelaRH(r, self.nav, "colaboradores")),
            ("estoque_itens", lambda r: TelaEstoque(r, self.nav, "itens")),
            ("compras_fornecedores", lambda r: TelaCompras(r, self.nav, "fornecedores")),
            ("tecnologia_cockpit", lambda r: TelaTecnologia(r, self.nav, "cockpit")),
        )
        for nome, fabrica in casos:
            with self.subTest(tela=nome): self._construir(fabrica)
