from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.seguranca import validar_forca_senha
from servidor_corporativo.config import ConfigServidor

RAIZ = Path(__file__).resolve().parents[1]


class PostgreSQLOnlyCorrecoesTests(unittest.TestCase):
    def test_senha_com_exclamacao_e_valida(self):
        # Regressão do caso real reportado na interface.
        validar_forca_senha("Caio01302890!")

    def test_backend_padrao_e_postgresql(self):
        ambiente = dict(os.environ)
        ambiente.pop("DATA_INTELLIGENCE_DB_BACKEND", None)
        ambiente.pop("DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE", None)
        with patch.dict(os.environ, ambiente, clear=True):
            self.assertEqual(banco.backend_banco(), "postgresql")

    def test_sqlite_de_producao_e_bloqueado(self):
        ambiente = dict(os.environ)
        ambiente["DATA_INTELLIGENCE_DB_BACKEND"] = "sqlite"
        ambiente.pop("DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE", None)
        with patch.dict(os.environ, ambiente, clear=True):
            with self.assertRaises(RuntimeError):
                banco.backend_banco()

    def test_config_servidor_padrao_e_postgresql(self):
        self.assertEqual(ConfigServidor().db_backend, "postgresql")

    def test_cliente_nao_replica_identidade_em_sqlite(self):
        texto = (RAIZ / "enterprise" / "servidor_cliente.py").read_text(encoding="utf-8")
        self.assertNotIn("_sincronizar_cache_identidade", texto)
        self.assertNotIn("INSERT OR REPLACE INTO usuarios", texto)
        self.assertIn("_BOOTSTRAP_MEMORIA", texto)

    def test_preferencias_nao_usam_json_local(self):
        texto = (RAIZ / "configuracoes" / "preferencias.py").read_text(encoding="utf-8")
        self.assertNotIn("PREFERENCIAS_PATH", texto)
        self.assertNotIn("write_text", texto)
        self.assertIn("preferencias_usuarios", texto)

    def test_schema_postgresql_inclui_historico_e_preferencias(self):
        texto = (RAIZ / "enterprise" / "postgresql" / "schema_v10_1.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS historico_analises", texto)
        self.assertIn("CREATE TABLE IF NOT EXISTS preferencias_usuarios", texto)
        self.assertNotIn("AUTOINCREMENT", texto)

    def test_rpc_centraliza_historico_e_preferencias(self):
        from core.rpc_central import RPC_ALLOWLIST
        self.assertIn("historico.repositorio", RPC_ALLOWLIST)
        self.assertIn("configuracoes.preferencias", RPC_ALLOWLIST)

    def test_configure_db_recupera_server_json_parcial_do_setup_1011(self):
        from servidor_corporativo.__main__ import cmd_configure_db
        from servidor_corporativo.config import carregar_config

        with tempfile.TemporaryDirectory() as td:
            raiz = Path(td)
            # Reproduz exatamente o estado deixado pelo Setup V10.2.0:
            # db_backend=postgresql gravado antes da referência DPAPI existir.
            (raiz / "server.json").write_text(
                json.dumps({
                    "host": "127.0.0.1", "porta": 8770, "tls": False,
                    "max_upload_mb": 1024, "ambiente": "producao",
                    "db_backend": "postgresql"
                }),
                encoding="utf-8",
            )
            senha = raiz / "senha.txt"
            senha.write_text("SenhaTeste!123", encoding="utf-8")
            bootstrap = raiz / "db-bootstrap.json"
            bootstrap.write_text(json.dumps({
                "backend": "postgresql",
                "server_host": "127.0.0.1", "server_porta": 8899,
                "server_tls": False, "server_max_upload_mb": 1024,
                "server_ambiente": "producao",
                "host": "127.0.0.1", "porta": 5432,
                "banco": "dataintelligence", "usuario": "dataintelligence",
                "sslmode": "prefer", "pool_min": 2, "pool_max": 12,
                "password_file": str(senha),
            }), encoding="utf-8")
            args = argparse.Namespace(
                bootstrap_file=bootstrap, backend="postgresql", host=None, porta=None,
                banco=None, usuario=None, sslmode="prefer", pool_min=2, pool_max=12,
                password_file=None,
            )
            with patch.dict(os.environ, {"DATA_INTELLIGENCE_SERVER_DATA_DIR": str(raiz)}):
                with patch("enterprise.postgresql.adapter.testar_conexao", return_value={
                    "banco": "dataintelligence", "usuario": "dataintelligence",
                    "versao": "PostgreSQL teste", "latencia_ms": 1.0,
                }), patch("enterprise.postgresql.bootstrap.inicializar_schema_postgresql"):
                    self.assertEqual(cmd_configure_db(args), 0)
                cfg = carregar_config()
                self.assertEqual(cfg.porta, 8899)
                self.assertEqual(cfg.postgres_porta, 5432)
                self.assertTrue(cfg.postgres_segredo)

    def test_setup_nao_grava_server_json_parcial_antes_do_configure_db(self):
        texto = (RAIZ / "installer" / "DataIntelligenceSetup.iss").read_text(encoding="utf-8")
        trecho = texto[texto.index("procedure ConfigureServer"):texto.index("procedure ConfigureAgent")]
        self.assertIn('"server_porta":', trecho)
        self.assertNotIn("SaveUtf8NoBom(ConfigPath, Payload)", trecho)
        self.assertIn("install-db-error.log", trecho)
        self.assertIn("LoadStringsFromFile", texto)
        self.assertNotIn("LoadStringFromFile(ErrorPath, ErrorDetails)", texto)


if __name__ == "__main__":
    unittest.main()
