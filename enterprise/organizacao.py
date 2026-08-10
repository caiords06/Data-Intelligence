"""Cadastros estruturais de empresas, filiais, departamentos e custos."""

from __future__ import annotations

import re
import sqlite3

from auth.banco import conectar, registrar_auditoria
from auth.sessao import SESSAO
from enterprise.contexto import garantir_contexto_sessao

_CODIGO = re.compile(r"^[A-Z0-9_-]{2,20}$")


def _exigir_admin(ator):
    if not ator or ator.get("perfil") != "admin":
        raise PermissionError("Esta operação exige um administrador.")


def listar_empresas() -> list[dict]:
    with conectar() as conexao:
        registros = conexao.execute(
            "SELECT id, nome, cnpj, ativo FROM empresas ORDER BY nome"
        ).fetchall()
    return [dict(item) for item in registros]


def listar_filiais(empresa_id: int | None = None) -> list[dict]:
    empresa_id = empresa_id or garantir_contexto_sessao()[0]
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id, empresa_id, nome, codigo, cidade, estado, ativo
            FROM filiais WHERE empresa_id = ? ORDER BY nome
            """,
            (int(empresa_id),),
        ).fetchall()
    return [dict(item) for item in registros]


def listar_departamentos(empresa_id: int | None = None) -> list[dict]:
    empresa_id = empresa_id or garantir_contexto_sessao()[0]
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id, empresa_id, nome, codigo, ativo
            FROM departamentos WHERE empresa_id = ? ORDER BY nome
            """,
            (int(empresa_id),),
        ).fetchall()
    return [dict(item) for item in registros]


def listar_centros_custo(empresa_id: int | None = None) -> list[dict]:
    empresa_id = empresa_id or garantir_contexto_sessao()[0]
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT c.id, c.empresa_id, c.departamento_id, c.nome, c.codigo,
                   c.ativo, d.nome AS departamento_nome
            FROM centros_custo c
            LEFT JOIN departamentos d ON d.id = c.departamento_id
            WHERE c.empresa_id = ? ORDER BY c.nome
            """,
            (int(empresa_id),),
        ).fetchall()
    return [dict(item) for item in registros]


def _validar_nome_codigo(nome: str, codigo: str) -> tuple[str, str]:
    nome = str(nome).strip()
    codigo = str(codigo).strip().upper()
    if len(nome) < 2 or len(nome) > 100:
        raise ValueError("O nome deve possuir entre 2 e 100 caracteres.")
    if not _CODIGO.fullmatch(codigo):
        raise ValueError("O código deve ter 2 a 20 letras, números, _ ou -.")
    return nome, codigo


def criar_empresa(nome: str, cnpj: str = "", ator=None) -> int:
    _exigir_admin(ator)
    nome = str(nome).strip()
    if len(nome) < 2 or len(nome) > 120:
        raise ValueError("Nome empresarial inválido.")
    with conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO empresas (nome, cnpj) VALUES (?, ?)",
            (nome, str(cnpj).strip() or None),
        )
        registro_id = int(cursor.lastrowid)
    registrar_auditoria(
        "empresa_criada",
        usuario_id=ator["id"],
        detalhes=f"empresa_id={registro_id}",
    )
    return registro_id


def criar_filial(nome, codigo, cidade="", estado="", ator=None) -> int:
    _exigir_admin(ator)
    empresa_id, _ = garantir_contexto_sessao()
    nome, codigo = _validar_nome_codigo(nome, codigo)
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO filiais (empresa_id, nome, codigo, cidade, estado)
                VALUES (?, ?, ?, ?, ?)
                """,
                (empresa_id, nome, codigo, str(cidade).strip(), str(estado).strip()),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe uma filial com este código.") from erro


def criar_departamento(nome, codigo, ator=None) -> int:
    _exigir_admin(ator)
    empresa_id, _ = garantir_contexto_sessao()
    nome, codigo = _validar_nome_codigo(nome, codigo)
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO departamentos (empresa_id, nome, codigo)
                VALUES (?, ?, ?)
                """,
                (empresa_id, nome, codigo),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe um departamento com este código.") from erro


def criar_centro_custo(nome, codigo, departamento_id=None, ator=None) -> int:
    _exigir_admin(ator)
    empresa_id, _ = garantir_contexto_sessao()
    nome, codigo = _validar_nome_codigo(nome, codigo)
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO centros_custo (
                    empresa_id, departamento_id, nome, codigo
                ) VALUES (?, ?, ?, ?)
                """,
                (empresa_id, departamento_id or None, nome, codigo),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe um centro de custo com este código.") from erro


def definir_contexto_empresa(empresa_id: int, filial_id=None) -> None:
    if not SESSAO.autenticado():
        raise PermissionError("Usuário não autenticado.")
    with conectar() as conexao:
        empresa = conexao.execute(
            "SELECT id FROM empresas WHERE id = ? AND ativo = 1",
            (int(empresa_id),),
        ).fetchone()
        if empresa is None:
            raise ValueError("Empresa inexistente ou inativa.")
        if filial_id is None:
            filial = conexao.execute(
                """
                SELECT id FROM filiais
                WHERE empresa_id = ? AND ativo = 1 ORDER BY id LIMIT 1
                """,
                (int(empresa_id),),
            ).fetchone()
            filial_id = int(filial["id"]) if filial else None
        else:
            filial = conexao.execute(
                """
                SELECT id FROM filiais
                WHERE id = ? AND empresa_id = ? AND ativo = 1
                """,
                (int(filial_id), int(empresa_id)),
            ).fetchone()
            if filial is None:
                raise ValueError("Filial não pertence à empresa selecionada.")
    SESSAO.definir_contexto_empresarial(int(empresa_id), filial_id)
