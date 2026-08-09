"""Regras de autenticação e administração de usuários."""

import sqlite3

from auth.banco import (
    alterar_status_usuario,
    atualizar_senha_usuario,
    buscar_usuario,
    inserir_usuario,
    listar_usuarios,
    registrar_login,
    tem_usuarios,
)
from auth.seguranca import gerar_hash_senha, verificar_senha

PERFIS_VALIDOS = {"admin", "usuario"}


def criar_usuario(nome, usuario, senha, perfil="usuario") -> dict:
    nome = str(nome).strip()
    usuario = str(usuario).strip().lower()
    perfil = str(perfil).strip().lower()

    if not nome:
        raise ValueError("Informe o nome do usuário.")
    if not usuario:
        raise ValueError("Informe o login.")
    if any(caractere.isspace() for caractere in usuario):
        raise ValueError("O login não pode conter espaços.")
    if perfil not in PERFIS_VALIDOS:
        raise ValueError("Perfil de usuário inválido.")

    senha_hash, salt = gerar_hash_senha(senha)
    try:
        usuario_id = inserir_usuario(nome, usuario, senha_hash, salt, perfil)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Este nome de usuário já está cadastrado.") from erro

    return {
        "id": usuario_id,
        "nome": nome,
        "usuario": usuario,
        "perfil": perfil,
        "ativo": True,
    }


def criar_admin_inicial(nome, usuario, senha) -> dict:
    if tem_usuarios():
        raise ValueError("O administrador inicial já foi configurado.")
    return criar_usuario(nome, usuario, senha, perfil="admin")


def autenticar_usuario(usuario, senha) -> dict:
    usuario = str(usuario).strip().lower()
    registro = buscar_usuario(usuario)

    if registro is None or not verificar_senha(
        senha,
        registro["senha_hash"],
        registro["salt"],
    ):
        raise ValueError("Usuário ou senha inválidos.")
    if not registro["ativo"]:
        raise PermissionError("Este usuário está desativado.")

    registrar_login(registro["id"])
    return {
        "id": registro["id"],
        "nome": registro["nome"],
        "usuario": registro["usuario"],
        "perfil": registro["perfil"],
        "ativo": bool(registro["ativo"]),
    }


def obter_usuarios() -> list[dict]:
    return listar_usuarios()


def definir_status_usuario(usuario_id, ativo) -> None:
    alterar_status_usuario(usuario_id, ativo)


def redefinir_senha(usuario_id, nova_senha) -> None:
    senha_hash, salt = gerar_hash_senha(nova_senha)
    atualizar_senha_usuario(usuario_id, senha_hash, salt)
