"""Regressões dos ajustes validados pelo usuário na V11.1.0."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class CorrecoesV1101Tests(unittest.TestCase):
    def test_preferencia_visual_local_e_atomica(self):
        from interface.gerenciador_tema import carregar_tema_local, salvar_tema_local
        with tempfile.TemporaryDirectory() as pasta, patch.dict(
            os.environ, {"DATA_INTELLIGENCE_USER_DATA_DIR": pasta}, clear=False,
        ):
            self.assertEqual(carregar_tema_local(), "escuro")
            self.assertEqual(salvar_tema_local("claro"), "claro")
            self.assertEqual(carregar_tema_local(), "claro")
            self.assertEqual(
                (Path(pasta) / "preferencia_visual.json").read_text(encoding="utf-8"),
                '{"tema":"claro"}',
            )

    def test_logger_faz_fallback_quando_destino_preferencial_nao_e_gravavel(self):
        import core.observabilidade as observabilidade
        real = observabilidade.RotatingFileHandler
        chamadas = {"n": 0}

        def construir(destino, *args, **kwargs):
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                raise PermissionError("ACL protegida")
            return real(destino, *args, **kwargs)

        with tempfile.TemporaryDirectory() as pasta, patch.object(
            observabilidade, "RotatingFileHandler", side_effect=construir,
        ), patch.object(observabilidade.tempfile, "gettempdir", return_value=pasta):
            logger = observabilidade.configurar_logger_rotativo(
                "data_intelligence.teste_acl_v1101", Path(pasta) / "protegido" / "desktop.jsonl",
            )
            self.assertIsNotNone(logger.arquivo_log)
            self.assertIn("DataIntelligence", str(logger.arquivo_log))
            for handler in list(logger.handlers):
                handler.close(); logger.removeHandler(handler)
            logging.Logger.manager.loggerDict.pop(logger.name, None)

    def test_analytics_e_reservado_a_gestao(self):
        from enterprise.contexto import eh_gestor_analytics
        self.assertFalse(eh_gestor_analytics({"id": 2, "ativo": True, "perfil": "usuario", "perfil_acesso": "analista"}))
        self.assertTrue(eh_gestor_analytics({"id": 3, "ativo": True, "perfil": "usuario", "perfil_acesso": "gestor_pessoas"}))
        self.assertTrue(eh_gestor_analytics({"id": 4, "ativo": True, "perfil": "usuario", "perfil_acesso": "diretoria"}))
        self.assertTrue(eh_gestor_analytics({"id": 1, "ativo": True, "perfil": "admin", "perfil_acesso": "administrador"}))

    def test_sidebar_analytics_termina_em_regras(self):
        from interface.navegacao_analytics import grupos_sidebar_analytics
        grupos = grupos_sidebar_analytics({"analytics_secao": lambda _destino: None})
        self.assertEqual([grupo[0] for grupo in grupos], ["INTELIGÊNCIA", "LABORATÓRIO", "ADMINISTRAÇÃO"])
        self.assertEqual(grupos[-1][1][-1][2], "Regras analíticas")

    def test_build_servidor_inclui_engines_dos_relatorios(self):
        spec = Path("DataIntelligenceServer.spec").read_text(encoding="utf-8")
        for pacote in ("pandas", "openpyxl", "reportlab"):
            self.assertIn(f'collect_submodules("{pacote}")', spec)


if __name__ == "__main__":
    unittest.main()
