"""Regressões arquiteturais da V9.5 sem alterar contratos funcionais."""
from __future__ import annotations

from pathlib import Path
import importlib
import unittest

from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA

RAIZ = Path(__file__).resolve().parents[1]


class ArquiteturaDominiosV95Tests(unittest.TestCase):
    def test_versao_v95(self):
        self.assertEqual(VERSAO_PLATAFORMA, "11.1.0")
        self.assertEqual(VERSAO_INTERFACE, "V11.1.0")

    def test_monolitos_principais_foram_reduzidos(self):
        limites = {
            "financeiro.py": 1300,
            "compras.py": 1350,
            "estoque.py": 1200,
            "tecnologia.py": 1200,
        }
        for nome, limite in limites.items():
            with self.subTest(nome=nome):
                linhas = len((RAIZ / "enterprise" / nome).read_text(encoding="utf-8").splitlines())
                self.assertLessEqual(linhas, limite, f"{nome} voltou a crescer para {linhas} linhas")

    def test_componentes_extraidos_sao_pequenos_e_importaveis(self):
        modulos = (
            "enterprise.domains.financeiro.base",
            "enterprise.domains.financeiro.conciliacao",
            "enterprise.domains.financeiro.inteligencia",
            "enterprise.domains.compras.base",
            "enterprise.domains.compras.inteligencia",
            "enterprise.domains.compras.relatorios",
            "enterprise.domains.estoque.base",
            "enterprise.domains.estoque.inteligencia",
            "enterprise.domains.estoque.relatorios",
            "enterprise.domains.tecnologia.base",
            "enterprise.domains.tecnologia.agentes",
            "enterprise.domains.tecnologia.infraestrutura",
        )
        for nome in modulos:
            with self.subTest(modulo=nome):
                modulo = importlib.import_module(nome)
                caminho = Path(modulo.__file__)
                self.assertLessEqual(len(caminho.read_text(encoding="utf-8").splitlines()), 500)

    def test_fachadas_historicas_continuam_expondo_funcoes_extraidas(self):
        casos = {
            "enterprise.financeiro": (
                "importar_extrato", "conciliar_item", "calcular_dre",
                "resumo_financeiro", "gerar_relatorio_financeiro",
            ),
            "enterprise.compras": (
                "listar_secao", "resumo_compras", "gerar_relatorio_compras",
            ),
            "enterprise.estoque": (
                "calcular_reposicao", "listar_secao", "gerar_relatorio_estoque",
            ),
            "enterprise.tecnologia": (
                "descobrir_segmento_rede", "atualizar_ativo", "registrar_snapshot_agente",
            ),
        }
        for modulo_nome, funcoes in casos.items():
            modulo = importlib.import_module(modulo_nome)
            for funcao in funcoes:
                with self.subTest(modulo=modulo_nome, funcao=funcao):
                    self.assertTrue(callable(getattr(modulo, funcao, None)))

    def test_interface_continua_dependendo_de_services_e_nao_de_domains_internos(self):
        for nome in ("financeiro", "compras", "estoque", "tecnologia", "rh"):
            arquivos = [RAIZ / "interface" / f"{nome}.py"]
            shared = RAIZ / "interface" / f"{nome}_shared.py"
            if shared.is_file():
                arquivos.append(shared)
            fonte = "\n".join(x.read_text(encoding="utf-8") for x in arquivos)
            self.assertIn(f"from services.departamentos.{nome} import (", fonte)
            self.assertNotIn("enterprise.domains", fonte)

    def test_roteador_e_leftbox_da_v94_foram_preservados(self):
        fonte = (RAIZ / "interface" / "navegacao_modulos.py").read_text(encoding="utf-8")
        for trecho in ("ALIASES_SECOES", "normalizar_secao_modulo", "criar_sidebar_modulo", "tipo_tela_modulo"):
            self.assertIn(trecho, fonte)
        self.assertTrue((RAIZ / "tests" / "test_v9_4_navegacao_interface.py").is_file())



    def test_fachadas_refatoradas_preservam_proxy_rpc_central(self):
        for nome in ("financeiro", "compras", "estoque", "tecnologia"):
            fonte = (RAIZ / "enterprise" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertIn("_instalar_proxy_modulo(globals(), __name__)", fonte, nome)

    def test_provider_de_persistencia_tem_fronteira_e_restauracao(self):
        from enterprise.repositories import backend_atual, obter_provider, provider_temporario
        original = obter_provider()
        fake = lambda: object()
        self.assertEqual(backend_atual(), "sqlite")
        with provider_temporario(fake, nome="postgresql-simulacao"):
            self.assertIs(obter_provider(), fake)
            self.assertEqual(backend_atual(), "postgresql-simulacao")
        self.assertIs(obter_provider(), original)
        self.assertEqual(backend_atual(), "sqlite")

    def test_release_inclui_componentes_de_dominio(self):
        from scripts.empacotar_fonte_limpa import ARQUIVOS_OBRIGATORIOS
        obrigatorios = {
            "enterprise/domains/financeiro/conciliacao.py",
            "enterprise/domains/compras/relatorios.py",
            "enterprise/domains/estoque/relatorios.py",
            "enterprise/domains/tecnologia/agentes.py",
            "enterprise/domains/tecnologia/infraestrutura.py",
            "README_V9_5_ARQUITETURA_DOMINIOS.md",
            "VERSAO_V10_1_1.txt",
        }
        self.assertTrue(obrigatorios <= ARQUIVOS_OBRIGATORIOS)


if __name__ == "__main__":
    unittest.main()
