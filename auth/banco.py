"""Persistência local de usuários em SQLite."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "app.db"


@contextmanager
def conectar():
    """Abre uma conexão transacional e garante seu fechamento."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(DB_PATH, timeout=5)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def inicializar_banco() -> None:
    with conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
                senha_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                perfil TEXT NOT NULL DEFAULT 'usuario'
                    CHECK (perfil IN ('admin', 'usuario')),
                ativo INTEGER NOT NULL DEFAULT 1
                    CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ultimo_login TEXT
            )
            """
        )


def tem_usuarios() -> bool:
    with conectar() as conexao:
        resultado = conexao.execute(
            "SELECT COUNT(*) AS total FROM usuarios"
        ).fetchone()
    return bool(resultado["total"])


def buscar_usuario(login: str):
    with conectar() as conexao:
        return conexao.execute(
            "SELECT * FROM usuarios WHERE usuario = ?",
            (login,),
        ).fetchone()


def inserir_usuario(nome, usuario, senha_hash, salt, perfil) -> int:
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO usuarios (nome, usuario, senha_hash, salt, perfil)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nome, usuario, senha_hash, salt, perfil),
        )
        return int(cursor.lastrowid)


def registrar_login(usuario_id: int) -> None:
    with conectar() as conexao:
        conexao.execute(
            "UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP WHERE id = ?",
            (usuario_id,),
        )


def listar_usuarios() -> list[dict]:
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id, nome, usuario, perfil, ativo, criado_em, ultimo_login
            FROM usuarios
            ORDER BY nome COLLATE NOCASE
            """
        ).fetchall()
    return [dict(registro) for registro in registros]


def alterar_status_usuario(usuario_id: int, ativo: bool) -> None:
    with conectar() as conexao:
        cursor = conexao.execute(
            "UPDATE usuarios SET ativo = ? WHERE id = ?",
            (1 if ativo else 0, usuario_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Usuário não encontrado.")


def atualizar_senha_usuario(usuario_id: int, senha_hash: str, salt: str) -> None:
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?, salt = ?
            WHERE id = ?
            """,
            (senha_hash, salt, usuario_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Usuário não encontrado.")
