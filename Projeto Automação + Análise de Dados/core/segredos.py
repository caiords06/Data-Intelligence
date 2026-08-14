"""Armazenamento de segredos de máquina.

No Windows usa DPAPI no escopo da máquina. Em outros sistemas o segredo deve
ser fornecido por variável de ambiente ou por um gerenciador externo; este
módulo não grava texto puro em disco.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess

CRYPTPROTECT_LOCAL_MACHINE = 0x4


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(dados: bytes):
    buffer = ctypes.create_string_buffer(dados)
    estrutura = _DataBlob(len(dados), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return estrutura, buffer


def _proteger_windows(segredo: bytes, descricao: str) -> bytes:
    entrada, buffer = _blob(segredo); saida = _DataBlob()
    crypt32 = ctypes.windll.crypt32; kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(entrada), descricao, None, None, None,
        CRYPTPROTECT_LOCAL_MACHINE, ctypes.byref(saida),
    )
    del buffer
    if not ok: raise ctypes.WinError()
    try: return ctypes.string_at(saida.pbData, saida.cbData)
    finally: kernel32.LocalFree(saida.pbData)


def _desproteger_windows(protegido: bytes) -> bytes:
    entrada, buffer = _blob(protegido); saida = _DataBlob()
    crypt32 = ctypes.windll.crypt32; kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(saida))
    del buffer
    if not ok: raise ctypes.WinError()
    try: return ctypes.string_at(saida.pbData, saida.cbData)
    finally: kernel32.LocalFree(saida.pbData)


def _restringir_acl_windows(pasta: Path) -> None:
    """Mantém segredos de máquina acessíveis apenas a SYSTEM/Administradores."""
    subprocess.run(
        [
            "icacls.exe", str(pasta), "/inheritance:r",
            "/grant:r", "*S-1-5-18:(OI)(CI)F",
            "/grant:r", "*S-1-5-32-544:(OI)(CI)F",
        ],
        check=True, capture_output=True, text=True, shell=False,
    )


def salvar_segredo_maquina(valor: str, caminho: str | Path, *, descricao: str = "Data Intelligence") -> Path:
    texto = str(valor or "")
    if not texto:
        raise ValueError("O segredo não pode ser vazio.")
    if os.name != "nt":
        raise OSError("A persistência local de segredos exige Windows DPAPI; use variável de ambiente fora do Windows.")
    destino = Path(caminho).expanduser().resolve(); destino.parent.mkdir(parents=True, exist_ok=True)
    protegido = _proteger_windows(texto.encode("utf-8"), descricao)
    tmp = destino.with_suffix(destino.suffix + ".tmp")
    tmp.write_bytes(base64.b64encode(protegido)); os.replace(tmp, destino)
    _restringir_acl_windows(destino.parent)
    return destino


def carregar_segredo_maquina(caminho: str | Path, *, variavel_ambiente: str | None = None) -> str:
    if variavel_ambiente:
        ambiente = str(os.environ.get(variavel_ambiente, "")).strip()
        if ambiente: return ambiente
    origem = Path(caminho).expanduser().resolve()
    if os.name != "nt":
        nome = variavel_ambiente or "variável de ambiente apropriada"
        raise FileNotFoundError(f"Defina {nome}; DPAPI só está disponível no Windows.")
    if not origem.is_file():
        raise FileNotFoundError(f"Segredo protegido não encontrado: {origem}")
    protegido = base64.b64decode(origem.read_bytes(), validate=True)
    return _desproteger_windows(protegido).decode("utf-8")
