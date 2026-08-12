"""Regressões para problemas encontrados na auditoria de estabilização."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from core.nodo import ConfigNodo, carregar_config_nodo
from enterprise.banco import inicializar_enterprise
from enterprise.migrations import MIGRACOES
from interface.captura_visual import salvar_manifesto
from servidor_corporativo.app import CorporateRequestHandler, CorporateServer, _filtro_empresa_filial
from servidor_corporativo.config import ConfigServidor, carregar_config
from servidor_corporativo import sessoes as sessoes_servidor
from scripts.empacotar_fonte_limpa import RAIZ as RAIZ_PACOTE, permitido


class AuditoriaRegressoesTests(unittest.TestCase):
    def test_registry_de_migrations_cobre_todos_os_arquivos_sem_numeros_duplicados(self):
        pasta = Path(__file__).resolve().parents[1] / "enterprise" / "migrations"
        arquivos = tuple(
            p.stem for p in sorted(pasta.glob("[0-9][0-9][0-9]_*.py"))
        )
        self.assertEqual(arquivos, MIGRACOES)
        numeros = [re.match(r"^(\d{3})_", nome).group(1) for nome in arquivos]
        self.assertEqual(len(numeros), len(set(numeros)))

    def test_banco_novo_cria_tabelas_de_compatibilidade_e_schema_canonico_de_arquivos(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            with (
                patch.object(banco, "DB_PATH", pasta / "app.db"),
                patch.object(banco, "STORAGE_DIR", pasta / "storage"),
            ):
                banco.inicializar_banco()
                inicializar_enterprise()
                with banco.conectar() as con:
                    tabelas = {
                        row["name"]
                        for row in con.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    }
                    colunas = {
                        row["name"]
                        for row in con.execute(
                            "PRAGMA table_info(arquivos_corporativos)"
                        ).fetchall()
                    }
                    mig = con.execute(
                        "SELECT 1 FROM migracoes_sistema WHERE chave='enterprise_019_compatibilidade_v9_legada'"
                    ).fetchone()
                self.assertTrue({"nos_plataforma", "mensagens", "tokens_api", "nonces_agente"} <= tabelas)
                self.assertTrue(
                    {
                        "id", "empresa_id", "filial_id", "modulo", "categoria", "nome",
                        "caminho_relativo", "tamanho_bytes", "sha256", "origem",
                        "criado_por", "criado_em", "excluido_em",
                    } <= colunas
                )
                self.assertIsNotNone(mig)

    def test_producao_wildcard_sem_tls_e_rejeitada(self):
        with self.assertRaisesRegex(ValueError, "produção.*TLS|produção.*tls|produção"):
            ConfigServidor(host="0.0.0.0", porta=8770, tls=False, ambiente="producao").validar()

    def test_configuracao_existente_invalida_falha_fechado(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / "server.json").write_text(
                json.dumps({
                    "host": "0.0.0.0",
                    "porta": 8770,
                    "tls": False,
                    "ambiente": "producao",
                }),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"DATA_INTELLIGENCE_SERVER_DATA_DIR": str(pasta)}):
                with self.assertRaisesRegex(ValueError, "Configuração do servidor rejeitada"):
                    carregar_config()

    def test_escopo_corporativo_enxerga_empresa_e_escopo_filial_inclui_corporativos(self):
        class SessaoFake:
            empresa_id = 12
            filial_id = None

        filtro, params = _filtro_empresa_filial(SessaoFake())
        self.assertEqual(filtro, "empresa_id=?")
        self.assertEqual(params, (12,))

        SessaoFake.filial_id = 4
        filtro, params = _filtro_empresa_filial(SessaoFake())
        self.assertIn("filial_id=?", filtro)
        self.assertIn("filial_id IS NULL", filtro)
        self.assertEqual(params, (12, 4))


    def test_config_nodo_rejeita_http_publico_e_falha_fechado(self):
        with self.assertRaisesRegex(ValueError, "HTTP sem TLS"):
            ConfigNodo(
                papel="cliente", servidor_url="http://8.8.8.8:8770",
                permitir_http_privado=True,
            ).validar()
        valido = ConfigNodo(
            papel="cliente", servidor_url="http://192.168.10.20:8770",
            permitir_http_privado=True,
        ).validar()
        self.assertEqual(valido.papel, "cliente")

        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "node.json"
            arquivo.write_text('{"papel":"cliente","servidor_url":"http://example.com:8770"}', encoding="utf-8")
            with patch.dict(os.environ, {"DATA_INTELLIGENCE_NODE_CONFIG": str(arquivo)}, clear=False):
                with self.assertRaisesRegex(ValueError, "Configuração do nó rejeitada"):
                    carregar_config_nodo()

    def test_empacotador_fonte_exclui_dados_e_preserva_codigo_necessario(self):
        self.assertFalse(permitido(RAIZ_PACOTE / "storage" / "app.db"))
        self.assertFalse(permitido(RAIZ_PACOTE / ".git" / "config"))
        self.assertFalse(permitido(RAIZ_PACOTE / "build" / "app.exe"))
        self.assertFalse(permitido(RAIZ_PACOTE / "dados_exemplo" / "Vendas - Dez - Copia.xlsx"))
        self.assertTrue(permitido(RAIZ_PACOTE / "historico" / "repositorio.py"))
        self.assertTrue(permitido(RAIZ_PACOTE / "dados_exemplo" / "Vendas - Dez.xlsx"))
        self.assertTrue(permitido(RAIZ_PACOTE / ".github" / "workflows" / "quality.yml"))


    def test_api_de_arquivos_bloqueia_usuario_nao_admin_no_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            with (
                patch.object(banco, "DB_PATH", pasta / "app.db"),
                patch.object(banco, "STORAGE_DIR", pasta / "storage"),
            ):
                banco.inicializar_banco()
                admin = criar_admin_inicial(
                    "Administrador", "admin", "SenhaAdmin#123",
                    email_corporativo="admin@empresa.local",
                )
                SESSAO.iniciar(admin)
                inicializar_enterprise()
                criar_usuario(
                    "Analista", "analista", "SenhaAnalista#123",
                    perfil_acesso="analista", ator=admin,
                    email_corporativo="analista@empresa.local",
                )
                cfg = ConfigServidor(host="127.0.0.1", porta=8770, tls=False, max_upload_mb=20)
                srv = CorporateServer(("127.0.0.1", 0), CorporateRequestHandler, cfg)
                thread = threading.Thread(target=srv.serve_forever, daemon=True)
                thread.start()
                try:
                    base = f"http://127.0.0.1:{srv.server_address[1]}"
                    corpo = json.dumps({"usuario": "analista", "senha": "SenhaAnalista#123"}).encode()
                    req = urllib.request.Request(
                        base + "/api/v1/auth/login", data=corpo, method="POST",
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=5) as resposta:
                        token = json.loads(resposta.read())["token"]
                    req = urllib.request.Request(
                        base + "/api/v1/files",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    with self.assertRaises(urllib.error.HTTPError) as erro:
                        urllib.request.urlopen(req, timeout=5)
                    self.assertEqual(erro.exception.code, 403)
                finally:
                    srv.shutdown(); srv.server_close()
                    sessoes_servidor._SESSOES.clear()
                    SESSAO.encerrar()

    def test_manifesto_visual_nao_vaza_caminho_absoluto(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            png = pasta / "001_tela.png"
            png.write_bytes(b"png-ficticio")
            manifesto = pasta / "MANIFESTO_VISUAL.json"
            salvar_manifesto(
                [{"tela": "Tela", "caminho": str(png), "status": "aprovada"}],
                manifesto,
            )
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            self.assertEqual(dados[0]["caminho"], "001_tela.png")
            self.assertNotIn(str(pasta.resolve()), manifesto.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
