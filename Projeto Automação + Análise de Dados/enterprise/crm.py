"""CRM compartilhado entre Marketing e Comercial — V10.3.0."""
from __future__ import annotations

from datetime import datetime, timezone

from auth.banco import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator


def _linha(registro):
    if registro is None:
        return None
    try:
        return {k: registro[k] for k in registro.keys()}
    except AttributeError:
        return dict(registro)


def _texto(valor, *, obrigatorio=False, nome="campo", maximo=300):
    valor = str(valor or "").strip()
    if obrigatorio and not valor:
        raise ValueError(f"{nome} é obrigatório.")
    if len(valor) > maximo:
        raise ValueError(f"{nome} deve possuir no máximo {maximo} caracteres.")
    return valor


def _escopo(ator):
    empresa_id, filial_id = obter_escopo_ator(ator)
    return int(empresa_id), int(filial_id) if filial_id is not None else None


def _exigir_crm(ator, acao="ler"):
    # Nesta versão o CRM nasce sob o domínio de Marketing. Comercial será
    # incorporado ao mesmo núcleo na V10.3.1 sem duplicar contatos/leads.
    exigir_permissao(ator, "marketing", acao)


def criar_empresa_crm(dados: dict, ator: dict) -> int:
    _exigir_crm(ator, "escrever")
    empresa_id, _ = _escopo(ator)
    nome = _texto(dados.get("nome"), obrigatorio=True, nome="Nome")
    with conectar() as con:
        cur = con.execute(
            """INSERT INTO crm_empresas
               (empresa_id,nome,nome_fantasia,cnpj,segmento,porte,site,cidade,estado,proprietario_id,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, nome, _texto(dados.get("nome_fantasia")), _texto(dados.get("cnpj")),
             _texto(dados.get("segmento")), _texto(dados.get("porte")), _texto(dados.get("site")),
             _texto(dados.get("cidade")), _texto(dados.get("estado"), maximo=40), int(ator["id"]),
             _texto(dados.get("status") or "Ativo")),
        )
        return int(cur.lastrowid)


def listar_empresas_crm(ator: dict, *, pesquisa="", limite=200) -> list[dict]:
    _exigir_crm(ator, "ler")
    empresa_id, _ = _escopo(ator)
    termo = f"%{str(pesquisa or '').strip()}%"
    with conectar() as con:
        rows = con.execute(
            """SELECT * FROM crm_empresas WHERE empresa_id=? AND status<>'Arquivado'
               AND (nome LIKE ? OR COALESCE(nome_fantasia,'') LIKE ? OR COALESCE(cnpj,'') LIKE ?)
               ORDER BY id DESC LIMIT ?""",
            (empresa_id, termo, termo, termo, max(1, min(1000, int(limite)))),
        ).fetchall()
    return [_linha(r) for r in rows]


def criar_contato(dados: dict, ator: dict) -> int:
    _exigir_crm(ator, "escrever")
    empresa_id, _ = _escopo(ator)
    nome = _texto(dados.get("nome"), obrigatorio=True, nome="Nome")
    email = _texto(dados.get("email"), maximo=180)
    if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
        raise ValueError("Informe um e-mail válido.")
    crm_empresa_id = int(dados["crm_empresa_id"]) if dados.get("crm_empresa_id") not in (None, "") else None
    with conectar() as con:
        if crm_empresa_id is not None:
            ok = con.execute("SELECT 1 FROM crm_empresas WHERE id=? AND empresa_id=?", (crm_empresa_id, empresa_id)).fetchone()
            if ok is None:
                raise ValueError("A empresa CRM informada não pertence à empresa atual.")
        cur = con.execute(
            """INSERT INTO crm_contatos
               (empresa_id,crm_empresa_id,nome,cargo,email,telefone,linkedin,responsavel_id,status,origem)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, crm_empresa_id, nome, _texto(dados.get("cargo")), email,
             _texto(dados.get("telefone"), maximo=80), _texto(dados.get("linkedin")), int(ator["id"]),
             _texto(dados.get("status") or "Ativo"), _texto(dados.get("origem"))),
        )
        return int(cur.lastrowid)


def listar_contatos(ator: dict, *, pesquisa="", limite=300) -> list[dict]:
    _exigir_crm(ator, "ler")
    empresa_id, _ = _escopo(ator)
    termo = f"%{str(pesquisa or '').strip()}%"
    with conectar() as con:
        rows = con.execute(
            """SELECT c.*, e.nome AS empresa_nome FROM crm_contatos c
               LEFT JOIN crm_empresas e ON e.id=c.crm_empresa_id
               WHERE c.empresa_id=? AND c.status<>'Arquivado'
               AND (c.nome LIKE ? OR COALESCE(c.email,'') LIKE ? OR COALESCE(e.nome,'') LIKE ?)
               ORDER BY c.id DESC LIMIT ?""",
            (empresa_id, termo, termo, termo, max(1, min(1000, int(limite)))),
        ).fetchall()
    return [_linha(r) for r in rows]


def criar_lead(dados: dict, ator: dict) -> int:
    _exigir_crm(ator, "escrever")
    empresa_id, filial_id = _escopo(ator)
    contato_id = int(dados["contato_id"]) if dados.get("contato_id") not in (None, "") else None
    crm_empresa_id = int(dados["crm_empresa_id"]) if dados.get("crm_empresa_id") not in (None, "") else None
    campanha_id = int(dados["campanha_id"]) if dados.get("campanha_id") not in (None, "") else None
    score = max(0, min(100, int(dados.get("score") or 0)))
    temperatura = _texto(dados.get("temperatura") or ("Quente" if score >= 75 else "Morno" if score >= 40 else "Frio"))
    status = _texto(dados.get("status") or "Novo")
    if status not in {"Novo", "Em nutrição", "MQL", "SQL", "Convertido", "Descartado"}:
        raise ValueError("Status de lead inválido.")
    with conectar() as con:
        if contato_id is not None and con.execute("SELECT 1 FROM crm_contatos WHERE id=? AND empresa_id=?", (contato_id, empresa_id)).fetchone() is None:
            raise ValueError("Contato inválido para o escopo atual.")
        if campanha_id is not None and con.execute("SELECT 1 FROM marketing_campanhas WHERE id=? AND empresa_id=?", (campanha_id, empresa_id)).fetchone() is None:
            raise ValueError("Campanha inválida para o escopo atual.")
        cur = con.execute(
            """INSERT INTO crm_leads
               (empresa_id,filial_id,contato_id,crm_empresa_id,origem,campanha_id,score,temperatura,responsavel_id,status,data_qualificacao,convertido_em,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, contato_id, crm_empresa_id, _texto(dados.get("origem")), campanha_id,
             score, temperatura, int(ator["id"]), status,
             datetime.now(timezone.utc).date().isoformat() if status in {"MQL", "SQL", "Convertido"} else None,
             datetime.now(timezone.utc).isoformat() if status == "Convertido" else None, int(ator["id"])),
        )
        return int(cur.lastrowid)


def _filtro_leads(ator: dict, *, status=None, pesquisa="") -> tuple[str, list]:
    empresa_id, filial_id = _escopo(ator)
    parametros = [empresa_id]
    escopo = "l.empresa_id=?"
    if filial_id is not None:
        escopo += " AND (l.filial_id=? OR l.filial_id IS NULL)"
        parametros.append(filial_id)
    if status:
        escopo += " AND l.status=?"
        parametros.append(str(status))
    termo = f"%{str(pesquisa or '').strip()}%"
    escopo += " AND (COALESCE(c.nome,'') LIKE ? OR COALESCE(c.email,'') LIKE ? OR COALESCE(e.nome,'') LIKE ?)"
    parametros.extend([termo, termo, termo])
    return escopo, parametros


def contar_leads(ator: dict, *, status=None, pesquisa="") -> int:
    _exigir_crm(ator, "ler")
    escopo, parametros = _filtro_leads(ator, status=status, pesquisa=pesquisa)
    with conectar() as con:
        row = con.execute(
            f"""SELECT COUNT(*) AS total FROM crm_leads l
                LEFT JOIN crm_contatos c ON c.id=l.contato_id
                LEFT JOIN crm_empresas e ON e.id=l.crm_empresa_id
                WHERE {escopo}""",
            tuple(parametros),
        ).fetchone()
    return int(row["total"] or 0)


def listar_leads(ator: dict, *, status=None, pesquisa="", limite=500, offset=0) -> list[dict]:
    _exigir_crm(ator, "ler")
    escopo, parametros = _filtro_leads(ator, status=status, pesquisa=pesquisa)
    limite = max(1, min(5000, int(limite)))
    offset = max(0, int(offset))
    parametros.extend([limite, offset])
    with conectar() as con:
        rows = con.execute(
            f"""SELECT l.*, c.nome AS contato_nome, c.email AS contato_email, e.nome AS empresa_nome,
                       mc.nome AS campanha_nome
                FROM crm_leads l
                LEFT JOIN crm_contatos c ON c.id=l.contato_id
                LEFT JOIN crm_empresas e ON e.id=l.crm_empresa_id
                LEFT JOIN marketing_campanhas mc ON mc.id=l.campanha_id
                WHERE {escopo}
                ORDER BY l.score DESC, l.id DESC LIMIT ? OFFSET ?""",
            tuple(parametros),
        ).fetchall()
    return [_linha(r) for r in rows]


def atualizar_lead_status(lead_id: int, status: str, ator: dict) -> dict:
    _exigir_crm(ator, "escrever")
    empresa_id, _ = _escopo(ator)
    status = _texto(status, obrigatorio=True, nome="Status")
    if status not in {"Novo", "Em nutrição", "MQL", "SQL", "Convertido", "Descartado"}:
        raise ValueError("Status de lead inválido.")
    qualificacao = datetime.now(timezone.utc).date().isoformat() if status in {"MQL", "SQL", "Convertido"} else None
    convertido = datetime.now(timezone.utc).isoformat() if status == "Convertido" else None
    with conectar() as con:
        cur = con.execute(
            """UPDATE crm_leads SET status=?, data_qualificacao=COALESCE(data_qualificacao,?),
               convertido_em=CASE WHEN ?='Convertido' THEN COALESCE(convertido_em,?) ELSE convertido_em END,
               atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?""",
            (status, qualificacao, status, convertido, int(lead_id), empresa_id),
        )
        if cur.rowcount != 1:
            raise ValueError("Lead não encontrado no escopo atual.")
    return {"id": int(lead_id), "status": status}


def registrar_atividade(dados: dict, ator: dict) -> int:
    _exigir_crm(ator, "escrever")
    empresa_id, filial_id = _escopo(ator)
    lead_id = int(dados["lead_id"]) if dados.get("lead_id") not in (None, "") else None
    with conectar() as con:
        if lead_id is not None and con.execute("SELECT 1 FROM crm_leads WHERE id=? AND empresa_id=?", (lead_id, empresa_id)).fetchone() is None:
            raise ValueError("Lead inválido para o escopo atual.")
        cur = con.execute(
            """INSERT INTO crm_atividades
               (empresa_id,filial_id,lead_id,oportunidade_id,tipo,descricao,realizada_em,proxima_acao,responsavel_id,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, lead_id, dados.get("oportunidade_id"),
             _texto(dados.get("tipo"), obrigatorio=True, nome="Tipo"), _texto(dados.get("descricao"), maximo=2000),
             _texto(dados.get("realizada_em")) or datetime.now(timezone.utc).isoformat(), _texto(dados.get("proxima_acao")),
             int(ator["id"]), int(ator["id"])),
        )
        return int(cur.lastrowid)


def resumo_crm(ator: dict) -> dict:
    _exigir_crm(ator, "ler")
    empresa_id, filial_id = _escopo(ator)
    filtro = "empresa_id=?"
    params = [empresa_id]
    if filial_id is not None:
        filtro += " AND (filial_id=? OR filial_id IS NULL)"
        params.append(filial_id)
    with conectar() as con:
        row = con.execute(
            f"""SELECT COUNT(*) total,
                SUM(CASE WHEN status='MQL' THEN 1 ELSE 0 END) mql,
                SUM(CASE WHEN status='SQL' THEN 1 ELSE 0 END) sql,
                SUM(CASE WHEN status='Convertido' THEN 1 ELSE 0 END) convertidos,
                AVG(score) score_medio FROM crm_leads WHERE {filtro}""",
            tuple(params),
        ).fetchone()
    r = _linha(row) or {}
    return {"leads": int(r.get("total") or 0), "mql": int(r.get("mql") or 0), "sql": int(r.get("sql") or 0),
            "convertidos": int(r.get("convertidos") or 0), "score_medio": float(r.get("score_medio") or 0)}


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
