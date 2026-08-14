"""Cadastros estruturais de empresas, filiais, departamentos e custos.

Em Central/Cliente, CRUD/listagens são executados no Servidor Corporativo via
RPC restrito. A estação não mantém cópia persistente dos dados corporativos.
"""
from __future__ import annotations

import re
import sqlite3

from auth.banco import conectar, registrar_auditoria
from auth.sessao import SESSAO
from enterprise.contexto import obter_escopo_ator

_CODIGO = re.compile(r"^[A-Z0-9_-]{2,20}$")


def _ator_efetivo(ator=None) -> dict:
    if ator:
        return ator
    if SESSAO.usuario:
        return dict(SESSAO.usuario)
    raise PermissionError("Usuário não autenticado.")


def _exigir_admin(ator):
    ator = _ator_efetivo(ator)
    if ator.get("perfil") != "admin":
        raise PermissionError("Esta operação exige um administrador.")
    return ator


def _empresa_consulta_permitida(empresa_id: int | None, ator=None) -> int:
    ator = _ator_efetivo(ator)
    contexto_empresa, _ = obter_escopo_ator(ator)
    alvo = int(empresa_id or contexto_empresa)
    if ator.get("perfil") == "admin":
        return alvo
    with conectar() as conexao:
        vinculo = conexao.execute(
            "SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(ator["id"]), alvo),
        ).fetchone()
    if vinculo is None:
        raise PermissionError("Seu usuário não possui acesso à empresa informada.")
    return alvo


def listar_empresas(ator=None) -> list[dict]:
    ator = _ator_efetivo(ator)
    with conectar() as conexao:
        if ator.get("perfil") == "admin":
            registros = conexao.execute(
                "SELECT id,nome,cnpj,ativo FROM empresas ORDER BY nome"
            ).fetchall()
        else:
            registros = conexao.execute(
                """SELECT e.id,e.nome,e.cnpj,e.ativo
                   FROM empresas e JOIN usuarios_empresas ue ON ue.empresa_id=e.id
                   WHERE ue.usuario_id=? AND ue.ativo=1 ORDER BY e.nome""",
                (int(ator["id"]),),
            ).fetchall()
    return [dict(x) for x in registros]


def listar_filiais(empresa_id: int | None = None, ator=None) -> list[dict]:
    ator = _ator_efetivo(ator)
    empresa_id = _empresa_consulta_permitida(empresa_id, ator)
    with conectar() as conexao:
        if ator.get("perfil") == "admin":
            registros = conexao.execute(
                "SELECT id,empresa_id,nome,codigo,cidade,estado,ativo FROM filiais WHERE empresa_id=? ORDER BY nome",
                (empresa_id,),
            ).fetchall()
        else:
            vinculo = conexao.execute(
                "SELECT filial_id FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
                (int(ator["id"]), empresa_id),
            ).fetchone()
            if vinculo is None:
                return []
            if vinculo["filial_id"] is None:
                registros = conexao.execute(
                    "SELECT id,empresa_id,nome,codigo,cidade,estado,ativo FROM filiais WHERE empresa_id=? ORDER BY nome",
                    (empresa_id,),
                ).fetchall()
            else:
                registros = conexao.execute(
                    "SELECT id,empresa_id,nome,codigo,cidade,estado,ativo FROM filiais WHERE id=? AND empresa_id=? ORDER BY nome",
                    (int(vinculo["filial_id"]), empresa_id),
                ).fetchall()
    return [dict(x) for x in registros]


def listar_departamentos(empresa_id: int | None = None, ator=None) -> list[dict]:
    empresa_id = _empresa_consulta_permitida(empresa_id, ator)
    with conectar() as conexao:
        registros = conexao.execute(
            "SELECT id,empresa_id,nome,codigo,ativo FROM departamentos WHERE empresa_id=? ORDER BY nome",
            (empresa_id,),
        ).fetchall()
    return [dict(x) for x in registros]


def listar_centros_custo(empresa_id: int | None = None, ator=None) -> list[dict]:
    empresa_id = _empresa_consulta_permitida(empresa_id, ator)
    with conectar() as conexao:
        registros = conexao.execute(
            """SELECT c.id,c.empresa_id,c.departamento_id,c.nome,c.codigo,c.ativo,
                      d.nome AS departamento_nome
               FROM centros_custo c LEFT JOIN departamentos d ON d.id=c.departamento_id
               WHERE c.empresa_id=? ORDER BY c.nome""",
            (empresa_id,),
        ).fetchall()
    return [dict(x) for x in registros]


def _validar_nome_codigo(nome: str, codigo: str) -> tuple[str, str]:
    nome = str(nome).strip()
    codigo = str(codigo).strip().upper()
    if len(nome) < 2 or len(nome) > 100:
        raise ValueError("O nome deve possuir entre 2 e 100 caracteres.")
    if not _CODIGO.fullmatch(codigo):
        raise ValueError("O código deve ter 2 a 20 letras, números, _ ou -.")
    return nome, codigo


def criar_empresa(nome: str, cnpj: str = "", ator=None) -> int:
    ator = _exigir_admin(ator)
    nome = str(nome).strip()
    if len(nome) < 2 or len(nome) > 120:
        raise ValueError("Nome empresarial inválido.")
    with conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO empresas (nome,cnpj) VALUES (?,?)",
            (nome, str(cnpj).strip() or None),
        )
        registro_id = int(cursor.lastrowid)
        conexao.execute(
            "INSERT OR IGNORE INTO usuarios_empresas (usuario_id,empresa_id) VALUES (?,?)",
            (int(ator["id"]), registro_id),
        )
    registrar_auditoria("empresa_criada", usuario_id=ator["id"], detalhes=f"empresa_id={registro_id}")
    from enterprise.core_v11.provisionamento import provisionar_empresa_v11
    provisionar_empresa_v11(registro_id, ator)
    # Somente standalone usa o atalho efêmero de remoção da sessão.
    if SESSAO.usuario and int(SESSAO.usuario.get("id")) == int(ator["id"]):
        SESSAO.registrar_empresa_criada(registro_id)
    return registro_id


def remover_empresa_criada_sessao(empresa_id: int, ator=None) -> None:
    from core.nodo import usa_servidor_remoto
    if usa_servidor_remoto():
        raise ValueError(
            "A remoção efêmera de empresa é um recurso de laboratório standalone "
            "e fica desativada em nós conectados ao Servidor Corporativo."
        )
    ator = _exigir_admin(ator)
    empresa_id = int(empresa_id)
    if not SESSAO.empresa_criada_na_sessao(empresa_id):
        raise ValueError("Somente empresas criadas durante a sessão atual podem ser removidas aqui.")
    if SESSAO.empresa_id is not None and int(SESSAO.empresa_id) == empresa_id:
        raise ValueError("A empresa está ativa na sessão. Selecione outra empresa antes de removê-la.")
    with conectar() as conexao:
        empresa = conexao.execute("SELECT id,nome,ativo FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if empresa is None or not int(empresa["ativo"]):
            raise ValueError("Empresa inexistente ou já removida.")
        conexao.execute("UPDATE empresas SET ativo=0 WHERE id=?", (empresa_id,))
        conexao.execute("UPDATE usuarios_empresas SET ativo=0 WHERE empresa_id=?", (empresa_id,))
        conexao.execute("UPDATE filiais SET ativo=0 WHERE empresa_id=?", (empresa_id,))
        conexao.execute("UPDATE departamentos SET ativo=0 WHERE empresa_id=?", (empresa_id,))
        conexao.execute("UPDATE centros_custo SET ativo=0 WHERE empresa_id=?", (empresa_id,))
    SESSAO.descartar_empresa_criada(empresa_id)
    registrar_auditoria(
        "empresa_removida_sessao", usuario_id=ator["id"],
        detalhes=f"empresa_id={empresa_id};nome={empresa['nome']}",
    )


def criar_filial(nome, codigo, cidade="", estado="", ator=None) -> int:
    ator = _exigir_admin(ator)
    empresa_id, _ = obter_escopo_ator(ator)
    nome, codigo = _validar_nome_codigo(nome, codigo)
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                "INSERT INTO filiais (empresa_id,nome,codigo,cidade,estado) VALUES (?,?,?,?,?)",
                (empresa_id, nome, codigo, str(cidade).strip(), str(estado).strip()),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe uma filial com este código.") from erro


def criar_departamento(nome, codigo, ator=None) -> int:
    ator = _exigir_admin(ator)
    empresa_id, _ = obter_escopo_ator(ator)
    nome, codigo = _validar_nome_codigo(nome, codigo)
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                "INSERT INTO departamentos (empresa_id,nome,codigo) VALUES (?,?,?)",
                (empresa_id, nome, codigo),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe um departamento com este código.") from erro


def criar_centro_custo(nome, codigo, departamento_id=None, ator=None) -> int:
    ator = _exigir_admin(ator)
    empresa_id, _ = obter_escopo_ator(ator)
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
                "INSERT INTO centros_custo (empresa_id,departamento_id,nome,codigo) VALUES (?,?,?,?)",
                (empresa_id, int(departamento_id) if departamento else None, nome, codigo),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe um centro de custo com este código.") from erro


def definir_contexto_empresa(empresa_id: int, filial_id=None) -> None:
    if not SESSAO.autenticado():
        raise PermissionError("Usuário não autenticado.")
    from core.nodo import usa_servidor_remoto
    if usa_servidor_remoto():
        from enterprise.servidor_cliente import definir_contexto_remoto
        payload = definir_contexto_remoto(int(empresa_id), filial_id)
        empresa = dict(payload.get("empresa") or {})
        SESSAO.definir_contexto_empresarial(
            int(empresa.get("id") or empresa_id),
            payload.get("filial_id"),
        )
        return

    ator = _ator_efetivo(SESSAO.usuario)
    alvo = _empresa_consulta_permitida(int(empresa_id), ator)
    with conectar() as conexao:
        filial_restrita = None
        if ator.get("perfil") != "admin":
            vinculo = conexao.execute(
                "SELECT filial_id FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
                (int(ator["id"]), alvo),
            ).fetchone()
            if vinculo is None:
                raise PermissionError("Seu usuário não possui acesso à empresa selecionada.")
            filial_restrita = vinculo["filial_id"]
        if filial_restrita is not None:
            if filial_id is not None and int(filial_id) != int(filial_restrita):
                raise PermissionError("Seu usuário não possui acesso à filial selecionada.")
            filial_id = int(filial_restrita)
        if filial_id is None:
            filial = conexao.execute(
                "SELECT id FROM filiais WHERE empresa_id=? AND ativo=1 ORDER BY id LIMIT 1",
                (alvo,),
            ).fetchone()
            filial_id = int(filial["id"]) if filial else None
        else:
            filial = conexao.execute(
                "SELECT id FROM filiais WHERE id=? AND empresa_id=? AND ativo=1",
                (int(filial_id), alvo),
            ).fetchone()
            if filial is None:
                raise ValueError("Filial não pertence à empresa selecionada.")
    SESSAO.definir_contexto_empresarial(alvo, filial_id)


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
