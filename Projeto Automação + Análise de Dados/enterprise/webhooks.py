"""Webhooks corporativos HTTPS assinados e entregues pela fila durável."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from auth import banco
from auth.banco import conectar, registrar_auditoria
from core.criptografia import carregar_criptografado, obter_chave_mestra, salvar_criptografado
from enterprise.contexto import obter_escopo_ator


def _chave_webhook() -> bytes:
    return obter_chave_mestra(
        variavel_ambiente="DATA_INTELLIGENCE_WEBHOOK_MASTER_KEY",
        caminho_dpapi=banco.STORAGE_DIR / "segredos" / "webhook_master.dpapi",
        descricao="Data Intelligence webhook master key",
    )


def _contexto(endpoint_id: int) -> bytes:
    return f"data-intelligence:webhook:{int(endpoint_id)}".encode("ascii")


def _validar_url(url: str) -> str:
    texto = str(url or "").strip()
    parsed = urlparse(texto)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("O endpoint deve ser uma URL HTTPS sem credenciais embutidas.")
    if parsed.port not in {None, 443}:
        raise ValueError("Webhooks externos devem usar a porta HTTPS padrão (443).")
    try:
        enderecos = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError("O host do webhook não pôde ser resolvido.") from exc
    if not enderecos:
        raise ValueError("O host do webhook não possui endereço válido.")
    for endereco in enderecos:
        ip = ipaddress.ip_address(endereco)
        if not ip.is_global:
            raise ValueError("O endpoint não pode apontar para rede local, reservada ou loopback.")
    return texto


def cadastrar_endpoint(nome: str, url: str, eventos: list[str], ator: dict) -> dict:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("O cadastro de webhooks exige administrador.")
    empresa_id, _ = obter_escopo_ator(ator)
    nome_norm = str(nome or "").strip()
    if len(nome_norm) < 2 or len(nome_norm) > 100:
        raise ValueError("O nome do webhook deve possuir entre 2 e 100 caracteres.")
    eventos_norm = sorted({str(x).strip()[:120] for x in eventos if str(x).strip()})
    if not eventos_norm:
        raise ValueError("Informe ao menos um tipo de evento ou '*'.")
    url_norm = _validar_url(url)
    segredo = secrets.token_urlsafe(40)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO webhook_endpoints
               (empresa_id,nome,url,eventos_json,segredo_ref,criado_por)
               VALUES (?,?,?,?,?,?)""",
            (int(empresa_id), nome_norm, url_norm, json.dumps(eventos_norm), "pendente", int(ator["id"])),
        )
        endpoint_id = int(cursor.lastrowid)
        referencia = f"segredos_webhook/endpoint_{endpoint_id}.key.enc"
        con.execute("UPDATE webhook_endpoints SET segredo_ref=? WHERE id=?", (referencia, endpoint_id))
    try:
        salvar_criptografado(
            banco.STORAGE_DIR / referencia, segredo.encode("utf-8"), _chave_webhook(),
            contexto=_contexto(endpoint_id),
        )
    except Exception:
        with conectar() as con:
            con.execute("DELETE FROM webhook_endpoints WHERE id=?", (endpoint_id,))
        raise
    registrar_auditoria("webhook_cadastrado", usuario_id=int(ator["id"]), detalhes=f"endpoint_id={endpoint_id}")
    return {"id": endpoint_id, "nome": nome_norm, "url": url_norm, "eventos": eventos_norm, "segredo": segredo}


def listar_endpoints(ator: dict) -> list[dict]:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("A administração de webhooks exige administrador.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as con:
        rows = con.execute(
            """SELECT id,nome,url,eventos_json,ativo,criado_em FROM webhook_endpoints
               WHERE empresa_id=? ORDER BY id DESC""",
            (int(empresa_id),),
        ).fetchall()
    return [{**dict(row), "eventos": json.loads(row["eventos_json"] or "[]")} for row in rows]


def publicar_evento(tipo: str, dados: dict, ator: dict, *, evento_id: str | None = None) -> dict:
    tipo_norm = str(tipo or "").strip()[:120]
    if not tipo_norm:
        raise ValueError("Tipo de evento obrigatório.")
    empresa_id, _ = obter_escopo_ator(ator)
    evento = str(evento_id or f"evt_{uuid4().hex}")[:120]
    with conectar() as con:
        endpoints = con.execute(
            "SELECT id,eventos_json FROM webhook_endpoints WHERE empresa_id=? AND ativo=1",
            (int(empresa_id),),
        ).fetchall()
    entregas: list[int] = []
    from enterprise.automacao_motor import enfileirar
    for endpoint in endpoints:
        assinaturas = set(json.loads(endpoint["eventos_json"] or "[]"))
        if "*" not in assinaturas and tipo_norm not in assinaturas:
            continue
        with conectar() as con:
            try:
                cursor = con.execute(
                    """INSERT INTO webhook_entregas(endpoint_id,evento_id,evento_tipo)
                       VALUES (?,?,?)""",
                    (int(endpoint["id"]), evento, tipo_norm),
                )
                entrega_id = int(cursor.lastrowid)
            except Exception:
                existente = con.execute(
                    "SELECT id FROM webhook_entregas WHERE endpoint_id=? AND evento_id=?",
                    (int(endpoint["id"]), evento),
                ).fetchone()
                if existente is None:
                    raise
                entrega_id = int(existente["id"])
        enfileirar(
            "webhook.entregar", f"Webhook {tipo_norm}",
            {"entrega_id": entrega_id, "evento_id": evento, "tipo": tipo_norm, "dados": dict(dados or {})},
            ator, idempotency_key=f"webhook:{int(endpoint['id'])}:{evento}", max_tentativas=6,
        )
        entregas.append(entrega_id)
    return {"evento_id": evento, "entregas": entregas}


class _SemRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def entregar(entrega_id: int, payload: dict) -> dict:
    with conectar() as con:
        row = con.execute(
            """SELECT e.id,e.endpoint_id,e.evento_id,e.evento_tipo,e.tentativa,
                      w.url,w.segredo_ref,w.ativo
               FROM webhook_entregas e JOIN webhook_endpoints w ON w.id=e.endpoint_id
               WHERE e.id=?""",
            (int(entrega_id),),
        ).fetchone()
    if row is None or not bool(row["ativo"]):
        raise ValueError("Entrega ou endpoint de webhook indisponível.")
    url = _validar_url(str(row["url"]))  # Revalida DNS em toda tentativa contra DNS rebinding.
    referencia = (banco.STORAGE_DIR / str(row["segredo_ref"])).resolve()
    if banco.STORAGE_DIR.resolve() not in referencia.parents:
        raise PermissionError("Referência de segredo do webhook inválida.")
    segredo = carregar_criptografado(referencia, _chave_webhook(), contexto=_contexto(int(row["endpoint_id"])))
    corpo = json.dumps(
        {"id": row["evento_id"], "tipo": row["evento_tipo"], "criado_em": datetime.now(timezone.utc).isoformat(), "dados": payload},
        ensure_ascii=False, separators=(",", ":"), default=str,
    ).encode("utf-8")
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    assinatura = hmac.new(segredo, timestamp.encode("ascii") + b"." + corpo, hashlib.sha256).hexdigest()
    request = Request(
        url, data=corpo, method="POST",
        headers={
            "Content-Type": "application/json", "User-Agent": "Data-Intelligence-Webhooks/1.0",
            "X-DI-Event": str(row["evento_tipo"]), "X-DI-Delivery": str(row["evento_id"]),
            "X-DI-Timestamp": timestamp, "X-DI-Signature": f"sha256={assinatura}",
        },
    )
    status = 0
    resumo = ""
    try:
        with build_opener(_SemRedirect).open(request, timeout=15) as resposta:
            status = int(resposta.status)
            resumo = resposta.read(1024).decode("utf-8", errors="replace")
        if status < 200 or status >= 300:
            raise RuntimeError(f"Webhook respondeu HTTP {status}.")
    except HTTPError as exc:
        status = int(exc.code)
        resumo = exc.read(1024).decode("utf-8", errors="replace")
        raise RuntimeError(f"Webhook respondeu HTTP {status}.") from exc
    except URLError as exc:
        resumo = str(exc.reason)[:1000]
        raise RuntimeError("Falha de transporte do webhook.") from exc
    finally:
        with conectar() as con:
            con.execute(
                """UPDATE webhook_entregas SET tentativa=tentativa+1,status=?,status_http=?,
                   resposta_resumo=?,concluido_em=? WHERE id=?""",
                (
                    "Entregue" if 200 <= status < 300 else "Falhou", status or None, resumo[:1000],
                    datetime.now(timezone.utc).isoformat(timespec="seconds") if 200 <= status < 300 else None,
                    int(entrega_id),
                ),
            )
    return {"entrega_id": int(entrega_id), "status_http": status}


__all__ = ("cadastrar_endpoint", "entregar", "listar_endpoints", "publicar_evento")
