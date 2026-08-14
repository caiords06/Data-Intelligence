"""Comentários, notificações, calendário, caixa de ações e dashboards."""
from __future__ import annotations

from datetime import datetime

from auth.banco import conectar
from enterprise.core_v11.common import dump, escopo, json_objeto, load, registrar_evento, registrar_historico, texto
from enterprise.core_v11.seguranca import exigir_permissao_contextual


def adicionar_comentario(
    recurso_tipo: str,
    recurso_id: int,
    comentario: str,
    ator: dict,
    *,
    modulo: str,
    interno: bool = False,
    comentario_pai_id: int | None = None,
) -> int:
    empresa_id, filial_id = escopo(ator)
    exigir_permissao_contextual(ator, modulo, "ler", {"recurso_tipo": recurso_tipo, "recurso_id": int(recurso_id)})
    conteudo = texto(comentario, minimo=1, maximo=10000, campo="Comentário")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_comentarios
               (empresa_id,filial_id,recurso_tipo,recurso_id,comentario_pai_id,texto,interno,criado_por)
               VALUES (?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, recurso_tipo, int(recurso_id), comentario_pai_id, conteudo, int(bool(interno)), int(ator["id"])),
        )
        comentario_id = int(cursor.lastrowid)
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="colaboracao.comentario_adicionado",
            recurso_tipo=recurso_tipo, recurso_id=int(recurso_id), ator=ator, payload={"comentario_id": comentario_id, "interno": bool(interno)},
        )
    return comentario_id


def listar_comentarios(recurso_tipo: str, recurso_id: int, ator: dict, *, modulo: str) -> list[dict]:
    empresa_id, _ = escopo(ator)
    exigir_permissao_contextual(ator, modulo, "ler", {"recurso_tipo": recurso_tipo, "recurso_id": int(recurso_id)})
    with conectar() as con:
        rows = con.execute(
            """SELECT c.*,u.nome autor_nome FROM core_comentarios c LEFT JOIN usuarios u ON u.id=c.criado_por
               WHERE c.empresa_id=? AND c.recurso_tipo=? AND c.recurso_id=? AND c.excluido_em IS NULL
               ORDER BY c.id""",
            (empresa_id, recurso_tipo, int(recurso_id)),
        ).fetchall()
    return [dict(x) for x in rows]


def notificar(
    usuario_id: int | None,
    titulo: str,
    mensagem: str,
    ator: dict,
    *,
    modulo: str,
    nivel: str = "info",
    recurso_tipo: str | None = None,
    recurso_id: int | None = None,
    acao_url: str | None = None,
) -> int:
    empresa_id, filial_id = escopo(ator)
    if nivel not in {"info", "sucesso", "aviso", "critico"}:
        raise ValueError("Nível de notificação inválido.")
    with conectar() as con:
        if usuario_id is not None and con.execute(
            "SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(usuario_id), empresa_id),
        ).fetchone() is None:
            raise ValueError("Destinatário fora do contexto empresarial.")
        cursor = con.execute(
            """INSERT INTO notificacoes
               (usuario_id,empresa_id,filial_id,modulo,titulo,mensagem,nivel,recurso_tipo,recurso_id,acao_url)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                int(usuario_id) if usuario_id is not None else None, empresa_id, filial_id, modulo,
                texto(titulo, minimo=2, maximo=180, campo="Título"), texto(mensagem, minimo=1, maximo=2000, campo="Mensagem"),
                nivel, recurso_tipo, recurso_id, str(acao_url or "")[:500] or None,
            ),
        )
        return int(cursor.lastrowid)


def criar_evento_calendario(dados: dict, ator: dict) -> int:
    modulo = str(dados.get("modulo") or "administrativo").strip().lower()
    empresa_id, filial_id = escopo(ator, modulo, "escrever")
    inicio = texto(dados.get("inicio"), minimo=10, maximo=40, campo="Início")
    fim = texto(dados.get("fim"), maximo=40) or None
    if fim and fim < inicio:
        raise ValueError("O término não pode ser anterior ao início.")
    participantes = dados.get("participantes") or []
    if not isinstance(participantes, list) or len(participantes) > 500:
        raise ValueError("Participantes inválidos.")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_calendario_eventos
               (empresa_id,filial_id,modulo,titulo,descricao,inicio,fim,dia_inteiro,timezone,
                recorrencia_json,local,recurso_tipo,recurso_id,visibilidade,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                empresa_id, filial_id, modulo, texto(dados.get("titulo"), minimo=2, maximo=180, campo="Título"),
                texto(dados.get("descricao"), maximo=4000), inicio, fim, int(bool(dados.get("dia_inteiro"))),
                str(dados.get("timezone") or "America/Sao_Paulo")[:80], dump(json_objeto(dados.get("recorrencia"))),
                texto(dados.get("local"), maximo=240), dados.get("recurso_tipo"), dados.get("recurso_id"),
                str(dados.get("visibilidade") or "Empresa")[:40], int(ator["id"]),
            ),
        )
        evento_id = int(cursor.lastrowid)
        for usuario_id in {int(x) for x in participantes if x not in (None, "")}:
            con.execute(
                """INSERT INTO core_calendario_participantes(evento_id,usuario_id)
                   VALUES (?,?) ON CONFLICT(evento_id,usuario_id) DO NOTHING""",
                (evento_id, usuario_id),
            )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="calendario.evento_criado",
            recurso_tipo="core_calendario_eventos", recurso_id=evento_id, ator=ator,
            payload={"titulo": dados.get("titulo"), "inicio": inicio, "fim": fim},
        )
    return evento_id


def listar_calendario(ator: dict, *, inicio: str, fim: str, modulo: str | None = None) -> list[dict]:
    empresa_id, filial_id = escopo(ator)
    filtros = ["e.empresa_id=?", "(e.filial_id=? OR ? IS NULL OR e.filial_id IS NULL)", "e.inicio<=?", "COALESCE(e.fim,e.inicio)>=?", "e.status<>'Cancelado'"]
    parametros: list = [empresa_id, filial_id, filial_id, str(fim), str(inicio)]
    if modulo:
        filtros.append("e.modulo=?"); parametros.append(str(modulo))
    with conectar() as con:
        rows = con.execute(
            f"""SELECT e.*,u.nome criado_por_nome FROM core_calendario_eventos e
                LEFT JOIN usuarios u ON u.id=e.criado_por WHERE {' AND '.join(filtros)} ORDER BY e.inicio,e.id""",
            tuple(parametros),
        ).fetchall()
    return [{**dict(x), "recorrencia": load(x["recorrencia_json"], {})} for x in rows]


def caixa_entrada(ator: dict, *, limite: int = 100) -> dict:
    empresa_id, filial_id = escopo(ator); usuario_id = int(ator["id"]); limite = max(1, min(int(limite), 500))
    with conectar() as con:
        notificacoes = con.execute(
            """SELECT * FROM notificacoes WHERE empresa_id=? AND (filial_id=? OR ? IS NULL OR filial_id IS NULL)
               AND (usuario_id=? OR usuario_id IS NULL) AND lida=0 AND COALESCE(arquivada,0)=0 ORDER BY id DESC LIMIT ?""",
            (empresa_id, filial_id, filial_id, usuario_id, limite),
        ).fetchall()
        tarefas = con.execute(
            """SELECT * FROM tarefas WHERE empresa_id=? AND (filial_id=? OR ? IS NULL OR filial_id IS NULL)
               AND (responsavel_id=? OR responsavel_id IS NULL) AND status NOT IN ('Concluída','Cancelada')
               AND COALESCE(estado_registro,'Ativo')='Ativo' ORDER BY id DESC LIMIT ?""",
            (empresa_id, filial_id, filial_id, usuario_id, limite),
        ).fetchall()
        aprovacoes = con.execute(
            """SELECT * FROM aprovacoes WHERE empresa_id=? AND (filial_id=? OR ? IS NULL OR filial_id IS NULL)
               AND status='Pendente' AND (responsavel_id=? OR responsavel_id IS NULL) ORDER BY id DESC LIMIT ?""",
            (empresa_id, filial_id, filial_id, usuario_id, limite),
        ).fetchall()
    return {
        "notificacoes": [dict(x) for x in notificacoes], "tarefas": [dict(x) for x in tarefas],
        "aprovacoes": [dict(x) for x in aprovacoes],
        "totais": {"notificacoes": len(notificacoes), "tarefas": len(tarefas), "aprovacoes": len(aprovacoes)},
    }


def salvar_dashboard(dados: dict, ator: dict, *, dashboard_id: int | None = None, expected_version: int | None = None) -> dict:
    empresa_id, filial_id = escopo(ator)
    nome = texto(dados.get("nome"), minimo=2, maximo=120, campo="Nome")
    layout = json_objeto(dados.get("layout"), campo="Layout")
    widgets = dados.get("widgets") or []
    if not isinstance(widgets, list) or len(widgets) > 100:
        raise ValueError("Widgets inválidos.")
    with conectar() as con:
        if dashboard_id is None:
            cursor = con.execute(
                """INSERT INTO core_dashboards
                   (empresa_id,filial_id,usuario_id,nome,escopo,layout_json,padrao,criado_por)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    empresa_id, filial_id, int(ator["id"]) if str(dados.get("escopo") or "Usuario") == "Usuario" else None,
                    nome, str(dados.get("escopo") or "Usuario")[:30], dump(layout), int(bool(dados.get("padrao"))), int(ator["id"]),
                ),
            )
            dashboard_id = int(cursor.lastrowid); versao = 0
        else:
            if expected_version is None:
                raise ValueError("expected_version é obrigatório para atualizar o dashboard.")
            cursor = con.execute(
                """UPDATE core_dashboards SET nome=?,layout_json=?,padrao=?,versao_registro=versao_registro+1,
                   atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND versao_registro=?""",
                (nome, dump(layout), int(bool(dados.get("padrao"))), int(dashboard_id), empresa_id, int(expected_version)),
            )
            if cursor.rowcount != 1:
                raise ValueError("Dashboard alterado por outro usuário.")
            versao = int(expected_version) + 1
            con.execute("DELETE FROM core_dashboard_widgets WHERE dashboard_id=?", (int(dashboard_id),))
        for ordem, widget in enumerate(widgets):
            widget = json_objeto(widget, campo="Widget")
            con.execute(
                """INSERT INTO core_dashboard_widgets
                   (dashboard_id,tipo,titulo,fonte,configuracao_json,posicao_json,ordem) VALUES (?,?,?,?,?,?,?)""",
                (
                    int(dashboard_id), str(widget.get("tipo") or "indicador")[:40],
                    texto(widget.get("titulo"), minimo=1, maximo=120, campo="Título do widget"),
                    texto(widget.get("fonte"), minimo=1, maximo=180, campo="Fonte"),
                    dump(json_objeto(widget.get("configuracao"))), dump(json_objeto(widget.get("posicao"))), ordem,
                ),
            )
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="analytics", recurso_tipo="core_dashboards",
            recurso_id=int(dashboard_id), acao="Salvo", ator=ator, depois={"nome": nome, "widgets": len(widgets), "versao": versao},
        )
    return {"id": int(dashboard_id), "versao_registro": versao}


def listar_dashboards(ator: dict) -> list[dict]:
    empresa_id, filial_id = escopo(ator)
    with conectar() as con:
        rows = con.execute(
            """SELECT * FROM core_dashboards WHERE empresa_id=? AND (filial_id=? OR ? IS NULL OR filial_id IS NULL)
               AND ativo=1 AND (usuario_id=? OR usuario_id IS NULL) ORDER BY padrao DESC,nome""",
            (empresa_id, filial_id, filial_id, int(ator["id"])),
        ).fetchall()
        resultado = []
        for row in rows:
            item = dict(row); item["layout"] = load(item.pop("layout_json"), {})
            widgets = con.execute("SELECT * FROM core_dashboard_widgets WHERE dashboard_id=? ORDER BY ordem,id", (int(item["id"]),)).fetchall()
            item["widgets"] = [{**dict(w), "configuracao": load(w["configuracao_json"], {}), "posicao": load(w["posicao_json"], {})} for w in widgets]
            resultado.append(item)
    return resultado


def salvar_preferencia_contextual(chave: str, valor: dict, ator: dict, *, escopo_preferencia: str = "Usuario") -> int:
    empresa_id, filial_id = escopo(ator); chave = texto(chave, minimo=2, maximo=120, campo="Chave")
    usuario_id = int(ator["id"]) if escopo_preferencia == "Usuario" else None
    filial_alvo = filial_id if escopo_preferencia in {"Usuario", "Filial"} else None
    conteudo = dump(json_objeto(valor, campo="Preferência"))
    with conectar() as con:
        row = con.execute(
            """SELECT id FROM core_preferencias_contextuais WHERE empresa_id=?
               AND COALESCE(filial_id,0)=COALESCE(?,0) AND COALESCE(usuario_id,0)=COALESCE(?,0) AND chave=?""",
            (empresa_id, filial_alvo, usuario_id, chave),
        ).fetchone()
        if row:
            con.execute(
                """UPDATE core_preferencias_contextuais SET valor_json=?,versao_registro=versao_registro+1,
                   atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
                (conteudo, int(ator["id"]), int(row["id"])),
            )
            return int(row["id"])
        cursor = con.execute(
            """INSERT INTO core_preferencias_contextuais
               (empresa_id,filial_id,usuario_id,chave,valor_json,atualizado_por) VALUES (?,?,?,?,?,?)""",
            (empresa_id, filial_alvo, usuario_id, chave, conteudo, int(ator["id"])),
        )
        return int(cursor.lastrowid)


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "adicionar_comentario", "caixa_entrada", "criar_evento_calendario", "listar_calendario",
    "listar_comentarios", "listar_dashboards", "notificar", "salvar_dashboard", "salvar_preferencia_contextual",
)
