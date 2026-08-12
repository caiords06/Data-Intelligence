"""Testes headless da infraestrutura de captura e diagnóstico visual."""

from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from interface.captura_visual import (
    analisar_png,
    gerar_folha_contato,
    gerar_relatorio_markdown,
    salvar_manifesto,
)
from scripts.gerar_capturas_interface import construir_catalogo


class CapturaVisualTests(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temporario.name)

    def tearDown(self):
        self.temporario.cleanup()

    def test_imagem_uniforme_e_reprovada(self):
        caminho = self.pasta / "uniforme.png"
        Image.new("RGB", (1000, 700), "#071525").save(caminho)
        resultado = analisar_png(caminho)
        self.assertEqual(resultado["status"], "reprovada")
        self.assertTrue(any("uniforme" in falha for falha in resultado["falhas"]))

    def test_mock_de_interface_com_contraste_e_aprovado(self):
        caminho = self.pasta / "interface.png"
        imagem = Image.new("RGB", (1200, 760), "#071525")
        desenho = ImageDraw.Draw(imagem)
        desenho.rectangle((0, 0, 230, 760), fill="#06111F")
        desenho.rectangle((260, 70, 1160, 170), fill="#11233A", outline="#2F80ED", width=2)
        for indice in range(4):
            x = 260 + indice * 225
            desenho.rectangle((x, 205, x + 205, 350), fill="#132740", outline="#334E68")
            desenho.line((x + 20, 320, x + 180, 250 + indice * 8), fill="#38BDF8", width=4)
        for linha in range(8):
            y = 390 + linha * 38
            desenho.rectangle((260, y, 1120, y + 25), fill="#0B1B2E")
            desenho.rectangle((280, y + 7, 480 + linha * 20, y + 16), fill="#94A3B8")
        imagem.save(caminho)

        resultado = analisar_png(caminho)
        self.assertEqual(resultado["status"], "aprovada")
        self.assertGreater(resultado["entropia"], 2)
        self.assertGreater(resultado["cores_amostradas"], 5)

    def test_dimensao_inferior_ao_minimo_e_reprovada(self):
        caminho = self.pasta / "pequena.png"
        imagem = Image.new("RGB", (400, 300), "#071525")
        ImageDraw.Draw(imagem).rectangle((20, 20, 380, 280), fill="#38BDF8")
        imagem.save(caminho)
        resultado = analisar_png(caminho)
        self.assertEqual(resultado["status"], "reprovada")
        self.assertTrue(any("menor que o mínimo" in falha for falha in resultado["falhas"]))

    def test_relatorio_manifesto_e_folha_de_contato_sao_gerados(self):
        resultados = []
        for indice, cor in enumerate(("#38BDF8", "#22C55E"), 1):
            caminho = self.pasta / f"tela_{indice}.png"
            imagem = Image.new("RGB", (1000, 700), "#071525")
            desenho = ImageDraw.Draw(imagem)
            desenho.rectangle((50, 50, 950, 650), fill="#132740", outline=cor, width=6)
            for linha in range(12):
                desenho.line((80, 100 + linha * 40, 900, 120 + linha * 40), fill=cor, width=3)
            imagem.save(caminho)
            resultado = analisar_png(caminho)
            resultado.update(tela=f"Tela {indice}", grupo="Teste", layout={})
            resultados.append(resultado)

        manifesto = salvar_manifesto(resultados, self.pasta / "manifesto.json")
        folha = gerar_folha_contato(resultados, self.pasta / "contato.png", colunas=2)
        relatorio = gerar_relatorio_markdown(resultados, self.pasta / "relatorio.md")
        self.assertGreater(manifesto.stat().st_size, 200)
        self.assertGreater(folha.stat().st_size, 1000)
        self.assertIn("Tela 1", relatorio.read_text(encoding="utf-8"))

    def test_catalogo_completo_cobre_todas_as_familias_de_interface(self):
        catalogo = construir_catalogo("completo")
        grupos = {caso.grupo for caso in catalogo}
        self.assertGreaterEqual(len(catalogo), 100)
        self.assertTrue(
            {
                "Acesso", "Global", "Analytics", "Financeiro", "Recursos Humanos",
                "Estoque", "Compras", "Tecnologia", "Ferramentas",
            } <= grupos
        )
        nomes = {caso.nome for caso in catalogo}
        self.assertIn("Login", nomes)
        self.assertIn("Dashboard analítico", nomes)
        self.assertIn("Tecnologia · portal", nomes)
        self.assertIn("Tecnologia · cockpit", nomes)
        self.assertIn("Tecnologia · rede", nomes)


if __name__ == "__main__":
    unittest.main()
