"""Regressões do pipeline de release V9.3."""
from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
import zipfile

from core.versao import PYTHON_RELEASE, VERSAO_INTERFACE, VERSAO_PLATAFORMA
from enterprise.migrations import MIGRACOES, validar_registry
from scripts.empacotar_fonte_limpa import (
    ARQUIVOS_OBRIGATORIOS,
    MANIFESTO_NOME,
    RAIZ,
    empacotar,
    permitido,
    validar_zip,
)


class ReleaseEngineeringV93Tests(unittest.TestCase):
    def test_versao_canonica(self):
        self.assertEqual(VERSAO_PLATAFORMA, "9.3.0")
        self.assertEqual(VERSAO_INTERFACE, "V9.3")
        self.assertEqual(PYTHON_RELEASE, (3, 14))

    def test_registry_fisico_e_canonico_sao_identicos(self):
        self.assertEqual(validar_registry(), MIGRACOES)
        self.assertEqual(len(MIGRACOES), 19)

    def test_migrations_legadas_nao_estao_no_caminho_executavel(self):
        pasta = RAIZ / "enterprise" / "migrations"
        self.assertFalse((pasta / "013_plataforma_distribuida.py").exists())
        self.assertFalse((pasta / "014_consistencia_monetaria.py").exists())

    def test_empacotador_preserva_specs_reais(self):
        for nome in ("DataIntelligencePlatform.spec", "DataIntelligenceServer.spec", "agente_ti.spec"):
            caminho = RAIZ / nome
            self.assertTrue(permitido(caminho), nome)
            ast.parse(caminho.read_text(encoding="utf-8"), filename=nome)
        for antigo in ("DataIntelligence.spec", "DataTIAgent.spec"):
            self.assertFalse(permitido(RAIZ / antigo), antigo)

    def test_source_zip_contem_obrigatorios_manifesto_e_nao_contem_residuos(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida, _ = empacotar(Path(tmp) / "source.zip")
            validar_zip(saida)
            with zipfile.ZipFile(saida) as zf:
                nomes = set(zf.namelist())
            self.assertTrue(ARQUIVOS_OBRIGATORIOS <= nomes)
            self.assertIn(MANIFESTO_NOME, nomes)
            self.assertFalse(any(x.startswith((".git/", "storage/", "dist/", "build/", "artifacts/")) for x in nomes))

    def test_source_zip_e_deterministico(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, _ = empacotar(Path(tmp) / "a.zip")
            b, _ = empacotar(Path(tmp) / "b.zip")
            self.assertEqual(sha256(a.read_bytes()).hexdigest(), sha256(b.read_bytes()).hexdigest())

    def test_scripts_de_build_referenciam_specs_e_locks_canonicos(self):
        texto = (RAIZ / "scripts" / "build_distribuicao_windows.ps1").read_text(encoding="utf-8")
        for trecho in (
            "requirements.lock.txt", "requirements-build.lock.txt",
            "DataIntelligencePlatform.spec", "DataIntelligenceServer.spec", "agente_ti.spec",
            "verificar_python_release.py",
        ):
            self.assertIn(trecho, texto)


if __name__ == "__main__":
    unittest.main()
