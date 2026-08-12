"""Proteção do token do agente com Windows DPAPI."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import os
from pathlib import Path

from agente_ti.config import caminho_segredo_padrao


VARIAVEL_TOKEN = "DATA_TI_AGENT_TOKEN"
CRYPTPROTECT_LOCAL_MACHINE = 0x4


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _blob(dados: bytes):
    buffer = ctypes.create_string_buffer(dados)
    estrutura = _DataBlob(
        len(dados),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    return estrutura, buffer


def _proteger_windows(segredo: bytes) -> bytes:
    entrada, buffer = _blob(segredo)
    saida = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(entrada),
        "Data Intelligence TI Agent",
        None,
        None,
        None,
        CRYPTPROTECT_LOCAL_MACHINE,
        ctypes.byref(saida),
    )
    del buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        kernel32.LocalFree(saida.pbData)


def _desproteger_windows(protegido: bytes) -> bytes:
    entrada, buffer = _blob(protegido)
    saida = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(saida)
    )
    del buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        kernel32.LocalFree(saida.pbData)


def salvar_token(token: str, caminho: str | Path | None = None) -> Path:
    texto = str(token or "").strip()
    if len(texto) < 24:
        raise ValueError("O token do agente precisa possuir pelo menos 24 caracteres.")
    if os.name != "nt":
        raise OSError(
            "O armazenamento persistente do token está disponível apenas no Windows. "
            f"Use temporariamente a variável {VARIAVEL_TOKEN}."
        )
    destino = Path(caminho) if caminho else caminho_segredo_padrao()
    destino.parent.mkdir(parents=True, exist_ok=True)
    protegido = _proteger_windows(texto.encode("utf-8"))
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    temporario.write_bytes(base64.b64encode(protegido))
    os.replace(temporario, destino)
    return destino


def carregar_token(caminho: str | Path | None = None) -> str:
    ambiente = os.environ.get(VARIAVEL_TOKEN, "").strip()
    if ambiente:
        if len(ambiente) < 24:
            raise ValueError(f"A variável {VARIAVEL_TOKEN} contém um token inválido.")
        return ambiente
    if os.name != "nt":
        raise FileNotFoundError(
            f"Defina {VARIAVEL_TOKEN}; o DPAPI somente existe no Windows."
        )
    origem = Path(caminho) if caminho else caminho_segredo_padrao()
    if not origem.is_file():
        raise FileNotFoundError("A credencial protegida do agente não foi configurada.")
    protegido = base64.b64decode(origem.read_bytes(), validate=True)
    return _desproteger_windows(protegido).decode("utf-8")
