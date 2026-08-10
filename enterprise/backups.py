"""Backup local verificável do banco SQLite."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

from auth import banco
from auth.banco import conectar
from enterprise.contexto import garantir_contexto_sessao


def _hash_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def criar_backup(ator: dict, destino: str | Path | None = None) -> dict:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Somente administradores podem criar backups completos.")
    empresa_id, _ = garantir_contexto_sessao()
    pasta = Path(destino) if destino else banco.STORAGE_DIR / "backups"
    pasta = pasta.expanduser().resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"enterprise_{datetime.now():%Y%m%d_%H%M%S_%f}.db"

    with conectar() as origem, sqlite3.connect(caminho) as copia:
        origem.backup(copia)
        integridade = copia.execute("PRAGMA quick_check").fetchone()[0]
    if integridade != "ok":
        caminho.unlink(missing_ok=True)
        raise RuntimeError("O backup falhou na verificação de integridade.")

    hash_sha256 = _hash_arquivo(caminho)
    tamanho = caminho.stat().st_size
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO backups (
                empresa_id, usuario_id, arquivo, hash_sha256, tamanho_bytes
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (empresa_id, ator["id"], str(caminho), hash_sha256, tamanho),
        )
        backup_id = int(cursor.lastrowid)
    return {
        "id": backup_id,
        "arquivo": str(caminho),
        "hash_sha256": hash_sha256,
        "tamanho_bytes": tamanho,
        "status": "Válido",
    }


def verificar_backup(caminho: str | Path, hash_esperado: str | None = None) -> dict:
    arquivo = Path(caminho).expanduser().resolve()
    if not arquivo.is_file():
        raise FileNotFoundError("Arquivo de backup não encontrado.")
    with sqlite3.connect(arquivo) as conexao:
        integridade = conexao.execute("PRAGMA quick_check").fetchone()[0]
    hash_atual = _hash_arquivo(arquivo)
    return {
        "integro": integridade == "ok",
        "hash_valido": hash_esperado is None or hash_atual == hash_esperado,
        "hash_sha256": hash_atual,
        "tamanho_bytes": arquivo.stat().st_size,
    }

