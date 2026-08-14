"""Regressões do instalador unificado da V10."""
from __future__ import annotations

from pathlib import Path
import unittest

from core.versao import VERSAO_INTERFACE, VERSAO_PLATAFORMA

RAIZ = Path(__file__).resolve().parents[1]
ISS = RAIZ / "installer" / "DataIntelligenceSetup.iss"


class InstaladorUnificadoV10Tests(unittest.TestCase):
    def test_versao_v10(self):
        self.assertEqual(VERSAO_PLATAFORMA, "11.1.0")
        self.assertEqual(VERSAO_INTERFACE, "V11.1.0")

    def test_seis_perfis_exatos_estao_no_setup(self):
        texto = ISS.read_text(encoding="utf-8")
        for perfil in (
            "PC SERVIDOR + PC CENTRAL", "PC CENTRAL", "PC SERVIDOR",
            "PC CLIENTE + AGENTE", "PC CLIENTE", "PC AGENTE",
        ):
            self.assertIn(f"RolePage.Add('{perfil}')", texto)
        self.assertIn("True, False", texto)  # seleção exclusiva por radio button

    def test_servidor_central_instala_desktop_e_servidor(self):
        texto = ISS.read_text(encoding="utf-8")
        self.assertIn('Check: HasRolePlatform', texto)
        self.assertIn('Check: HasRoleServer', texto)
        self.assertIn("if Role() = 'servercentral' then", texto)
        self.assertIn("http://127.0.0.1:", texto)

    def test_cliente_agente_instala_os_dois_componentes(self):
        texto = ISS.read_text(encoding="utf-8")
        self.assertIn('Check: HasRoleAgent', texto)
        self.assertIn("(Role() = 'clientagent')", texto)

    def test_dados_persistentes_ficam_fora_program_files(self):
        texto = ISS.read_text(encoding="utf-8")
        self.assertIn("{commonappdata}\\DataIntelligence\\Platform", texto)
        self.assertIn("{commonappdata}\\DataIntelligence\\Server", texto)
        self.assertIn("Intencionalmente NÃO removemos", texto)

    def test_setup_configura_autostart_servidor_e_agente(self):
        texto = ISS.read_text(encoding="utf-8")
        self.assertIn("install-task --executable", texto)
        self.assertIn("wait-ready --timeout 45", texto)
        self.assertIn("install --executable", texto)
        self.assertIn("'start-task'", texto)
        self.assertNotIn("schtasks /Create /TN DataIntelligenceCorporateServer", texto)

    def test_senha_admin_nao_e_passada_em_argumento(self):
        texto = ISS.read_text(encoding="utf-8")
        self.assertIn("--bootstrap-file", texto)
        self.assertNotIn("--password ", texto)
        self.assertNotIn("AdminPasswordPage.Values[0] +", texto)

    def test_build_principal_gera_setup_unico(self):
        texto = (RAIZ / "scripts" / "build_distribuicao_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("build_setup_windows.ps1", texto)
        self.assertIn("DataIntelligence_Setup_V11.1.0.exe", texto)

    def test_source_zip_exige_instalador_v10(self):
        texto = (RAIZ / "scripts" / "empacotar_fonte_limpa.py").read_text(encoding="utf-8")
        for item in (
            "installer/DataIntelligenceSetup.iss",
            "scripts/build_setup_windows.ps1",
            "README_V10_INSTALADOR_UNIFICADO.md",
        ):
            self.assertIn(item, texto)

    def test_bootstrap_servidor_tem_modo_nao_interativo(self):
        texto = (RAIZ / "servidor_corporativo" / "__main__.py").read_text(encoding="utf-8")
        for item in ('--nome', '--usuario', '--email', '--password-file'):
            self.assertIn(item, texto)


if __name__ == "__main__":
    unittest.main()
