"""Regressões da infraestrutura visual compartilhada V9.8."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA
from interface.componentes import AreaRolavel, GradeResponsiva, criar_sidebar, criar_card
from interface.painel_modulo import TelaPainelModulo
from interface.painel_modulo_visao import PainelModuloVisaoMixin
from interface.painel_modulo_operacoes import PainelModuloOperacoesMixin
from interface.central_analytics import TelaCentralAnalytics
from interface.central_analytics_inteligencia import CentralAnalyticsInteligenciaMixin
from interface.central_analytics_datasets import CentralAnalyticsDatasetsMixin
from interface.central_analytics_recursos import CentralAnalyticsRecursosMixin
from interface.modulo_empresarial import TelaModuloEmpresarial
from interface.modulo_empresarial_tabela import ModuloEmpresarialTabelaMixin
from interface.modulo_empresarial_formularios import ModuloEmpresarialFormulariosMixin

RAIZ = Path(__file__).resolve().parents[1]

def linhas(relativo: str) -> int:
    return len((RAIZ / relativo).read_text(encoding="utf-8").splitlines())

class InfraestruturaVisualV98Tests(unittest.TestCase):
    def test_versao_canonica(self):
        self.assertEqual(VERSAO_PLATAFORMA, "11.1.0")
        self.assertEqual(VERSAO_INTERFACE, "V11.1.0")

    def test_componentes_fachada_preserva_api(self):
        for obj in (AreaRolavel, GradeResponsiva, criar_sidebar, criar_card):
            self.assertTrue(callable(obj))

    def test_classes_publicas_usam_componentes(self):
        self.assertTrue(issubclass(TelaPainelModulo, PainelModuloVisaoMixin))
        self.assertTrue(issubclass(TelaPainelModulo, PainelModuloOperacoesMixin))
        self.assertTrue(issubclass(TelaCentralAnalytics, CentralAnalyticsInteligenciaMixin))
        self.assertTrue(issubclass(TelaCentralAnalytics, CentralAnalyticsDatasetsMixin))
        self.assertTrue(issubclass(TelaCentralAnalytics, CentralAnalyticsRecursosMixin))
        self.assertTrue(issubclass(TelaModuloEmpresarial, ModuloEmpresarialTabelaMixin))
        self.assertTrue(issubclass(TelaModuloEmpresarial, ModuloEmpresarialFormulariosMixin))

    def test_fachadas_permanecem_pequenas(self):
        limites = {
            "interface/componentes.py": 80,
            "interface/painel_modulo.py": 120,
            "interface/central_analytics.py": 120,
            "interface/modulo_empresarial.py": 120,
        }
        for arquivo, limite in limites.items():
            with self.subTest(arquivo=arquivo):
                self.assertLessEqual(linhas(arquivo), limite)

    def test_componentes_especializados_nao_viram_novos_monolitos(self):
        limites = {
            "interface/componentes_navegacao.py": 550,
            "interface/componentes_acoes.py": 80,
            "interface/componentes_basicos.py": 350,
            "interface/componentes_responsivos.py": 300,
            "interface/painel_modulo_visao.py": 350,
            "interface/painel_modulo_operacoes.py": 700,
            "interface/central_analytics_inteligencia.py": 420,
            "interface/central_analytics_dashboard.py": 300,
            "interface/central_analytics_datasets.py": 450,
            "interface/central_analytics_recursos.py": 350,
            "interface/modulo_empresarial_tabela.py": 420,
            "interface/modulo_empresarial_formularios.py": 350,
        }
        for arquivo, limite in limites.items():
            with self.subTest(arquivo=arquivo):
                self.assertLessEqual(linhas(arquivo), limite)

    def test_metodos_esperados_continuam_publicos(self):
        casos = (
            (TelaPainelModulo, ("criar_interface", "abrir_secao", "_visao_geral", "_secao_operacional", "carregar_recursos")),
            (TelaCentralAnalytics, ("criar_interface", "abrir_secao", "_visao_executiva", "_insights_empresariais", "_biblioteca_dados", "_recurso_analytics")),
            (TelaModuloEmpresarial, ("criar_interface", "carregar", "abrir_formulario", "editar_selecionado")),
        )
        for classe, metodos in casos:
            for metodo in metodos:
                with self.subTest(classe=classe.__name__, metodo=metodo):
                    self.assertTrue(callable(getattr(classe, metodo, None)))

    def test_novos_arquivos_compilam(self):
        arquivos = (
            "interface/componentes.py", "interface/componentes_navegacao.py", "interface/componentes_acoes.py",
            "interface/componentes_basicos.py", "interface/componentes_responsivos.py",
            "interface/painel_modulo.py", "interface/painel_modulo_shared.py",
            "interface/painel_modulo_visao.py", "interface/painel_modulo_operacoes.py",
            "interface/central_analytics.py", "interface/central_analytics_shared.py",
            "interface/central_analytics_inteligencia.py", "interface/central_analytics_dashboard.py", "interface/central_analytics_datasets.py",
            "interface/central_analytics_recursos.py", "interface/modulo_empresarial.py",
            "interface/modulo_empresarial_shared.py", "interface/modulo_empresarial_tabela.py",
            "interface/modulo_empresarial_formularios.py",
        )
        for arquivo in arquivos:
            with self.subTest(arquivo=arquivo):
                ast.parse((RAIZ / arquivo).read_text(encoding="utf-8"), filename=arquivo)

    def test_release_aponta_para_v98(self):
        workflow=(RAIZ/".github/workflows/quality.yml").read_text(encoding="utf-8")
        self.assertIn("Qualidade V11", workflow)
        self.assertIn("DataIntelligence-Source-V11.1.0", workflow)
        emp=(RAIZ/"scripts/empacotar_fonte_limpa.py").read_text(encoding="utf-8")
        for esperado in ("README_V9_8_INFRAESTRUTURA_VISUAL.md", "interface/componentes_navegacao.py", "interface/central_analytics_datasets.py"):
            self.assertIn(esperado, emp)

if __name__ == "__main__":
    unittest.main()
