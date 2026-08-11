"""Autenticação HMAC e proteção contra replay do agente TI."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import re
import sqlite3
import time
from typing import Mapping

from auth.banco import conectar

TOLERANCIA_SEGUNDOS = 300
NONCE_RE = re.compile(r"^[0-9a-fA-F]{32,128}$")
AGENT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,160}$")


class AgentAuthError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class AgenteAutenticado:
    id: int
    empresa_id: int
    filial_id: int | None
    ativo_id: int
    agent_id: str
    patrimonio: str
    criado_por: int


def _header(headers: Mapping[str, str], nome: str) -> str:
    for chave, valor in headers.items():
        if str(chave).lower() == nome.lower():
            return str(valor or "").strip()
    return ""


def _assinatura_com_hash(token_hash: str, corpo: bytes, timestamp: str, nonce: str) -> str:
    try:
        chave = bytes.fromhex(token_hash)
    except ValueError as erro:
        raise AgentAuthError("Credencial do agente inválida.") from erro
    resumo = hashlib.sha256(corpo).hexdigest()
    mensagem = f"{timestamp}\n{nonce}\n{resumo}".encode("utf-8")
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()


def autenticar(headers: Mapping[str, str], corpo: bytes, *, agora: int | None = None) -> AgenteAutenticado:
    agent_id = _header(headers, "X-Agent-ID")
    timestamp = _header(headers, "X-Agent-Timestamp")
    nonce = _header(headers, "X-Agent-Nonce")
    assinatura = _header(headers, "X-Agent-Signature")
    if not AGENT_ID_RE.fullmatch(agent_id):
        raise AgentAuthError("Identidade do agente inválida.")
    try:
        instante = int(timestamp)
    except (TypeError, ValueError):
        raise AgentAuthError("Timestamp do agente inválido.") from None
    atual = int(time.time() if agora is None else agora)
    if abs(atual - instante) > TOLERANCIA_SEGUNDOS:
        raise AgentAuthError("Heartbeat fora da janela de tempo permitida.")
    if not NONCE_RE.fullmatch(nonce):
        raise AgentAuthError("Nonce do agente inválido.")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", assinatura):
        raise AgentAuthError("Assinatura do agente inválida.")

    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT g.id,g.empresa_id,g.filial_id,g.ativo_id,g.agent_id,g.token_hash,g.patrimonio,g.criado_por
               FROM ti_agentes g JOIN ti_ativos a ON a.id=g.ativo_id
               WHERE g.agent_id=? AND g.ativo=1 AND g.status!='Revogado' AND a.ativo=1""",
            (agent_id,),
        ).fetchone()
        if linha is None:
            raise AgentAuthError("Agente não autorizado.")
        esperada = _assinatura_com_hash(str(linha["token_hash"]), corpo, timestamp, nonce)
        if not hmac.compare_digest(esperada, assinatura.lower()):
            raise AgentAuthError("Assinatura do agente inválida.")
        conexao.execute("DELETE FROM ti_agente_nonces WHERE recebido_em < ?", (atual - (TOLERANCIA_SEGUNDOS * 2),))
        try:
            conexao.execute(
                "INSERT INTO ti_agente_nonces (agente_id,nonce,recebido_em) VALUES (?,?,?)",
                (int(linha["id"]), nonce.lower(), atual),
            )
        except sqlite3.IntegrityError:
            raise AgentAuthError("Heartbeat repetido recusado.") from None
        return AgenteAutenticado(
            id=int(linha["id"]),
            empresa_id=int(linha["empresa_id"]),
            filial_id=int(linha["filial_id"]) if linha["filial_id"] is not None else None,
            ativo_id=int(linha["ativo_id"]),
            agent_id=str(linha["agent_id"]),
            patrimonio=str(linha["patrimonio"]),
            criado_por=int(linha["criado_por"]),
        )
