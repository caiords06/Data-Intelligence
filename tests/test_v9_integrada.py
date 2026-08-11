"""Regressões dos contratos transversais introduzidos na V9."""

from pathlib import Path
import json
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from agente_ti.transport import assinatura_requisicao
from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario, redefinir_senha
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.comunicacao import enviar_mensagem, listar_mensagens, obter_mensagem
from enterprise.contexto import obter_contexto
from enterprise.nos_plataforma import cadastrar_no
from enterprise.organizacao import criar_filial, definir_contexto_empresa
from enterprise.rh import abrir_folha, fechar_folha
from servidor.seguranca import autenticar_agente
from servidor.api import executar_servidor


class PlataformaV9IntegradaTests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
        patch_db.start(); patch_storage.start()
        self.addCleanup(patch_db.stop); self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        contexto = obter_contexto()
        return admin, contexto

    def test_alteracao_de_credencial_revoga_sessao_corrente(self):
        admin, _ = self._ambiente()
        redefinir_senha(admin["id"], "NovaSenhaAdmin#456", ator=admin)
        self.assertFalse(SESSAO.validar())
        self.assertIsNone(SESSAO.usuario)

    def test_folha_de_outra_filial_nao_pode_ser_fechada(self):
        admin, contexto = self._ambiente()
        filial_a = int(contexto["filial_id"])
        filial_b = criar_filial("Filial B", "FB", ator=admin)
        definir_contexto_empresa(int(contexto["empresa_id"]), filial_b)
        folha_b = abrir_folha("2026-08", admin)
        definir_contexto_empresa(int(contexto["empresa_id"]), filial_a)
        with self.assertRaisesRegex(ValueError, "contexto atual|aberta"):
            fechar_folha(folha_b, admin)

    def test_correio_isola_empresa_e_marca_leitura(self):
        admin, contexto = self._ambiente()
        destinatario = criar_usuario(
            "Analista Financeiro", "financeiro", "SenhaUsuario#123",
            ator=admin, perfil_acesso="financeiro_analista",
            email_corporativo="financeiro@empresa.local",
        )
        mensagem_id = enviar_mensagem(
            {
                "para": ["financeiro@empresa.local"],
                "assunto": "Fechamento mensal",
                "corpo": "Revise o fechamento antes da reunião.",
            },
            admin,
        )
        ator_destino = {
            **destinatario,
            "_empresa_id": int(contexto["empresa_id"]),
            "_filial_id": int(contexto["filial_id"]),
        }
        entrada = listar_mensagens(ator_destino)
        self.assertEqual([item["id"] for item in entrada], [mensagem_id])
        self.assertEqual(entrada[0]["lida"], 0)
        obter_mensagem(mensagem_id, ator_destino)
        self.assertEqual(listar_mensagens(ator_destino)[0]["lida"], 1)

    def test_hmac_do_agente_rejeita_replay(self):
        admin, _ = self._ambiente()
        credencial = cadastrar_no(
            {"nome": "PC-FIN-001", "tipo": "Agente", "sistema": "Windows"},
            admin,
        )
        corpo = b'{"agent_id":"teste","hostname":"PC-FIN-001"}'
        timestamp = str(int(time.time()))
        nonce = "nonce-v9-integrado-0001"
        assinatura = assinatura_requisicao(
            credencial["token"], corpo, timestamp, nonce
        )
        autenticado = autenticar_agente(
            credencial["identificador"], timestamp, nonce, assinatura, corpo
        )
        self.assertEqual(autenticado["id"], credencial["id"])
        with self.assertRaisesRegex(PermissionError, "utilizada"):
            autenticar_agente(
                credencial["identificador"], timestamp, nonce, assinatura, corpo
            )

    def test_servidor_publica_health_sem_expor_dados(self):
        self._ambiente()
        servidor = executar_servidor("127.0.0.1", 0)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        try:
            porta = int(servidor.server_address[1])
            with urlopen(f"http://127.0.0.1:{porta}/health", timeout=3) as resposta:
                corpo = json.loads(resposta.read().decode("utf-8"))
                self.assertEqual(resposta.status, 200)
                self.assertEqual(corpo["status"], "operacional")
                self.assertNotIn("storage", corpo)
        finally:
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=3)

    def test_valor_em_centavos_e_a_unica_fonte_monetaria(self):
        admin, contexto = self._ambiente()
        with banco.conectar() as conexao:
            identificador = int(conexao.execute(
                """
                INSERT INTO aprovacoes (
                    empresa_id,filial_id,solicitante_id,modulo,recurso_tipo,
                    recurso_id,titulo,valor,valor_centavos
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    contexto["empresa_id"], contexto["filial_id"], admin["id"],
                    "financeiro", "teste", 1, "Teste monetário", 999.99, 12345,
                ),
            ).lastrowid)
        with banco.conectar() as conexao:
            registro = conexao.execute(
                "SELECT valor,valor_centavos FROM aprovacoes WHERE id=?",
                (identificador,),
            ).fetchone()
        self.assertEqual(registro["valor_centavos"], 12345)
        self.assertAlmostEqual(registro["valor"], 123.45, places=2)


if __name__ == "__main__":
    unittest.main()
