"""MFA TOTP obrigatório, recuperação segura e segredos cifrados."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from pathlib import Path
from urllib.parse import quote

from auth import banco
from auth.banco import conectar, registrar_auditoria
from core.criptografia import carregar_criptografado, obter_chave_mestra, salvar_criptografado


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
    return any(
        hmac.compare_digest(recebido, _codigo(secret, base + janela * 30))
        for janela in (-1, 0, 1)
    )


def _passo_totp_valido(secret: str, codigo: str, *, agora: int | None = None) -> int | None:
    recebido = "".join(x for x in str(codigo or "") if x.isdigit())
    if len(recebido) != 6:
        return None
    base = int(agora if agora is not None else time.time())
    for janela in (-1, 0, 1):
        instante = base + janela * 30
        if hmac.compare_digest(recebido, _codigo(secret, instante)):
            return instante // 30
    return None


def _resolver(referencia: str) -> Path:
    caminho = (banco.STORAGE_DIR / str(referencia)).resolve()
    if banco.STORAGE_DIR.resolve() not in caminho.parents:
        raise PermissionError("Referência MFA inválida.")
    return caminho


def _chave_mfa() -> bytes:
    return obter_chave_mestra(
        variavel_ambiente="DATA_INTELLIGENCE_MFA_MASTER_KEY",
        caminho_dpapi=banco.STORAGE_DIR / "segredos" / "mfa_master.dpapi",
        descricao="Data Intelligence MFA master key",
    )


def _contexto(usuario_id: int) -> bytes:
    return f"data-intelligence:mfa:{int(usuario_id)}".encode("ascii")


def _salvar_segredo(usuario_id: int, secret: str) -> str:
    caminho = banco.STORAGE_DIR / "segredos_mfa" / f"usuario_{int(usuario_id)}.key.enc"
    salvar_criptografado(
        caminho, secret.encode("ascii"), _chave_mfa(), contexto=_contexto(usuario_id),
    )
    return caminho.relative_to(banco.STORAGE_DIR).as_posix()


def _ler_segredo(usuario_id: int, referencia: str) -> str:
    caminho = _resolver(referencia)
    if not caminho.is_file():
        raise PermissionError("O segredo MFA não está disponível.")
    if caminho.suffix == ".enc":
        return carregar_criptografado(
            caminho, _chave_mfa(), contexto=_contexto(usuario_id),
        ).decode("ascii")

    # Migra uma única vez instalações que ainda guardavam Base32 puro.
    secret = caminho.read_text(encoding="ascii").strip()
    nova_ref = _salvar_segredo(usuario_id, secret)
    with conectar() as conexao:
        conexao.execute(
            "UPDATE usuarios SET mfa_secret_ref=? WHERE id=? AND mfa_secret_ref=?",
            (nova_ref, int(usuario_id), referencia),
        )
    caminho.unlink(missing_ok=True)
    registrar_auditoria("mfa_segredo_migrado", alvo_usuario_id=int(usuario_id))
    return secret


def carregar_segredo(usuario_id: int, *, permitir_pendente: bool = False) -> str | None:
    _garantir_execucao_servidor()
    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT mfa_habilitado,mfa_pendente,mfa_secret_ref FROM usuarios WHERE id=?",
            (int(usuario_id),),
        ).fetchone()
    if usuario is None:
        return None
    if not bool(usuario["mfa_habilitado"]) and not (
        permitir_pendente and bool(usuario["mfa_pendente"])
    ):
        return None
    referencia = str(usuario["mfa_secret_ref"] or "")
    if not referencia:
        raise PermissionError("A conta exige MFA, mas o segredo protegido está ausente.")
    return _ler_segredo(int(usuario_id), referencia)


def _garantir_execucao_servidor() -> None:
    try:
        from core.nodo import usa_servidor_remoto
        remoto = usa_servidor_remoto()
    except ValueError:
        remoto = False
    if remoto:
        raise RuntimeError(
            "MFA deve ser configurado no Servidor Corporativo; a estação não pode persistir segredo local."
        )


def _autorizar_configuracao(usuario_id: int, ator: dict) -> None:
    if int(usuario_id) != int(ator.get("id") or 0) and str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Você só pode configurar o próprio MFA.")


def preparar_mfa(usuario_id: int, ator: dict) -> dict:
    """Cria segredo pendente; a proteção só ativa após confirmação."""
    _garantir_execucao_servidor()
    _autorizar_configuracao(usuario_id, ator)
    secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
    referencia = _salvar_segredo(int(usuario_id), secret)
    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT usuario,email_corporativo,mfa_secret_ref FROM usuarios WHERE id=?",
            (int(usuario_id),),
        ).fetchone()
        if usuario is None:
            _resolver(referencia).unlink(missing_ok=True)
            raise ValueError("Usuário não encontrado.")
        referencia_anterior = str(usuario["mfa_secret_ref"] or "")
        conexao.execute(
            "UPDATE usuarios SET mfa_habilitado=0,mfa_pendente=1,mfa_secret_ref=?,mfa_ultimo_passo=NULL WHERE id=?",
            (referencia, int(usuario_id)),
        )
        conexao.execute("DELETE FROM mfa_codigos_recuperacao WHERE usuario_id=?", (int(usuario_id),))
    if referencia_anterior and referencia_anterior != referencia:
        _resolver(referencia_anterior).unlink(missing_ok=True)
    conta = usuario["email_corporativo"] or usuario["usuario"]
    uri = (
        f"otpauth://totp/{quote('Data Intelligence')}:{quote(conta)}?"
        f"secret={secret}&issuer={quote('Data Intelligence')}&digits=6&period=30"
    )
    registrar_auditoria("mfa_configuracao_iniciada", usuario_id=int(ator["id"]), alvo_usuario_id=int(usuario_id))
    return {"secret": secret, "uri": uri, "confirmacao_necessaria": True}


def _normalizar_recuperacao(codigo: str) -> str:
    return "".join(x for x in str(codigo or "").upper() if x.isalnum())


def _hash_recuperacao(codigo: str, salt: bytes) -> str:
    return hashlib.scrypt(
        _normalizar_recuperacao(codigo).encode("ascii"), salt=salt,
        n=2**14, r=8, p=1, dklen=32,
    ).hex()


def _gerar_codigos_recuperacao(usuario_id: int, quantidade: int = 10) -> list[str]:
    codigos: list[str] = []
    with conectar() as conexao:
        conexao.execute("DELETE FROM mfa_codigos_recuperacao WHERE usuario_id=?", (int(usuario_id),))
        for _ in range(max(5, min(int(quantidade), 20))):
            bruto = base64.b32encode(secrets.token_bytes(8)).decode("ascii").rstrip("=")[:12]
            codigo = f"{bruto[:4]}-{bruto[4:8]}-{bruto[8:12]}"
            salt = secrets.token_bytes(16)
            conexao.execute(
                "INSERT INTO mfa_codigos_recuperacao(usuario_id,salt,codigo_hash) VALUES (?,?,?)",
                (int(usuario_id), salt.hex(), _hash_recuperacao(codigo, salt)),
            )
            codigos.append(codigo)
    return codigos


def confirmar_mfa(usuario_id: int, codigo: str, ator: dict) -> dict:
    _garantir_execucao_servidor()
    _autorizar_configuracao(usuario_id, ator)
    segredo = carregar_segredo(int(usuario_id), permitir_pendente=True)
    passo = _passo_totp_valido(segredo, codigo) if segredo else None
    if passo is None:
        raise ValueError("Código MFA inválido; a configuração não foi ativada.")
    with conectar() as conexao:
        cursor = conexao.execute(
            """UPDATE usuarios SET mfa_habilitado=1,mfa_pendente=0,
               mfa_confirmado_em=CURRENT_TIMESTAMP,mfa_ultimo_passo=?,
               sessao_epoch=COALESCE(sessao_epoch,0)+1 WHERE id=? AND mfa_pendente=1""",
            (int(passo), int(usuario_id)),
        )
        if cursor.rowcount == 0:
            raise ValueError("Não existe configuração MFA pendente para confirmar.")
    codigos = _gerar_codigos_recuperacao(int(usuario_id))
    registrar_auditoria("mfa_habilitado", usuario_id=int(ator["id"]), alvo_usuario_id=int(usuario_id))
    return {"habilitado": True, "codigos_recuperacao": codigos, "relogin_necessario": True}


def habilitar_mfa(usuario_id: int, ator: dict) -> dict:
    """Compatibilidade: inicia o fluxo e exige ``confirmar_mfa``."""
    return preparar_mfa(usuario_id, ator)


def _usar_codigo_recuperacao(usuario_id: int, codigo: str) -> bool:
    normalizado = _normalizar_recuperacao(codigo)
    if len(normalizado) != 12:
        return False
    with conectar() as conexao:
        linhas = conexao.execute(
            "SELECT id,salt,codigo_hash FROM mfa_codigos_recuperacao WHERE usuario_id=? AND usado_em IS NULL",
            (int(usuario_id),),
        ).fetchall()
        for linha in linhas:
            salt = bytes.fromhex(str(linha["salt"]))
            if hmac.compare_digest(_hash_recuperacao(normalizado, salt), str(linha["codigo_hash"])):
                cursor = conexao.execute(
                    "UPDATE mfa_codigos_recuperacao SET usado_em=CURRENT_TIMESTAMP WHERE id=? AND usado_em IS NULL",
                    (int(linha["id"]),),
                )
                return cursor.rowcount == 1
    return False


def validar_segundo_fator(usuario_id: int, codigo: str) -> bool:
    segredo = carregar_segredo(int(usuario_id))
    if not segredo:
        return True
    passo = _passo_totp_valido(segredo, codigo)
    if passo is not None:
        with conectar() as conexao:
            cursor = conexao.execute(
                """UPDATE usuarios SET mfa_ultimo_passo=? WHERE id=?
                   AND (mfa_ultimo_passo IS NULL OR mfa_ultimo_passo<?)""",
                (passo, int(usuario_id), passo),
            )
        return cursor.rowcount == 1
    return _usar_codigo_recuperacao(int(usuario_id), codigo)


def regenerar_codigos_recuperacao(usuario_id: int, codigo: str, ator: dict) -> list[str]:
    _autorizar_configuracao(usuario_id, ator)
    if not validar_segundo_fator(int(usuario_id), codigo):
        raise ValueError("Confirme um segundo fator válido.")
    codigos = _gerar_codigos_recuperacao(int(usuario_id))
    registrar_auditoria("mfa_recuperacao_regenerada", usuario_id=int(ator["id"]), alvo_usuario_id=int(usuario_id))
    return codigos


def desabilitar_mfa(usuario_id: int, ator: dict, codigo: str | None = None) -> None:
    _garantir_execucao_servidor()
    _autorizar_configuracao(usuario_id, ator)
    if int(usuario_id) == int(ator.get("id") or 0) and not validar_segundo_fator(int(usuario_id), str(codigo or "")):
        raise ValueError("Confirme um código MFA ou de recuperação válido.")
    with conectar() as conexao:
        usuario = conexao.execute("SELECT mfa_secret_ref FROM usuarios WHERE id=?", (int(usuario_id),)).fetchone()
        if usuario is None:
            raise ValueError("Usuário não encontrado.")
        conexao.execute(
            """UPDATE usuarios SET mfa_habilitado=0,mfa_pendente=0,mfa_secret_ref=NULL,
               mfa_confirmado_em=NULL,mfa_ultimo_passo=NULL,
               sessao_epoch=COALESCE(sessao_epoch,0)+1 WHERE id=?""",
            (int(usuario_id),),
        )
        conexao.execute("DELETE FROM mfa_codigos_recuperacao WHERE usuario_id=?", (int(usuario_id),))
    if usuario["mfa_secret_ref"]:
        _resolver(usuario["mfa_secret_ref"]).unlink(missing_ok=True)
    registrar_auditoria("mfa_desabilitado", usuario_id=int(ator["id"]), alvo_usuario_id=int(usuario_id))


__all__ = (
    "carregar_segredo", "confirmar_mfa", "desabilitar_mfa", "habilitar_mfa",
    "preparar_mfa", "regenerar_codigos_recuperacao", "validar_segundo_fator",
    "verificar_totp",
)
