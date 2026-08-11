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
        if SESSAO.eh_admin():
            registros = conexao.execute(
                "SELECT id, nome, cnpj, ativo FROM empresas ORDER BY nome"
            ).fetchall()
        elif SESSAO.usuario:
            registros = conexao.execute(
                """
                SELECT e.id, e.nome, e.cnpj, e.ativo
                FROM empresas e
                JOIN usuarios_empresas ue ON ue.empresa_id=e.id
                WHERE ue.usuario_id=? AND ue.ativo=1
                ORDER BY e.nome
                """,
                (int(SESSAO.usuario["id"]),),
            ).fetchall()
        else:
            registros = []
    return [dict(item) for item in registros]


def listar_filiais(empresa_id: int | None = None) -> list[dict]:
    empresa_id = empresa_id or garantir_contexto_sessao()[0]
    with conectar() as conexao:
        if SESSAO.eh_admin():
            registros = conexao.execute(
                """
                SELECT id, empresa_id, nome, codigo, cidade, estado, ativo
                FROM filiais WHERE empresa_id = ? ORDER BY nome
                """,
                (int(empresa_id),),
            ).fetchall()
        elif SESSAO.usuario:
            vinculo = conexao.execute(
                "SELECT filial_id FROM usuarios_empresas "
                "WHERE usuario_id=? AND empresa_id=? AND ativo=1",
                (int(SESSAO.usuario["id"]), int(empresa_id)),
            ).fetchone()
            if vinculo is None:
                return []
            if vinculo["filial_id"] is None:
                registros = conexao.execute(
                    """
                    SELECT id, empresa_id, nome, codigo, cidade, estado, ativo
                    FROM filiais WHERE empresa_id = ? ORDER BY nome
                    """,
                    (int(empresa_id),),
                ).fetchall()
            else:
                registros = conexao.execute(
                    """
                    SELECT id, empresa_id, nome, codigo, cidade, estado, ativo
                    FROM filiais WHERE id=? AND empresa_id=? ORDER BY nome
                    """,
                    (int(vinculo["filial_id"]), int(empresa_id)),
                ).fetchall()
        else:
            registros = []
    return [dict(item) for item in registros]


def _empresa_consulta_permitida(empresa_id: int | None) -> int:
    contexto_empresa, _ = garantir_contexto_sessao()
    alvo = int(empresa_id or contexto_empresa)
    if SESSAO.eh_admin():
        return alvo
    if not SESSAO.usuario:
        raise PermissionError("Usuário não autenticado.")
    with conectar() as conexao:
        vinculo = conexao.execute(
            "SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(SESSAO.usuario["id"]), alvo),
        ).fetchone()
    if vinculo is None:
        raise PermissionError("Seu usuário não possui acesso à empresa informada.")
    return alvo


def listar_departamentos(empresa_id: int | None = None) -> list[dict]:
    empresa_id = _empresa_consulta_permitida(empresa_id)
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
    empresa_id = _empresa_consulta_permitida(empresa_id)
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
        conexao.execute(
            "INSERT OR IGNORE INTO usuarios_empresas (usuario_id, empresa_id) VALUES (?, ?)",
            (int(ator["id"]), registro_id),
        )
    registrar_auditoria(
        "empresa_criada",
        usuario_id=ator["id"],
        detalhes=f"empresa_id={registro_id}",
    )
    if (
        SESSAO.usuario
        and int(SESSAO.usuario.get("id")) == int(ator["id"])
    ):
        SESSAO.registrar_empresa_criada(registro_id)
    return registro_id


def remover_empresa_criada_sessao(empresa_id: int, ator=None) -> None:
    """Remove logicamente uma empresa criada durante a sessão atual.

    A remoção é propositalmente restrita às empresas registradas na memória da
    sessão atual. Empresas preexistentes não podem ser removidas por este
    atalho, evitando que um teste de estrutura organizacional vire uma exclusão
    acidental de dados persistidos. O registro é desativado, preservando
    rastreabilidade e integridade referencial.
    """
    _exigir_admin(ator)
    empresa_id = int(empresa_id)
    if not SESSAO.empresa_criada_na_sessao(empresa_id):
        raise ValueError(
            "Somente empresas criadas durante a sessão atual podem ser removidas aqui."
        )
    if SESSAO.empresa_id is not None and int(SESSAO.empresa_id) == empresa_id:
        raise ValueError(
            "A empresa está ativa na sessão. Selecione outra empresa antes de removê-la."
        )

    with conectar() as conexao:
        empresa = conexao.execute(
            "SELECT id, nome, ativo FROM empresas WHERE id=?",
            (empresa_id,),
        ).fetchone()
        if empresa is None or not int(empresa["ativo"]):
            raise ValueError("Empresa inexistente ou já removida.")

        # Soft delete: a empresa desaparece da operação normal, mas registros
        # vinculados continuam íntegros e auditáveis.
        conexao.execute("UPDATE empresas SET ativo=0 WHERE id=?", (empresa_id,))
        conexao.execute(
            "UPDATE usuarios_empresas SET ativo=0 WHERE empresa_id=?",
            (empresa_id,),
        )
        conexao.execute("UPDATE filiais SET ativo=0 WHERE empresa_id=?", (empresa_id,))
        conexao.execute(
            "UPDATE departamentos SET ativo=0 WHERE empresa_id=?",
            (empresa_id,),
        )
        conexao.execute(
            "UPDATE centros_custo SET ativo=0 WHERE empresa_id=?",
            (empresa_id,),
        )

    SESSAO.descartar_empresa_criada(empresa_id)
    registrar_auditoria(
        "empresa_removida_sessao",
        usuario_id=ator["id"],
        detalhes=f"empresa_id={empresa_id};nome={empresa['nome']}",
    )


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
            departamento = None
            if departamento_id not in (None, ""):
                departamento = conexao.execute(
                    "SELECT id FROM departamentos WHERE id=? AND empresa_id=? AND ativo=1",
                    (int(departamento_id), empresa_id),
                ).fetchone()
                if departamento is None:
                    raise ValueError("O departamento não pertence à empresa ativa.")
            cursor = conexao.execute(
                """
                INSERT INTO centros_custo (
                    empresa_id, departamento_id, nome, codigo
                ) VALUES (?, ?, ?, ?)
                """,
                (empresa_id, int(departamento_id) if departamento else None, nome, codigo),
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

        filial_restrita = None
        if not SESSAO.eh_admin():
            vinculo = conexao.execute(
                """
                SELECT filial_id FROM usuarios_empresas
                WHERE usuario_id=? AND empresa_id=? AND ativo=1
                """,
                (int(SESSAO.usuario["id"]), int(empresa_id)),
            ).fetchone()
            if vinculo is None:
                raise PermissionError(
                    "Seu usuário não possui acesso à empresa selecionada."
                )
            filial_restrita = vinculo["filial_id"]

        if filial_restrita is not None:
            if filial_id is not None and int(filial_id) != int(filial_restrita):
                raise PermissionError(
                    "Seu usuário não possui acesso à filial selecionada."
                )
            filial_id = int(filial_restrita)

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
    from core.nodo import usa_servidor_remoto
    if usa_servidor_remoto():
        from enterprise.servidor_cliente import definir_contexto_remoto
        definir_contexto_remoto(int(empresa_id), filial_id)
    SESSAO.definir_contexto_empresarial(int(empresa_id), filial_id)
