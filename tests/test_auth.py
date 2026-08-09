from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import autenticar_usuario, criar_usuario, definir_status_usuario
from auth.seguranca import gerar_hash_senha, verificar_senha


class AuthTests(unittest.TestCase):
    def test_hash_senha(self):
        senha_hash, salt = gerar_hash_senha("senha-forte")
        self.assertTrue(verificar_senha("senha-forte", senha_hash, salt))
        self.assertFalse(verificar_senha("senha-errada", senha_hash, salt))

    def test_senha_curta_e_rejeitada(self):
        with self.assertRaises(ValueError):
            gerar_hash_senha("123")

    def test_fluxo_usuario_em_banco_temporario(self):
        with tempfile.TemporaryDirectory() as pasta:
            db_path = Path(pasta) / "teste.db"
            with patch.object(banco, "DB_PATH", db_path), patch.object(
                banco, "STORAGE_DIR", Path(pasta)
            ):
                banco.inicializar_banco()
                usuario = criar_usuario("Teste", "teste", "senha-123", "admin")
                autenticado = autenticar_usuario("teste", "senha-123")
                self.assertEqual(autenticado["id"], usuario["id"])
                definir_status_usuario(usuario["id"], False)
                with self.assertRaises(PermissionError):
                    autenticar_usuario("teste", "senha-123")


if __name__ == "__main__":
    unittest.main()
