"""Regressões das garantias introduzidas no hardening de produção."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from auth import banco
from auth.autenticacao import autenticar_usuario, criar_admin_inicial
from auth.banco import ConcorrenciaConflito, alterar_status_usuario, inicializar_banco
from auth.mfa import _codigo, confirmar_mfa, preparar_mfa
from enterprise import inicializar_enterprise
from enterprise.automacao_motor import (
    aprovar, enfileirar, executar_um, listar as listar_automacoes, registrar_handler,
)
from enterprise.backups import criar_backup, verificar_backup
from enterprise.organizacao import criar_empresa
from enterprise.privacidade import (
    _excluir_arquivos_retidos,
    definir_politica_retencao, listar_leituras_sensiveis, mascarar_cpf,
    registrar_leitura_sensivel,
)
from servidor_corporativo.config import ConfigServidor
from servidor_corporativo.controles_api import RateLimitExcedido, executar_idempotente, verificar_limite
from servidor_corporativo import sessoes


CHAVE_TESTE = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


class HardeningProducaoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.ambiente = patch.dict(os.environ, {
            "DATA_INTELLIGENCE_DB_BACKEND": "sqlite",
            "DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE": "1",
            "DATA_INTELLIGENCE_NODE_ROLE": "servidor",
            "DATA_INTELLIGENCE_MFA_MASTER_KEY": CHAVE_TESTE,
            "DATA_INTELLIGENCE_BACKUP_MASTER_KEY": CHAVE_TESTE,
            "DATA_INTELLIGENCE_WEBHOOK_MASTER_KEY": CHAVE_TESTE,
        })
        self.ambiente.start()
        self.patch_storage = patch.object(banco, "STORAGE_DIR", self.raiz)
        self.patch_db = patch.object(banco, "DB_PATH", self.raiz / "app.db")
        self.patch_storage.start(); self.patch_db.start()
        inicializar_banco(); inicializar_enterprise()
        self.admin = criar_admin_inicial("Administrador", "admin", "SenhaForte#2026", "admin@example.com")
        self.empresa_id = criar_empresa("Empresa Teste", "00000000000000", ator=self.admin)
        self.ator = {**self.admin, "_empresa_id": self.empresa_id, "_filial_id": None}

    def tearDown(self):
        sessoes._SESSOES.clear()
        self.patch_db.stop(); self.patch_storage.stop(); self.ambiente.stop(); self.tmp.cleanup()

    def test_migration_criou_controles(self):
        esperadas = {
            "mfa_codigos_recuperacao", "sessoes_servidor", "api_rate_limits",
            "api_idempotencia", "automacao_fila", "automacao_agendamentos",
            "auditoria_leituras_sensiveis", "politicas_retencao", "webhook_endpoints",
        }
        with banco.conectar() as con:
            existentes = {x["name"] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        self.assertTrue(esperadas.issubset(existentes))

    def test_mfa_obrigatorio_cifrado_e_recuperacao_uso_unico(self):
        setup = preparar_mfa(self.admin["id"], self.admin)
        confirmacao = confirmar_mfa(self.admin["id"], _codigo(setup["secret"], int(time.time())), self.admin)
        segredo_arquivo = next(self.raiz.glob("segredos_mfa/*.enc"))
        self.assertNotIn(setup["secret"].encode("ascii"), segredo_arquivo.read_bytes())
        with self.assertRaises(PermissionError):
            autenticar_usuario("admin", "SenhaForte#2026")
        recuperacao = confirmacao["codigos_recuperacao"][0]
        usuario = autenticar_usuario("admin", "SenhaForte#2026", recuperacao)
        self.assertTrue(usuario["mfa_habilitado"])
        with self.assertRaises(PermissionError):
            autenticar_usuario("admin", "SenhaForte#2026", recuperacao)

    def test_sessao_persiste_sem_token_em_claro_e_pode_ser_revogada(self):
        usuario = autenticar_usuario("admin", "SenhaForte#2026")
        sessao = sessoes.criar(usuario, self.empresa_id, None, cliente="unittest")
        with banco.conectar() as con:
            row = con.execute("SELECT token_hash FROM sessoes_servidor").fetchone()
        self.assertNotEqual(row["token_hash"], sessao.token)
        sessoes._SESSOES.clear()
        self.assertIsNotNone(sessoes.obter(sessao.token))
        sessoes.revogar(sessao.token)
        self.assertIsNone(sessoes.obter(sessao.token))

    def test_fila_aprovacao_idempotencia_dead_letter_e_rate_limit(self):
        nome_ok = "teste.ok." + uuid4().hex
        @registrar_handler(nome_ok)
        def ok(payload, ator, cancelar):
            return {"valor": payload["valor"]}
        job = enfileirar(
            nome_ok, "Ação sensível", {"valor": 7}, self.ator,
            idempotency_key="hardening-job-0001", requer_aprovacao=True,
        )
        self.assertFalse(executar_um())
        aprovar(job["id"], self.ator); self.assertTrue(executar_um())
        repetido = enfileirar(nome_ok, "Repetido", {"valor": 99}, self.ator, idempotency_key="hardening-job-0001")
        self.assertEqual(repetido["id"], job["id"])
        self.assertEqual(listar_automacoes(self.ator)[0]["status"], "Concluído")

        nome_erro = "teste.erro." + uuid4().hex
        @registrar_handler(nome_erro)
        def falhar(payload, ator, cancelar):
            raise RuntimeError("falha controlada")
        morto = enfileirar(nome_erro, "Falha", {}, self.ator, max_tentativas=1)
        self.assertTrue(executar_um())
        estados = {x["id"]: x["status"] for x in listar_automacoes(self.ator)}
        self.assertEqual(estados[morto["id"]], "Dead-letter")

        primeira = executar_idempotente(
            usuario_id=self.admin["id"], metodo="POST", caminho="/teste",
            chave="idem-chave-0001", dados={"a": 1}, executar=lambda: (201, {"ok": True}),
        )
        segunda = executar_idempotente(
            usuario_id=self.admin["id"], metodo="POST", caminho="/teste",
            chave="idem-chave-0001", dados={"a": 1}, executar=lambda: (500, {}),
        )
        self.assertFalse(primeira[2]); self.assertTrue(segunda[2]); self.assertEqual(segunda[0], 201)
        verificar_limite("teste", limite=1, janela_segundos=60)
        with self.assertRaises(RateLimitExcedido):
            verificar_limite("teste", limite=1, janela_segundos=60)

    def test_backup_cifrado_privacidade_e_concorrencia(self):
        backup = criar_backup(
            self.ator, self.raiz / "backups", sincronizar_servidor=False, criptografar=True,
        )
        arquivo = Path(backup["arquivo"])
        self.assertEqual(arquivo.suffix, ".dibak")
        self.assertTrue(verificar_backup(arquivo)["integro"])
        self.assertEqual(mascarar_cpf("12345678901"), "***.***.789-**")
        registrar_leitura_sensivel(
            ator=self.ator, modulo="RH", entidade="colaborador", entidade_id=1,
            campos=["cpf", "salario_centavos"], finalidade="Teste",
        )
        self.assertEqual(len(listar_leituras_sensiveis(self.ator)), 1)
        self.assertGreater(definir_politica_retencao("RH", "colaborador", 365, self.ator), 0)
        anexo = self.raiz / "rh" / "documentos" / "anexo.pdf"
        anexo.parent.mkdir(parents=True)
        anexo.write_bytes(b"documento pessoal")
        pendentes = _excluir_arquivos_retidos(["rh/documentos/anexo.pdf", "../fora-do-storage.pdf"])
        self.assertFalse(anexo.exists())
        self.assertEqual(pendentes, ["../fora-do-storage.pdf"])
        alterar_status_usuario(self.admin["id"], True, expected_epoch=0)
        with self.assertRaises(ConcorrenciaConflito):
            alterar_status_usuario(self.admin["id"], True, expected_epoch=0)

    def test_tls_producao_e_manifesto_ed25519(self):
        with self.assertRaises(ValueError):
            ConfigServidor(
                host="192.168.1.10", ambiente="producao", tls=False,
                postgres_segredo="env:DATA_INTELLIGENCE_PG_PASSWORD",
            ).validar()
        privada = Ed25519PrivateKey.generate()
        publica = privada.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        with patch.dict(os.environ, {"DATA_INTELLIGENCE_UPDATE_PUBLIC_KEY": base64.b64encode(publica).decode("ascii")}):
            payload = {
                "versao": "10.5.1", "url": "https://updates.example.com/pacote.zip",
                "sha256": "a" * 64, "tamanho_bytes": 1024,
            }
            canonico = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
            payload["assinatura"] = base64.b64encode(privada.sign(canonico)).decode("ascii")
            with patch("core.atualizacoes.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
                from core.atualizacoes import AtualizacaoInvalida, preparar_atualizacao, validar_manifesto
                self.assertEqual(validar_manifesto(payload)["versao"], "10.5.1")
                antigo = {**payload, "versao": "10.4.9"}
                sem_assinatura = {k: antigo[k] for k in antigo if k != "assinatura"}
                canonico_antigo = json.dumps(
                    sem_assinatura, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
                ).encode("utf-8")
                antigo["assinatura"] = base64.b64encode(privada.sign(canonico_antigo)).decode("ascii")
                with patch("core.atualizacoes._baixar_json", return_value=antigo):
                    with self.assertRaises(AtualizacaoInvalida):
                        preparar_atualizacao("https://updates.example.com/manifest.json")


if __name__ == "__main__":
    unittest.main()
