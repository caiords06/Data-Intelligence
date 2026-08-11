"""Backup empresarial completo, verificável e restaurável.

O pacote inclui uma cópia consistente do SQLite e os arquivos persistidos sob
``storage`` (documentos, datasets, relatórios, anexos etc.). Backups anteriores
em formato ``.db`` continuam sendo verificáveis por compatibilidade.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

from auth import banco
from auth.banco import conectar
from enterprise.contexto import obter_escopo_ator

VERSAO_BACKUP = 2
PASTAS_IGNORADAS = {"backups", "cache", "tmp", "temp", "logs"}


def _hash_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _arquivos_storage() -> list[Path]:
    raiz = banco.STORAGE_DIR.resolve()
    if not raiz.exists():
        return []
    saida = []
    db_atual = Path(banco.DB_PATH).resolve()
    for caminho in raiz.rglob("*"):
        if not caminho.is_file():
            continue
        try:
            relativo = caminho.relative_to(raiz)
        except ValueError:
            continue
        if any(parte.lower() in PASTAS_IGNORADAS for parte in relativo.parts[:-1]):
            continue
        if caminho.resolve() == db_atual:
            continue
        if caminho.suffix.lower() in {".db-wal", ".db-shm"}:
            continue
        saida.append(caminho)
    return saida


def _copiar_banco_consistente(destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with conectar() as origem, closing(sqlite3.connect(destino)) as copia:
        origem.backup(copia)
        integridade = copia.execute("PRAGMA quick_check").fetchone()[0]
        fk = copia.execute("PRAGMA foreign_key_check").fetchall()
    if integridade != "ok" or fk:
        destino.unlink(missing_ok=True)
        raise RuntimeError("O banco do backup falhou na verificação de integridade.")


def criar_backup(ator: dict, destino: str | Path | None = None, *, sincronizar_servidor: bool = True) -> dict:
    from core.nodo import usa_servidor_remoto
    if usa_servidor_remoto():
        if destino is not None:
            raise ValueError("Em estação conectada, o backup é criado no Servidor Corporativo; não informe destino local.")
        from enterprise.servidor_cliente import criar_backup_servidor
        return criar_backup_servidor()
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Somente administradores podem criar backups completos.")
    empresa_id, _ = obter_escopo_ator(ator)
    pasta = Path(destino) if destino else banco.STORAGE_DIR / "backups"
    pasta = pasta.expanduser().resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"enterprise_full_{datetime.now():%Y%m%d_%H%M%S_%f}.zip"

    with tempfile.TemporaryDirectory(prefix="dataintelligence_backup_") as tmp:
        staging = Path(tmp)
        db_backup = staging / "app.db"
        _copiar_banco_consistente(db_backup)
        itens = []
        with zipfile.ZipFile(caminho, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.write(db_backup, "database/app.db")
            itens.append({"caminho": "database/app.db", "sha256": _hash_arquivo(db_backup), "tamanho": db_backup.stat().st_size})
            raiz = banco.STORAGE_DIR.resolve()
            for arquivo in _arquivos_storage():
                relativo = arquivo.relative_to(raiz).as_posix()
                arcname = f"storage/{relativo}"
                zf.write(arquivo, arcname)
                itens.append({"caminho": arcname, "sha256": _hash_arquivo(arquivo), "tamanho": arquivo.stat().st_size})
            manifesto = {
                "versao": VERSAO_BACKUP,
                "criado_em": datetime.now().isoformat(timespec="seconds"),
                "empresa_id": empresa_id,
                "usuario_id": int(ator["id"]),
                "itens": itens,
            }
            zf.writestr("manifest.json", json.dumps(manifesto, ensure_ascii=False, indent=2))

    validacao = verificar_backup(caminho)
    if not validacao["integro"]:
        caminho.unlink(missing_ok=True)
        raise RuntimeError("O pacote de backup falhou na verificação final.")
    hash_sha256 = _hash_arquivo(caminho)
    tamanho = caminho.stat().st_size
    with conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO backups (empresa_id,usuario_id,arquivo,hash_sha256,tamanho_bytes) VALUES (?,?,?,?,?)",
            (empresa_id, int(ator["id"]), str(caminho), hash_sha256, tamanho),
        )
        backup_id = int(cursor.lastrowid)
        # Catálogo novo, quando disponível.
        try:
            conexao.execute(
                """INSERT INTO backups_empresariais
                   (empresa_id,tipo,arquivo_relativo,tamanho_bytes,sha256,criado_por)
                   VALUES (?,'Completo',?,?,?,?)""",
                (empresa_id, str(caminho), tamanho, hash_sha256, int(ator["id"])),
            )
        except sqlite3.OperationalError:
            pass
    resultado = {"id": backup_id, "arquivo": str(caminho), "hash_sha256": hash_sha256, "tamanho_bytes": tamanho, "status": "Válido", "completo": True}
    if sincronizar_servidor:
        try:
            from core.nodo import usa_servidor_remoto
            if usa_servidor_remoto():
                from enterprise.servidor_cliente import enviar_backup
                remoto = enviar_backup(caminho)
                resultado["servidor"] = remoto
        except Exception as erro:
            # Nunca invalida a cópia local íntegra; informa a pendência ao chamador.
            resultado["servidor_erro"] = str(erro)
    return resultado


def verificar_backup(caminho: str | Path, hash_esperado: str | None = None) -> dict:
    arquivo = Path(caminho).expanduser().resolve()
    if not arquivo.is_file():
        raise FileNotFoundError("Arquivo de backup não encontrado.")
    hash_atual = _hash_arquivo(arquivo)
    hash_valido = hash_esperado is None or hash_atual == hash_esperado
    if arquivo.suffix.lower() != ".zip":
        with closing(sqlite3.connect(arquivo)) as conexao:
            integridade = conexao.execute("PRAGMA quick_check").fetchone()[0]
        return {"integro": integridade == "ok", "hash_valido": hash_valido, "hash_sha256": hash_atual, "tamanho_bytes": arquivo.stat().st_size, "formato": "legado-db"}

    erros = []
    with tempfile.TemporaryDirectory(prefix="dataintelligence_verify_") as tmp:
        tmp_path = Path(tmp)
        try:
            with zipfile.ZipFile(arquivo) as zf:
                nomes = set(zf.namelist())
                if "manifest.json" not in nomes or "database/app.db" not in nomes:
                    erros.append("manifesto ou banco ausente")
                else:
                    manifesto = json.loads(zf.read("manifest.json").decode("utf-8"))
                    for item in manifesto.get("itens", []):
                        nome = item.get("caminho")
                        if not nome or nome not in nomes:
                            erros.append(f"item ausente: {nome}")
                            continue
                        dados = zf.read(nome)
                        if hashlib.sha256(dados).hexdigest() != item.get("sha256"):
                            erros.append(f"hash inválido: {nome}")
                    db = tmp_path / "app.db"
                    db.write_bytes(zf.read("database/app.db"))
                    with closing(sqlite3.connect(db)) as conexao:
                        if conexao.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                            erros.append("quick_check do banco falhou")
                        if conexao.execute("PRAGMA foreign_key_check").fetchall():
                            erros.append("foreign_key_check do banco falhou")
        except (zipfile.BadZipFile, json.JSONDecodeError, OSError) as erro:
            erros.append(str(erro))
    return {"integro": not erros, "hash_valido": hash_valido, "hash_sha256": hash_atual, "tamanho_bytes": arquivo.stat().st_size, "formato": "completo-v2", "erros": erros}


def restaurar_backup(caminho: str | Path, ator: dict) -> dict:
    """Restaura banco + arquivos após validação e cria um backup de segurança."""
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Somente administradores podem restaurar backups.")
    origem = Path(caminho).expanduser().resolve()
    validacao = verificar_backup(origem)
    if not validacao["integro"] or not validacao["hash_valido"]:
        raise ValueError("O backup não é íntegro e não pode ser restaurado.")
    if origem.suffix.lower() != ".zip":
        raise ValueError("A restauração completa exige um backup .zip V2.")

    seguranca = criar_backup(ator)
    with tempfile.TemporaryDirectory(prefix="dataintelligence_restore_") as tmp:
        staging = Path(tmp)
        with zipfile.ZipFile(origem) as zf:
            for membro in zf.infolist():
                destino = (staging / membro.filename).resolve()
                if staging.resolve() not in destino.parents and destino != staging.resolve():
                    raise ValueError("Backup contém caminho inseguro.")
            zf.extractall(staging)
        novo_db = staging / "database" / "app.db"
        destino_db = Path(banco.DB_PATH).resolve()
        destino_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(novo_db, destino_db)
        storage_staging = staging / "storage"
        if storage_staging.exists():
            for arquivo in storage_staging.rglob("*"):
                if not arquivo.is_file():
                    continue
                relativo = arquivo.relative_to(storage_staging)
                alvo = banco.STORAGE_DIR / relativo
                alvo.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(arquivo, alvo)
    return {"restaurado": True, "backup_seguranca": seguranca["arquivo"], "origem": str(origem)}
