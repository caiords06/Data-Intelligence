from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from configuracoes import preferencias
from historico.repositorio import (
    excluir_analise,
    listar_historico,
    obter_analise,
    registrar_analise,
)


class HistoricoPreferenciasTests(unittest.TestCase):
    def test_preferencias_sao_normalizadas_e_persistidas_no_banco(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta)
            with patch.object(banco, "DB_PATH", destino / "teste.db"), patch.object(
                banco, "STORAGE_DIR", destino
            ):
                banco.inicializar_banco()
                admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
                SESSAO.iniciar(admin)
                try:
                    salvas = preferencias.salvar_preferencias(
                        {
                            "atraso_minimo_segundos": 99,
                            "categoria_padrao": "financeiro",
                            "tempo_sessao_minutos": 1,
                        }
                    )
                    self.assertEqual(salvas["atraso_minimo_segundos"], 15)
                    self.assertEqual(salvas["tempo_sessao_minutos"], 5)
                    self.assertEqual(
                        preferencias.carregar_preferencias()["categoria_padrao"],
                        "financeiro",
                    )
                    inseguras = preferencias.salvar_preferencias(
                        {"url_validacao": "file:///C:/dados/privados.txt"}
                    )
                    self.assertEqual(inseguras["url_validacao"], "https://example.com")
                    self.assertFalse((destino / "preferencias.json").exists())
                finally:
                    SESSAO.encerrar()

    def test_historico_respeita_o_dono_e_nao_grava_caminho_completo(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta)
            with patch.object(banco, "DB_PATH", destino / "teste.db"), patch.object(
                banco, "STORAGE_DIR", destino
            ):
                banco.inicializar_banco()
                admin = criar_admin_inicial(
                    "Administrador", "admin", "SenhaAdmin#123"
                )
                usuario = criar_usuario(
                    "Analista",
                    "analista",
                    "SenhaAnalista#123",
                    ator=admin,
                )
                resultado = {
                    "dataframe": pd.DataFrame({"valor": [10, 20]}),
                    "arquivos": ["/dados/sigilosos/financeiro.xlsx"],
                    "categoria": "financeiro",
                    "configuracao": {"fonte": "computador"},
                    "indicadores": {"saldo": 30},
                    "qualidade": {
                        "score_qualidade": 98.0,
                        "nivel_qualidade": "Excelente",
                    },
                }
                historico_id = registrar_analise(resultado, usuario["id"])
                self.assertEqual(len(listar_historico(usuario)), 1)
                detalhe = obter_analise(historico_id, usuario)
                self.assertEqual(detalhe["resumo"]["arquivos"], ["financeiro.xlsx"])

                outro = criar_usuario(
                    "Outro", "outro", "SenhaOutro#123", ator=admin
                )
                self.assertEqual(listar_historico(outro), [])
                with self.assertRaises(PermissionError):
                    obter_analise(historico_id, outro)
                excluir_analise(historico_id, admin)
                self.assertEqual(listar_historico(admin), [])


if __name__ == "__main__":
    unittest.main()
