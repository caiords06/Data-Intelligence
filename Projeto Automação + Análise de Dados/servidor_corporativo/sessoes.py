"""Sessões bearer persistentes, compartilháveis e revogáveis."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import sqlite3
import threading

from auth.banco import conectar


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: datetime) -> str:
    return valor.astimezone(timezone.utc).isoformat(timespec="seconds")


def _data(valor) -> datetime:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    texto = str(valor or "").strip().replace(" ", "T", 1)
    instante = datetime.fromisoformat(texto)
    return instante if instante.tzinfo else instante.replace(tzinfo=timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


@dataclass(slots=True)
class SessaoServidor:
    token: str
    usuario: dict
    empresa_id: int
    filial_id: int | None
    expira_em: datetime

    def ator(self) -> dict:
        return {**self.usuario, "_empresa_id": self.empresa_id, "_filial_id": self.filial_id}


_LOCK = threading.RLock()
_SESSOES: dict[str, SessaoServidor] = {}


def _limpar_expiradas(conexao, agora: datetime) -> None:
    conexao.execute(
        "DELETE FROM sessoes_servidor WHERE expira_em<? OR (revogado_em IS NOT NULL AND revogado_em<?)",
        (_iso(agora), _iso(agora - timedelta(days=7))),
    )


def criar(
    usuario: dict,
    empresa_id: int,
    filial_id: int | None,
    horas: int = 8,
    *,
    ip_hash: str | None = None,
    cliente: str | None = None,
) -> SessaoServidor:
    token = secrets.token_urlsafe(48)
    agora = _agora()
    expira = agora + timedelta(hours=max(1, min(int(horas), 24)))
    sessao = SessaoServidor(
        token, dict(usuario), int(empresa_id),
        int(filial_id) if filial_id is not None else None, expira,
    )
    with conectar() as conexao:
        _limpar_expiradas(conexao, agora)
        conexao.execute(
            """INSERT INTO sessoes_servidor
               (token_hash,usuario_id,empresa_id,filial_id,sessao_epoch,criado_em,
                ultima_atividade_em,expira_em,ip_hash,cliente)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                _hash_token(token), int(usuario["id"]), int(empresa_id), sessao.filial_id,
                int(usuario.get("sessao_epoch", 0) or 0), _iso(agora), _iso(agora),
                _iso(expira), str(ip_hash or "")[:128] or None,
                str(cliente or "")[:240] or None,
            ),
        )
    with _LOCK:
        _SESSOES[token] = sessao
    return sessao


def _carregar_persistida(token: str) -> SessaoServidor | None:
    try:
        with conectar() as con:
            row = con.execute(
                """SELECT s.usuario_id,s.empresa_id,s.filial_id,s.sessao_epoch,s.expira_em,s.revogado_em,
                          u.nome,u.usuario,u.perfil,u.perfil_acesso,u.email_corporativo,u.ativo,
                          u.sessao_epoch AS usuario_epoch,u.mfa_habilitado
                   FROM sessoes_servidor s JOIN usuarios u ON u.id=s.usuario_id
                   WHERE s.token_hash=?""",
                (_hash_token(token),),
            ).fetchone()
    except sqlite3.OperationalError as exc:
        # Compatibilidade com health/tests que sobem somente o handler, sem o
        # bootstrap do servidor. Na execução real, readiness valida a migration.
        if "sessoes_servidor" not in str(exc):
            raise
        return None
    if row is None or row["revogado_em"] is not None:
        return None
    expira = _data(row["expira_em"])
    if expira <= _agora() or not bool(row["ativo"]):
        revogar(token)
        return None
    if int(row["sessao_epoch"] or 0) != int(row["usuario_epoch"] or 0):
        revogar(token)
        return None
    usuario = {
        "id": int(row["usuario_id"]), "nome": row["nome"], "usuario": row["usuario"],
        "perfil": row["perfil"], "perfil_acesso": row["perfil_acesso"] or "analista",
        "email_corporativo": row["email_corporativo"], "ativo": True,
        "sessao_epoch": int(row["usuario_epoch"] or 0),
        "mfa_habilitado": bool(row["mfa_habilitado"]),
    }
    return SessaoServidor(
        token, usuario, int(row["empresa_id"]),
        int(row["filial_id"]) if row["filial_id"] is not None else None, expira,
    )


def obter(token: str) -> SessaoServidor | None:
    token = str(token or "").strip()
    if not token:
        return None
    with _LOCK:
        sessao = _SESSOES.get(token)
    if sessao is None:
        sessao = _carregar_persistida(token)
        if sessao is None:
            return None
        with _LOCK:
            _SESSOES[token] = sessao
    if sessao.expira_em <= _agora():
        revogar(token)
        return None

    with conectar() as con:
        row = con.execute(
            "SELECT ativo,sessao_epoch,perfil,perfil_acesso,email_corporativo,nome,usuario,mfa_habilitado FROM usuarios WHERE id=?",
            (int(sessao.usuario["id"]),),
        ).fetchone()
        if row is None or not bool(row["ativo"]) or int(row["sessao_epoch"] or 0) != int(sessao.usuario.get("sessao_epoch", 0) or 0):
            row = None
        else:
            con.execute(
                "UPDATE sessoes_servidor SET ultima_atividade_em=? WHERE token_hash=? AND revogado_em IS NULL",
                (_iso(_agora()), _hash_token(token)),
            )
    if row is None:
        revogar(token)
        return None
    sessao.usuario.update({
        "nome": row["nome"], "usuario": row["usuario"], "perfil": row["perfil"],
        "perfil_acesso": row["perfil_acesso"] or "analista",
        "email_corporativo": row["email_corporativo"], "ativo": True,
        "mfa_habilitado": bool(row["mfa_habilitado"]),
    })
    return sessao


def revogar(token: str) -> None:
    bruto = str(token or "").strip()
    if not bruto:
        return
    with _LOCK:
        _SESSOES.pop(bruto, None)
    with conectar() as con:
        con.execute(
            "UPDATE sessoes_servidor SET revogado_em=? WHERE token_hash=? AND revogado_em IS NULL",
            (_iso(_agora()), _hash_token(bruto)),
        )


def revogar_usuario(usuario_id: int, *, exceto_token: str | None = None) -> int:
    parametros: list = [_iso(_agora()), int(usuario_id)]
    filtro = ""
    if exceto_token:
        filtro = " AND token_hash<>?"
        parametros.append(_hash_token(exceto_token))
    with conectar() as con:
        cursor = con.execute(
            f"UPDATE sessoes_servidor SET revogado_em=? WHERE usuario_id=? AND revogado_em IS NULL{filtro}",
            tuple(parametros),
        )
    with _LOCK:
        for token, sessao in list(_SESSOES.items()):
            if int(sessao.usuario["id"]) == int(usuario_id) and token != exceto_token:
                _SESSOES.pop(token, None)
    return max(0, int(cursor.rowcount or 0))


def listar_usuario(usuario_id: int) -> list[dict]:
    with conectar() as con:
        rows = con.execute(
            """SELECT token_hash,criado_em,ultima_atividade_em,expira_em,revogado_em,
                      empresa_id,filial_id,ip_hash,cliente
               FROM sessoes_servidor WHERE usuario_id=? ORDER BY criado_em DESC LIMIT 100""",
            (int(usuario_id),),
        ).fetchall()
    return [
        {
            **dict(row),
            "id_sessao": str(row["token_hash"])[:16],
            "token_hash": None,
        }
        for row in rows
    ]


def alterar_contexto(sessao: SessaoServidor, empresa_id: int, filial_id: int | None) -> SessaoServidor:
    """Altera o escopo do bearer após validar empresa/filial do usuário."""
    uid = int(sessao.usuario["id"])
    empresa_id = int(empresa_id)
    filial_norm = int(filial_id) if filial_id is not None else None
    with conectar() as con:
        empresa = con.execute("SELECT id FROM empresas WHERE id=? AND ativo=1", (empresa_id,)).fetchone()
        if empresa is None:
            raise ValueError("Empresa inexistente ou inativa.")
        if str(sessao.usuario.get("perfil", "")).lower() != "admin":
            vinculo = con.execute(
                "SELECT filial_id FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
                (uid, empresa_id),
            ).fetchone()
            if vinculo is None:
                raise PermissionError("O usuário não possui acesso à empresa selecionada.")
            restrita = vinculo["filial_id"]
            if restrita is not None:
                if filial_norm is None or int(restrita) != filial_norm:
                    raise PermissionError("O usuário não possui acesso à filial selecionada.")
                filial_norm = int(restrita)
        if filial_norm is not None:
            filial = con.execute(
                "SELECT id FROM filiais WHERE id=? AND empresa_id=? AND ativo=1",
                (filial_norm, empresa_id),
            ).fetchone()
            if filial is None:
                raise ValueError("A filial não pertence à empresa selecionada.")
        con.execute(
            "UPDATE sessoes_servidor SET empresa_id=?,filial_id=?,ultima_atividade_em=? WHERE token_hash=? AND revogado_em IS NULL",
            (empresa_id, filial_norm, _iso(_agora()), _hash_token(sessao.token)),
        )
    sessao.empresa_id = empresa_id
    sessao.filial_id = filial_norm
    return sessao


__all__ = (
    "SessaoServidor", "alterar_contexto", "criar", "listar_usuario", "obter",
    "revogar", "revogar_usuario",
)
