"""Regressões do Design System V10.2.0."""

from pathlib import Path
import unittest

from configuracoes.preferencias import PREFERENCIAS_PADRAO, normalizar_preferencias
from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA
from interface.icones import ICONES
from interface.tema import (
    CORES, TEMAS, TEMA_CLARO, TEMA_ESCURO, aplicar_paleta, normalizar_tema, tema_atual,
)


def _luminancia(cor: str) -> float:
    rgb = [int(cor[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in rgb]
    return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2]


def _contraste(a: str, b: str) -> float:
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + .05) / (lb + .05)


class DesignSystemV102Tests(unittest.TestCase):
    def tearDown(self):
        aplicar_paleta("escuro")

    def test_versao_canonica(self):
        self.assertEqual(VERSAO_PLATAFORMA, "11.1.0")
        self.assertEqual(VERSAO_INTERFACE, "V11.1.0")

    def test_temas_possuem_mesmos_tokens(self):
        self.assertEqual(set(TEMA_ESCURO), set(TEMA_CLARO))
        self.assertGreaterEqual(len(TEMA_ESCURO), 30)
        for nome, paleta in TEMAS.items():
            with self.subTest(tema=nome):
                for chave, valor in paleta.items():
                    self.assertRegex(valor, r"^#[0-9A-Fa-f]{6}$", chave)

    def test_troca_atualiza_o_mesmo_dicionario_cores(self):
        identidade = id(CORES)
        aplicar_paleta("claro")
        self.assertEqual(id(CORES), identidade)
        self.assertEqual(tema_atual(), "claro")
        self.assertEqual(CORES["bg"], TEMA_CLARO["bg"])
        aplicar_paleta("escuro")
        self.assertEqual(id(CORES), identidade)
        self.assertEqual(CORES["bg"], TEMA_ESCURO["bg"])

    def test_tema_invalido_falha_para_padrao_seguro(self):
        self.assertEqual(normalizar_tema("qualquer"), "escuro")
        self.assertEqual(normalizar_tema(None), "escuro")

    def test_preferencia_de_tema_e_normalizada(self):
        self.assertEqual(PREFERENCIAS_PADRAO["tema_interface"], "escuro")
        self.assertEqual(normalizar_preferencias({"tema_interface": "CLARO"})["tema_interface"], "claro")
        self.assertEqual(normalizar_preferencias({"tema_interface": "neon"})["tema_interface"], "escuro")

    def test_contraste_de_texto_normal_atende_aa(self):
        for nome, paleta in TEMAS.items():
            with self.subTest(tema=nome, token="text"):
                self.assertGreaterEqual(_contraste(paleta["text"], paleta["bg"]), 4.5)
            with self.subTest(tema=nome, token="text_sec"):
                self.assertGreaterEqual(_contraste(paleta["text_sec"], paleta["bg"]), 4.5)
            with self.subTest(tema=nome, token="primary-button"):
                self.assertGreaterEqual(_contraste(paleta["on_primary"], paleta["primary"]), 4.5)

    def test_icones_nao_usam_emoticons_com_rosto(self):
        proibidos = {"😀", "😃", "😄", "😁", "🙂", "😉", "😎", "🤓"}
        self.assertFalse(proibidos & set(ICONES.values()))
        for chave in ("financeiro", "rh", "estoque", "compras", "ti", "marketing", "administrativo", "juridico", "comercial"):
            self.assertIn(chave, ICONES)

    def test_login_nao_depende_das_imagens_antigas(self):
        fonte = Path("interface/login.py").read_text(encoding="utf-8")
        self.assertNotIn("interface.imagens", fonte)
        self.assertNotIn("backgrounds/login", fonte)
        self.assertNotIn("illustrations/login", fonte)
        self.assertIn("alternar_tema", fonte)


if __name__ == "__main__":
    unittest.main()
