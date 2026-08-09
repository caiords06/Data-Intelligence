"""Funções de hash e verificação de senha usando scrypt."""

import hashlib
import hmac
import os

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def gerar_hash_senha(senha: str) -> tuple[str, str]:
    if not isinstance(senha, str) or len(senha) < 8:
        raise ValueError("A senha deve possuir pelo menos 8 caracteres.")

    salt = os.urandom(16)
    senha_hash = hashlib.scrypt(
        senha.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    return senha_hash.hex(), salt.hex()


def verificar_senha(senha: str, senha_hash: str, salt: str) -> bool:
    try:
        hash_calculado = hashlib.scrypt(
            senha.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
        )
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(hash_calculado.hex(), senha_hash)
