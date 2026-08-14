from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArquiteturaWebReadyV105Tests(unittest.TestCase):
    def test_interface_nao_contorna_camada_services(self):
        violacoes = []
        for arquivo in sorted((ROOT / "interface").rglob("*.py")):
            arvore = ast.parse(arquivo.read_text(encoding="utf-8-sig"), filename=str(arquivo))
            for no in ast.walk(arvore):
                if isinstance(no, ast.Import):
                    for alias in no.names:
                        if alias.name == "enterprise" or alias.name.startswith("enterprise."):
                            violacoes.append(f"{arquivo.name}:{no.lineno}:{alias.name}")
                elif isinstance(no, ast.ImportFrom):
                    modulo = no.module or ""
                    if modulo == "enterprise" or modulo.startswith("enterprise."):
                        violacoes.append(f"{arquivo.name}:{no.lineno}:{modulo}")
        self.assertEqual(violacoes, [])

    def test_todos_os_departamentos_possuem_service(self):
        esperados = {
            "financeiro", "rh", "estoque", "compras", "tecnologia",
            "marketing", "comercial", "administrativo", "juridico",
        }
        existentes = {p.stem for p in (ROOT / "services" / "departamentos").glob("*.py") if p.stem != "__init__"}
        self.assertTrue(esperados.issubset(existentes))

    def test_analytics_expoe_decisao_e_esconde_placeholders(self):
        from interface.navegacao_analytics import MENU_ANALYTICS
        chaves = {x[0] for x in MENU_ANALYTICS}
        self.assertTrue({"visao", "insights", "alertas", "nova", "importacoes", "regras"}.issubset(chaves))
        self.assertTrue({"modelos", "assistente", "perfis"}.isdisjoint(chaves))

    def test_api_publica_e_migrations_finais_estao_registradas(self):
        from servidor_corporativo.api_v1 import PUBLIC_ENDPOINTS
        from enterprise.migrations import MIGRACOES, validar_registry
        self.assertIn("/api/v1/analytics/insights", PUBLIC_ENDPOINTS)
        self.assertIn("/api/v1/crm/leads/to-opportunity", PUBLIC_ENDPOINTS)
        self.assertEqual(MIGRACOES[-5:], (
            "024_v10_4_analytics_inteligencia", "025_v10_4_1_inteligencia_transversal",
            "026_hardening_producao", "027_v11_core_empresarial", "028_v11_1_conformidade",
        ))
        self.assertEqual(validar_registry(), MIGRACOES)


if __name__ == "__main__":
    unittest.main()
