"""Domínio especializado de Marketing — V10.3.0."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd

from auth.banco import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator
from enterprise.crm import criar_lead, listar_leads, resumo_crm

STATUS_CAMPANHA = {"Planejada", "Em produção", "Ativa", "Pausada", "Concluída", "Cancelada"}


def _linha(r):
    return {k: r[k] for k in r.keys()} if r is not None else None


def _texto(v, *, obrigatorio=False, nome="Campo", maximo=500):
    v = str(v or "").strip()
    if obrigatorio and not v:
        raise ValueError(f"{nome} é obrigatório.")
    if len(v) > maximo:
        raise ValueError(f"{nome} deve possuir no máximo {maximo} caracteres.")
    return v


def _centavos(v):
    if v in (None, ""):
        return 0
    t = str(v).strip().replace("R$", "").replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        d = Decimal(t).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor monetário inválido.") from exc
    if not d.is_finite() or d < 0:
        raise ValueError("O valor monetário deve ser positivo e finito.")
    return int(d * 100)


def _escopo(ator):
    empresa_id, filial_id = obter_escopo_ator(ator)
    return int(empresa_id), int(filial_id) if filial_id is not None else None


def criar_canal(dados: dict, ator: dict) -> int:
    exigir_permissao(ator, "marketing", "escrever")
    empresa_id, filial_id = _escopo(ator)
    nome = _texto(dados.get("nome"), obrigatorio=True, nome="Nome do canal")
    with conectar() as con:
        existente = con.execute("SELECT id FROM marketing_canais WHERE empresa_id=? AND nome=?", (empresa_id, nome)).fetchone()
        if existente:
            return int(existente["id"])
        cur = con.execute(
            "INSERT INTO marketing_canais (empresa_id,filial_id,nome,tipo,custo_mensal_centavos,status,criado_por) VALUES (?,?,?,?,?,?,?)",
            (empresa_id, filial_id, nome, _texto(dados.get("tipo") or "Outro"), _centavos(dados.get("custo_mensal")),
             _texto(dados.get("status") or "Ativo"), int(ator["id"])),
        )
        return int(cur.lastrowid)


def listar_canais(ator: dict) -> list[dict]:
    exigir_permissao(ator, "marketing", "ler")
    empresa_id, _ = _escopo(ator)
    with conectar() as con:
        rows = con.execute("SELECT * FROM marketing_canais WHERE empresa_id=? ORDER BY status DESC,nome", (empresa_id,)).fetchall()
    return [_linha(x) for x in rows]


def criar_campanha(dados: dict, ator: dict) -> int:
    exigir_permissao(ator, "marketing", "escrever")
    empresa_id, filial_id = _escopo(ator)
    nome = _texto(dados.get("nome"), obrigatorio=True, nome="Nome da campanha")
    status = _texto(dados.get("status") or "Planejada")
    if status not in STATUS_CAMPANHA:
        raise ValueError("Status de campanha inválido.")
    canal_id = int(dados["canal_id"]) if dados.get("canal_id") not in (None, "") else None
    with conectar() as con:
        if canal_id is not None and con.execute("SELECT 1 FROM marketing_canais WHERE id=? AND empresa_id=?", (canal_id, empresa_id)).fetchone() is None:
            raise ValueError("Canal inválido para a empresa atual.")
        cur = con.execute(
            """INSERT INTO marketing_campanhas
               (empresa_id,filial_id,nome,objetivo,canal_id,publico,orcamento_centavos,investimento_centavos,
                receita_atribuida_centavos,inicio,fim,responsavel_id,status,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, nome, _texto(dados.get("objetivo")), canal_id, _texto(dados.get("publico")),
             _centavos(dados.get("orcamento")), _centavos(dados.get("investimento")), _centavos(dados.get("receita_atribuida")),
             _texto(dados.get("inicio")), _texto(dados.get("fim")), int(ator["id"]), status, int(ator["id"])),
        )
        return int(cur.lastrowid)


def _filtro_campanhas(ator: dict, *, pesquisa="", status=None) -> tuple[list[str], list]:
    empresa_id, filial_id = _escopo(ator)
    where = ["c.empresa_id=?"]
    params = [empresa_id]
    if filial_id is not None:
        where.append("(c.filial_id=? OR c.filial_id IS NULL)")
        params.append(filial_id)
    if status:
        where.append("c.status=?")
        params.append(str(status))
    termo = f"%{str(pesquisa or '').strip()}%"
    where.append("(c.nome LIKE ? OR COALESCE(c.objetivo,'') LIKE ?)")
    params.extend([termo, termo])
    return where, params


def contar_campanhas(ator: dict, *, pesquisa="", status=None) -> int:
    exigir_permissao(ator, "marketing", "ler")
    where, params = _filtro_campanhas(ator, pesquisa=pesquisa, status=status)
    with conectar() as con:
        row = con.execute(f"SELECT COUNT(*) AS total FROM marketing_campanhas c WHERE {' AND '.join(where)}", tuple(params)).fetchone()
    return int(row["total"] or 0)


def listar_campanhas(ator: dict, *, pesquisa="", status=None, limite=500, offset=0) -> list[dict]:
    exigir_permissao(ator, "marketing", "ler")
    where, params = _filtro_campanhas(ator, pesquisa=pesquisa, status=status)
    params.extend([max(1, min(5000, int(limite))), max(0, int(offset))])
    with conectar() as con:
        rows = con.execute(
            f"""SELECT c.*, mc.nome AS canal_nome FROM marketing_campanhas c
                 LEFT JOIN marketing_canais mc ON mc.id=c.canal_id
                 WHERE {' AND '.join(where)}
                 ORDER BY c.id DESC LIMIT ? OFFSET ?""", tuple(params)).fetchall()
    return [_linha(x) for x in rows]


def atualizar_status_campanha(campanha_id: int, status: str, ator: dict) -> dict:
    exigir_permissao(ator, "marketing", "escrever")
    if status not in STATUS_CAMPANHA:
        raise ValueError("Status de campanha inválido.")
    empresa_id, _ = _escopo(ator)
    with conectar() as con:
        cur = con.execute("UPDATE marketing_campanhas SET status=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?", (status, int(campanha_id), empresa_id))
        if cur.rowcount != 1:
            raise ValueError("Campanha não encontrada.")
    return {"id": int(campanha_id), "status": status}


def criar_conteudo(dados: dict, ator: dict) -> int:
    exigir_permissao(ator, "marketing", "escrever")
    empresa_id, filial_id = _escopo(ator)
    titulo = _texto(dados.get("titulo"), obrigatorio=True, nome="Título")
    campanha_id = int(dados["campanha_id"]) if dados.get("campanha_id") not in (None, "") else None
    with conectar() as con:
        cur = con.execute(
            """INSERT INTO marketing_conteudos
               (empresa_id,filial_id,campanha_id,titulo,formato,canal,etapa,responsavel_id,data_publicacao,observacoes,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, campanha_id, titulo, _texto(dados.get("formato") or "Post"),
             _texto(dados.get("canal")), _texto(dados.get("etapa") or "Pauta"), int(ator["id"]),
             _texto(dados.get("data_publicacao")), _texto(dados.get("observacoes"), maximo=2000), int(ator["id"])),
        )
        return int(cur.lastrowid)


def listar_conteudos(ator: dict, *, limite=500) -> list[dict]:
    exigir_permissao(ator, "marketing", "ler")
    empresa_id, filial_id = _escopo(ator)
    params = [empresa_id]
    filtro = "x.empresa_id=?"
    if filial_id is not None:
        filtro += " AND (x.filial_id=? OR x.filial_id IS NULL)"
        params.append(filial_id)
    params.append(max(1, min(2000, int(limite))))
    with conectar() as con:
        rows = con.execute(f"""SELECT x.*,c.nome AS campanha_nome FROM marketing_conteudos x
            LEFT JOIN marketing_campanhas c ON c.id=x.campanha_id WHERE {filtro}
            ORDER BY COALESCE(x.data_publicacao,'9999-12-31'),x.id DESC LIMIT ?""", tuple(params)).fetchall()
    return [_linha(x) for x in rows]


def criar_automacao(dados: dict, ator: dict) -> int:
    exigir_permissao(ator, "marketing", "escrever")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        cur = con.execute(
            """INSERT INTO marketing_automacoes (empresa_id,filial_id,nome,gatilho,acao,campanha_id,ativo,criado_por)
               VALUES (?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, _texto(dados.get("nome"), obrigatorio=True, nome="Nome"),
             _texto(dados.get("gatilho"), obrigatorio=True, nome="Gatilho"), _texto(dados.get("acao"), obrigatorio=True, nome="Ação", maximo=1000),
             int(dados["campanha_id"]) if dados.get("campanha_id") not in (None, "") else None,
             1 if bool(dados.get("ativo", True)) else 0, int(ator["id"])),
        )
        return int(cur.lastrowid)


def listar_automacoes(ator: dict) -> list[dict]:
    exigir_permissao(ator, "marketing", "ler")
    empresa_id, _ = _escopo(ator)
    with conectar() as con:
        rows = con.execute("SELECT * FROM marketing_automacoes WHERE empresa_id=? ORDER BY ativo DESC,id DESC", (empresa_id,)).fetchall()
    return [_linha(x) for x in rows]


def registrar_metricas(campanha_id: int, referencia: str, dados: dict, ator: dict) -> dict:
    exigir_permissao(ator, "marketing", "escrever")
    empresa_id, filial_id = _escopo(ator)
    valores = {
        "impressoes": max(0, int(dados.get("impressoes") or 0)), "cliques": max(0, int(dados.get("cliques") or 0)),
        "leads": max(0, int(dados.get("leads") or 0)), "mqls": max(0, int(dados.get("mqls") or 0)),
        "conversoes": max(0, int(dados.get("conversoes") or 0)), "investimento": _centavos(dados.get("investimento")),
        "receita": _centavos(dados.get("receita")),
    }
    referencia = _texto(referencia, obrigatorio=True, nome="Referência", maximo=40)
    with conectar() as con:
        if con.execute("SELECT 1 FROM marketing_campanhas WHERE id=? AND empresa_id=?", (int(campanha_id), empresa_id)).fetchone() is None:
            raise ValueError("Campanha não encontrada.")
        con.execute(
            """INSERT INTO marketing_metricas
               (empresa_id,filial_id,campanha_id,referencia,impressoes,cliques,leads,mqls,conversoes,investimento_centavos,receita_centavos,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(campanha_id,referencia) DO UPDATE SET
               impressoes=excluded.impressoes,cliques=excluded.cliques,leads=excluded.leads,mqls=excluded.mqls,
               conversoes=excluded.conversoes,investimento_centavos=excluded.investimento_centavos,receita_centavos=excluded.receita_centavos""",
            (empresa_id, filial_id, int(campanha_id), referencia, valores["impressoes"], valores["cliques"], valores["leads"], valores["mqls"],
             valores["conversoes"], valores["investimento"], valores["receita"], int(ator["id"])),
        )
    return valores


def resumo_marketing(ator: dict) -> dict:
    exigir_permissao(ator, "marketing", "ler")
    empresa_id, filial_id = _escopo(ator)
    params = [empresa_id]
    filtro = "empresa_id=?"
    if filial_id is not None:
        filtro += " AND (filial_id=? OR filial_id IS NULL)"
        params.append(filial_id)
    with conectar() as con:
        c = _linha(con.execute(f"""SELECT COUNT(*) total,
            SUM(CASE WHEN status='Ativa' THEN 1 ELSE 0 END) ativas,
            COALESCE(SUM(investimento_centavos),0) investimento,
            COALESCE(SUM(receita_atribuida_centavos),0) receita FROM marketing_campanhas WHERE {filtro}""", tuple(params)).fetchone())
        m = _linha(con.execute(f"""SELECT COALESCE(SUM(leads),0) leads,COALESCE(SUM(mqls),0) mqls,
            COALESCE(SUM(conversoes),0) conversoes,COALESCE(SUM(investimento_centavos),0) investimento,
            COALESCE(SUM(receita_centavos),0) receita FROM marketing_metricas WHERE {filtro}""", tuple(params)).fetchone())
    crm = resumo_crm(ator)
    investimento = int(m.get("investimento") or c.get("investimento") or 0)
    receita = int(m.get("receita") or c.get("receita") or 0)
    leads = int(m.get("leads") or crm.get("leads") or 0)
    conversoes = int(m.get("conversoes") or crm.get("convertidos") or 0)
    return {
        "campanhas": int(c.get("total") or 0), "campanhas_ativas": int(c.get("ativas") or 0),
        "investimento_centavos": investimento, "receita_centavos": receita, "leads": leads,
        "mqls": int(m.get("mqls") or crm.get("mql") or 0), "conversoes": conversoes,
        "cpl_centavos": int(investimento / leads) if leads else 0,
        "cac_centavos": int(investimento / conversoes) if conversoes else 0,
        "roas": round(receita / investimento, 2) if investimento else 0.0,
    }


def exportar_dataframe_marketing(ator: dict) -> pd.DataFrame:
    exigir_permissao(ator, "marketing", "ler")
    campanhas = listar_campanhas(ator, limite=5000)
    if not campanhas:
        return pd.DataFrame(columns=["nome","canal","status","investimento","receita","leads","conversoes"])
    df = pd.DataFrame(campanhas)
    df["investimento"] = pd.to_numeric(df.get("investimento_centavos", 0), errors="coerce").fillna(0) / 100
    df["receita"] = pd.to_numeric(df.get("receita_atribuida_centavos", 0), errors="coerce").fillna(0) / 100
    df["canal"] = df.get("canal_nome", "")
    return df


def analisar_marketing(ator: dict) -> dict:
    resumo = resumo_marketing(ator)
    alertas = []
    if resumo["campanhas_ativas"] and resumo["leads"] == 0:
        alertas.append("Há campanhas ativas sem leads registrados.")
    if resumo["investimento_centavos"] and resumo["roas"] < 1:
        alertas.append("O retorno atribuído está abaixo do investimento registrado.")
    if resumo["leads"] and resumo["mqls"] == 0:
        alertas.append("Há leads cadastrados, mas nenhum foi qualificado como MQL.")
    return {"resumo": resumo, "alertas": alertas}


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
