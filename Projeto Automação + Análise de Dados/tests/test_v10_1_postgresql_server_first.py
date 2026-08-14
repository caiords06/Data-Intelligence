"""Regressões da V10.1 — PostgreSQL + Server First."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest

from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA
from enterprise.postgresql.adapter import HybridRow, traduzir_sql
from servidor_corporativo.config import ConfigServidor

RAIZ = Path(__file__).resolve().parents[1]
SCHEMA = RAIZ / "enterprise" / "postgresql" / "schema_v10_1.sql"
ISS = RAIZ / "installer" / "DataIntelligenceSetup.iss"


class PostgreSQLServerFirstV101Tests(unittest.TestCase):
    def test_versao(self):
        self.assertEqual(VERSAO_PLATAFORMA, "11.1.0")
        self.assertEqual(VERSAO_INTERFACE, "V11.1.0")

    def test_servidor_e_postgresql_por_padrao(self):
        self.assertEqual(ConfigServidor().db_backend, "postgresql")
        with self.assertRaises(ValueError):
            ConfigServidor().validar()

    def test_postgresql_exige_referencia_de_segredo(self):
        with self.assertRaises(ValueError):
            replace(ConfigServidor(), db_backend="postgresql").validar()
        cfg = replace(
            ConfigServidor(), db_backend="postgresql", postgres_segredo="env:DATA_INTELLIGENCE_PG_PASSWORD"
        ).validar()
        self.assertEqual(cfg.postgres_banco, "dataintelligence")
        self.assertNotIn("password", json.dumps(cfg.__dict__ if hasattr(cfg, "__dict__") else {}, default=str))

    def test_hybrid_row_mantem_acesso_por_indice_e_nome(self):
        row = HybridRow(["id", "nome"], [7, "Teste"])
        self.assertEqual(row[0], 7)
        self.assertEqual(row["nome"], "Teste")

    def test_tradutor_qmark_is_e_insert_ignore(self):
        self.assertEqual(traduzir_sql("SELECT * FROM x WHERE a=?"), "SELECT * FROM x WHERE a=%s")
        t = traduzir_sql("SELECT * FROM x WHERE a IS ?")
        self.assertIn("IS NOT DISTINCT FROM %s", t)
        t = traduzir_sql("INSERT OR IGNORE INTO x(a) VALUES (?)")
        self.assertIn("INSERT INTO", t)
        self.assertIn("ON CONFLICT DO NOTHING", t)
        self.assertIn("%s", t)

    def test_tradutor_sqlite_master_parametrizado_e_literal(self):
        parametrizado = traduzir_sql(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
        )
        self.assertIn("information_schema.tables", parametrizado)
        self.assertIn("table_name=%s", parametrizado)
        self.assertNotIn("sqlite_master", parametrizado)

        literal = traduzir_sql(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='usuarios_empresas'"
        )
        self.assertIn("information_schema.tables", literal)
        self.assertIn("table_name='usuarios_empresas'", literal)
        self.assertNotIn("sqlite_master", literal)

    def test_schema_postgresql_e_baseline(self):
        t = SCHEMA.read_text(encoding="utf-8")
        self.assertIn("postgresql_baseline_v10_1", t)
        self.assertIn("CREATE UNIQUE INDEX", t)
        self.assertIn("LOWER(usuario)", t)
        self.assertIn("FOREIGN KEY (filial_id, empresa_id)", t)
        self.assertNotIn("AUTOINCREMENT", t)
        self.assertNotIn("sqlite_master", t)
        self.assertGreaterEqual(t.upper().count("CREATE TABLE"), 150)

    def test_cli_expoe_config_health_e_migracao(self):
        t = (RAIZ / "servidor_corporativo" / "__main__.py").read_text(encoding="utf-8")
        for item in ("configure-db", "check-db", "migrate-sqlite", "--bootstrap-file"):
            self.assertIn(item, t)

    def test_setup_preserva_seis_perfis_e_configura_postgres(self):
        t = ISS.read_text(encoding="utf-8")
        self.assertEqual(t.count("RolePage.Add("), 6)
        for perfil in (
            "PC SERVIDOR + PC CENTRAL", "PC CENTRAL", "PC SERVIDOR",
            "PC CLIENTE + AGENTE", "PC CLIENTE", "PC AGENTE",
        ):
            self.assertIn(f"RolePage.Add('{perfil}')", t)
        for item in (
            "PostgreSQL (obrigatório)",
            "configure-db --bootstrap-file", "migrate-sqlite --source",
            "postgresql_migrated_v10_1.marker", "DataIntelligence_Setup_V11.1.0",
        ):
            self.assertIn(item, t)
        self.assertNotIn("SQLite (compatibilidade/standalone)", t)
        self.assertNotIn("configure-db --backend sqlite", t)
        self.assertNotRegex(t, r"--password\s")

    def test_server_spec_empacota_driver_e_schema(self):
        t = (RAIZ / "DataIntelligenceServer.spec").read_text(encoding="utf-8")
        self.assertIn('collect_submodules("psycopg")', t)
        self.assertIn('collect_submodules("psycopg_pool")', t)
        self.assertIn("schema_v10_1.sql", t)

    def test_release_exige_componentes_v101(self):
        from scripts.empacotar_fonte_limpa import ARQUIVOS_OBRIGATORIOS
        for item in (
            "enterprise/postgresql/adapter.py", "enterprise/postgresql/bootstrap.py",
            "enterprise/postgresql/migracao.py", "enterprise/postgresql/schema_v10_1.sql",
            "core/segredos.py", "README_V10_1_POSTGRESQL_SERVER_FIRST.md",
            "scripts/verificar_instalador_v10_1.py", "VERSAO_V10_1_1.txt",
        ):
            self.assertIn(item, ARQUIVOS_OBRIGATORIOS)

    def test_ci_exige_postgresql_real(self):
        workflow = (RAIZ / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
        self.assertIn("name: Qualidade V11.1.0", workflow)
        self.assertIn("postgresql-integracao:", workflow)
        self.assertIn("image: postgres:17", workflow)
        self.assertIn("RUN_POSTGRES_INTEGRATION: '1'", workflow)
        self.assertIn("tests/test_v10_1_postgresql_integration.py", workflow)
        self.assertIn("postgresql-integracao, pacote-fonte-testes", workflow)

    def test_backups_tem_caminho_postgresql(self):
        t = (RAIZ / "enterprise" / "backups.py").read_text(encoding="utf-8")
        for item in ("pg_dump", "pg_restore", "postgresql.dump", "backend_banco"):
            self.assertIn(item, t)


if __name__ == "__main__":
    unittest.main()
