"""Persistência local de usuários em SQLite."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "app.db"


@contextmanager
def conectar():
    """Abre uma conexão transacional segura e garante seu fechamento.

    O SQLite desativa chaves estrangeiras por conexão. A ativação precisa
    acontecer aqui — e não apenas durante a inicialização do schema — para
    que qualquer serviço da aplicação respeite a integridade referencial.
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(DB_PATH, timeout=5)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 5000")
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
                perfil_acesso TEXT NOT NULL DEFAULT 'analista',
                ativo INTEGER NOT NULL DEFAULT 1
                    CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ultimo_login TEXT,
                tentativas_falhas INTEGER NOT NULL DEFAULT 0,
                bloqueado_ate TEXT,
                senha_alterada_em TEXT
            )
            """
        )
        colunas = {
            registro["name"]
            for registro in conexao.execute("PRAGMA table_info(usuarios)").fetchall()
        }
        migracoes = {
            "tentativas_falhas": (
                "ALTER TABLE usuarios ADD COLUMN "
                "tentativas_falhas INTEGER NOT NULL DEFAULT 0"
            ),
            "bloqueado_ate": "ALTER TABLE usuarios ADD COLUMN bloqueado_ate TEXT",
            "senha_alterada_em": (
                "ALTER TABLE usuarios ADD COLUMN senha_alterada_em TEXT"
            ),
            "perfil_acesso": (
                "ALTER TABLE usuarios ADD COLUMN "
                "perfil_acesso TEXT NOT NULL DEFAULT 'analista'"
            ),
        }
        for coluna, comando in migracoes.items():
            if coluna not in colunas:
                conexao.execute(comando)

        conexao.execute(
            """
            UPDATE usuarios
            SET perfil_acesso = 'administrador'
            WHERE perfil = 'admin' AND perfil_acesso != 'administrador'
            """
        )

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                alvo_usuario_id INTEGER,
                acao TEXT NOT NULL,
                detalhes TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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


def buscar_usuario_por_id(usuario_id: int):
    with conectar() as conexao:
        return conexao.execute(
            "SELECT * FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()


def inserir_usuario(
    nome,
    usuario,
    senha_hash,
    salt,
    perfil,
    perfil_acesso="analista",
) -> int:
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO usuarios (
                nome, usuario, senha_hash, salt, perfil, perfil_acesso
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (nome, usuario, senha_hash, salt, perfil, perfil_acesso),
        )
        return int(cursor.lastrowid)


def registrar_login(usuario_id: int) -> None:
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE usuarios
            SET ultimo_login = CURRENT_TIMESTAMP,
                tentativas_falhas = 0,
                bloqueado_ate = NULL
            WHERE id = ?
            """,
            (usuario_id,),
        )


def registrar_falha_autenticacao(
    usuario_id: int,
    limite: int = 5,
    minutos_bloqueio: int = 5,
) -> bool:
    """Registra falha e retorna True quando a conta foi bloqueada."""
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT tentativas_falhas FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        if registro is None:
            return False
        tentativas = int(registro["tentativas_falhas"] or 0) + 1
        bloqueado = tentativas >= limite
        bloqueado_ate = (
            (datetime.now(timezone.utc) + timedelta(minutes=minutos_bloqueio)).isoformat()
            if bloqueado
            else None
        )
        conexao.execute(
            """
            UPDATE usuarios
            SET tentativas_falhas = ?, bloqueado_ate = ?
            WHERE id = ?
            """,
            (0 if bloqueado else tentativas, bloqueado_ate, usuario_id),
        )
        return bloqueado


def limpar_falhas_autenticacao(usuario_id: int) -> None:
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE usuarios
            SET tentativas_falhas = 0, bloqueado_ate = NULL
            WHERE id = ?
            """,
            (usuario_id,),
        )


def listar_usuarios() -> list[dict]:
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id, nome, usuario, perfil, perfil_acesso, ativo,
                   criado_em, ultimo_login,
                   tentativas_falhas, bloqueado_ate, senha_alterada_em
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


def alterar_perfil_acesso_usuario(usuario_id: int, perfil_acesso: str) -> None:
    with conectar() as conexao:
        cursor = conexao.execute(
            "UPDATE usuarios SET perfil_acesso = ? WHERE id = ?",
            (str(perfil_acesso), int(usuario_id)),
        )
        if cursor.rowcount == 0:
            raise ValueError("Usuário não encontrado.")


def atualizar_senha_usuario(usuario_id: int, senha_hash: str, salt: str) -> None:
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?, salt = ?,
                senha_alterada_em = CURRENT_TIMESTAMP,
                tentativas_falhas = 0,
                bloqueado_ate = NULL
            WHERE id = ?
            """,
            (senha_hash, salt, usuario_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Usuário não encontrado.")


def contar_administradores_ativos() -> int:
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT COUNT(*) AS total
            FROM usuarios
            WHERE perfil = 'admin' AND ativo = 1
            """
        ).fetchone()
    return int(registro["total"])


def registrar_auditoria(
    acao: str,
    usuario_id: int | None = None,
    alvo_usuario_id: int | None = None,
    detalhes: str | None = None,
) -> None:
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO auditoria (usuario_id, alvo_usuario_id, acao, detalhes)
            VALUES (?, ?, ?, ?)
            """,
            (usuario_id, alvo_usuario_id, str(acao), detalhes),
        )


def listar_auditoria(limite: int = 200) -> list[dict]:
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id, usuario_id, alvo_usuario_id, acao, detalhes, criado_em
            FROM auditoria
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(int(limite), 1000)),),
        ).fetchall()
    return [dict(registro) for registro in registros]
