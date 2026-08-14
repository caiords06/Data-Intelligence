"""Regressões da refatoração visual V9.6."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA
from interface.app import AplicacaoAutomacao
from interface.app_layout import AppLayoutMixin
from interface.financeiro import TelaFinanceiro
from interface.financeiro_views import FinanceiroViewsMixin
from interface.financeiro_dialogos import FinanceiroDialogosMixin
from interface.compras import TelaCompras
from interface.compras_views import ComprasViewsMixin
from interface.compras_acoes import ComprasAcoesMixin
from interface.tecnologia import TelaTecnologia
from interface.tecnologia_operacoes import TecnologiaOperacoesMixin
from interface.tecnologia_acoes import TecnologiaAcoesMixin

RAIZ = Path(__file__).resolve().parents[1]


def linhas(relativo: str) -> int:
    return len((RAIZ / relativo).read_text(encoding="utf-8").splitlines())


class RefatoracaoInterfaceV96Tests(unittest.TestCase):
    def test_versao_canonica(self):
        self.assertGreaterEqual(tuple(map(int, VERSAO_PLATAFORMA.split("."))), (9, 6, 0))
        self.assertTrue(VERSAO_INTERFACE.startswith(("V9.", "V10", "V11")))

    def test_classes_publicas_preservam_mixins(self):
        self.assertTrue(issubclass(AplicacaoAutomacao, AppLayoutMixin))
        self.assertTrue(issubclass(TelaFinanceiro, FinanceiroViewsMixin))
        self.assertTrue(issubclass(TelaFinanceiro, FinanceiroDialogosMixin))
        self.assertTrue(issubclass(TelaCompras, ComprasViewsMixin))
        self.assertTrue(issubclass(TelaCompras, ComprasAcoesMixin))
        self.assertTrue(issubclass(TelaTecnologia, TecnologiaOperacoesMixin))
        self.assertTrue(issubclass(TelaTecnologia, TecnologiaAcoesMixin))

    def test_arquivos_fachada_ficaram_menores(self):
        limites = {
            "interface/app.py": 1000,
            "interface/tecnologia.py": 650,
            "interface/financeiro.py": 350,
            "interface/compras.py": 350,
        }
        for arquivo, limite in limites.items():
            with self.subTest(arquivo=arquivo):
                self.assertLessEqual(linhas(arquivo), limite)

    def test_metodos_extraidos_continuam_disponiveis(self):
        for classe, metodos in (
            (AplicacaoAutomacao, ("criar_interface", "criar_card", "configurar_dashboard_categoria")),
            (TelaFinanceiro, ("_visao_geral", "_livro", "_form_lancamento", "_importar_extrato")),
            (TelaCompras, ("_visao", "_secao_operacional", "_nova_solicitacao", "_novo_recebimento")),
            (TelaTecnologia, ("_portal_suporte", "_rede_interativa", "_formulario", "_acesso_remoto_registro")),
        ):
            for metodo in metodos:
                with self.subTest(classe=classe.__name__, metodo=metodo):
                    self.assertTrue(callable(getattr(classe, metodo, None)))

    def test_modulos_visuais_compilam_sem_dependencia_circular(self):
        arquivos = (
            "interface/app.py", "interface/app_layout.py",
            "interface/financeiro.py", "interface/financeiro_views.py", "interface/financeiro_dialogos.py",
            "interface/compras.py", "interface/compras_views.py", "interface/compras_acoes.py",
            "interface/tecnologia.py", "interface/tecnologia_operacoes.py", "interface/tecnologia_acoes.py",
        )
        for arquivo in arquivos:
            with self.subTest(arquivo=arquivo):
                ast.parse((RAIZ / arquivo).read_text(encoding="utf-8"), filename=arquivo)

    def test_runner_possui_timeout_por_arquivo(self):
        runner = (RAIZ / "scripts" / "executar_grupo_testes.py").read_text(encoding="utf-8")
        self.assertIn("timeout=timeout_segundos", runner)
        self.assertIn("subprocess.TimeoutExpired", runner)
        self.assertIn("--timeout-arquivo", runner)

    def test_workflow_e_release_usam_versao_canonica(self):
        workflow = (RAIZ / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
        self.assertIn(f"Qualidade {VERSAO_INTERFACE}", workflow)
        self.assertIn(f"DataIntelligence-Source-V{VERSAO_PLATAFORMA}", workflow)


if __name__ == "__main__":
    unittest.main()
