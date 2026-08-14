"""Rate limit compartilhado e idempotência persistente da API HTTP."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import time
from typing import Callable

from auth.banco import conectar


class RateLimitExcedido(PermissionError):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, int(retry_after))
        super().__init__("Limite de requisições excedido. Tente novamente em instantes.")


class IdempotenciaEmProcessamento(RuntimeError):
    pass


def verificar_limite(chave: str, *, limite: int, janela_segundos: int) -> None:
    agora = int(time.time())
    janela = max(1, int(janela_segundos))
    inicio = agora - (agora % janela)
    chave_hash = hashlib.sha256(str(chave).encode("utf-8")).hexdigest()
    with conectar() as con:
        con.execute("DELETE FROM api_rate_limits WHERE expira_em<?", (agora,))
        row = con.execute(
            """INSERT INTO api_rate_limits(chave_hash,janela_inicio,contador,expira_em)
               VALUES (?,?,1,?)
               ON CONFLICT(chave_hash,janela_inicio) DO UPDATE SET contador=api_rate_limits.contador+1
               RETURNING contador""",
            (chave_hash, inicio, inicio + janela * 2),
        ).fetchone()
    if int(row["contador"] if hasattr(row, "keys") else row[0]) > max(1, int(limite)):
        raise RateLimitExcedido(inicio + janela - agora)


def _idempotencia_hash(usuario_id: int, metodo: str, caminho: str, chave: str) -> str:
    return hashlib.sha256(
        f"{int(usuario_id)}\x00{metodo.upper()}\x00{caminho}\x00{chave}".encode("utf-8")
    ).hexdigest()


def executar_idempotente(
    *,
    usuario_id: int,
    metodo: str,
    caminho: str,
    chave: str,
    dados: dict,
    executar: Callable[[], tuple[int, dict] | None],
) -> tuple[int, dict, bool] | None:
    chave = str(chave or "").strip()
    if not chave:
        resultado = executar()
        return (*resultado, False) if resultado is not None else None
    if not 8 <= len(chave) <= 200:
        raise ValueError("Idempotency-Key deve possuir entre 8 e 200 caracteres.")
    req_hash = hashlib.sha256(
        json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    chave_hash = _idempotencia_hash(usuario_id, metodo, caminho, chave)
    expira = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(timespec="seconds")
    reservado = False
    with conectar() as con:
        con.execute("DELETE FROM api_idempotencia WHERE expira_em<?", (datetime.now(timezone.utc).isoformat(timespec="seconds"),))
        row = con.execute("SELECT * FROM api_idempotencia WHERE chave_hash=?", (chave_hash,)).fetchone()
        if row is None:
            cursor = con.execute(
                """INSERT INTO api_idempotencia
                   (chave_hash,usuario_id,metodo,caminho,requisicao_hash,expira_em)
                   VALUES (?,?,?,?,?,?) ON CONFLICT(chave_hash) DO NOTHING""",
                (chave_hash, int(usuario_id), metodo.upper(), caminho, req_hash, expira),
            )
            reservado = cursor.rowcount == 1
            if not reservado:
                row = con.execute("SELECT * FROM api_idempotencia WHERE chave_hash=?", (chave_hash,)).fetchone()
        if not reservado:
            if row is None:
                raise IdempotenciaEmProcessamento("Não foi possível reservar a chave de idempotência.")
            if str(row["requisicao_hash"]) != req_hash:
                raise ValueError("A mesma Idempotency-Key foi reutilizada com outro payload.")
            if row["resposta_json"] is None:
                raise IdempotenciaEmProcessamento("Uma requisição com esta Idempotency-Key ainda está em processamento.")
            return int(row["status_http"]), json.loads(row["resposta_json"]), True
    try:
        resultado = executar()
        if resultado is None:
            with conectar() as con:
                con.execute("DELETE FROM api_idempotencia WHERE chave_hash=?", (chave_hash,))
            return None
        status, payload = resultado
        with conectar() as con:
            con.execute(
                "UPDATE api_idempotencia SET status_http=?,resposta_json=? WHERE chave_hash=?",
                (int(status), json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), chave_hash),
            )
        return int(status), payload, False
    except Exception:
        if reservado:
            with conectar() as con:
                con.execute("DELETE FROM api_idempotencia WHERE chave_hash=?", (chave_hash,))
        raise


__all__ = ("IdempotenciaEmProcessamento", "RateLimitExcedido", "executar_idempotente", "verificar_limite")
