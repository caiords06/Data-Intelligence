"""Autenticação multifator TOTP (RFC 6238) com segredo fora do SQLite."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from pathlib import Path
from urllib.parse import quote

from auth import banco
from auth.banco import conectar, registrar_auditoria


def _codigo(secret: str, instante: int) -> str:
    chave = base64.b32decode(secret.upper() + "=" * ((8 - len(secret) % 8) % 8))
    contador = instante // 30
    digest = hmac.new(chave, struct.pack(">Q", contador), hashlib.sha1).digest()
    deslocamento = digest[-1] & 0x0F
    numero = (struct.unpack(">I", digest[deslocamento:deslocamento + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{numero:06d}"


def verificar_totp(secret: str, codigo: str, *, agora: int | None = None) -> bool:
    recebido = "".join(x for x in str(codigo or "") if x.isdigit())
    if len(recebido) != 6:
        return False
    base = int(agora if agora is not None else time.time())
    return any(hmac.compare_digest(recebido, _codigo(secret, base + janela * 30)) for janela in (-1, 0, 1))


def _resolver(referencia: str) -> Path:
    caminho = (banco.STORAGE_DIR / str(referencia)).resolve()
    if banco.STORAGE_DIR.resolve() not in caminho.parents:
        raise PermissionError("Referência MFA inválida.")
    return caminho


def carregar_segredo(usuario_id: int) -> str | None:
    with conectar() as conexao:
        usuario = conexao.execute("SELECT mfa_habilitado,mfa_secret_ref FROM usuarios WHERE id=?", (int(usuario_id),)).fetchone()
    if usuario is None or not bool(usuario["mfa_habilitado"]):
        return None
    caminho = _resolver(usuario["mfa_secret_ref"] or "")
    if not caminho.is_file():
        raise PermissionError("O segredo MFA não está disponível.")
    return caminho.read_text(encoding="ascii").strip()


def habilitar_mfa(usuario_id: int, ator: dict) -> dict:
    if int(usuario_id) != int(ator.get("id") or 0) and str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Você só pode configurar o próprio MFA.")
    secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
    pasta = banco.STORAGE_DIR / "segredos_mfa"; pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"usuario_{int(usuario_id)}.key"
    temporario = caminho.with_suffix(".tmp"); temporario.write_text(secret, encoding="ascii")
    os.replace(temporario, caminho)
    try: os.chmod(caminho, 0o600)
    except OSError: pass
    referencia = caminho.relative_to(banco.STORAGE_DIR).as_posix()
    with conectar() as conexao:
        usuario = conexao.execute("SELECT usuario,email_corporativo FROM usuarios WHERE id=?", (int(usuario_id),)).fetchone()
        if usuario is None: raise ValueError("Usuário não encontrado.")
        conexao.execute("UPDATE usuarios SET mfa_habilitado=1,mfa_secret_ref=?,sessao_epoch=sessao_epoch+1 WHERE id=?", (referencia, int(usuario_id)))
    conta = usuario["email_corporativo"] or usuario["usuario"]
    uri = f"otpauth://totp/{quote('Data Intelligence')}:{quote(conta)}?secret={secret}&issuer={quote('Data Intelligence')}&digits=6&period=30"
    registrar_auditoria("mfa_habilitado", usuario_id=int(ator["id"]), alvo_usuario_id=int(usuario_id))
    return {"secret": secret, "uri": uri}


def desabilitar_mfa(usuario_id: int, ator: dict, codigo: str | None = None) -> None:
    if int(usuario_id) != int(ator.get("id") or 0) and str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Você só pode configurar o próprio MFA.")
    if int(usuario_id) == int(ator.get("id") or 0):
        segredo = carregar_segredo(int(usuario_id))
        if segredo and not verificar_totp(segredo, str(codigo or "")):
            raise ValueError("Confirme um código MFA válido para desabilitar a proteção.")
    with conectar() as conexao:
        usuario = conexao.execute("SELECT mfa_secret_ref FROM usuarios WHERE id=?", (int(usuario_id),)).fetchone()
        if usuario is None: raise ValueError("Usuário não encontrado.")
        conexao.execute("UPDATE usuarios SET mfa_habilitado=0,mfa_secret_ref=NULL,sessao_epoch=sessao_epoch+1 WHERE id=?", (int(usuario_id),))
    if usuario["mfa_secret_ref"]:
        _resolver(usuario["mfa_secret_ref"]).unlink(missing_ok=True)
    registrar_auditoria("mfa_desabilitado", usuario_id=int(ator["id"]), alvo_usuario_id=int(usuario_id))
