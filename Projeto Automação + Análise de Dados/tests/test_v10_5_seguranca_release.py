from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from servidor_corporativo.config import ConfigServidor, carregar_config, salvar_config

RAIZ = Path(__file__).resolve().parents[1]


class SegurancaReleaseV105Tests(unittest.TestCase):
    def test_servidor_falha_fechado_por_padrao_sem_expor_lan(self):
        cfg = ConfigServidor()
        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertEqual(cfg.ambiente, "producao")
        self.assertFalse(cfg.tls)

    def test_cors_exige_origens_explicitas_em_producao(self):
        base = dict(postgres_segredo="env:DATA_INTELLIGENCE_PG_PASSWORD")
        cfg = ConfigServidor(cors_origins=("HTTPS://APP.Empresa.Local/",), **base).validar()
        self.assertEqual(cfg.cors_origins, ("https://app.empresa.local",))
        with self.assertRaisesRegex(ValueError, "CORS.*produção"):
            ConfigServidor(cors_origins=("*",), **base).validar()
        desenvolvimento = ConfigServidor(
            ambiente="desenvolvimento", cors_origins=("*",), **base
        ).validar()
        self.assertEqual(desenvolvimento.cors_origins, ("*",))

    def test_cors_persiste_em_server_json_sem_wildcard_de_producao(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ", {"DATA_INTELLIGENCE_SERVER_DATA_DIR": tmp}, clear=False
        ):
            salvar_config(ConfigServidor(
                postgres_segredo="env:DATA_INTELLIGENCE_PG_PASSWORD",
                cors_origins=("https://app.empresa.local",),
            ))
            carregada = carregar_config()
            self.assertEqual(carregada.cors_origins, ("https://app.empresa.local",))

    def test_setup_nao_habilita_http_lan_sem_consentimento(self):
        texto = (RAIZ / "installer" / "DataIntelligenceSetup.iss").read_text(encoding="utf-8")
        self.assertIn("ServerPage.Values[0] := 'https://servidor.empresa.local:8770';", texto)
        self.assertIn("AllowPrivateHttpPage.Values[0] := False;", texto)
        self.assertIn("ServerHost := '127.0.0.1';", texto)
        self.assertIn("ServerEnvironment := 'producao';", texto)
        self.assertNotIn("ServerHost := '0.0.0.0';", texto)
        self.assertNotIn("ServerEnvironment := 'lan';", texto)
        self.assertIn("HTTP fora de loopback não é permitido", texto)

    def test_script_servidor_exige_switch_para_expor_http_na_lan(self):
        texto = (RAIZ / "scripts" / "Instalar-Servidor-Corporativo.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$PermitirHttpLan", texto)
        self.assertIn('if ($PermitirHttpLan) { throw "HTTP na LAN foi desativado', texto)
        self.assertIn('$ServerHost = "127.0.0.1"', texto)
        self.assertIn('$ServerAmbiente = "producao"', texto)

    def test_runner_nao_depende_de_pipe_herdavel_por_processos_netos(self):
        texto = (RAIZ / "scripts" / "executar_grupo_testes.py").read_text(encoding="utf-8")
        self.assertIn("TemporaryFile", texto)
        self.assertIn("processo.wait(timeout=timeout_segundos)", texto)
        self.assertNotIn('"stdout": subprocess.PIPE', texto)
        self.assertIn('ambiente["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"', texto)

    def test_build_publica_marcador_da_versao_atual(self):
        texto = (RAIZ / "scripts" / "build_distribuicao_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('"VERSAO_V11_1_0.txt"', texto)
        self.assertNotIn('Copy-Item (Join-Path $ProjectRoot "VERSAO_V10_1_1.txt")', texto)


if __name__ == "__main__":
    unittest.main()
