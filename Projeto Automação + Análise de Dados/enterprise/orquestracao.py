"""Orquestração empresarial transversal — V10.4.1.

Fluxos entre departamentos são registrados e auditáveis. A camada não executa
baixas financeiras, bloqueios de identidade ou compras irreversíveis sem uma
ação explícita no módulo responsável.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Iterable

from auth.banco import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator, tem_permissao


def _agora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _escopo(ator: dict) -> tuple[int, int | None]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    return int(empresa_id), int(filial_id) if filial_id is not None else None


def _linha(row):
    if row is None:
        return None
    item = dict(row)
    try:
        item["dados"] = json.loads(item.get("dados_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        item["dados"] = {}
    return item


def _criar_orquestracao(
    *, ator: dict, tipo: str, titulo: str, referencia_tipo: str | None = None,
    referencia_id: int | None = None, etapas: Iterable[tuple[str, str, str]],
    dados: dict | None = None,
) -> int:
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        if referencia_tipo and referencia_id is not None:
            existente = con.execute(
                """SELECT id FROM orquestracoes_empresariais
                   WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL) AND tipo=?
                     AND referencia_tipo=? AND referencia_id=? AND status NOT IN ('Cancelada','Concluída')
                   ORDER BY id DESC LIMIT 1""",
                (empresa_id, filial_id, tipo, referencia_tipo, int(referencia_id)),
            ).fetchone()
            if existente:
                return int(existente["id"])
        cur = con.execute(
            """INSERT INTO orquestracoes_empresariais
               (empresa_id,filial_id,tipo,referencia_tipo,referencia_id,titulo,status,responsavel_id,dados_json,criado_por)
               VALUES (?,?,?,?,?,?,'Aberta',?,?,?)""",
            (empresa_id, filial_id, tipo, referencia_tipo, int(referencia_id) if referencia_id is not None else None,
             str(titulo).strip()[:220], int(ator["id"]), json.dumps(dados or {}, ensure_ascii=False, default=str), int(ator["id"])),
        )
        oid = int(cur.lastrowid)
        for ordem, (codigo, titulo_etapa, modulo) in enumerate(etapas, 1):
            con.execute(
                """INSERT INTO orquestracao_etapas
                   (orquestracao_id,codigo,titulo,modulo,ordem,status,responsavel_id,dados_json)
                   VALUES (?,?,?,?,?,'Pendente',?, '{}')""",
                (oid, codigo, titulo_etapa, modulo, ordem, int(ator["id"])),
            )
    return oid


def converter_lead_em_oportunidade(lead_id: int, dados: dict, ator: dict) -> dict:
    """Reaproveita o CRM do Marketing e cria uma oportunidade comercial idempotente."""
    exigir_permissao(ator, "marketing", "ler")
    exigir_permissao(ator, "comercial", "escrever")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        lead = con.execute(
            """SELECT l.*,c.nome AS contato_nome,e.nome AS empresa_nome
               FROM crm_leads l LEFT JOIN crm_contatos c ON c.id=l.contato_id
               LEFT JOIN crm_empresas e ON e.id=l.crm_empresa_id
               WHERE l.id=? AND l.empresa_id=? AND (l.filial_id=? OR l.filial_id IS NULL)""",
            (int(lead_id), empresa_id, filial_id),
        ).fetchone()
        if lead is None:
            raise ValueError("Lead não encontrado no contexto atual.")
        if str(lead["status"]) not in {"MQL", "SQL", "Convertido"}:
            raise ValueError("Somente leads qualificados (MQL/SQL) podem ser enviados ao Comercial.")
        existente = con.execute(
            """SELECT id,status FROM comercial_oportunidades
               WHERE empresa_id=? AND lead_id=? AND status<>'Perdida' ORDER BY id DESC LIMIT 1""",
            (empresa_id, int(lead_id)),
        ).fetchone()
    if existente:
        return {"oportunidade_id": int(existente["id"]), "criada": False, "status": existente["status"]}

    from enterprise.comercial import criar_oportunidade
    from enterprise.crm import registrar_atividade, atualizar_lead_status
    titulo = str(dados.get("titulo") or lead["empresa_nome"] or lead["contato_nome"] or f"Lead #{lead_id}").strip()
    oid = criar_oportunidade({
        "crm_empresa_id": lead["crm_empresa_id"], "contato_id": lead["contato_id"], "lead_id": int(lead_id),
        "titulo": titulo, "valor": dados.get("valor") or 0, "probabilidade": dados.get("probabilidade") or 25,
        "fechamento_previsto": dados.get("fechamento_previsto") or "", "proxima_acao": dados.get("proxima_acao") or "Primeiro contato comercial",
        "status": "Aberta",
    }, ator)
    atualizar_lead_status(int(lead_id), "SQL", ator)
    registrar_atividade({
        "lead_id": int(lead_id), "oportunidade_id": oid, "tipo": "Encaminhamento ao Comercial",
        "descricao": f"Lead qualificado convertido em oportunidade comercial #{oid} sem duplicação cadastral.",
        "proxima_acao": dados.get("proxima_acao") or "Realizar primeiro contato comercial",
    }, ator)
    fluxo = _criar_orquestracao(
        ator=ator, tipo="marketing_comercial", titulo=f"Marketing → Comercial · {titulo}",
        referencia_tipo="crm_leads", referencia_id=int(lead_id), dados={"oportunidade_id": oid},
        etapas=(("lead_qualificado", "Lead qualificado pelo Marketing", "marketing"),
                ("oportunidade_criada", "Oportunidade criada com o mesmo CRM", "comercial"),
                ("primeiro_contato", "Executar primeiro contato comercial", "comercial")),
    )
    # As duas primeiras etapas já ocorreram nesta operação.
    with conectar() as con:
        con.execute("UPDATE orquestracao_etapas SET status='Concluída',concluido_em=?,concluido_por=? WHERE orquestracao_id=? AND codigo IN ('lead_qualificado','oportunidade_criada')",
                    (_agora(), int(ator["id"]), fluxo))
    return {"oportunidade_id": oid, "orquestracao_id": fluxo, "criada": True, "status": "Aberta"}


def criar_fluxo_admissao(colaborador_id: int, ator: dict) -> int:
    exigir_permissao(ator, "rh", "escrever")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        col = con.execute("SELECT id,nome_completo,status FROM rh_colaboradores WHERE id=? AND empresa_id=? AND (filial_id=? OR filial_id IS NULL)",
                          (int(colaborador_id), empresa_id, filial_id)).fetchone()
        if col is None: raise ValueError("Colaborador não encontrado.")
    return _criar_orquestracao(
        ator=ator, tipo="admissao", titulo=f"Admissão integrada · {col['nome_completo']}",
        referencia_tipo="rh_colaboradores", referencia_id=int(colaborador_id), dados={"status_colaborador": col["status"]},
        etapas=(("rh_documentos", "RH · validar documentos e jornada", "rh"),
                ("ti_identidade", "TI · criar identidade e acessos", "ti"),
                ("ti_dispositivo", "TI · preparar dispositivo", "ti"),
                ("estoque_equipamento", "Estoque · separar e vincular equipamentos", "estoque"),
                ("administrativo_estrutura", "Administrativo · preparar estrutura física", "administrativo"),
                ("rh_concluir", "RH · concluir admissão", "rh")),
    )


def criar_fluxo_desligamento(colaborador_id: int, ator: dict) -> int:
    exigir_permissao(ator, "rh", "escrever")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        col = con.execute("SELECT id,nome_completo,status FROM rh_colaboradores WHERE id=? AND empresa_id=? AND (filial_id=? OR filial_id IS NULL)",
                          (int(colaborador_id), empresa_id, filial_id)).fetchone()
        if col is None: raise ValueError("Colaborador não encontrado.")
    return _criar_orquestracao(
        ator=ator, tipo="desligamento", titulo=f"Desligamento integrado · {col['nome_completo']}",
        referencia_tipo="rh_colaboradores", referencia_id=int(colaborador_id), dados={"status_colaborador": col["status"]},
        etapas=(("rh_rescisao", "RH · preparar rescisão e documentos", "rh"),
                ("ti_revogar", "TI · revogar identidade e acessos", "ti"),
                ("estoque_recolher", "Estoque · recolher equipamentos", "estoque"),
                ("administrativo_encerrar", "Administrativo · encerrar recursos físicos", "administrativo"),
                ("financeiro_pendencias", "Financeiro · calcular e liquidar pendências", "financeiro"),
                ("rh_concluir", "RH · concluir desligamento", "rh")),
    )


def encaminhar_provisao_financeiro(provisao_id: int, ator: dict) -> dict:
    """Cria uma solicitação auditável; não cria lançamento contábil silenciosamente."""
    exigir_permissao(ator, "juridico", "escrever")
    if not tem_permissao(ator, "financeiro", "ler"):
        raise PermissionError("Seu perfil precisa de acesso ao Financeiro para encaminhar provisões.")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        p = con.execute("SELECT * FROM juridico_provisoes WHERE id=? AND empresa_id=? AND (filial_id=? OR filial_id IS NULL)",
                        (int(provisao_id), empresa_id, filial_id)).fetchone()
        if p is None: raise ValueError("Provisão jurídica não encontrada.")
    oid = _criar_orquestracao(
        ator=ator, tipo="juridico_financeiro", titulo=f"Provisão jurídica → Financeiro · {p['referencia']}",
        referencia_tipo="juridico_provisoes", referencia_id=int(provisao_id),
        dados={"valor_centavos": int(p["valor_centavos"] or 0), "referencia": p["referencia"]},
        etapas=(("juridico_validar", "Jurídico · validar risco, valor e referência", "juridico"),
                ("financeiro_analisar", "Financeiro · analisar classificação e competência", "financeiro"),
                ("financeiro_registrar", "Financeiro · registrar provisão após aprovação", "financeiro")),
    )
    return {"orquestracao_id": oid, "provisao_id": int(provisao_id), "status": "Aberta"}


def criar_fluxo_reposicao(reposicao_id: int, ator: dict) -> dict:
    """Encaminha uma sugestão de Estoque à fila de Compras e registra o fluxo."""
    exigir_permissao(ator, "estoque", "escrever")
    if not tem_permissao(ator, "compras", "ler"):
        raise PermissionError("Seu perfil precisa de acesso a Compras para encaminhar reposição.")
    from enterprise.estoque import encaminhar_reposicao_compras
    compra_id = encaminhar_reposicao_compras(int(reposicao_id), ator)
    oid = _criar_orquestracao(
        ator=ator, tipo="estoque_compras", titulo=f"Reposição de estoque → Compras · #{reposicao_id}",
        referencia_tipo="est_reposicoes", referencia_id=int(reposicao_id), dados={"solicitacao_compra_id": compra_id},
        etapas=(("estoque_sugeriu", "Estoque · validar necessidade de reposição", "estoque"),
                ("compras_cotacao", "Compras · cotar e selecionar fornecedor", "compras"),
                ("compras_pedido", "Compras · emitir pedido aprovado", "compras"),
                ("estoque_receber", "Estoque · receber e conferir material", "estoque")),
    )
    with conectar() as con:
        con.execute("UPDATE orquestracao_etapas SET status='Concluída',concluido_em=?,concluido_por=? WHERE orquestracao_id=? AND codigo='estoque_sugeriu'",
                    (_agora(), int(ator["id"]), oid))
    return {"orquestracao_id": oid, "solicitacao_compra_id": compra_id}


def _filtro_orquestracoes(ator: dict, *, tipo: str | None = None, status: str | None = None) -> tuple[list[str], list]:
    empresa_id, filial_id = _escopo(ator)
    where=["empresa_id=?","(filial_id=? OR filial_id IS NULL)"]; params=[empresa_id,filial_id]
    if tipo: where.append("tipo=?"); params.append(str(tipo))
    if status and status != "Todos": where.append("status=?"); params.append(str(status))
    return where, params


def contar_orquestracoes(ator: dict, *, tipo: str | None = None, status: str | None = None) -> int:
    exigir_permissao(ator, "analytics", "ler")
    where, params = _filtro_orquestracoes(ator, tipo=tipo, status=status)
    with conectar() as con:
        row=con.execute(f"SELECT COUNT(*) AS total FROM orquestracoes_empresariais WHERE {' AND '.join(where)}",tuple(params)).fetchone()
    return int(row["total"] or 0)


def listar_orquestracoes(ator: dict, *, tipo: str | None = None, status: str | None = None, limite: int = 300, offset: int = 0) -> list[dict]:
    exigir_permissao(ator, "analytics", "ler")
    where, params = _filtro_orquestracoes(ator, tipo=tipo, status=status)
    params.extend([max(1,min(5000,int(limite))),max(0,int(offset))])
    with conectar() as con:
        rows=con.execute(f"SELECT * FROM orquestracoes_empresariais WHERE {' AND '.join(where)} ORDER BY CASE status WHEN 'Aberta' THEN 0 WHEN 'Em andamento' THEN 1 ELSE 2 END,id DESC LIMIT ? OFFSET ?",tuple(params)).fetchall()
    return [_linha(x) for x in rows]


def listar_etapas_orquestracao(orquestracao_id: int, ator: dict) -> list[dict]:
    exigir_permissao(ator, "analytics", "ler")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        ok=con.execute("SELECT 1 FROM orquestracoes_empresariais WHERE id=? AND empresa_id=? AND (filial_id=? OR filial_id IS NULL)",
                       (int(orquestracao_id),empresa_id,filial_id)).fetchone()
        if ok is None: raise ValueError("Orquestração não encontrada.")
        rows=con.execute("SELECT * FROM orquestracao_etapas WHERE orquestracao_id=? ORDER BY ordem,id",(int(orquestracao_id),)).fetchall()
    return [dict(x) for x in rows]


def concluir_etapa(etapa_id: int, ator: dict) -> dict:
    exigir_permissao(ator, "analytics", "escrever")
    empresa_id, filial_id = _escopo(ator); agora=_agora()
    with conectar() as con:
        row=con.execute("""SELECT e.*,o.empresa_id,o.filial_id FROM orquestracao_etapas e
                           JOIN orquestracoes_empresariais o ON o.id=e.orquestracao_id
                           WHERE e.id=? AND o.empresa_id=? AND (o.filial_id=? OR o.filial_id IS NULL)""",
                        (int(etapa_id),empresa_id,filial_id)).fetchone()
        if row is None: raise ValueError("Etapa não encontrada.")
        modulo=str(row["modulo"] or "analytics")
        if modulo != "analytics" and not tem_permissao(ator,modulo,"escrever"):
            raise PermissionError(f"Seu perfil não pode concluir etapas do módulo {modulo}.")
        con.execute("UPDATE orquestracao_etapas SET status='Concluída',concluido_em=?,concluido_por=? WHERE id=?",
                    (agora,int(ator["id"]),int(etapa_id)))
        pend=con.execute("SELECT COUNT(*) n FROM orquestracao_etapas WHERE orquestracao_id=? AND status<>'Concluída'",(int(row["orquestracao_id"]),)).fetchone()
        if int(pend["n"] or 0)==0:
            con.execute("UPDATE orquestracoes_empresariais SET status='Concluída',concluido_em=?,atualizado_em=? WHERE id=?",
                        (agora,agora,int(row["orquestracao_id"])))
        else:
            con.execute("UPDATE orquestracoes_empresariais SET status='Em andamento',atualizado_em=? WHERE id=?",(agora,int(row["orquestracao_id"])))
    return {"id":int(etapa_id),"status":"Concluída","orquestracao_id":int(row["orquestracao_id"])}


def resumo_orquestracoes(ator: dict) -> dict:
    exigir_permissao(ator,"analytics","ler"); empresa_id,filial_id=_escopo(ator)
    with conectar() as con:
        r=con.execute("""SELECT COUNT(*) total,
            SUM(CASE WHEN status='Aberta' THEN 1 ELSE 0 END) abertas,
            SUM(CASE WHEN status='Em andamento' THEN 1 ELSE 0 END) andamento,
            SUM(CASE WHEN status='Concluída' THEN 1 ELSE 0 END) concluidas
            FROM orquestracoes_empresariais WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL)""",
            (empresa_id,filial_id)).fetchone()
    return {k:int(r[k] or 0) for k in ("total","abertas","andamento","concluidas")}


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__=("converter_lead_em_oportunidade","criar_fluxo_admissao","criar_fluxo_desligamento",
         "encaminhar_provisao_financeiro","criar_fluxo_reposicao","listar_orquestracoes","contar_orquestracoes",
         "listar_etapas_orquestracao","concluir_etapa","resumo_orquestracoes")
