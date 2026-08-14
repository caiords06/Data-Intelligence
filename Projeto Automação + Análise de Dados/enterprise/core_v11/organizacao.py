"""Estrutura organizacional hierárquica e multiunidade da V11."""
from __future__ import annotations

from auth.banco import conectar
from enterprise.core_v11.common import codigo, dump, escopo, json_objeto, registrar_evento, registrar_historico, texto

TIPOS_UNIDADE = {"Matriz", "Filial", "Unidade", "Departamento", "Equipe", "Centro de custo", "Projeto"}


def criar_unidade(dados: dict, ator: dict) -> int:
    empresa_id, filial_contexto = escopo(ator, "administrativo", "escrever")
    tipo = str(dados.get("tipo") or "Unidade").strip().capitalize()
    normalizados = {x.casefold(): x for x in TIPOS_UNIDADE}
    tipo = normalizados.get(tipo.casefold(), tipo)
    if tipo not in TIPOS_UNIDADE:
        raise ValueError("Tipo de unidade organizacional inválido.")
    nome = texto(dados.get("nome"), minimo=2, maximo=160, campo="Nome")
    codigo_unidade = codigo(dados.get("codigo"), campo="Código da unidade").upper()
    filial_id = int(dados["filial_id"]) if dados.get("filial_id") not in (None, "") else filial_contexto
    pai_id = int(dados["unidade_pai_id"]) if dados.get("unidade_pai_id") not in (None, "") else None
    departamento_id = int(dados["departamento_id"]) if dados.get("departamento_id") not in (None, "") else None
    centro_custo_id = int(dados["centro_custo_id"]) if dados.get("centro_custo_id") not in (None, "") else None
    extras = json_objeto(dados.get("dados"))
    with conectar() as con:
        if pai_id is not None and con.execute(
            "SELECT 1 FROM unidades_organizacionais WHERE id=? AND empresa_id=? AND ativo=1", (pai_id, empresa_id),
        ).fetchone() is None:
            raise ValueError("Unidade superior não pertence à empresa atual.")
        if filial_id is not None and con.execute(
            "SELECT 1 FROM filiais WHERE id=? AND empresa_id=? AND ativo=1", (filial_id, empresa_id),
        ).fetchone() is None:
            raise ValueError("Filial não pertence à empresa atual.")
        cursor = con.execute(
            """INSERT INTO unidades_organizacionais
               (empresa_id,filial_id,unidade_pai_id,departamento_id,centro_custo_id,tipo,codigo,nome,timezone,dados_json,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                empresa_id, filial_id, pai_id, departamento_id, centro_custo_id, tipo, codigo_unidade, nome,
                str(dados.get("timezone") or "America/Sao_Paulo")[:80], dump(extras), int(ator["id"]),
            ),
        )
        unidade_id = int(cursor.lastrowid)
        depois = {"id": unidade_id, "tipo": tipo, "codigo": codigo_unidade, "nome": nome, "unidade_pai_id": pai_id}
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="administrativo",
            recurso_tipo="unidades_organizacionais", recurso_id=unidade_id, acao="Criado", ator=ator, depois=depois,
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="administrativo", tipo="organizacao.unidade_criada",
            recurso_tipo="unidades_organizacionais", recurso_id=unidade_id, ator=ator, payload=depois,
        )
    return unidade_id


def listar_unidades(ator: dict, *, tipo: str | None = None, incluir_inativas: bool = False) -> list[dict]:
    empresa_id, filial_id = escopo(ator, "administrativo", "ler")
    filtros = ["u.empresa_id=?", "(u.filial_id=? OR ? IS NULL OR u.filial_id IS NULL)"]
    parametros: list = [empresa_id, filial_id, filial_id]
    if not incluir_inativas:
        filtros.append("u.ativo=1")
    if tipo:
        filtros.append("u.tipo=?"); parametros.append(str(tipo))
    with conectar() as con:
        rows = con.execute(
            f"""SELECT u.*,p.nome unidade_pai_nome,f.nome filial_nome,d.nome departamento_nome,c.nome centro_custo_nome
                FROM unidades_organizacionais u
                LEFT JOIN unidades_organizacionais p ON p.id=u.unidade_pai_id
                LEFT JOIN filiais f ON f.id=u.filial_id
                LEFT JOIN departamentos d ON d.id=u.departamento_id
                LEFT JOIN centros_custo c ON c.id=u.centro_custo_id
                WHERE {' AND '.join(filtros)} ORDER BY COALESCE(u.unidade_pai_id,0),u.tipo,u.nome""",
            tuple(parametros),
        ).fetchall()
    return [dict(x) for x in rows]


def arvore_organizacional(ator: dict) -> list[dict]:
    itens = listar_unidades(ator)
    por_pai: dict[int | None, list[dict]] = {}
    for item in itens:
        item["filhos"] = []
        por_pai.setdefault(int(item["unidade_pai_id"]) if item["unidade_pai_id"] is not None else None, []).append(item)
    for item in itens:
        item["filhos"] = por_pai.get(int(item["id"]), [])
    return por_pai.get(None, [])


def atualizar_unidade(unidade_id: int, dados: dict, ator: dict, *, expected_version: int) -> int:
    empresa_id, filial_id = escopo(ator, "administrativo", "escrever")
    permitidos = {"nome", "timezone", "dados_json", "ativo", "centro_custo_id", "departamento_id", "unidade_pai_id"}
    atualizacoes = {k: v for k, v in dados.items() if k in permitidos}
    if not atualizacoes:
        raise ValueError("Nenhuma alteração organizacional válida foi informada.")
    if "nome" in atualizacoes:
        atualizacoes["nome"] = texto(atualizacoes["nome"], minimo=2, maximo=160, campo="Nome")
    if "dados_json" in atualizacoes:
        atualizacoes["dados_json"] = dump(json_objeto(atualizacoes["dados_json"]))
    with conectar() as con:
        antes = con.execute("SELECT * FROM unidades_organizacionais WHERE id=? AND empresa_id=?", (int(unidade_id), empresa_id)).fetchone()
        if antes is None:
            raise ValueError("Unidade não encontrada.")
        colunas = ",".join(f"{k}=?" for k in atualizacoes)
        cursor = con.execute(
            f"""UPDATE unidades_organizacionais SET {colunas},versao_registro=versao_registro+1,
                atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND versao_registro=?""",
            (*atualizacoes.values(), int(unidade_id), empresa_id, int(expected_version)),
        )
        if cursor.rowcount != 1:
            raise ValueError("A unidade foi alterada por outro usuário. Atualize a página.")
        nova_versao = int(expected_version) + 1
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="administrativo",
            recurso_tipo="unidades_organizacionais", recurso_id=int(unidade_id), acao="Atualizado", ator=ator,
            antes=dict(antes), depois={**atualizacoes, "versao_registro": nova_versao},
        )
    return nova_versao


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = ("TIPOS_UNIDADE", "arvore_organizacional", "atualizar_unidade", "criar_unidade", "listar_unidades")
