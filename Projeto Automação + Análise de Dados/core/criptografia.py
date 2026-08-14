"""Criptografia autenticada para segredos e artefatos locais do servidor.

O conteúdo é protegido com AES-256-GCM. No Windows, a chave mestra é
armazenada por DPAPI no escopo da máquina. Em Linux/containers a chave deve vir
de um secret manager pela variável de ambiente indicada pelo chamador.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.segredos import carregar_segredo_maquina, salvar_segredo_maquina

_MAGIC = b"DIENC1\x00"


def _decodificar_chave(valor: str) -> bytes:
    texto = str(valor or "").strip()
    if not texto:
        raise ValueError("Chave mestra vazia.")
    try:
        chave = base64.urlsafe_b64decode(texto + "=" * ((4 - len(texto) % 4) % 4))
    except (ValueError, TypeError) as exc:
        raise ValueError("Chave mestra deve estar em Base64 URL-safe.") from exc
    if len(chave) != 32:
        raise ValueError("A chave mestra deve possuir exatamente 32 bytes.")
    return chave


def gerar_chave_base64() -> str:
    """Gera uma chave AES-256 adequada para um secret manager."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def obter_chave_mestra(
    *,
    variavel_ambiente: str,
    caminho_dpapi: str | Path,
    descricao: str,
) -> bytes:
    """Obté a chave sem permitir fallback para texto puro em disco."""
    ambiente = str(os.environ.get(variavel_ambiente, "")).strip()
    if ambiente:
        return _decodificar_chave(ambiente)

    caminho = Path(caminho_dpapi).expanduser().resolve()
    if os.name != "nt":
        raise FileNotFoundError(
            f"Defina {variavel_ambiente} com uma chave Base64 de 32 bytes; "
            "fora do Windows a plataforma não persiste chaves mestras locais."
        )
    if not caminho.is_file():
        salvar_segredo_maquina(
            gerar_chave_base64(), caminho, descricao=descricao,
        )
    return _decodificar_chave(
        carregar_segredo_maquina(caminho, variavel_ambiente=variavel_ambiente)
    )


def criptografar_bytes(dados: bytes, chave: bytes, *, contexto: bytes = b"") -> bytes:
    if len(chave) != 32:
        raise ValueError("AES-256-GCM exige uma chave de 32 bytes.")
    nonce = secrets.token_bytes(12)
    return _MAGIC + nonce + AESGCM(chave).encrypt(nonce, bytes(dados), contexto)


def descriptografar_bytes(pacote: bytes, chave: bytes, *, contexto: bytes = b"") -> bytes:
    bruto = bytes(pacote)
    if not bruto.startswith(_MAGIC) or len(bruto) < len(_MAGIC) + 12 + 16:
        raise ValueError("Artefato criptografado inválido ou incompatível.")
    inicio = len(_MAGIC)
    nonce = bruto[inicio:inicio + 12]
    return AESGCM(chave).decrypt(nonce, bruto[inicio + 12:], contexto)


def salvar_criptografado(
    caminho: str | Path,
    dados: bytes,
    chave: bytes,
    *,
    contexto: bytes = b"",
) -> Path:
    destino = Path(caminho).expanduser().resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    temporario.write_bytes(criptografar_bytes(dados, chave, contexto=contexto))
    os.replace(temporario, destino)
    try:
        os.chmod(destino, 0o600)
    except OSError:
        # ACL/DPAPI é a proteção efetiva no Windows; chmod pode não existir.
        pass
    return destino


def carregar_criptografado(
    caminho: str | Path,
    chave: bytes,
    *,
    contexto: bytes = b"",
) -> bytes:
    return descriptografar_bytes(
        Path(caminho).expanduser().resolve().read_bytes(), chave, contexto=contexto,
    )


__all__ = (
    "carregar_criptografado", "criptografar_bytes", "descriptografar_bytes",
    "gerar_chave_base64", "obter_chave_mestra", "salvar_criptografado",
)
