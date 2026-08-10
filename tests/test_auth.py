from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import (
    autenticar_usuario,
    criar_admin_inicial,
    criar_usuario,
    definir_status_usuario,
)
from auth.seguranca import gerar_hash_senha, verificar_senha


class AuthTests(unittest.TestCase):
    def test_hash_senha(self):
        senha_hash, salt = gerar_hash_senha("SenhaForte#123")
        self.assertTrue(verificar_senha("SenhaForte#123", senha_hash, salt))
        self.assertFalse(verificar_senha("SenhaErrada#123", senha_hash, salt))

    def test_senha_fraca_e_rejeitada(self):
        for senha in ("123", "somenteletras", "SEM-MINUSCULA1", "SemSimbolo123"):
            with self.subTest(senha=senha), self.assertRaises(ValueError):
                gerar_hash_senha(senha)

    def test_fluxo_autorizado_e_protecao_do_administrador(self):
        with tempfile.TemporaryDirectory() as pasta:
            db_path = Path(pasta) / "teste.db"
            with patch.object(banco, "DB_PATH", db_path), patch.object(
                banco, "STORAGE_DIR", Path(pasta)
            ):
                banco.inicializar_banco()
                admin = criar_admin_inicial(
                    "Administrador", "admin", "SenhaAdmin#123"
                )
                funcionario = criar_usuario(
                    "Funcionário",
                    "funcionario",
                    "SenhaUsuario#123",
                    ator=admin,
                )
                autenticado = autenticar_usuario("funcionario", "SenhaUsuario#123")
                self.assertEqual(autenticado["id"], funcionario["id"])

                definir_status_usuario(funcionario["id"], False, ator=admin)
                with self.assertRaises(PermissionError):
                    autenticar_usuario("funcionario", "SenhaUsuario#123")
                with self.assertRaises(ValueError):
                    definir_status_usuario(admin["id"], False, ator=admin)

    def test_cinco_falhas_bloqueiam_temporariamente(self):
        with tempfile.TemporaryDirectory() as pasta:
            db_path = Path(pasta) / "teste.db"
            with patch.object(banco, "DB_PATH", db_path), patch.object(
                banco, "STORAGE_DIR", Path(pasta)
            ):
                banco.inicializar_banco()
                criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
                for _ in range(4):
                    with self.assertRaises(ValueError):
                        autenticar_usuario("admin", "SenhaErrada#123")
                with self.assertRaises(PermissionError):
                    autenticar_usuario("admin", "SenhaErrada#123")
                with self.assertRaises(PermissionError):
                    autenticar_usuario("admin", "SenhaAdmin#123")


if __name__ == "__main__":
    unittest.main()
