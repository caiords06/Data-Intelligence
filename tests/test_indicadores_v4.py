import unittest

import pandas as pd

from dados.classificador import classificar_dataframe
from dados.indicadores import (
    calcular_indicadores,
    calcular_indicadores_cadastro,
    calcular_indicadores_estoque,
    calcular_indicadores_financeiros,
    calcular_indicadores_rh,
    calcular_indicadores_universais,
)


def campos(df):
    return classificar_dataframe(df)["campos"]


class IndicadoresV4Tests(unittest.TestCase):
    def test_indicadores_universais(self):
        df = pd.DataFrame({"nome": ["A", "A", None], "valor": [10, 10, 20]})
        resultado = calcular_indicadores_universais(df)
        self.assertEqual(resultado["total_registros"], 3)
        self.assertEqual(resultado["valores_ausentes"], 1)
        self.assertEqual(resultado["registros_duplicados"], 1)

    def test_motor_financeiro(self):
        df = pd.DataFrame(
            {
                "Receita": [1000, 500],
                "Despesa": [200, 100],
                "Categoria": ["Serviços", "Produtos"],
            }
        )
        resultado = calcular_indicadores_financeiros(df, campos(df))
        self.assertEqual(resultado["receita_total"], 1500.0)
        self.assertEqual(resultado["despesa_total"], 300.0)
        self.assertEqual(resultado["saldo"], 1200.0)
        self.assertEqual(resultado["margem_operacional"], 80.0)
        self.assertEqual(resultado["categoria_maior_movimentacao"], "Serviços")

    def test_motor_financeiro_interpreta_valores_com_sinal_sem_tipo(self):
        df = pd.DataFrame({"Valor": [1000, -250, 500, -50]})
        resultado = calcular_indicadores_financeiros(df, campos(df))
        self.assertEqual(resultado["receita_total"], 1500.0)
        self.assertEqual(resultado["despesa_total"], 300.0)
        self.assertEqual(resultado["saldo"], 1200.0)

    def test_motor_estoque(self):
        df = pd.DataFrame(
            {
                "Produto": ["A", "B", "C"],
                "Estoque": [10, 2, 0],
                "Custo": [5, 20, 8],
            }
        )
        resultado = calcular_indicadores_estoque(df, campos(df))
        self.assertEqual(resultado["estoque_total"], 12.0)
        self.assertEqual(resultado["produtos_baixo_estoque"], 1)
        self.assertEqual(resultado["produtos_sem_estoque"], 1)
        self.assertEqual(resultado["valor_estoque"], 90.0)
        self.assertEqual(resultado["produto_critico"], "C")

    def test_motor_cadastro(self):
        df = pd.DataFrame(
            {
                "ID Cadastro": [1, 2, 2],
                "Cliente": ["A", "B", "B"],
                "Status": ["Ativo", "Inativo", "Inativo"],
                "Categoria": ["X", "Y", "Y"],
            }
        )
        resultado = calcular_indicadores_cadastro(df, campos(df))
        self.assertEqual(resultado["total_registros"], 3)
        self.assertEqual(resultado["registros_unicos"], 2)
        self.assertEqual(resultado["registros_ativos"], 1)
        self.assertEqual(resultado["registros_inativos"], 2)
        self.assertEqual(resultado["maior_categoria"], "Y")

    def test_motor_recursos_humanos(self):
        df = pd.DataFrame(
            {
                "Colaborador": ["Ana", "Bruno"],
                "Setor": ["TI", "RH"],
                "Admissão": pd.to_datetime(["2020-01-01", "2024-01-01"]),
                "Desligamento": [pd.NaT, pd.Timestamp("2026-01-01")],
                "Salário": [5000, 3000],
                "Status": ["Ativo", "Inativo"],
            }
        )
        resultado = calcular_indicadores_rh(df, campos(df))
        self.assertEqual(resultado["total_colaboradores"], 2)
        self.assertEqual(resultado["total_setores"], 2)
        self.assertEqual(resultado["folha_total"], 8000.0)
        self.assertEqual(resultado["salario_medio"], 4000.0)
        self.assertEqual(
            resultado["taxa_desligamentos_sobre_base_percentual"],
            50.0,
        )
        self.assertNotIn("turnover_percentual", resultado)

    def test_motor_estoque_respeita_minimo_empresarial(self):
        df = pd.DataFrame(
            {
                "Produto": ["A", "B"],
                "Estoque": [8, 8],
                "Estoque mínimo": [10, 5],
            }
        )
        resultado = calcular_indicadores_estoque(df, campos(df))
        self.assertEqual(resultado["produtos_baixo_estoque"], 1)

    def test_despachante_inclui_motor_e_indicadores_universais(self):
        df = pd.DataFrame({"Produto": ["A"], "Estoque": [3]})
        resultado = calcular_indicadores("estoque", df, campos(df))
        self.assertEqual(resultado["categoria_motor"], "estoque")
        self.assertIn("universais", resultado)
        self.assertEqual(resultado["universais"]["total_registros"], 1)


if __name__ == "__main__":
    unittest.main()
