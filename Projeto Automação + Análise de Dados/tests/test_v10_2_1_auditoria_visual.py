import unittest
from pathlib import Path

from interface.tema import TEMA_CLARO, TEMA_ESCURO
from scripts.gerar_capturas_interface import executar_matriz_capturas


class AuditoriaVisualV1021Tests(unittest.TestCase):
    def test_temas_nao_usam_preto_puro_nem_fundo_branco_puro(self):
        self.assertNotEqual(TEMA_ESCURO["bg"].upper(), "#000000")
        self.assertNotEqual(TEMA_CLARO["bg"].upper(), "#FFFFFF")
        self.assertNotEqual(TEMA_CLARO["card"].upper(), "#FFFFFF")

    def test_matriz_visual_canonica_existe(self):
        self.assertTrue(callable(executar_matriz_capturas))

    def test_marketing_especializado_entra_no_catalogo_visual(self):
        texto=Path("scripts/gerar_capturas_interface.py").read_text(encoding="utf-8")
        self.assertIn("MENU_MARKETING",texto)
        self.assertIn("TelaMarketing",texto)
