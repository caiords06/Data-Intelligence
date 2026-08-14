"""Grupos, funções e permissões contextuais compartilhadas."""
from __future__ import annotations

from datetime import datetime, timezone

from auth.banco import conectar
from enterprise.contexto import tem_permissao
from enterprise.core_v11.common import MODULOS_PERMISSAO, codigo, dump, escopo, exigir_admin, json_objeto, load, registrar_evento, texto


def criar_grupo(dados: dict, ator: dict) -> int:
    exigir_admin(ator); empresa_id, filial_id = escopo(ator)
    permissoes = json_objeto(dados.get("permissoes"), campo="Permissões")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO grupos_acesso(empresa_id,nome,codigo,descricao,permissoes_json,criado_por)
               VALUES (?,?,?,?,?,?)""",
            (
                empresa_id, texto(dados.get("nome"), minimo=2, maximo=100, campo="Nome"),
                codigo(dados.get("codigo"), campo="Código").upper(), texto(dados.get("descricao"), maximo=500),
                dump(permissoes), int(ator["id"]),
            ),
        )
        grupo_id = int(cursor.lastrowid)
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="administrativo", tipo="acesso.grupo_criado",
            recurso_tipo="grupos_acesso", recurso_id=grupo_id, ator=ator, payload={"nome": dados.get("nome")},
        )
    return grupo_id


def adicionar_membro(grupo_id: int, usuario_id: int, ator: dict) -> None:
    exigir_admin(ator); empresa_id, _ = escopo(ator)
    with conectar() as con:
        grupo = con.execute("SELECT id FROM grupos_acesso WHERE id=? AND empresa_id=? AND ativo=1", (int(grupo_id), empresa_id)).fetchone()
        usuario = con.execute(
            """SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1""",
            (int(usuario_id), empresa_id),
        ).fetchone()
        if grupo is None or usuario is None:
            raise ValueError("Grupo ou usuário não pertence à empresa ativa.")
        con.execute(
            """INSERT INTO membros_grupo_acesso(grupo_id,usuario_id,criado_por) VALUES (?,?,?)
               ON CONFLICT(grupo_id,usuario_id) DO NOTHING""",
            (int(grupo_id), int(usuario_id), int(ator["id"])),
        )


def criar_funcao_contextual(dados: dict, ator: dict) -> int:
    exigir_admin(ator); empresa_id, _ = escopo(ator)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO funcoes_contextuais
               (empresa_id,codigo,nome,permissoes_json,restricoes_json,criado_por) VALUES (?,?,?,?,?,?)""",
            (
                empresa_id, codigo(dados.get("codigo")).upper(), texto(dados.get("nome"), minimo=2, maximo=100),
                dump(json_objeto(dados.get("permissoes"), campo="Permissões")),
                dump(json_objeto(dados.get("restricoes"), campo="Restrições")), int(ator["id"]),
            ),
        )
        return int(cursor.lastrowid)


def atribuir_funcao(funcao_id: int, usuario_id: int, contexto: dict, ator: dict) -> int:
    exigir_admin(ator); empresa_id, _ = escopo(ator)
    contexto = json_objeto(contexto, campo="Contexto")
    with conectar() as con:
        funcao = con.execute("SELECT id FROM funcoes_contextuais WHERE id=? AND empresa_id=? AND ativo=1", (int(funcao_id), empresa_id)).fetchone()
        if funcao is None:
            raise ValueError("Função contextual não encontrada.")
        cursor = con.execute(
            """INSERT INTO atribuicoes_funcoes_contextuais
               (empresa_id,funcao_id,usuario_id,filial_id,departamento_id,unidade_id,recurso_tipo,recurso_id,
                valido_de,valido_ate,criado_por) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                empresa_id, int(funcao_id), int(usuario_id), contexto.get("filial_id"), contexto.get("departamento_id"),
                contexto.get("unidade_id"), contexto.get("recurso_tipo"), contexto.get("recurso_id"),
                contexto.get("valido_de"), contexto.get("valido_ate"), int(ator["id"]),
            ),
        )
        return int(cursor.lastrowid)


def _contexto_compativel(atribuicao: dict, contexto: dict) -> bool:
    hoje = datetime.now(timezone.utc).date().isoformat()
    if atribuicao.get("valido_de") and str(atribuicao["valido_de"])[:10] > hoje:
        return False
    if atribuicao.get("valido_ate") and str(atribuicao["valido_ate"])[:10] < hoje:
        return False
    for campo in ("filial_id", "departamento_id", "unidade_id", "recurso_tipo", "recurso_id"):
        esperado = atribuicao.get(campo)
        if esperado is not None and str(esperado) != str(contexto.get(campo)):
            return False
    return True


def tem_permissao_contextual(ator: dict, modulo: str, acao: str, contexto: dict | None = None) -> bool:
    if tem_permissao(ator, MODULOS_PERMISSAO.get(modulo, modulo), acao):
        return True
    empresa_id, _ = escopo(ator)
    contexto = contexto or {}
    with conectar() as con:
        grupos = con.execute(
            """SELECT g.permissoes_json FROM grupos_acesso g
               JOIN membros_grupo_acesso m ON m.grupo_id=g.id
               WHERE g.empresa_id=? AND m.usuario_id=? AND g.ativo=1""",
            (empresa_id, int(ator["id"])),
        ).fetchall()
        atribuicoes = con.execute(
            """SELECT a.*,f.permissoes_json,f.restricoes_json FROM atribuicoes_funcoes_contextuais a
               JOIN funcoes_contextuais f ON f.id=a.funcao_id
               WHERE a.empresa_id=? AND a.usuario_id=? AND a.ativo=1 AND f.ativo=1""",
            (empresa_id, int(ator["id"])),
        ).fetchall()
    for grupo in grupos:
        if bool(load(grupo["permissoes_json"], {}).get(modulo, {}).get(acao)):
            return True
    for row in atribuicoes:
        item = dict(row)
        if not _contexto_compativel(item, contexto):
            continue
        permissoes = load(item["permissoes_json"], {})
        restricoes = load(item["restricoes_json"], {})
        if bool(permissoes.get(modulo, {}).get(acao)) and all(contexto.get(k) == v for k, v in restricoes.items()):
            return True
    return False


def exigir_permissao_contextual(ator: dict, modulo: str, acao: str, contexto: dict | None = None) -> None:
    if not tem_permissao_contextual(ator, modulo, acao, contexto):
        raise PermissionError("Seu usuário não possui permissão neste contexto.")


def listar_grupos_funcoes(ator: dict) -> dict:
    exigir_admin(ator); empresa_id, _ = escopo(ator)
    with conectar() as con:
        grupos = con.execute("SELECT * FROM grupos_acesso WHERE empresa_id=? ORDER BY nome", (empresa_id,)).fetchall()
        funcoes = con.execute("SELECT * FROM funcoes_contextuais WHERE empresa_id=? ORDER BY nome", (empresa_id,)).fetchall()
    return {
        "grupos": [{**dict(x), "permissoes": load(x["permissoes_json"], {})} for x in grupos],
        "funcoes": [{**dict(x), "permissoes": load(x["permissoes_json"], {}), "restricoes": load(x["restricoes_json"], {})} for x in funcoes],
    }


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "adicionar_membro", "atribuir_funcao", "criar_funcao_contextual", "criar_grupo",
    "exigir_permissao_contextual", "listar_grupos_funcoes", "tem_permissao_contextual",
)
