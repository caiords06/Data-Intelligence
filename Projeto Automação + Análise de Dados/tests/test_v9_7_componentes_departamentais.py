"""Regressões da componentização departamental V9.8."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA
from interface.rh import TelaRH
from interface.rh_views import TelaRHViewsMixin
from interface.rh_acoes import TelaRHAcoesMixin
from interface.estoque import TelaEstoque
from interface.estoque_views import TelaEstoqueViewsMixin
from interface.estoque_acoes import TelaEstoqueAcoesMixin
from interface.componentes_departamentais import renderizar_metricas, renderizar_acessos_rapidos

RAIZ = Path(__file__).resolve().parents[1]


def linhas(relativo: str) -> int:
    return len((RAIZ / relativo).read_text(encoding="utf-8").splitlines())


class ComponentesDepartamentaisV97Tests(unittest.TestCase):
    def test_versao_canonica(self):
        self.assertEqual(VERSAO_PLATAFORMA, "11.1.0")
        self.assertEqual(VERSAO_INTERFACE, "V11.1.0")

    def test_fachadas_usam_mixins(self):
        self.assertTrue(issubclass(TelaRH, TelaRHViewsMixin))
        self.assertTrue(issubclass(TelaRH, TelaRHAcoesMixin))
        self.assertTrue(issubclass(TelaEstoque, TelaEstoqueViewsMixin))
        self.assertTrue(issubclass(TelaEstoque, TelaEstoqueAcoesMixin))

    def test_fachadas_permanecem_pequenas(self):
        self.assertLessEqual(linhas("interface/rh.py"), 100)
        self.assertLessEqual(linhas("interface/estoque.py"), 100)
        self.assertLessEqual(linhas("interface/rh_views.py"), 300)
        self.assertLessEqual(linhas("interface/estoque_views.py"), 300)
        self.assertLessEqual(linhas("interface/rh_acoes.py"), 400)
        self.assertLessEqual(linhas("interface/estoque_acoes.py"), 400)

    def test_metodos_publicamente_esperados_continuam_disponiveis(self):
        casos = (
            (TelaRH, ("_visao", "_carregar_tabela", "_novo_colaborador", "_relatorios")),
            (TelaEstoque, ("_visao", "_secao_operacional", "_novo_item", "_abrir_inventario", "_relatorios")),
        )
        for classe, metodos in casos:
            for metodo in metodos:
                with self.subTest(classe=classe.__name__, metodo=metodo):
                    self.assertTrue(callable(getattr(classe, metodo, None)))

    def test_componentes_departamentais_reutilizaveis_existentes(self):
        self.assertTrue(callable(renderizar_metricas))
        self.assertTrue(callable(renderizar_acessos_rapidos))
        rh = (RAIZ / "interface/rh_views.py").read_text(encoding="utf-8")
        estoque = (RAIZ / "interface/estoque_views.py").read_text(encoding="utf-8")
        self.assertIn("renderizar_metricas", rh)
        self.assertIn("renderizar_acessos_rapidos", rh)
        self.assertIn("renderizar_metricas", estoque)
        self.assertIn("renderizar_acessos_rapidos", estoque)

    def test_modulos_compilam_sem_import_circular(self):
        arquivos = (
            "interface/rh.py", "interface/rh_shared.py", "interface/rh_views.py", "interface/rh_acoes.py",
            "interface/estoque.py", "interface/estoque_shared.py", "interface/estoque_views.py", "interface/estoque_acoes.py",
            "interface/componentes_departamentais.py",
        )
        for arquivo in arquivos:
            with self.subTest(arquivo=arquivo):
                ast.parse((RAIZ / arquivo).read_text(encoding="utf-8"), filename=arquivo)

    def test_release_aponta_para_v97(self):
        workflow = (RAIZ / ".github/workflows/quality.yml").read_text(encoding="utf-8")
        self.assertIn("Qualidade V11", workflow)
        self.assertIn("DataIntelligence-Source-V11.1.0", workflow)
        empacotador = (RAIZ / "scripts/empacotar_fonte_limpa.py").read_text(encoding="utf-8")
        self.assertIn("V11.1.0", empacotador)


if __name__ == "__main__":
    unittest.main()
