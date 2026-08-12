"""Política de senha, hash scrypt e comparação resistente a timing attacks."""

import hashlib
import hmac
import os

_SCRYPT_N = 2**14  # Mantido para compatibilidade com hashes das versões anteriores.
_SCRYPT_R = 8
_SCRYPT_P = 1
_SENHAS_COMUNS = {
    "1234567890",
    "administrador",
    "admin12345",
    "password123",
    "senha12345",
}


def validar_forca_senha(senha: str) -> None:
    if not isinstance(senha, str) or len(senha) < 10:
        raise ValueError("A senha deve possuir pelo menos 10 caracteres.")
    if senha.casefold() in _SENHAS_COMUNS:
        raise ValueError("Escolha uma senha menos previsível.")
    if not any(caractere.islower() for caractere in senha):
        raise ValueError("A senha deve possuir ao menos uma letra minúscula.")
    if not any(caractere.isupper() for caractere in senha):
        raise ValueError("A senha deve possuir ao menos uma letra maiúscula.")
    if not any(caractere.isdigit() for caractere in senha):
        raise ValueError("A senha deve possuir ao menos um número.")
    if not any(not caractere.isalnum() for caractere in senha):
        raise ValueError("A senha deve possuir ao menos um símbolo.")


def gerar_hash_senha(senha: str) -> tuple[str, str]:
    validar_forca_senha(senha)
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
    except (AttributeError, MemoryError, TypeError, ValueError):
        return False
    return hmac.compare_digest(hash_calculado.hex(), senha_hash)
