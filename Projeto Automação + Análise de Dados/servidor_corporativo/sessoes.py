"""Sessões bearer curtas, mantidas apenas na memória do servidor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
import threading

from auth.banco import conectar


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


def criar(usuario: dict, empresa_id: int, filial_id: int | None, horas: int = 8) -> SessaoServidor:
    token = secrets.token_urlsafe(40)
    sessao = SessaoServidor(token, dict(usuario), int(empresa_id), int(filial_id) if filial_id is not None else None,
                            datetime.now(timezone.utc) + timedelta(hours=max(1, min(horas, 24))))
    with _LOCK:
        _SESSOES[token] = sessao
    return sessao


def obter(token: str) -> SessaoServidor | None:
    token = str(token or "").strip()
    if not token:
        return None
    with _LOCK:
        sessao = _SESSOES.get(token)
        if sessao is None:
            return None
        if sessao.expira_em <= datetime.now(timezone.utc):
            _SESSOES.pop(token, None)
            return None
    with conectar() as con:
        row = con.execute("SELECT ativo,sessao_epoch,perfil,perfil_acesso,email_corporativo,nome,usuario FROM usuarios WHERE id=?",
                          (int(sessao.usuario["id"]),)).fetchone()
    if row is None or not bool(row["ativo"]) or int(row["sessao_epoch"] or 0) != int(sessao.usuario.get("sessao_epoch", 0) or 0):
        revogar(token)
        return None
    # mantém metadados não sensíveis atualizados.
    sessao.usuario.update({"nome": row["nome"], "usuario": row["usuario"], "perfil": row["perfil"],
                           "perfil_acesso": row["perfil_acesso"] or "analista", "email_corporativo": row["email_corporativo"],
                           "ativo": bool(row["ativo"])})
    return sessao


def revogar(token: str) -> None:
    with _LOCK:
        _SESSOES.pop(str(token or ""), None)


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
    sessao.empresa_id = empresa_id
    sessao.filial_id = filial_norm
    return sessao
