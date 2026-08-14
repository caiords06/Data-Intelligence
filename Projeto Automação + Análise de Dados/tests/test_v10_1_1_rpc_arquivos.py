"""Transporte de arquivos Central/Cliente <-> Servidor Corporativo."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class RPCArquivosTests(unittest.TestCase):
    def test_upload_marca_caminho_e_envia_bytes_ao_servidor(self):
        from enterprise import servidor_cliente
        from core.rpc_central import desserializar

        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "extrato.csv"
            arquivo.write_text("data,valor\n2026-08-01,10\n", encoding="utf-8")
            capturado = {}

            def fake_upload(p, endpoint, *, headers, timeout):
                capturado.update(path=p, endpoint=endpoint, headers=headers, timeout=timeout)
                return {"resultado": 17}

            with patch.object(servidor_cliente, "_upload_streaming", side_effect=fake_upload):
                resultado = servidor_cliente.executar_operacao_arquivo_remota(
                    "enterprise.financeiro",
                    "importar_extrato",
                    args=(3, str(arquivo), {"id": 9}),
                )

            self.assertEqual(resultado, 17)
            self.assertEqual(capturado["endpoint"], "/api/v1/rpc/file-upload")
            self.assertEqual(capturado["path"], arquivo.resolve())
            meta = json.loads(base64.urlsafe_b64decode(capturado["headers"]["X-RPC-Meta"]).decode("utf-8"))
            meta = desserializar(meta)
            self.assertEqual(meta["args"][0], 3)
            self.assertEqual(meta["args"][1], {"__di_rpc_input_file__": True})
            self.assertEqual(meta["args"][2]["id"], 9)

    def test_relatorio_com_destino_volta_para_caminho_escolhido(self):
        from enterprise import servidor_cliente

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "rh_colaboradores.csv"
            with patch.object(
                servidor_cliente,
                "_request_resultado_arquivo",
                return_value=(b"a,b\n1,2\n", "servidor.csv", "/storage/servidor.csv"),
            ) as requisitar:
                resultado = servidor_cliente.executar_operacao_arquivo_remota(
                    "enterprise.rh",
                    "gerar_relatorio_rh",
                    args=("Colaboradores", "CSV", str(destino), {"id": 2}),
                )
            self.assertEqual(Path(resultado), destino.resolve())
            self.assertEqual(destino.read_bytes(), b"a,b\n1,2\n")
            payload = requisitar.call_args.args[0]
            self.assertEqual(payload["nome_destino"], destino.name)
            self.assertEqual(payload["args"][2], {"__di_rpc_output_file__": True})

    def test_wrapper_bloqueado_agora_usa_transporte_especializado(self):
        import enterprise.financeiro as financeiro

        with patch.dict(os.environ, {
            "DATA_INTELLIGENCE_NODE_ROLE": "central",
            "DATA_INTELLIGENCE_SERVER_URL": "http://127.0.0.1:8770",
        }, clear=False), patch(
            "enterprise.servidor_cliente.executar_operacao_arquivo_remota",
            return_value=91,
        ) as remoto:
            resultado = financeiro.anexar_documento(10, "C:/arquivo.pdf", {"id": 4})
        self.assertEqual(resultado, 91)
        remoto.assert_called_once()
        self.assertEqual(remoto.call_args.args[0:2], ("enterprise.financeiro", "anexar_documento"))

    def test_verificar_documento_ferramenta_e_rpc_comum(self):
        import enterprise.ferramentas as ferramentas

        with patch.dict(os.environ, {
            "DATA_INTELLIGENCE_NODE_ROLE": "central",
            "DATA_INTELLIGENCE_SERVER_URL": "http://127.0.0.1:8770",
        }, clear=False), patch(
            "enterprise.servidor_cliente.executar_rpc_remoto",
            return_value={"existe": True, "integro": True, "caminho": "/servidor/doc.pdf"},
        ) as remoto:
            resultado = ferramentas.verificar_documento(5, {"id": 4})
        self.assertTrue(resultado["integro"])
        remoto.assert_called_once()

    def test_dataset_para_nova_analise_baixa_copia_transitoria(self):
        from enterprise import servidor_cliente

        esperado = {"id": 7, "nome": "Base", "caminho": "C:/Temp/base.xlsx"}
        with patch.object(servidor_cliente, "executar_operacao_arquivo_remota", return_value=esperado) as remoto:
            resultado = servidor_cliente.baixar_conjunto_remoto(7, {"id": 2})
        self.assertEqual(resultado, esperado)
        remoto.assert_called_once()
        self.assertEqual(remoto.call_args.args[:2], ("enterprise.datasets", "obter_conjunto"))

    def test_toda_operacao_bloqueada_do_rpc_generico_tem_transporte_de_arquivo(self):
        from core.rpc_arquivos import (
            RPC_ARQUIVO_ENTRADA, RPC_ARQUIVO_SAIDA_PARAM,
            RPC_ARQUIVO_RETORNO, RPC_ARQUIVO_PERSISTE_SERVIDOR,
        )
        from core.rpc_central import RPC_BLOQUEADAS_REMOTO

        bloqueadas = {
            (modulo, funcao)
            for modulo, funcoes in RPC_BLOQUEADAS_REMOTO.items()
            for funcao in funcoes
        }
        especializadas = (
            set(RPC_ARQUIVO_ENTRADA)
            | set(RPC_ARQUIVO_SAIDA_PARAM)
            | set(RPC_ARQUIVO_RETORNO)
            | set(RPC_ARQUIVO_PERSISTE_SERVIDOR)
        )
        self.assertFalse(bloqueadas - especializadas)

    def test_backup_remoto_nao_exige_pasta_da_estacao(self):
        from enterprise import backups

        with patch.dict(os.environ, {
            "DATA_INTELLIGENCE_NODE_ROLE": "central",
            "DATA_INTELLIGENCE_SERVER_URL": "http://127.0.0.1:8770",
        }, clear=False), patch(
            "enterprise.servidor_cliente.criar_backup_servidor",
            return_value={"id": 8, "status": "Válido", "tamanho_bytes": 1024},
        ) as remoto:
            resultado = backups.criar_backup({"id": 1, "perfil": "admin"})
        self.assertEqual(resultado["id"], 8)
        remoto.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
