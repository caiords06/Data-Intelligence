from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PostgreSQLGroupByCockpitTests(unittest.TestCase):
    def test_estoque_alertas_agrupa_nome_do_item(self):
        texto = (ROOT / "enterprise/domains/estoque/inteligencia.py").read_text(encoding="utf-8")
        self.assertIn("GROUP BY l.id, i.nome, s.deposito_id", texto)

    def test_listagem_lotes_agrupa_colunas_do_item(self):
        texto = (ROOT / "enterprise/domains/estoque/inteligencia.py").read_text(encoding="utf-8")
        self.assertIn("GROUP BY l.id, i.codigo, i.nome", texto)

    def test_analise_estoque_nao_usa_alias_no_having(self):
        texto = (ROOT / "enterprise/domains/estoque/inteligencia.py").read_text(encoding="utf-8")
        self.assertNotIn("HAVING saldo>0", texto)
        self.assertIn("HAVING COALESCE(SUM(s.quantidade_fisica),0)>0", texto)

    def test_cockpit_isola_falha_de_um_modulo(self):
        texto = (ROOT / "enterprise/central.py").read_text(encoding="utf-8")
        self.assertIn("Falha ao calcular resumo do módulo %s", texto)
        self.assertIn("except Exception:", texto)

    def test_outros_group_by_portaveis_corrigidos(self):
        estoque = (ROOT / "enterprise/domains/estoque/consultas.py").read_text(encoding="utf-8")
        self.assertIn("GROUP BY i.id, c.nome, u.codigo", estoque)
        self.assertIn("GROUP BY i.id, d.nome", estoque)
        ti = (ROOT / "enterprise/tecnologia.py").read_text(encoding="utf-8")
        self.assertNotIn("HAVING utilizadas <", ti)

    def test_compras_recorrentes_nao_seleciona_coluna_fora_do_group_by(self):
        texto = (ROOT / "enterprise/domains/compras/inteligencia.py").read_text(encoding="utf-8")
        self.assertIn("SELECT MIN(si.descricao) descricao,COUNT(DISTINCT s.id)", texto)
        self.assertNotIn("SELECT si.descricao,COUNT(DISTINCT s.id)", texto)


if __name__ == "__main__":
    unittest.main()
