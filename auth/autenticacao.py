"""Regras de autenticação, autorização e administração de usuários."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from auth.banco import (
    alterar_perfil_acesso_usuario,
    alterar_status_usuario,
    atualizar_senha_usuario,
    buscar_usuario,
    buscar_usuario_por_id,
    contar_administradores_ativos,
    inserir_usuario,
    listar_usuarios,
    limpar_falhas_autenticacao,
    registrar_auditoria,
    registrar_falha_autenticacao,
    registrar_login,
    tem_usuarios,
)
from auth.seguranca import gerar_hash_senha, verificar_senha
from enterprise.perfis_acesso import validar_perfil_acesso

PERFIS_VALIDOS = {"admin", "usuario"}
_LOGIN_VALIDO = re.compile(r"^[a-z0-9._-]{3,40}$")
_HASH_FICTICIO, _SALT_FICTICIO = gerar_hash_senha("ContaFicticia#2026")


def _exigir_admin(ator: dict | None) -> None:
    if not ator or ator.get("perfil") != "admin" or not ator.get("ativo", True):
        raise PermissionError("Esta operação exige um administrador autenticado.")


def _usuario_publico(registro) -> dict:
    perfil_acesso = (
        "administrador"
        if registro["perfil"] == "admin"
        else registro["perfil_acesso"] or "analista"
    )
    return {
        "id": int(registro["id"]),
        "nome": registro["nome"],
        "usuario": registro["usuario"],
        "perfil": registro["perfil"],
        "perfil_acesso": perfil_acesso,
        "ativo": bool(registro["ativo"]),
    }


def _criar_usuario(nome, usuario, senha, perfil, perfil_acesso=None) -> dict:
    nome = str(nome).strip()
    usuario = str(usuario).strip().lower()
    perfil = str(perfil).strip().lower()
    if len(nome) < 2 or len(nome) > 100:
        raise ValueError("O nome deve possuir entre 2 e 100 caracteres.")
    if not _LOGIN_VALIDO.fullmatch(usuario):
        raise ValueError(
            "O login deve ter de 3 a 40 caracteres e usar apenas letras, "
            "números, ponto, hífen ou sublinhado."
        )
    if perfil not in PERFIS_VALIDOS:
        raise ValueError("Perfil de usuário inválido.")
    if perfil == "admin":
        perfil_acesso = "administrador"
    else:
        perfil_acesso = validar_perfil_acesso(perfil_acesso)

    senha_hash, salt = gerar_hash_senha(senha)
    try:
        usuario_id = inserir_usuario(
            nome,
            usuario,
            senha_hash,
            salt,
            perfil,
            perfil_acesso,
        )
    except sqlite3.IntegrityError as erro:
        raise ValueError("Este nome de usuário já está cadastrado.") from erro
    return {
        "id": usuario_id,
        "nome": nome,
        "usuario": usuario,
        "perfil": perfil,
        "perfil_acesso": perfil_acesso,
        "ativo": True,
    }


def criar_usuario(
    nome,
    usuario,
    senha,
    perfil="usuario",
    ator=None,
    perfil_acesso=None,
) -> dict:
    if tem_usuarios():
        _exigir_admin(ator)
    criado = _criar_usuario(nome, usuario, senha, perfil, perfil_acesso)
    registrar_auditoria(
        "usuario_criado",
        usuario_id=(ator or {}).get("id"),
        alvo_usuario_id=criado["id"],
        detalhes=(
            f"perfil={criado['perfil']};"
            f"perfil_acesso={criado['perfil_acesso']}"
        ),
    )
    return criado


def criar_admin_inicial(nome, usuario, senha) -> dict:
    if tem_usuarios():
        raise ValueError("O administrador inicial já foi configurado.")
    criado = _criar_usuario(
        nome,
        usuario,
        senha,
        perfil="admin",
        perfil_acesso="administrador",
    )
    registrar_auditoria(
        "admin_inicial_criado",
        usuario_id=criado["id"],
        alvo_usuario_id=criado["id"],
    )
    return criado


def _bloqueio_ativo(valor: str | None) -> bool:
    if not valor:
        return False
    try:
        instante = datetime.fromisoformat(valor)
        if instante.tzinfo is None:
            instante = instante.replace(tzinfo=timezone.utc)
        return instante > datetime.now(timezone.utc)
    except ValueError:
        return False


def autenticar_usuario(usuario, senha) -> dict:
    login = str(usuario).strip().lower()
    registro = buscar_usuario(login)
    if registro is None:
        verificar_senha(str(senha), _HASH_FICTICIO, _SALT_FICTICIO)
        raise ValueError("Usuário ou senha inválidos.")
    if _bloqueio_ativo(registro["bloqueado_ate"]):
        registrar_auditoria(
            "login_bloqueado",
            alvo_usuario_id=registro["id"],
        )
        raise PermissionError(
            "Acesso temporariamente bloqueado. Aguarde alguns minutos."
        )
    if not verificar_senha(str(senha), registro["senha_hash"], registro["salt"]):
        bloqueado = registrar_falha_autenticacao(registro["id"])
        registrar_auditoria(
            "falha_login",
            alvo_usuario_id=registro["id"],
            detalhes="conta_bloqueada" if bloqueado else None,
        )
        if bloqueado:
            raise PermissionError(
                "Muitas tentativas inválidas. A conta foi bloqueada por 5 minutos."
            )
        raise ValueError("Usuário ou senha inválidos.")
    if not registro["ativo"]:
        registrar_auditoria("login_conta_inativa", alvo_usuario_id=registro["id"])
        raise PermissionError("Este usuário está desativado.")

    limpar_falhas_autenticacao(registro["id"])
    registrar_login(registro["id"])
    registrar_auditoria("login_sucesso", usuario_id=registro["id"])
    return _usuario_publico(registro)


def obter_usuarios(ator=None) -> list[dict]:
    _exigir_admin(ator)
    return listar_usuarios()


def definir_status_usuario(usuario_id, ativo, ator=None) -> None:
    _exigir_admin(ator)
    alvo = buscar_usuario_por_id(int(usuario_id))
    if alvo is None:
        raise ValueError("Usuário não encontrado.")
    if not ativo and int(alvo["id"]) == int(ator["id"]):
        raise ValueError("Você não pode desativar sua própria conta.")
    if (
        not ativo
        and alvo["perfil"] == "admin"
        and bool(alvo["ativo"])
        and contar_administradores_ativos() <= 1
    ):
        raise ValueError("Não é possível desativar o último administrador ativo.")
    alterar_status_usuario(int(usuario_id), bool(ativo))
    registrar_auditoria(
        "usuario_ativado" if ativo else "usuario_desativado",
        usuario_id=ator["id"],
        alvo_usuario_id=int(usuario_id),
    )


def redefinir_senha(usuario_id, nova_senha, ator=None) -> None:
    _exigir_admin(ator)
    if buscar_usuario_por_id(int(usuario_id)) is None:
        raise ValueError("Usuário não encontrado.")
    senha_hash, salt = gerar_hash_senha(nova_senha)
    atualizar_senha_usuario(int(usuario_id), senha_hash, salt)
    registrar_auditoria(
        "senha_redefinida",
        usuario_id=ator["id"],
        alvo_usuario_id=int(usuario_id),
    )


def definir_perfil_acesso_usuario(
    usuario_id: int,
    perfil_acesso: str,
    ator=None,
) -> None:
    _exigir_admin(ator)
    alvo = buscar_usuario_por_id(int(usuario_id))
    if alvo is None:
        raise ValueError("Usuário não encontrado.")
    if alvo["perfil"] == "admin":
        raise ValueError(
            "O perfil do administrador é fixo e possui acesso integral."
        )
    codigo = validar_perfil_acesso(perfil_acesso)
    alterar_perfil_acesso_usuario(int(usuario_id), codigo)
    registrar_auditoria(
        "perfil_acesso_alterado",
        usuario_id=ator["id"],
        alvo_usuario_id=int(usuario_id),
        detalhes=f"perfil_acesso={codigo}",
    )


def alterar_propria_senha(ator: dict, senha_atual: str, nova_senha: str) -> None:
    if not ator or not ator.get("id"):
        raise PermissionError("Usuário não autenticado.")
    registro = buscar_usuario_por_id(int(ator["id"]))
    if registro is None or not verificar_senha(
        senha_atual,
        registro["senha_hash"],
        registro["salt"],
    ):
        raise ValueError("A senha atual está incorreta.")
    senha_hash, salt = gerar_hash_senha(nova_senha)
    atualizar_senha_usuario(int(ator["id"]), senha_hash, salt)
    registrar_auditoria(
        "senha_propria_alterada",
        usuario_id=int(ator["id"]),
        alvo_usuario_id=int(ator["id"]),
    )
