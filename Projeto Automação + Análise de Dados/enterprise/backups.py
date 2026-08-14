"""Backup empresarial completo, verificável e restaurável.

Em produção, o pacote inclui um dump consistente do PostgreSQL e os arquivos
gerenciados pelo Servidor Corporativo. Backups SQLite antigos continuam sendo
legíveis exclusivamente para migração/compatibilidade.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from auth import banco
from auth.banco import conectar, backend_banco
from enterprise.contexto import obter_escopo_ator

VERSAO_BACKUP = 3
PASTAS_IGNORADAS = {"backups", "cache", "tmp", "temp", "logs"}
MAGIC_BACKUP_CIFRADO = b"DIBAK1\x00"


def _hash_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _chave_backup() -> bytes:
    from core.criptografia import obter_chave_mestra
    return obter_chave_mestra(
        variavel_ambiente="DATA_INTELLIGENCE_BACKUP_MASTER_KEY",
        caminho_dpapi=banco.STORAGE_DIR / "segredos" / "backup_master.dpapi",
        descricao="Data Intelligence backup master key",
    )


def _criptografar_backup(entrada: Path, saida: Path) -> None:
    """AES-256-GCM em streaming: confidencialidade e autenticação do pacote."""
    nonce = os.urandom(12)
    cifra = Cipher(algorithms.AES(_chave_backup()), modes.GCM(nonce)).encryptor()
    cifra.authenticate_additional_data(MAGIC_BACKUP_CIFRADO)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with entrada.open("rb") as origem, saida.open("wb") as destino:
        destino.write(MAGIC_BACKUP_CIFRADO)
        destino.write(nonce)
        for bloco in iter(lambda: origem.read(1024 * 1024), b""):
            destino.write(cifra.update(bloco))
        destino.write(cifra.finalize())
        destino.write(cifra.tag)


def _descriptografar_backup(entrada: Path, saida: Path) -> None:
    tamanho_minimo = len(MAGIC_BACKUP_CIFRADO) + 12 + 16
    if entrada.stat().st_size < tamanho_minimo:
        raise ValueError("Backup cifrado truncado.")
    with entrada.open("rb") as origem:
        if origem.read(len(MAGIC_BACKUP_CIFRADO)) != MAGIC_BACKUP_CIFRADO:
            raise ValueError("Cabeçalho de backup cifrado inválido.")
        nonce = origem.read(12)
        origem.seek(-16, os.SEEK_END)
        tag = origem.read(16)
        bytes_cifrados = entrada.stat().st_size - tamanho_minimo
        origem.seek(len(MAGIC_BACKUP_CIFRADO) + 12)
        decifra = Cipher(algorithms.AES(_chave_backup()), modes.GCM(nonce, tag)).decryptor()
        decifra.authenticate_additional_data(MAGIC_BACKUP_CIFRADO)
        saida.parent.mkdir(parents=True, exist_ok=True)
        restantes = bytes_cifrados
        try:
            with saida.open("wb") as destino:
                while restantes:
                    bloco = origem.read(min(1024 * 1024, restantes))
                    if not bloco:
                        raise ValueError("Backup cifrado truncado.")
                    restantes -= len(bloco)
                    destino.write(decifra.update(bloco))
                destino.write(decifra.finalize())
        except Exception:
            saida.unlink(missing_ok=True)
            raise


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


def _copiar_banco_sqlite_consistente(destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with conectar() as origem, closing(sqlite3.connect(destino)) as copia:
        origem.backup(copia)
        integridade = copia.execute("PRAGMA quick_check").fetchone()[0]
        fk = copia.execute("PRAGMA foreign_key_check").fetchall()
    if integridade != "ok" or fk:
        destino.unlink(missing_ok=True)
        raise RuntimeError("O banco do backup falhou na verificação de integridade.")


def _eh_windows() -> bool:
    return os.name == "nt"


def _comando_postgres(nome: str) -> str:
    """Localiza utilitários PostgreSQL mesmo quando o serviço não herda o PATH.

    Serviços Windows normalmente executam com um PATH diferente do usuário que
    instalou o PostgreSQL. O servidor já pode conectar via psycopg enquanto
    ``shutil.which('pg_dump')`` retorna ``None``. Procuramos primeiro o PATH e
    depois os diretórios padrão do instalador PostgreSQL.
    """
    nome = str(nome).strip()
    exe = shutil.which(nome)
    if exe:
        return exe

    candidatos: list[Path] = []
    pg_bin = str(os.environ.get("DATA_INTELLIGENCE_PG_BIN", "")).strip()
    if pg_bin:
        candidatos.append(Path(pg_bin).expanduser())

    if _eh_windows():
        for variavel in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            raiz = str(os.environ.get(variavel, "")).strip()
            if not raiz:
                continue
            base = Path(raiz) / "PostgreSQL"
            if base.is_dir():
                # Versões maiores primeiro (18, 17, 16...).
                versoes = sorted(
                    (item for item in base.iterdir() if item.is_dir()),
                    key=lambda item: tuple(
                        int(parte) if parte.isdigit() else 0
                        for parte in item.name.replace("-", ".").split(".")
                    ),
                    reverse=True,
                )
                candidatos.extend(item / "bin" for item in versoes)
    else:
        candidatos.extend(
            Path(item)
            for item in (
                "/usr/lib/postgresql/18/bin", "/usr/lib/postgresql/17/bin",
                "/usr/lib/postgresql/16/bin", "/usr/lib/postgresql/15/bin",
                "/usr/local/pgsql/bin",
            )
        )

    nomes = [nome]
    if _eh_windows() and not nome.lower().endswith(".exe"):
        nomes.insert(0, nome + ".exe")
    for pasta in candidatos:
        for candidato_nome in nomes:
            candidato = (pasta / candidato_nome).resolve()
            if candidato.is_file():
                return str(candidato)

    raise RuntimeError(
        f"{nome} não encontrado no servidor. O PostgreSQL pode estar funcionando, "
        "mas as ferramentas de backup não estão no PATH do serviço. Instale os "
        "Command Line Tools do PostgreSQL ou defina DATA_INTELLIGENCE_PG_BIN "
        "apontando para a pasta bin da instalação PostgreSQL."
    )



def validar_dependencias_backup() -> dict:
    """Falha cedo quando a instalação do servidor não pode produzir/restaurar dumps.

    A conexão via psycopg não garante que ``pg_dump``/``pg_restore`` estejam
    visíveis para a conta do serviço. Validamos os dois utilitários no startup
    para que o problema apareça na instalação/health, e não somente quando o
    administrador clicar em Backup.
    """
    if backend_banco() != "postgresql":
        return {"backend": backend_banco(), "ok": True}
    return {
        "backend": "postgresql",
        "ok": True,
        "pg_dump": _comando_postgres("pg_dump"),
        "pg_restore": _comando_postgres("pg_restore"),
    }


def _ambiente_pg() -> dict:
    env=os.environ.copy()
    if os.environ.get("DATA_INTELLIGENCE_PG_PASSWORD"):
        env["PGPASSWORD"]=os.environ["DATA_INTELLIGENCE_PG_PASSWORD"]
    return env


def _argumentos_pg() -> list[str]:
    return [
        "--host", os.environ.get("DATA_INTELLIGENCE_PG_HOST","127.0.0.1"),
        "--port", os.environ.get("DATA_INTELLIGENCE_PG_PORT","5432"),
        "--username", os.environ.get("DATA_INTELLIGENCE_PG_USER","dataintelligence"),
    ]


def _criar_dump_postgresql(destino: Path) -> None:
    destino.parent.mkdir(parents=True,exist_ok=True)
    cmd=[_comando_postgres("pg_dump"),*_argumentos_pg(),"--format=custom","--no-owner","--no-privileges","--file",str(destino),os.environ.get("DATA_INTELLIGENCE_PG_DATABASE","dataintelligence")]
    proc=subprocess.run(cmd,env=_ambiente_pg(),capture_output=True,text=True,timeout=1800)
    if proc.returncode!=0 or not destino.is_file():
        destino.unlink(missing_ok=True)
        raise RuntimeError("pg_dump falhou: "+(proc.stderr.strip() or "erro desconhecido"))


def _verificar_dump_postgresql(arquivo: Path) -> None:
    cmd=[_comando_postgres("pg_restore"),"--list",str(arquivo)]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    if proc.returncode!=0 or "TABLE" not in proc.stdout.upper():
        raise RuntimeError("pg_restore não reconheceu o dump PostgreSQL.")


def criar_backup(
    ator: dict,
    destino: str | Path | None = None,
    *,
    sincronizar_servidor: bool = True,
    criptografar: bool | None = None,
) -> dict:
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
    backend = backend_banco()
    # Produção é PostgreSQL e nunca gera backup em claro por padrão.
    usar_criptografia = backend == "postgresql" if criptografar is None else bool(criptografar)
    extensao = ".dibak" if usar_criptografia else ".zip"
    caminho = pasta / f"enterprise_full_{datetime.now():%Y%m%d_%H%M%S_%f}{extensao}"

    with tempfile.TemporaryDirectory(prefix="dataintelligence_backup_") as tmp:
        staging = Path(tmp)
        pacote_zip = staging / "pacote.zip" if usar_criptografia else caminho
        db_backup = staging / ("postgresql.dump" if backend=="postgresql" else "app.db")
        if backend=="postgresql": _criar_dump_postgresql(db_backup)
        else: _copiar_banco_sqlite_consistente(db_backup)
        itens = []
        arc_db="database/postgresql.dump" if backend=="postgresql" else "database/app.db"
        with zipfile.ZipFile(pacote_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.write(db_backup, arc_db)
            itens.append({"caminho": arc_db, "sha256": _hash_arquivo(db_backup), "tamanho": db_backup.stat().st_size})
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
                "backend": backend,
                "itens": itens,
            }
            zf.writestr("manifest.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
        if usar_criptografia:
            _criptografar_backup(pacote_zip, caminho)

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
    resultado = {
        "id": backup_id, "arquivo": str(caminho), "hash_sha256": hash_sha256,
        "tamanho_bytes": tamanho, "status": "Válido", "completo": True,
        "criptografado": usar_criptografia,
    }
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


def _verificar_zip(arquivo: Path) -> list[str]:
    erros: list[str] = []
    with tempfile.TemporaryDirectory(prefix="dataintelligence_verify_adhoc_") as tmp:
        tmp_path = Path(tmp)
        try:
            with zipfile.ZipFile(arquivo) as zf:
                nomes = set(zf.namelist())
                if "manifest.json" not in nomes:
                    erros.append("manifesto ausente")
                else:
                    manifesto = json.loads(zf.read("manifest.json").decode("utf-8"))
                    backend_manifesto = str(manifesto.get("backend") or ("postgresql" if "database/postgresql.dump" in nomes else "sqlite"))
                    db_nome = "database/postgresql.dump" if backend_manifesto == "postgresql" else "database/app.db"
                    if db_nome not in nomes:
                        erros.append("banco/dump ausente")
                    for item in manifesto.get("itens", []):
                        nome = item.get("caminho")
                        if not nome or nome not in nomes:
                            erros.append(f"item ausente: {nome}")
                            continue
                        dados = zf.read(nome)
                        if hashlib.sha256(dados).hexdigest() != item.get("sha256"):
                            erros.append(f"hash inválido: {nome}")
                    if db_nome in nomes:
                        db = tmp_path / Path(db_nome).name
                        db.write_bytes(zf.read(db_nome))
                        if backend_manifesto == "postgresql":
                            try:
                                _verificar_dump_postgresql(db)
                            except Exception as exc:
                                erros.append(str(exc))
                        else:
                            with closing(sqlite3.connect(db)) as conexao:
                                if conexao.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                                    erros.append("quick_check do banco falhou")
                                if conexao.execute("PRAGMA foreign_key_check").fetchall():
                                    erros.append("foreign_key_check do banco falhou")
        except (zipfile.BadZipFile, json.JSONDecodeError, OSError, ValueError) as erro:
            erros.append(str(erro))
    return erros


def verificar_backup(caminho: str | Path, hash_esperado: str | None = None) -> dict:
    arquivo = Path(caminho).expanduser().resolve()
    if not arquivo.is_file():
        raise FileNotFoundError("Arquivo de backup não encontrado.")
    hash_atual = _hash_arquivo(arquivo)
    hash_valido = hash_esperado is None or hash_atual == hash_esperado
    if arquivo.suffix.lower() == ".dibak":
        with tempfile.TemporaryDirectory(prefix="dataintelligence_decrypt_verify_") as tmp:
            pacote = Path(tmp) / "pacote.zip"
            try:
                _descriptografar_backup(arquivo, pacote)
                erros = _verificar_zip(pacote)
            except Exception as erro:
                erros = [f"falha de autenticação/decifragem: {erro}"]
        return {
            "integro": not erros, "hash_valido": hash_valido, "hash_sha256": hash_atual,
            "tamanho_bytes": arquivo.stat().st_size, "formato": f"completo-cifrado-v{VERSAO_BACKUP}",
            "criptografado": True, "erros": erros,
        }
    if arquivo.suffix.lower() != ".zip":
        with closing(sqlite3.connect(arquivo)) as conexao:
            integridade = conexao.execute("PRAGMA quick_check").fetchone()[0]
        return {"integro": integridade == "ok", "hash_valido": hash_valido, "hash_sha256": hash_atual, "tamanho_bytes": arquivo.stat().st_size, "formato": "legado-db"}

    erros = _verificar_zip(arquivo)
    return {
        "integro": not erros, "hash_valido": hash_valido, "hash_sha256": hash_atual,
        "tamanho_bytes": arquivo.stat().st_size, "formato": f"completo-v{VERSAO_BACKUP}",
        "criptografado": False, "erros": erros,
    }


def restaurar_backup(caminho: str | Path, ator: dict) -> dict:
    """Restaura banco + arquivos após validação e cria um backup de segurança."""
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Somente administradores podem restaurar backups.")
    origem = Path(caminho).expanduser().resolve()
    validacao = verificar_backup(origem)
    if not validacao["integro"] or not validacao["hash_valido"]:
        raise ValueError("O backup não é íntegro e não pode ser restaurado.")
    if origem.suffix.lower() not in {".zip", ".dibak"}:
        raise ValueError("A restauração completa exige backup .zip ou .dibak.")

    seguranca = criar_backup(ator)
    with tempfile.TemporaryDirectory(prefix="dataintelligence_restore_") as tmp:
        staging = Path(tmp)
        pacote = origem
        if origem.suffix.lower() == ".dibak":
            pacote = staging / "pacote.zip"
            _descriptografar_backup(origem, pacote)
        with zipfile.ZipFile(pacote) as zf:
            for membro in zf.infolist():
                destino = (staging / membro.filename).resolve()
                if staging.resolve() not in destino.parents and destino != staging.resolve():
                    raise ValueError("Backup contém caminho inseguro.")
            zf.extractall(staging)
        manifesto=json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
        backend_manifesto=str(manifesto.get("backend") or "sqlite")
        if backend_banco()=="postgresql":
            if backend_manifesto!="postgresql":
                raise ValueError("Servidor PostgreSQL exige backup PostgreSQL para restauração direta.")
            dump=staging / "database" / "postgresql.dump"
            cmd=[_comando_postgres("pg_restore"),*_argumentos_pg(),"--clean","--if-exists","--no-owner","--no-privileges","--dbname",os.environ.get("DATA_INTELLIGENCE_PG_DATABASE","dataintelligence"),str(dump)]
            proc=subprocess.run(cmd,env=_ambiente_pg(),capture_output=True,text=True,timeout=3600)
            if proc.returncode!=0: raise RuntimeError("pg_restore falhou: "+(proc.stderr.strip() or "erro desconhecido"))
        else:
            if backend_manifesto!="sqlite": raise ValueError("Backup PostgreSQL não pode ser restaurado diretamente no SQLite.")
            novo_db = staging / "database" / "app.db"
            destino_db = Path(banco.DB_PATH).resolve(); destino_db.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(novo_db, destino_db)
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
