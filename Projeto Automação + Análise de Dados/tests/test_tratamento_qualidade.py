import unittest

import pandas as pd

from dados.inconsistencias import analisar_inconsistencias, detectar_outliers
from dados.qualidade import analisar_qualidade
from dados.tratamento import normalizar_colunas, tratar_dataframe


class TratamentoQualidadeTests(unittest.TestCase):
    def test_tratamento_converte_numero_data_e_texto_sem_alterar_original(self):
        original = pd.DataFrame(
            {
                "Data Venda": ["31/12/2025", "data inválida", None],
                "Valor Final": ["R$ 1.234,56", "99,90", "inválido"],
                "Produto ": ["  Camisa   Azul ", "N/A", "Calça"],
            }
        )

        tratado, relatorio = tratar_dataframe(original)

        self.assertEqual(
            list(tratado.columns),
            ["data_venda", "valor_final", "produto"],
        )
        self.assertEqual(float(tratado.loc[0, "valor_final"]), 1234.56)
        self.assertEqual(float(tratado.loc[1, "valor_final"]), 99.90)
        self.assertTrue(pd.isna(tratado.loc[2, "valor_final"]))
        self.assertEqual(tratado.loc[0, "produto"], "Camisa Azul")
        self.assertTrue(pd.isna(tratado.loc[1, "produto"]))
        self.assertEqual(relatorio["total_valores_invalidos"], 2)
        self.assertEqual(original.loc[0, "Valor Final"], "R$ 1.234,56")
        self.assertEqual(original.loc[0, "Produto "], "  Camisa   Azul ")

    def test_normalizacao_resolve_colisoes_sem_perder_coluna(self):
        df = pd.DataFrame({"Valor Final": [10], "valor_final": [20]})
        tratado, relatorio = normalizar_colunas(df)
        self.assertEqual(list(tratado.columns), ["valor_final", "valor_final_2"])
        self.assertEqual(relatorio["quantidade_colisoes_colunas"], 1)
        self.assertEqual(int(tratado.iloc[0].sum()), 30)

    def test_outlier_e_sinalizado_sem_ser_removido(self):
        df = pd.DataFrame({"valor": [10, 11, 12, 13, 14, 15, 16, 17, 1000]})
        diagnostico = detectar_outliers(df)
        self.assertEqual(diagnostico["total_outliers"], 1)
        self.assertEqual(diagnostico["por_coluna"]["valor"]["maior_outlier"], 1000.0)
        self.assertEqual(len(df), 9)

    def test_inconsistencias_negativas_temporais_e_textuais(self):
        ano_futuro = pd.Timestamp.now().year + 2
        df = pd.DataFrame(
            {
                "quantidade": [1, -2],
                "data": ["01/01/2020", f"01/01/{ano_futuro}"],
                "regiao": ["São Paulo", "sao paulo"],
                "data_admissao": ["10/01/2024", "10/01/2024"],
                "data_desligamento": ["09/01/2024", None],
            }
        )
        diagnostico = analisar_inconsistencias(df)
        self.assertEqual(diagnostico["total_valores_negativos"], 1)
        self.assertEqual(diagnostico["total_datas_futuras"], 1)
        self.assertEqual(diagnostico["ordens_temporais_invalidas"], 1)
        self.assertEqual(diagnostico["total_grupos_textuais_inconsistentes"], 1)

    def test_qualidade_inclui_novas_dimensoes(self):
        df = pd.DataFrame({"produto": ["A", "A"], "quantidade": [1, -1]})
        qualidade = analisar_qualidade(
            df,
            relatorio_tratamento={"total_valores_invalidos": 1},
        )
        self.assertIn("validade", qualidade)
        self.assertIn("consistencia", qualidade)
        self.assertIn("outliers", qualidade)
        self.assertEqual(qualidade["valores_invalidos"], 1)
        self.assertEqual(
            qualidade["inconsistencias"]["total_valores_negativos"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
