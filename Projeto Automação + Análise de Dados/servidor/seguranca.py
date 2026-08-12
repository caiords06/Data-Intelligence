"""Validação HMAC e proteção contra replay do receptor central."""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
import time

from auth.banco import conectar
from agente_ti.transport import assinatura_requisicao
from enterprise.nos_plataforma import carregar_segredo_no, obter_no_por_identificador

JANELA_SEGUNDOS = 300


def autenticar_agente(agent_id: str, timestamp: str, nonce: str, assinatura: str, corpo: bytes) -> dict:
    no = obter_no_por_identificador(agent_id)
    if no is None or no.get("tipo") != "Agente" or no.get("status") != "Ativo":
        raise PermissionError("Agente desconhecido ou inativo.")
    try:
        instante = int(timestamp)
    except (TypeError, ValueError):
        raise PermissionError("Timestamp do agente inválido.") from None
    if abs(int(time.time()) - instante) > JANELA_SEGUNDOS:
        raise PermissionError("Requisição do agente fora da janela permitida.")
    if len(str(nonce)) < 16 or len(str(nonce)) > 128:
        raise PermissionError("Nonce do agente inválido.")
    esperado = assinatura_requisicao(carregar_segredo_no(no), corpo, str(timestamp), str(nonce))
    if not hmac.compare_digest(esperado, str(assinatura or "")):
        raise PermissionError("Assinatura do agente inválida.")
    with conectar() as conexao:
        conexao.execute(
            "DELETE FROM nonces_agente WHERE usado_em < datetime('now','-1 day')"
        )
        try:
            conexao.execute(
                "INSERT INTO nonces_agente (agent_id,nonce) VALUES (?,?)",
                (agent_id, nonce),
            )
        except sqlite3.IntegrityError:
            raise PermissionError("Requisição do agente já utilizada.") from None
    return no
