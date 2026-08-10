"""Contratos estruturais do novo front-end V7 sem depender de display gráfico."""

import unittest

from enterprise.catalogo import ORDEM_MODULOS
from interface.central_analytics import MENU_ANALYTICS
from interface.componentes import ITENS_NAVEGACAO
from interface.configuracao_modulos_ui import PAINEIS_MODULOS
from interface.nova_analise import CATEGORIAS, FONTES_DADOS
from interface.tema import CORES, VERSAO_INTERFACE


class InterfaceV7Tests(unittest.TestCase):
    def test_todos_departamentos_possuem_painel_especifico(self):
        departamentos = set(ORDEM_MODULOS) - {"analytics"}
        self.assertEqual(set(PAINEIS_MODULOS), departamentos)

    def test_menus_departamentais_possuem_visao_e_registros(self):
        for modulo, painel in PAINEIS_MODULOS.items():
            with self.subTest(modulo=modulo):
                chaves = [item[0] for item in painel["menu"]]
                self.assertEqual(chaves[0], "visao")
                self.assertIn("registros", chaves)
                self.assertEqual(len(chaves), len(set(chaves)))
                self.assertGreaterEqual(len(painel["acoes"]), 3)
                self.assertGreaterEqual(len(painel["etapas"]), 5)
                self.assertGreaterEqual(len(painel["recursos"]), 4)

    def test_sidebar_global_preserva_hierarquia_do_analytics(self):
        chaves = {item[0] for item in ITENS_NAVEGACAO}
        self.assertIn("modulos", chaves)
        self.assertNotIn("analytics", chaves)
        self.assertNotIn("nova", chaves)

    def test_central_analytics_expoe_recursos_futuros(self):
        chaves = {item[0] for item in MENU_ANALYTICS}
        self.assertTrue(
            {"visao", "nova", "importacoes", "relatorios", "agendamentos", "modelos", "assistente"}
            <= chaves
        )

    def test_nova_analise_distingue_fontes_funcionais_e_previas(self):
        fontes = {nome: funcional for nome, _icone, _descricao, funcional in FONTES_DADOS}
        self.assertTrue(fontes["Computador"])
        self.assertFalse(fontes["Google Drive"])
        self.assertFalse(fontes["OneDrive"])
        self.assertFalse(fontes["Banco de dados"])
        self.assertFalse(fontes["URL"])
        self.assertIn("Recursos Humanos", CATEGORIAS)
        self.assertIn("Jurídico", CATEGORIAS)

    def test_design_system_possui_estados_acessiveis(self):
        self.assertEqual(VERSAO_INTERFACE, "V7")
        for chave in (
            "bg", "sidebar", "card", "input", "border", "text", "text_sec",
            "primary", "success", "warning", "danger",
        ):
            self.assertIn(chave, CORES)
            self.assertRegex(CORES[chave], r"^#[0-9A-Fa-f]{6}$")


if __name__ == "__main__":
    unittest.main()
