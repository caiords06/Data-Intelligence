"""Revenue Workspace — domínio Comercial especializado V10.3.1."""
from __future__ import annotations
from datetime import date
import pandas as pd
from auth.banco import conectar
from enterprise.contexto import exigir_permissao
from enterprise._especializado_utils import linha, texto, centavos, escopo

STATUS_OPORTUNIDADE={"Aberta","Ganha","Perdida"}
STATUS_PROPOSTA={"Rascunho","Em aprovação","Enviada","Aceita","Recusada","Expirada"}


def garantir_etapas_padrao(ator: dict) -> None:
    exigir_permissao(ator,"comercial","ler"); empresa_id,_=escopo(ator)
    etapas=(("Novo",10,10),("Qualificação",20,25),("Proposta",30,50),("Negociação",40,70),("Fechamento",50,90))
    with conectar() as con:
        for nome,ordem,prob in etapas:
            con.execute("INSERT INTO comercial_pipeline_etapas (empresa_id,nome,ordem,probabilidade) VALUES (?,?,?,?) ON CONFLICT(empresa_id,nome) DO NOTHING",(empresa_id,nome,ordem,prob))


def listar_etapas(ator: dict) -> list[dict]:
    garantir_etapas_padrao(ator); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT * FROM comercial_pipeline_etapas WHERE empresa_id=? AND ativo=1 ORDER BY ordem,id",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def criar_oportunidade(dados: dict, ator: dict) -> int:
    exigir_permissao(ator,"comercial","escrever"); garantir_etapas_padrao(ator); empresa_id,filial_id=escopo(ator)
    titulo=texto(dados.get("titulo"),obrigatorio=True,nome="Título da oportunidade")
    etapa_id=int(dados["etapa_id"]) if dados.get("etapa_id") not in (None,"") else listar_etapas(ator)[0]["id"]
    prob=int(dados.get("probabilidade") or 0); prob=max(0,min(100,prob))
    status=texto(dados.get("status") or "Aberta")
    if status not in STATUS_OPORTUNIDADE: raise ValueError("Status de oportunidade inválido.")
    crm_empresa_id=int(dados["crm_empresa_id"]) if dados.get("crm_empresa_id") not in (None,"") else None
    contato_id=int(dados["contato_id"]) if dados.get("contato_id") not in (None,"") else None
    lead_id=int(dados["lead_id"]) if dados.get("lead_id") not in (None,"") else None
    with conectar() as con:
        cur=con.execute("""INSERT INTO comercial_oportunidades
        (empresa_id,filial_id,crm_empresa_id,contato_id,lead_id,titulo,responsavel_id,etapa_id,valor_centavos,probabilidade,fechamento_previsto,status,proxima_acao,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,crm_empresa_id,contato_id,lead_id,titulo,int(ator["id"]),etapa_id,centavos(dados.get("valor")),prob,texto(dados.get("fechamento_previsto")),status,texto(dados.get("proxima_acao")),int(ator["id"])))
        oportunidade_id=int(cur.lastrowid)
        if lead_id:
            con.execute("UPDATE crm_leads SET status='SQL', atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?",(lead_id,empresa_id))
    return oportunidade_id


def _filtro_oportunidades(ator: dict, *, status=None) -> tuple[list[str], list]:
    empresa_id,filial_id=escopo(ator); where=["o.empresa_id=?"]; params=[empresa_id]
    if filial_id is not None: where.append("(o.filial_id=? OR o.filial_id IS NULL)"); params.append(filial_id)
    if status: where.append("o.status=?"); params.append(str(status))
    return where, params


def contar_oportunidades(ator: dict, *, status=None) -> int:
    exigir_permissao(ator,"comercial","ler"); where,params=_filtro_oportunidades(ator,status=status)
    with conectar() as con:
        row=con.execute(f"SELECT COUNT(*) AS total FROM comercial_oportunidades o WHERE {' AND '.join(where)}",tuple(params)).fetchone()
    return int(row["total"] or 0)


def listar_oportunidades(ator: dict, *, status=None, limite=1000, offset=0) -> list[dict]:
    exigir_permissao(ator,"comercial","ler"); where,params=_filtro_oportunidades(ator,status=status)
    params.extend([max(1,min(5000,int(limite))),max(0,int(offset))])
    with conectar() as con:
        rows=con.execute(f"""SELECT o.*,e.nome AS etapa_nome,ce.nome AS empresa_nome,cc.nome AS contato_nome
        FROM comercial_oportunidades o LEFT JOIN comercial_pipeline_etapas e ON e.id=o.etapa_id
        LEFT JOIN crm_empresas ce ON ce.id=o.crm_empresa_id LEFT JOIN crm_contatos cc ON cc.id=o.contato_id
        WHERE {' AND '.join(where)} ORDER BY CASE o.status WHEN 'Aberta' THEN 0 WHEN 'Ganha' THEN 1 ELSE 2 END,e.ordem,o.id DESC LIMIT ? OFFSET ?""",tuple(params)).fetchall()
    return [linha(r) for r in rows]


def mover_oportunidade(oportunidade_id:int, etapa_id:int, ator:dict, *, status=None) -> dict:
    exigir_permissao(ator,"comercial","escrever"); empresa_id,_=escopo(ator)
    with conectar() as con:
        etapa=con.execute("SELECT nome,probabilidade FROM comercial_pipeline_etapas WHERE id=? AND empresa_id=?",(int(etapa_id),empresa_id)).fetchone()
        if not etapa: raise ValueError("Etapa comercial inválida.")
        novo=status or "Aberta"
        if novo not in STATUS_OPORTUNIDADE: raise ValueError("Status de oportunidade inválido.")
        prob=100 if novo=="Ganha" else 0 if novo=="Perdida" else int(etapa["probabilidade"] or 0)
        cur=con.execute("UPDATE comercial_oportunidades SET etapa_id=?,status=?,probabilidade=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?",(int(etapa_id),novo,prob,int(oportunidade_id),empresa_id))
        if cur.rowcount!=1: raise ValueError("Oportunidade não encontrada.")
    return {"id":int(oportunidade_id),"etapa":etapa["nome"],"status":novo,"probabilidade":prob}


def registrar_atividade(oportunidade_id:int,dados:dict,ator:dict)->int:
    exigir_permissao(ator,"comercial","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("""INSERT INTO comercial_atividades (empresa_id,filial_id,oportunidade_id,tipo,descricao,realizada_em,proxima_acao,responsavel_id,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,int(oportunidade_id),texto(dados.get("tipo") or "Contato"),texto(dados.get("descricao"),maximo=3000),texto(dados.get("realizada_em") or date.today().isoformat()),texto(dados.get("proxima_acao")),int(ator["id"]),int(ator["id"])))
        con.execute("UPDATE comercial_oportunidades SET proxima_acao=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?",(texto(dados.get("proxima_acao")),int(oportunidade_id),empresa_id))
        return int(cur.lastrowid)


def criar_proposta(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"comercial","escrever"); empresa_id,filial_id=escopo(ator)
    oportunidade_id=int(dados.get("oportunidade_id") or 0)
    if not oportunidade_id: raise ValueError("Oportunidade é obrigatória.")
    numero=texto(dados.get("numero") or f"PROP-{date.today().strftime('%Y%m%d')}-{oportunidade_id}",obrigatorio=True,nome="Número")
    status=texto(dados.get("status") or "Rascunho")
    if status not in STATUS_PROPOSTA: raise ValueError("Status de proposta inválido.")
    with conectar() as con:
        cur=con.execute("""INSERT INTO comercial_propostas (empresa_id,filial_id,oportunidade_id,numero,validade,valor_centavos,desconto_centavos,status,observacoes,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,oportunidade_id,numero,texto(dados.get("validade")),centavos(dados.get("valor")),centavos(dados.get("desconto")),status,texto(dados.get("observacoes"),maximo=3000),int(ator["id"])))
        return int(cur.lastrowid)


def listar_propostas(ator:dict)->list[dict]:
    exigir_permissao(ator,"comercial","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("""SELECT p.*,o.titulo AS oportunidade_titulo FROM comercial_propostas p JOIN comercial_oportunidades o ON o.id=p.oportunidade_id WHERE p.empresa_id=? ORDER BY p.id DESC""",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def salvar_meta(referencia:str,valor,ator:dict)->dict:
    exigir_permissao(ator,"comercial","escrever"); empresa_id,filial_id=escopo(ator); referencia=texto(referencia,obrigatorio=True,nome="Referência",maximo=20); v=centavos(valor)
    with conectar() as con:
        con.execute("""INSERT INTO comercial_metas (empresa_id,filial_id,responsavel_id,referencia,valor_centavos,criado_por) VALUES (?,?,?,?,?,?)
        ON CONFLICT(empresa_id,filial_id,responsavel_id,referencia) DO UPDATE SET valor_centavos=excluded.valor_centavos""",(empresa_id,filial_id,int(ator["id"]),referencia,v,int(ator["id"])))
    return {"referencia":referencia,"valor_centavos":v}


def resumo_comercial(ator:dict)->dict:
    exigir_permissao(ator,"comercial","ler"); empresa_id,filial_id=escopo(ator); filtro="empresa_id=?"; params=[empresa_id]
    if filial_id is not None: filtro+=" AND (filial_id=? OR filial_id IS NULL)"; params.append(filial_id)
    with conectar() as con:
        r=con.execute(f"""SELECT COUNT(*) total,SUM(CASE WHEN status='Aberta' THEN 1 ELSE 0 END) abertas,
        SUM(CASE WHEN status='Ganha' THEN 1 ELSE 0 END) ganhas,SUM(CASE WHEN status='Perdida' THEN 1 ELSE 0 END) perdidas,
        SUM(CASE WHEN status='Aberta' THEN valor_centavos ELSE 0 END) pipeline,
        SUM(CASE WHEN status='Aberta' THEN CAST(valor_centavos*probabilidade/100 AS INTEGER) ELSE 0 END) ponderado,
        SUM(CASE WHEN status='Ganha' THEN valor_centavos ELSE 0 END) receita FROM comercial_oportunidades WHERE {filtro}""",tuple(params)).fetchone()
        meta=con.execute("SELECT COALESCE(SUM(valor_centavos),0) valor FROM comercial_metas WHERE empresa_id=? AND (? IS NULL OR filial_id=? OR filial_id IS NULL)",(empresa_id,filial_id,filial_id)).fetchone()
    total=int(r["total"] or 0); ganhas=int(r["ganhas"] or 0); perdidas=int(r["perdidas"] or 0); fechadas=ganhas+perdidas
    return {"oportunidades":total,"abertas":int(r["abertas"] or 0),"ganhas":ganhas,"perdidas":perdidas,"pipeline_centavos":int(r["pipeline"] or 0),"ponderado_centavos":int(r["ponderado"] or 0),"receita_centavos":int(r["receita"] or 0),"meta_centavos":int(meta["valor"] or 0),"taxa_conversao":round(ganhas*100/fechadas,1) if fechadas else 0.0}


def analisar_comercial(ator:dict)->dict:
    r=resumo_comercial(ator); alertas=[]
    if r["abertas"] and r["ponderado_centavos"] < r["pipeline_centavos"]*0.35: alertas.append("Grande parte do pipeline ainda está em etapas de baixa probabilidade.")
    if r["meta_centavos"] and r["ponderado_centavos"] < r["meta_centavos"]: alertas.append("Forecast ponderado está abaixo da meta comercial cadastrada.")
    if r["perdidas"] > r["ganhas"] and r["perdidas"]>=3: alertas.append("Perdas superam ganhos no histórico atual; revise motivos e etapas.")
    return {"resumo":r,"alertas":alertas}


def exportar_dataframe_comercial(ator:dict)->pd.DataFrame:
    rows=listar_oportunidades(ator,limite=3000)
    for x in rows:
        x["valor"]=int(x.get("valor_centavos") or 0)/100
    return pd.DataFrame(rows)

from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
