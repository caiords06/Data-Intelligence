"""Regressões de navegação e leftbox introduzidas na V9.4."""
from __future__ import annotations

from pathlib import Path
import os
import unittest
from unittest.mock import patch

from interface.navegacao_modulos import (
    ALIASES_SECOES,
    criar_sidebar_modulo,
    normalizar_secao_modulo,
    tipo_tela_modulo,
)


RAIZ = Path(__file__).resolve().parents[1]


class NavegacaoInterfaceV94Tests(unittest.TestCase):
    def test_aliases_legados_apontam_para_secoes_especializadas_reais(self):
        esperados = {
            "financeiro": "lancamentos",
            "rh": "colaboradores",
            "estoque": "itens",
            "compras": "solicitacoes",
            "comercial": "oportunidades",
            "administrativo": "solicitacoes",
            "juridico": "contratos",
        }
        self.assertEqual(set(ALIASES_SECOES), set(esperados))
        for modulo, destino in esperados.items():
            with self.subTest(modulo=modulo):
                self.assertEqual(normalizar_secao_modulo(modulo, "registros"), destino)
                self.assertEqual(normalizar_secao_modulo(modulo, "visao"), "visao")

    def test_tecnologia_resolve_visao_e_registros_por_permissao(self):
        usuario = {"id": 1}
        with patch("interface.navegacao_modulos.tem_permissao", return_value=True):
            self.assertEqual(normalizar_secao_modulo("ti", "visao", usuario=usuario), "cockpit")
            self.assertEqual(normalizar_secao_modulo("ti", "registros", usuario=usuario), "chamados")
        with patch("interface.navegacao_modulos.tem_permissao", return_value=False):
            self.assertEqual(normalizar_secao_modulo("ti", "visao", usuario=usuario), "portal")
            self.assertEqual(normalizar_secao_modulo("ti", "registros", usuario=usuario), "meus_chamados")

    def test_modulos_especializados_usam_um_unico_renderizador_em_todas_as_secoes(self):
        for modulo in ("financeiro", "rh", "estoque", "compras", "ti", "marketing", "comercial", "administrativo", "juridico"):
            with self.subTest(modulo=modulo):
                self.assertEqual(tipo_tela_modulo(modulo, "visao"), modulo)
                self.assertEqual(tipo_tela_modulo(modulo, "qualquer_secao"), modulo)

    def test_departamentos_v10_3_usam_renderizadores_especializados(self):
        self.assertEqual(tipo_tela_modulo("marketing", "conteudo"), "marketing")
        self.assertEqual(tipo_tela_modulo("comercial", "pipeline"), "comercial")
        self.assertEqual(tipo_tela_modulo("administrativo", "reservas"), "administrativo")
        self.assertEqual(tipo_tela_modulo("juridico", "processos"), "juridico")

    def test_sidebar_converte_menu_em_callbacks_do_roteador_canonico(self):
        chamadas = []
        recebido = {}
        navegacao = {
            "secao_modulo": lambda modulo, secao: chamadas.append((modulo, secao)),
            "modulos": lambda: chamadas.append(("global", "modulos")),
            "correio": lambda modulo: chamadas.append((modulo, "correio")),
        }

        def fake_sidebar(parent, nav, **kwargs):
            recebido.update(kwargs)
            return "sidebar"

        grupos = (("FINANCEIRO", (("visao", "⌂", "Visão geral"), ("lancamentos", "≡", "Lançamentos"))),)
        with patch("interface.navegacao_modulos.criar_sidebar", side_effect=fake_sidebar):
            retorno = criar_sidebar_modulo(
                object(), navegacao, modulo="financeiro", titulo="FINANCEIRO",
                ativo="visao", grupos_menu=grupos, grupos_recolhiveis=True,
            )
        self.assertEqual(retorno, "sidebar")
        self.assertEqual(recebido["titulo_customizado"], "FINANCEIRO")
        self.assertEqual(recebido["ativo"], "visao")
        grupos_convertidos = recebido["grupos_customizados"]
        _, itens = grupos_convertidos[0]
        itens[1][3]()
        self.assertEqual(chamadas, [("financeiro", "lancamentos")])
        self.assertEqual(grupos_convertidos[-1][0], "COLABORAÇÃO")

    def test_catalogo_visual_nao_substitui_visao_especializada_por_tela_legada(self):
        fonte = (RAIZ / "scripts" / "gerar_capturas_interface.py").read_text(encoding="utf-8")
        self.assertNotIn('if secao == "visao" and grupo != "Tecnologia"', fonte)
        self.assertIn('fabrica = lambda r, c=classe, sec=secao: c(r, navegacao, secao=sec)', fonte)

    def test_interface_nao_exibe_rotulos_de_versao_v9_0(self):
        encontrados = []
        for arquivo in (RAIZ / "interface").glob("*.py"):
            if "V9.0" in arquivo.read_text(encoding="utf-8"):
                encontrados.append(arquivo.name)
        self.assertEqual(encontrados, [])

    def test_dominios_departamentais_usam_gateway_de_repositorio(self):
        for modulo in ("financeiro", "rh", "estoque", "compras", "tecnologia"):
            fonte = (RAIZ / "enterprise" / f"{modulo}.py").read_text(encoding="utf-8")
            self.assertIn("from enterprise.repositories import conectar", fonte)
            self.assertNotIn("from auth.banco import conectar", fonte)
        self.assertTrue((RAIZ / "enterprise" / "repositories" / "__init__.py").is_file())

    def test_telas_especializadas_dependem_da_camada_de_servicos(self):
        for modulo in ("financeiro", "rh", "estoque", "compras", "tecnologia"):
            fontes = [(RAIZ / "interface" / f"{modulo}.py").read_text(encoding="utf-8")]
            compartilhado = RAIZ / "interface" / f"{modulo}_shared.py"
            if compartilhado.exists():
                fontes.append(compartilhado.read_text(encoding="utf-8"))
            self.assertIn(f"from services.departamentos.{modulo} import (", "\n".join(fontes))
            self.assertNotIn(f"from enterprise.{modulo} import (", "\n".join(fontes))
            self.assertTrue((RAIZ / "services" / "departamentos" / f"{modulo}.py").is_file())

    def test_main_possui_um_unico_roteador_departamental(self):
        fonte = (RAIZ / "main.py").read_text(encoding="utf-8")
        self.assertEqual(fonte.count("def _renderizar_modulo("), 1)
        self.assertIn("normalizar_secao_modulo(modulo, secao", fonte)
        self.assertIn("tipo_tela_modulo(modulo, secao)", fonte)

    @unittest.skipUnless(
        os.environ.get("RUN_TK_SMOKE") == "1",
        "Validação da leftbox real exige RUN_TK_SMOKE=1 e display Tk.",
    )
    def test_leftbox_especializada_permanece_a_mesma_da_visao_geral_ao_detalhe(self):
        import tkinter as tk
        from scripts.gerar_capturas_interface import banco_visual_temporario, _navegacao_inerte
        from interface.financeiro import GRUPOS_MENU as FIN_MENU, TelaFinanceiro
        from interface.rh import GRUPOS_MENU as RH_MENU, TelaRH
        from interface.estoque import GRUPOS_MENU as EST_MENU, TelaEstoque
        from interface.compras import GRUPOS_MENU as COM_MENU, TelaCompras
        from interface.tecnologia import GRUPOS_MENU as TI_MENU, TelaTecnologia

        casos = (
            (TelaFinanceiro, FIN_MENU, "visao", "lancamentos"),
            (TelaRH, RH_MENU, "visao", "colaboradores"),
            (TelaEstoque, EST_MENU, "visao", "itens"),
            (TelaCompras, COM_MENU, "visao", "solicitacoes"),
            (TelaTecnologia, TI_MENU, "portal", "cockpit"),
        )
        navegacao = _navegacao_inerte()

        def todos_widgets(widget):
            yield widget
            for filho in widget.winfo_children():
                yield from todos_widgets(filho)

        with banco_visual_temporario():
            for classe, grupos, visao, detalhe in casos:
                esperados = tuple(rotulo for _grupo, itens in grupos for _chave, _icone, rotulo in itens)
                menus = []
                for secao in (visao, detalhe):
                    root = tk.Tk()
                    root.geometry("1366x768+0+0")
                    try:
                        classe(root, navegacao, secao=secao)
                        root.update_idletasks(); root.update()
                        textos = tuple(
                            str(w.cget("text")) for w in todos_widgets(root)
                            if isinstance(w, tk.Button)
                        )
                        menus.append(tuple(rotulo for rotulo in esperados if any(rotulo in t for t in textos)))
                    finally:
                        try:
                            root.destroy()
                        except tk.TclError:
                            pass
                self.assertEqual(menus[0], menus[1], classe.__name__)
                self.assertTrue(menus[0], classe.__name__)



if __name__ == "__main__":
    unittest.main()
