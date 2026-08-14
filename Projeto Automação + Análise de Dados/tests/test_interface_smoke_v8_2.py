"""Smoke tests reais de Tkinter para regressões de construção de telas.

São executados apenas com opt-in explícito. Em CI/local use
``RUN_TK_SMOKE=1 xvfb-run -a python -m pytest tests/test_interface_smoke_v8_2.py``.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto


@unittest.skipUnless(
    os.environ.get("RUN_TK_SMOKE") == "1",
    "Smoke gráfico exige RUN_TK_SMOKE=1 e um display Tk válido.",
)
class InterfaceSmokeV82Tests(unittest.TestCase):
    def setUp(self):
        # Mantém um único interpretador Tcl/Tk por método de teste.
        # As telas individuais são abertas em Toplevels. Isso evita recriar
        # dezenas de interpretadores Tk no mesmo processo, comportamento
        # desnecessário para este smoke e instável em alguns builds Windows.
        self._tk_master = tk.Tk()
        self._tk_master.withdraw()
        self.temporario = tempfile.TemporaryDirectory()
        pasta = Path(self.temporario.name)
        self.patch_db = patch.object(banco, "DB_PATH", pasta / "ui.db")
        self.patch_storage = patch.object(banco, "STORAGE_DIR", pasta)
        self.patch_db.start()
        self.patch_storage.start()
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        obter_contexto()
        self.navegacao = {
            chave: (lambda *args, **kwargs: None)
            for chave in (
                "inicio", "modulos", "modulo", "registros_modulo", "secao_modulo",
                "analisar_modulo", "analytics", "analytics_secao", "nova", "historico",
                "aprovacoes", "notificacoes", "configuracoes", "organizacao", "perfis",
                "usuarios", "busca", "ferramenta", "sair", "voltar",
            )
        }

    def tearDown(self):
        SESSAO.encerrar()
        self.patch_db.stop()
        self.patch_storage.stop()
        self.temporario.cleanup()
        self._finalizar_root(self._tk_master)

    def _nova_janela(self):
        # Toplevel possui o mesmo conjunto de operações de janela usado pelas
        # telas (geometry/title/protocol/update etc.), mas compartilha o mesmo
        # interpretador Tcl/Tk do teste.
        return tk.Toplevel(self._tk_master)

    @staticmethod
    def _finalizar_root(root):
        try:
            agendamentos = root.tk.call("after", "info")
        except tk.TclError:
            agendamentos = ()
        for identificador in agendamentos:
            try:
                root.after_cancel(identificador)
            except tk.TclError:
                pass
        try:
            root.destroy()
        except tk.TclError:
            pass

    @staticmethod
    def _widgets(widget, classe=None):
        encontrados = []
        for filho in widget.winfo_children():
            if classe is None or isinstance(filho, classe):
                encontrados.append(filho)
            encontrados.extend(InterfaceSmokeV82Tests._widgets(filho, classe))
        return encontrados

    def _botao_sidebar(self, root, texto):
        for botao in self._widgets(root, tk.Button):
            if texto in str(botao.cget("text")):
                return botao
        self.fail(f"Botão de sidebar não encontrado: {texto}")

    def test_telas_criticas_constroem_sem_tclerror_ou_typeerror(self):
        from interface.aprovacoes import TelaAprovacoes
        from interface.catalogo_modulos import TelaCatalogoModulos
        from interface.central_analytics import TelaCentralAnalytics
        from interface.configuracoes_app import TelaConfiguracoesApp
        from interface.ferramentas import TelaFerramentaCorporativa
        from interface.financeiro import TelaFinanceiro
        from interface.historico import TelaHistorico
        from interface.modulo_empresarial import TelaModuloEmpresarial
        from interface.notificacoes import TelaNotificacoes
        from interface.nova_analise import TelaNovaAnalise
        from interface.organizacao import TelaOrganizacao
        from interface.painel_modulo import TelaPainelModulo
        from interface.perfis_analise import TelaPerfisAnalise
        from interface.principal import TelaPrincipal
        from interface.rh import TelaRH
        from interface.tecnologia import TelaTecnologia
        from interface.usuarios import TelaUsuarios

        modulos = (
            "rh", "financeiro", "estoque", "compras", "ti",
            "marketing", "administrativo", "juridico", "comercial",
        )
        casos = [
            ("principal", lambda r: TelaPrincipal(r, self.navegacao)),
            ("catalogo", lambda r: TelaCatalogoModulos(r, self.navegacao)),
            ("central", lambda r: TelaCentralAnalytics(r, self.navegacao)),
            (
                "nova_analise",
                lambda r: TelaNovaAnalise(
                    r, lambda _config: None, navegacao=self.navegacao
                ),
            ),
            ("historico", lambda r: TelaHistorico(r, self.navegacao)),
            ("aprovacoes", lambda r: TelaAprovacoes(r, self.navegacao)),
            ("notificacoes", lambda r: TelaNotificacoes(r, self.navegacao)),
            ("configuracoes", lambda r: TelaConfiguracoesApp(r, self.navegacao)),
            ("organizacao", lambda r: TelaOrganizacao(r, self.navegacao)),
            ("perfis", lambda r: TelaPerfisAnalise(r, self.navegacao)),
            ("usuarios", lambda r: TelaUsuarios(r, navegacao=self.navegacao)),
            ("financeiro_2_0", lambda r: TelaFinanceiro(r, self.navegacao)),
            ("rh_2_0", lambda r: TelaRH(r, self.navegacao)),
            ("tecnologia_2_0", lambda r: TelaTecnologia(r, self.navegacao)),
        ]
        for modulo in modulos:
            casos.extend(
                (
                    (
                        f"painel_{modulo}",
                        lambda r, m=modulo: TelaPainelModulo(r, self.navegacao, m),
                    ),
                    (
                        f"cadastro_{modulo}",
                        lambda r, m=modulo: TelaModuloEmpresarial(r, self.navegacao, m),
                    ),
                )
            )
        for ferramenta in (
            "tarefas", "documentos", "workflows", "integracoes",
            "relatorios", "auditoria",
        ):
            casos.append(
                (
                    f"ferramenta_{ferramenta}",
                    lambda r, f=ferramenta: TelaFerramentaCorporativa(
                        r, self.navegacao, f
                    ),
                )
            )
        for nome, fabrica in casos:
            with self.subTest(tela=nome):
                root = self._nova_janela()
                root.geometry("1366x768+0+0")
                try:
                    fabrica(root)
                    root.update_idletasks()
                    root.update()
                    self.assertGreater(root.winfo_width(), 0)
                    self.assertGreater(root.winfo_height(), 0)
                finally:
                    self._finalizar_root(root)

    def test_area_rolavel_ignora_evento_tardio_depois_de_destruida(self):
        from interface.componentes import AreaRolavel

        root = self._nova_janela()
        root.geometry("800x600+0+0")
        try:
            area = AreaRolavel(root)
            area.pack(fill="both", expand=True)
            tk.Frame(area.conteudo, height=1200, bg="#000000").pack(fill="x")
            root.update_idletasks()
            area._ativar_roda()
            area.destroy()
            root.update_idletasks()
            # Reproduz o cenário do traceback relatado: um evento de roda
            # chega depois que a scrollbar da página anterior já foi destruída.
            area._rolar(SimpleNamespace(delta=120))
            area._rolar_linux(SimpleNamespace(num=4))
        finally:
            self._finalizar_root(root)

    def test_sidebar_destaca_a_pagina_global_correta(self):
        from interface.aprovacoes import TelaAprovacoes
        from interface.catalogo_modulos import TelaCatalogoModulos
        from interface.configuracoes_app import TelaConfiguracoesApp
        from interface.historico import TelaHistorico
        from interface.notificacoes import TelaNotificacoes
        from interface.organizacao import TelaOrganizacao
        from interface.principal import TelaPrincipal
        from interface.usuarios import TelaUsuarios
        from interface.tema import CORES

        for nome, fabrica, titulo in (
            ("inicio", lambda r: TelaPrincipal(r, self.navegacao), "Visão geral"),
            ("modulos", lambda r: TelaCatalogoModulos(r, self.navegacao), "Módulos"),
            ("historico", lambda r: TelaHistorico(r, self.navegacao), "Histórico analítico"),
            ("aprovacoes", lambda r: TelaAprovacoes(r, self.navegacao), "Aprovações"),
            (
                "notificacoes",
                lambda r: TelaNotificacoes(r, self.navegacao),
                "Central de notificações",
            ),
            ("configuracoes", lambda r: TelaConfiguracoesApp(r, self.navegacao), "Configurações"),
            (
                "organizacao",
                lambda r: TelaOrganizacao(r, self.navegacao),
                "Organização",
            ),
            ("usuarios", lambda r: TelaUsuarios(r, navegacao=self.navegacao), "Usuários e acessos"),
        ):
            with self.subTest(tela=nome):
                root = self._nova_janela()
                root.geometry("1366x768+0+0")
                try:
                    fabrica(root)
                    root.update_idletasks()
                    botao = self._botao_sidebar(root, titulo)
                    self.assertEqual(botao.cget("bg"), CORES["sidebar_ativo"])
                finally:
                    self._finalizar_root(root)

    def test_empresa_criada_na_sessao_habilita_remocao_apenas_quando_nao_ativa(self):
        from enterprise.organizacao import criar_empresa
        from interface.organizacao import TelaOrganizacao

        empresa_id = criar_empresa("Temporária UI", ator=SESSAO.usuario)
        root = self._nova_janela()
        root.geometry("1366x768+0+0")
        try:
            tela = TelaOrganizacao(root, self.navegacao)
            rotulo = next(
                rotulo for rotulo, codigo in tela.mapa_empresas.items()
                if int(codigo) == int(empresa_id)
            )
            tela.empresa_var.set(rotulo)
            tela._atualizar_estado_remocao()
            self.assertEqual(str(tela.botao_remover_empresa.cget("state")), "normal")

            # A empresa ativa nunca pode ser removida pelo botão.
            rotulo_ativo = next(
                rotulo for rotulo, codigo in tela.mapa_empresas.items()
                if int(codigo) == int(SESSAO.empresa_id)
            )
            tela.empresa_var.set(rotulo_ativo)
            tela._atualizar_estado_remocao()
            self.assertEqual(str(tela.botao_remover_empresa.cget("state")), "disabled")
        finally:
            self._finalizar_root(root)

    def test_historico_multisselecao_apaga_acoes_de_item_unico(self):
        from interface.historico import TelaHistorico

        root = self._nova_janela()
        root.geometry("1366x768+0+0")
        try:
            tela = TelaHistorico(root, self.navegacao)
            tela.tabela.insert("", tk.END, iid="9001", values=("a", "b", 1, 1, "ok", "x"))
            tela.tabela.insert("", tk.END, iid="9002", values=("a", "b", 1, 1, "ok", "x"))
            tela.tabela.selection_set(("9001", "9002"))
            tela._atualizar_estado_acoes()
            self.assertEqual(str(tela.botao_detalhes.cget("state")), "disabled")
            self.assertEqual(str(tela.botao_excluir.cget("state")), "normal")

            tela.tabela.selection_set(("9001",))
            tela._atualizar_estado_acoes()
            self.assertEqual(str(tela.botao_detalhes.cget("state")), "normal")
            self.assertEqual(str(tela.botao_excluir.cget("state")), "normal")
        finally:
            self._finalizar_root(root)

    def test_menus_departamentais_permanecem_identicos_entre_secoes(self):
        from interface.configuracao_modulos_ui import PAINEIS_MODULOS
        from interface.modulo_empresarial import TelaModuloEmpresarial
        from interface.painel_modulo import TelaPainelModulo

        for modulo, configuracao in PAINEIS_MODULOS.items():
            esperados = tuple(titulo for _chave, _icone, titulo in configuracao["menu"])
            # Uma seção especializada e o cadastro principal exercitam os dois
            # construtores de página usados pelo menu departamental.
            especializada = next(
                (chave for chave, _icone, _titulo in configuracao["menu"]
                 if chave not in {"visao", "registros"}),
                "visao",
            )
            casos = (
                ("visao", lambda r, m=modulo: TelaPainelModulo(r, self.navegacao, m, "visao")),
                (especializada, lambda r, m=modulo, s=especializada: TelaPainelModulo(r, self.navegacao, m, s)),
                ("registros", lambda r, m=modulo: TelaModuloEmpresarial(r, self.navegacao, m)),
            )
            menus = []
            for secao, fabrica in casos:
                root = self._nova_janela()
                root.geometry("1366x768+0+0")
                try:
                    fabrica(root)
                    root.update_idletasks()
                    textos = tuple(str(item.cget("text")) for item in self._widgets(root, tk.Button))
                    menu = tuple(titulo for titulo in esperados if any(titulo in texto for texto in textos))
                    self.assertEqual(menu, esperados, f"Menu divergente em {modulo}/{secao}")
                    menus.append(menu)
                finally:
                    self._finalizar_root(root)
            self.assertTrue(all(menu == menus[0] for menu in menus[1:]))

    def test_dashboard_e_explorar_dados_usam_o_mesmo_menu_analytics(self):
        from interface.app import AplicacaoAutomacao
        from interface.central_analytics import TelaCentralAnalytics
        from interface.navegacao_analytics import MENU_ANALYTICS

        esperados = tuple(titulo for _chave, _icone, titulo in MENU_ANALYTICS)

        menus = []
        for fabrica in (
            lambda r: AplicacaoAutomacao(r, navegacao=self.navegacao),
            lambda r: TelaCentralAnalytics(r, self.navegacao, secao="conjuntos"),
        ):
            root = self._nova_janela()
            root.geometry("1440x900+0+0")
            try:
                fabrica(root)
                root.update_idletasks()
                textos = tuple(str(item.cget("text")) for item in self._widgets(root, tk.Button))
                menus.append(textos)
                for titulo in esperados:
                    self.assertTrue(
                        any(titulo in texto for texto in textos),
                        f"Item ausente na sidebar Analytics: {titulo}",
                    )
                self.assertFalse(any("Conjuntos de dados" in texto for texto in textos))
            finally:
                self._finalizar_root(root)

        self.assertEqual(
            tuple(t for t in esperados if any(t in x for x in menus[0])),
            tuple(t for t in esperados if any(t in x for x in menus[1])),
        )

    def test_tecnologia_3_0_constroi_portal_cockpit_rede_e_ativos(self):
        from interface.tecnologia import TelaTecnologia

        for secao in ("portal", "abrir_chamado", "meus_chamados", "cockpit", "rede", "ativos"):
            with self.subTest(secao=secao):
                root = self._nova_janela()
                root.geometry("1366x768+0+0")
                try:
                    TelaTecnologia(root, self.navegacao, secao=secao)
                    root.update_idletasks()
                    root.update()
                    self.assertGreater(root.winfo_width(), 0)
                finally:
                    self._finalizar_root(root)

    def test_tecnologia_janela_provisionamento_agente_abre_sem_ficar_em_branco(self):
        from interface.tecnologia import TelaTecnologia
        from interface.tema import CORES

        root = self._nova_janela()
        root.geometry("1366x768+0+0")
        try:
            tela = TelaTecnologia(root, self.navegacao, secao="ativos")
            root.update_idletasks()
            root.update()

            credencial = {
                "patrimonio": "TI-TESTE-001",
                "agent_id": "agent-ui-smoke",
                "token": "token-temporario-smoke",
            }
            tela._janela_credencial_agente(credencial, "http://192.168.1.4:8765")
            root.update_idletasks()
            root.update()

            janelas = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
            self.assertEqual(len(janelas), 1)
            janela = janelas[0]
            self.assertEqual(janela.title(), "Provisionamento do agente TI")
            self.assertEqual(str(janela.cget("bg")), str(CORES["bg"]))

            caixas = self._widgets(janela, tk.Text)
            self.assertEqual(len(caixas), 1)
            conteudo = caixas[0].get("1.0", "end")
            self.assertIn("TI-TESTE-001", conteudo)
            self.assertIn("agent-ui-smoke", conteudo)
            self.assertIn("http://192.168.1.4:8765", conteudo)
            janela.destroy()
        finally:
            self._finalizar_root(root)

    def test_tecnologia_portal_abre_para_usuario_sem_permissao_ti(self):
        from auth.autenticacao import criar_usuario
        from interface.tecnologia import TelaTecnologia

        admin = dict(SESSAO.usuario)
        usuario = criar_usuario(
            "Analista Portal", "analista.portal.ui", "SenhaPortal#123",
            ator=admin, perfil_acesso="analista",
        )
        SESSAO.iniciar(usuario)
        obter_contexto()
        root = self._nova_janela()
        root.geometry("1366x768+0+0")
        try:
            tela = TelaTecnologia(root, self.navegacao, secao="cockpit")
            root.update_idletasks()
            root.update()
            # Pedido de seção operacional é rebaixado de forma segura ao portal.
            self.assertEqual(tela.secao, "portal")
            textos = tuple(str(item.cget("text")) for item in self._widgets(root, tk.Button))
            self.assertTrue(any("Abrir chamado" in x or "ABRIR CHAMADO" in x for x in textos))
            self.assertFalse(any("Rede ao vivo" in x for x in textos))
        finally:
            self._finalizar_root(root)


if __name__ == "__main__":
    unittest.main()
