"""Teste visual real que exporta as interfaces para PNG.

No Windows:

    set RUN_TK_SCREENSHOTS=1
    python -m unittest tests.test_interface_screenshots -v

O resultado é salvo em ``artifacts/interface_png``. Use
``TK_SCREENSHOT_SCOPE=essencial`` para uma rodada curta; o padrão é completo.
"""

from __future__ import annotations

import os
from pathlib import Path
import unittest

from scripts.gerar_capturas_interface import executar_capturas


@unittest.skipUnless(
    os.environ.get("RUN_TK_SCREENSHOTS") == "1",
    "Capturas reais exigem RUN_TK_SCREENSHOTS=1 e um desktop gráfico desbloqueado.",
)
class InterfaceScreenshotTests(unittest.TestCase):
    def test_todas_as_interfaces_exportam_png_valido(self):
        destino = Path(
            os.environ.get("TK_SCREENSHOT_DIR", "artifacts/interface_png")
        ).resolve()
        resultados = executar_capturas(
            destino,
            escopo=os.environ.get("TK_SCREENSHOT_SCOPE", "completo"),
            largura=int(os.environ.get("TK_SCREENSHOT_WIDTH", "1600")),
            altura=int(os.environ.get("TK_SCREENSHOT_HEIGHT", "900")),
            espera_ms=int(os.environ.get("TK_SCREENSHOT_WAIT_MS", "180")),
        )
        reprovadas = [
            f"{item['tela']}: {'; '.join(item['falhas'])}"
            for item in resultados
            if item["status"] == "reprovada"
        ]
        self.assertFalse(reprovadas, "\n".join(reprovadas))
        self.assertTrue((destino / "FOLHA_CONTATO.png").is_file())
        self.assertTrue((destino / "RELATORIO_VISUAL.md").is_file())
        self.assertTrue((destino / "MANIFESTO_VISUAL.json").is_file())


if __name__ == "__main__":
    unittest.main()

