from pathlib import Path
import tempfile
import unittest

import pandas as pd

from analysis.temporal import analisar_periodos
from core.orquestrador import OrquestradorAnalise
from dados.classificador import classificar_dataframe
from dados.leitor import carregar_planilha, consolidar_planilhas, verificar_compatibilidade
from dados.periodos import identificar_periodo_nome
from dados.qualidade import analisar_qualidade

ROOT = Path(__file__).resolve().parents[1]
ARQUIVO_VENDAS = ROOT / "dados_exemplo" / "Vendas - Dez.xlsx"


class DataEngineTests(unittest.TestCase):
    def test_classificacao_e_indicadores_vendas(self):
        config = {
            "fonte": "computador",
            "categoria": "automatica",
            "periodo": "automatico",
            "modulos": {
                "estrutural": True,
                "indicadores": True,
                "temporal": True,
                "qualidade": True,
            },
        }
        resultado = OrquestradorAnalise().processar([str(ARQUIVO_VENDAS)], config)
        self.assertEqual(resultado["categoria"], "vendas")
        self.assertAlmostEqual(resultado["indicadores"]["faturamento_total"], 2917311.0)
        self.assertEqual(resultado["indicadores"]["total_vendas"], 3787)
        self.assertAlmostEqual(resultado["indicadores"]["quantidade_total"], 15227.0)
        self.assertEqual(resultado["indicadores"]["produto_maior_faturamento"], "Terno Linho")
        self.assertEqual(resultado["indicadores"]["loja_maior_faturamento"], "Iguatemi Campinas")

    def test_modulos_sao_independentes(self):
        config = {
            "fonte": "computador",
            "categoria": "automatica",
            "periodo": "automatico",
            "modulos": {
                "tratamento": False,
                "estrutural": False,
                "indicadores": False,
                "temporal": True,
                "qualidade": False,
            },
        }
        resultado = OrquestradorAnalise().processar([str(ARQUIVO_VENDAS)], config)
        self.assertIsNone(resultado["estrutural"])
        self.assertIsNone(resultado["tratamento"])
        self.assertIsNone(resultado["qualidade"])
        self.assertIsNone(resultado["indicadores"])
        self.assertIsNotNone(resultado["temporal"])
        self.assertEqual(len(resultado["temporal"]["periodos"]), 1)

    def test_orquestrador_preserva_original_e_entrega_copia_tratada(self):
        resultado = OrquestradorAnalise().processar([str(ARQUIVO_VENDAS)])
        self.assertIn("Código Venda", resultado["dataframe_original"].columns)
        self.assertIn("codigo_venda", resultado["dataframe"].columns)
        self.assertNotIn("Código Venda", resultado["dataframe"].columns)
        self.assertEqual(len(resultado["dataframe_original"]), len(resultado["dataframe"]))
        self.assertEqual(resultado["tratamento"]["linhas_removidas"], 0)

    def test_categoria_manual_preserva_deteccao_original(self):
        config = {
            "fonte": "computador",
            "categoria": "financeiro",
            "periodo": "automatico",
            "modulos": {"indicadores": True},
        }
        resultado = OrquestradorAnalise().processar([str(ARQUIVO_VENDAS)], config)
        self.assertEqual(resultado["categoria"], "financeiro")
        self.assertEqual(resultado["classificacao"]["categoria_detectada"], "vendas")
        self.assertEqual(resultado["classificacao"]["origem_categoria"], "usuario")
        self.assertIn("Receita total", resultado["classificacao"]["indicadores_sugeridos"])

    def test_compatibilidade_ignora_ordem_das_colunas(self):
        df1 = pd.DataFrame({"A": [1], "B": [2]})
        df2 = pd.DataFrame({"B": [3], "A": [4]})
        resultado = verificar_compatibilidade(
            [
                {"nome_arquivo": "a.xlsx", "dataframe": df1},
                {"nome_arquivo": "b.xlsx", "dataframe": df2},
            ]
        )
        self.assertTrue(resultado["compativel"])

    def test_qualidade_considera_texto_vazio_e_ignora_metadata_na_duplicidade(self):
        df = pd.DataFrame(
            {
                "produto": ["A", "A", ""],
                "valor": [10, 10, 20],
                "arquivo_origem": ["a.xlsx", "b.xlsx", "c.xlsx"],
            }
        )
        qualidade = analisar_qualidade(df)
        self.assertEqual(qualidade["valores_ausentes"], 1)
        self.assertEqual(qualidade["linhas_duplicadas"], 1)

    def test_nome_sem_ano_nao_inventa_ano_atual(self):
        periodo = identificar_periodo_nome("Vendas - Jan.xlsx")
        self.assertEqual(periodo["mes"], 1)
        self.assertIsNone(periodo["ano"])
        self.assertEqual(periodo["periodo"], "01/????")


    def test_csv_com_ponto_e_virgula(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "dados.csv"
            caminho.write_text("produto;valor\nA;10\nB;20\n", encoding="utf-8")
            df = carregar_planilha(caminho)
            self.assertEqual(list(df.columns), ["produto", "valor"])
            self.assertEqual(int(df["valor"].sum()), 30)

    def test_consolidacao_deriva_periodo_por_linha(self):
        df = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2025-01-15", "2025-07-20"]),
                "Valor": [10, 20],
            }
        )
        item = {
            "nome_arquivo": "multiperiodo.xlsx",
            "dataframe": df,
            "periodo": {
                "origem_identificacao": "coluna_data",
                "coluna_data": "Data",
            },
        }
        consolidado = consolidar_planilhas([item])
        self.assertEqual(list(consolidado["periodo_origem"]), ["01/2025", "07/2025"])
        self.assertEqual(list(consolidado["trimestre_origem"]), ["T1", "T3"])
        self.assertEqual(list(consolidado["semestre_origem"]), ["S1", "S2"])

    def test_temporal_respeita_granularidade(self):
        df = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2025-01-01", "2025-04-01"]),
                "Valor": [100.0, 200.0],
            }
        )
        classificacao = classificar_dataframe(df)
        trimestral = analisar_periodos(df, classificacao["campos"], "trimestral")
        semestral = analisar_periodos(df, classificacao["campos"], "semestral")
        self.assertEqual(len(trimestral["periodos"]), 2)
        self.assertEqual(len(semestral["periodos"]), 1)
        self.assertEqual(semestral["periodos"][0]["valor"], 300.0)


if __name__ == "__main__":
    unittest.main()
