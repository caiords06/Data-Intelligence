"""Persistência transacional centralizada. PostgreSQL é o backend obrigatório em produção."""

import sqlite3
import json
import os
import platform
from uuid import uuid4
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.caminhos import pasta_dados
from core.versao import VERSAO_INTERFACE

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = pasta_dados()
DB_PATH = STORAGE_DIR / "app.db"


class ConcorrenciaConflito(ValueError):
    """A versão informada pelo cliente não é mais a atual."""


def _distinguir_conflito(conexao, usuario_id: int) -> None:
    existe = conexao.execute("SELECT 1 FROM usuarios WHERE id=?", (int(usuario_id),)).fetchone()
    if existe is None:
        raise ValueError("Usuário não encontrado.")
    raise ConcorrenciaConflito("O usuário foi alterado por outra sessão; recarregue os dados.")


def _papel_estacao_configurado() -> str | None:
    """Lê apenas o papel do nó, sem inicializar banco nem assumir fallback.

    Esta checagem existe como barreira arquitetural: mesmo que um módulo da UI
    esqueça o wrapper RPC, Central/Cliente jamais podem abrir uma conexão SQL.
    O Servidor Corporativo é a única autoridade de persistência.
    """
    papel_env = str(os.environ.get("DATA_INTELLIGENCE_NODE_ROLE", "")).strip().lower()
    if papel_env:
        return papel_env
    try:
        override = str(os.environ.get("DATA_INTELLIGENCE_NODE_CONFIG", "")).strip()
        caminho = Path(override).expanduser().resolve() if override else pasta_dados() / "node.json"
        if not caminho.is_file():
            return None
        bruto = json.loads(caminho.read_text(encoding="utf-8-sig"))
        if isinstance(bruto, dict):
            return str(bruto.get("papel") or "").strip().lower() or None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return None


def _garantir_autoridade_banco() -> None:
    papel = _papel_estacao_configurado()
    if papel in {"central", "cliente"}:
        raise RuntimeError(
            "A estação Central/Cliente não pode abrir banco de dados diretamente. "
            "Esta operação deve ser executada no Servidor Corporativo via RPC/API."
        )


@contextmanager
def _conectar_sqlite():
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
        conexao.execute("PRAGMA journal_mode = WAL")
        conexao.execute("PRAGMA synchronous = NORMAL")
    except sqlite3.DatabaseError:
        # Alguns bancos temporários/readonly usados em testes podem não aceitar WAL.
        pass
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()



def backend_banco() -> str:
    """Retorna o backend transacional do processo.

    PostgreSQL é o padrão e a única opção aceita em execução normal. SQLite
    permanece somente como ferramenta explícita de migração/testes legados;
    nunca existe fallback automático para um banco local.
    """
    valor = str(os.environ.get("DATA_INTELLIGENCE_DB_BACKEND", "postgresql")).strip().lower()
    if valor in {"postgres", "postgresql", "pg", ""}:
        return "postgresql"
    if valor == "sqlite":
        legado = str(os.environ.get("DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE", "")).strip().lower()
        if legado in {"1", "true", "yes", "sim"}:
            return "sqlite"
        raise RuntimeError(
            "SQLite local está desativado. Configure o Servidor Corporativo com PostgreSQL "
            "ou habilite DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE=1 somente para migração/testes."
        )
    raise ValueError(f"Backend de banco inválido: {valor}")


@contextmanager
def conectar():
    _garantir_autoridade_banco()
    if backend_banco() == "postgresql":
        from enterprise.postgresql.adapter import conectar_postgresql
        with conectar_postgresql() as conexao:
            yield conexao
        return
    with _conectar_sqlite() as conexao:
        yield conexao


def banco_central_postgresql() -> bool:
    return backend_banco() == "postgresql"

def inicializar_banco() -> None:
    _garantir_autoridade_banco()
    if backend_banco() == "postgresql":
        from enterprise.postgresql.bootstrap import inicializar_schema_postgresql
        inicializar_schema_postgresql()
        return
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
                email_corporativo TEXT,
                sessao_epoch INTEGER NOT NULL DEFAULT 0,
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
            "email_corporativo": "ALTER TABLE usuarios ADD COLUMN email_corporativo TEXT",
            "sessao_epoch": (
                "ALTER TABLE usuarios ADD COLUMN sessao_epoch INTEGER NOT NULL DEFAULT 0"
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
    empresa_id=None,
    filial_id=None,
    email_corporativo=None,
) -> int:
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO usuarios (
                nome, usuario, senha_hash, salt, perfil, perfil_acesso, email_corporativo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (nome, usuario, senha_hash, salt, perfil, perfil_acesso, email_corporativo),
        )
        usuario_id = int(cursor.lastrowid)
        existe_vinculo = conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            ("usuarios_empresas",),
        ).fetchone()
        if existe_vinculo:
            if perfil == "admin":
                conexao.execute(
                    """
                    INSERT OR IGNORE INTO usuarios_empresas (usuario_id, empresa_id, filial_id)
                    SELECT ?, e.id,
                           (SELECT f.id FROM filiais f WHERE f.empresa_id=e.id AND f.ativo=1 ORDER BY f.id LIMIT 1)
                    FROM empresas e WHERE e.ativo=1
                    """,
                    (usuario_id,),
                )
            else:
                if empresa_id is not None:
                    conexao.execute(
                        """
                        INSERT OR IGNORE INTO usuarios_empresas (
                            usuario_id, empresa_id, filial_id
                        )
                        SELECT ?, e.id,
                               COALESCE(
                                   (SELECT f.id FROM filiais f
                                    WHERE f.id=? AND f.empresa_id=e.id AND f.ativo=1),
                                   (SELECT f.id FROM filiais f
                                    WHERE f.empresa_id=e.id AND f.ativo=1
                                    ORDER BY f.id LIMIT 1)
                               )
                        FROM empresas e WHERE e.id=? AND e.ativo=1
                        """,
                        (usuario_id, filial_id, int(empresa_id)),
                    )
                else:
                    conexao.execute(
                        """
                        INSERT OR IGNORE INTO usuarios_empresas (
                            usuario_id, empresa_id, filial_id
                        )
                        SELECT ?, e.id,
                               (SELECT f.id FROM filiais f
                                WHERE f.empresa_id=e.id AND f.ativo=1
                                ORDER BY f.id LIMIT 1)
                        FROM empresas e WHERE e.ativo=1 ORDER BY e.id LIMIT 1
                        """,
                        (usuario_id,),
                    )
        return usuario_id


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
            SELECT id, nome, usuario, perfil, perfil_acesso, email_corporativo,
                   sessao_epoch, ativo, criado_em, ultimo_login,
                   tentativas_falhas, bloqueado_ate, senha_alterada_em
            FROM usuarios
            ORDER BY nome COLLATE NOCASE
            """
        ).fetchall()
    return [dict(registro) for registro in registros]


def alterar_status_usuario(usuario_id: int, ativo: bool, *, expected_epoch: int | None = None) -> None:
    with conectar() as conexao:
        filtro = "" if expected_epoch is None else " AND sessao_epoch=?"
        parametros = [1 if ativo else 0, int(usuario_id)]
        if expected_epoch is not None:
            parametros.append(int(expected_epoch))
        cursor = conexao.execute(
            "UPDATE usuarios SET ativo = ?, sessao_epoch = COALESCE(sessao_epoch,0) + 1 WHERE id = ?" + filtro,
            tuple(parametros),
        )
        if cursor.rowcount == 0:
            _distinguir_conflito(conexao, usuario_id)


def alterar_perfil_acesso_usuario(usuario_id: int, perfil_acesso: str, *, expected_epoch: int | None = None) -> None:
    with conectar() as conexao:
        filtro = "" if expected_epoch is None else " AND sessao_epoch=?"
        parametros = [str(perfil_acesso), int(usuario_id)]
        if expected_epoch is not None:
            parametros.append(int(expected_epoch))
        cursor = conexao.execute(
            "UPDATE usuarios SET perfil_acesso = ?, sessao_epoch = COALESCE(sessao_epoch,0) + 1 WHERE id = ?" + filtro,
            tuple(parametros),
        )
        if cursor.rowcount == 0:
            _distinguir_conflito(conexao, usuario_id)


def atualizar_senha_usuario(
    usuario_id: int, senha_hash: str, salt: str, *, expected_epoch: int | None = None,
) -> None:
    with conectar() as conexao:
        filtro = "" if expected_epoch is None else " AND sessao_epoch=?"
        parametros = [senha_hash, salt, int(usuario_id)]
        if expected_epoch is not None:
            parametros.append(int(expected_epoch))
        cursor = conexao.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?, salt = ?,
                senha_alterada_em = CURRENT_TIMESTAMP,
                tentativas_falhas = 0,
                bloqueado_ate = NULL,
                sessao_epoch = COALESCE(sessao_epoch,0) + 1
            WHERE id = ?
            """ + filtro,
            tuple(parametros),
        )
        if cursor.rowcount == 0:
            _distinguir_conflito(conexao, usuario_id)



def atualizar_email_corporativo_usuario(
    usuario_id: int, email: str, *, expected_epoch: int | None = None,
) -> None:
    email = str(email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("Informe um e-mail corporativo válido.")
    try:
        with conectar() as conexao:
            filtro = "" if expected_epoch is None else " AND sessao_epoch=?"
            parametros = [email, int(usuario_id)]
            if expected_epoch is not None:
                parametros.append(int(expected_epoch))
            cursor = conexao.execute(
                "UPDATE usuarios SET email_corporativo=?, sessao_epoch=COALESCE(sessao_epoch,0)+1 WHERE id=?" + filtro,
                tuple(parametros),
            )
            if cursor.rowcount == 0:
                _distinguir_conflito(conexao, usuario_id)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Este e-mail corporativo já está em uso.") from erro


def revogar_sessoes_usuario(usuario_id: int) -> None:
    with conectar() as conexao:
        cursor = conexao.execute(
            "UPDATE usuarios SET sessao_epoch=COALESCE(sessao_epoch,0)+1 WHERE id=?",
            (int(usuario_id),),
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
    *,
    modulo: str | None = None,
    entidade: str | None = None,
    entidade_id: int | None = None,
    dados_antes=None,
    dados_depois=None,
    empresa_id: int | None = None,
    filial_id: int | None = None,
    operacao_id: str | None = None,
) -> None:
    with conectar() as conexao:
        colunas = {
            item["name"] for item in conexao.execute("PRAGMA table_info(auditoria)")
        }
        if {"empresa_id", "operacao_id"}.issubset(colunas):
            if empresa_id is None:
                try:
                    from auth.sessao import SESSAO

                    empresa_id, filial_id = SESSAO.empresa_id, SESSAO.filial_id
                except (ImportError, AttributeError):
                    pass
            conexao.execute(
                """
                INSERT INTO auditoria (
                    usuario_id, alvo_usuario_id, acao, detalhes,
                    empresa_id, filial_id, modulo, entidade, entidade_id,
                    dados_antes, dados_depois, operacao_id,
                    versao_aplicacao, maquina
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usuario_id,
                    alvo_usuario_id,
                    str(acao),
                    detalhes,
                    empresa_id,
                    filial_id,
                    modulo,
                    entidade,
                    entidade_id,
                    json.dumps(dados_antes, ensure_ascii=False, default=str)
                    if dados_antes is not None
                    else None,
                    json.dumps(dados_depois, ensure_ascii=False, default=str)
                    if dados_depois is not None
                    else None,
                    operacao_id or f"AUD-{uuid4().hex[:12].upper()}",
                    VERSAO_INTERFACE,
                    platform.node()[:120],
                ),
            )
        else:
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
