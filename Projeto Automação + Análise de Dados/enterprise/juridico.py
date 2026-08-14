"""Legal Operations — domínio Jurídico especializado V10.3.3."""
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
from auth.banco import conectar
from enterprise.contexto import exigir_permissao
from enterprise._especializado_utils import linha, texto, centavos, escopo


def criar_contrato(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"juridico","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("""INSERT INTO juridico_contratos (empresa_id,filial_id,numero,titulo,parte,objeto,valor_centavos,risco,inicio,vencimento,responsavel_id,status,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,texto(dados.get("numero")),texto(dados.get("titulo"),obrigatorio=True,nome="Título"),texto(dados.get("parte"),obrigatorio=True,nome="Parte"),texto(dados.get("objeto"),maximo=3000),centavos(dados.get("valor")),texto(dados.get("risco") or "Baixo"),texto(dados.get("inicio")),texto(dados.get("vencimento")),int(ator["id"]),texto(dados.get("status") or "Elaboração"),int(ator["id"])))
        return int(cur.lastrowid)


def listar_contratos(ator:dict)->list[dict]:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT * FROM juridico_contratos WHERE empresa_id=? ORDER BY COALESCE(vencimento,'9999-12-31'),id DESC",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def criar_processo(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"juridico","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("""INSERT INTO juridico_processos (empresa_id,filial_id,numero,titulo,tribunal,parte_contraria,advogado_responsavel,tipo,fase,valor_causa_centavos,probabilidade,risco,status,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,texto(dados.get("numero"),obrigatorio=True,nome="Número do processo"),texto(dados.get("titulo"),obrigatorio=True,nome="Título"),texto(dados.get("tribunal")),texto(dados.get("parte_contraria")),texto(dados.get("advogado_responsavel")),texto(dados.get("tipo")),texto(dados.get("fase")),centavos(dados.get("valor_causa")),texto(dados.get("probabilidade") or "Possível"),texto(dados.get("risco") or "Médio"),texto(dados.get("status") or "Ativo"),int(ator["id"])))
        return int(cur.lastrowid)


def contar_processos(ator:dict)->int:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: row=con.execute("SELECT COUNT(*) AS total FROM juridico_processos WHERE empresa_id=?",(empresa_id,)).fetchone()
    return int(row["total"] or 0)


def listar_processos(ator:dict,*,limite=5000,offset=0)->list[dict]:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator)
    limite=max(1,min(5000,int(limite))); offset=max(0,int(offset))
    with conectar() as con: rows=con.execute("SELECT * FROM juridico_processos WHERE empresa_id=? ORDER BY id DESC LIMIT ? OFFSET ?",(empresa_id,limite,offset)).fetchall()
    return [linha(r) for r in rows]


def criar_prazo(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"juridico","escrever"); empresa_id,filial_id=escopo(ator); venc=texto(dados.get("vencimento"),obrigatorio=True,nome="Vencimento")
    with conectar() as con:
        cur=con.execute("""INSERT INTO juridico_prazos (empresa_id,filial_id,processo_id,contrato_id,titulo,vencimento,tipo,prioridade,responsavel_id,status,observacoes,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,int(dados["processo_id"]) if dados.get("processo_id") not in (None,"") else None,int(dados["contrato_id"]) if dados.get("contrato_id") not in (None,"") else None,texto(dados.get("titulo"),obrigatorio=True,nome="Título"),venc,texto(dados.get("tipo")),texto(dados.get("prioridade") or "Alta"),int(ator["id"]),texto(dados.get("status") or "Pendente"),texto(dados.get("observacoes"),maximo=3000),int(ator["id"])))
        return int(cur.lastrowid)


def listar_prazos(ator:dict,*,somente_pendentes=False)->list[dict]:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator); filtro="empresa_id=?"; params=[empresa_id]
    if somente_pendentes: filtro+=" AND status='Pendente'"
    with conectar() as con: rows=con.execute(f"SELECT * FROM juridico_prazos WHERE {filtro} ORDER BY vencimento,id",tuple(params)).fetchall()
    return [linha(r) for r in rows]


def concluir_prazo(prazo_id:int,ator:dict)->dict:
    exigir_permissao(ator,"juridico","escrever"); empresa_id,_=escopo(ator)
    with conectar() as con:
        cur=con.execute("UPDATE juridico_prazos SET status='Concluído' WHERE id=? AND empresa_id=?",(int(prazo_id),empresa_id))
        if cur.rowcount!=1: raise ValueError("Prazo não encontrado.")
    return {"id":int(prazo_id),"status":"Concluído"}


def criar_audiencia(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"juridico","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("INSERT INTO juridico_audiencias (empresa_id,filial_id,processo_id,data_hora,local,tipo,responsavel,status,observacoes,criado_por) VALUES (?,?,?,?,?,?,?,?,?,?)",(empresa_id,filial_id,int(dados.get("processo_id") or 0),texto(dados.get("data_hora"),obrigatorio=True,nome="Data/hora"),texto(dados.get("local")),texto(dados.get("tipo")),texto(dados.get("responsavel")),texto(dados.get("status") or "Agendada"),texto(dados.get("observacoes"),maximo=3000),int(ator["id"])))
        return int(cur.lastrowid)


def listar_audiencias(ator:dict)->list[dict]:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT a.*,p.numero AS processo_numero FROM juridico_audiencias a LEFT JOIN juridico_processos p ON p.id=a.processo_id WHERE a.empresa_id=? ORDER BY a.data_hora",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def registrar_risco(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"juridico","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("""INSERT INTO juridico_riscos (empresa_id,filial_id,processo_id,contrato_id,titulo,probabilidade,impacto,exposicao_centavos,justificativa,responsavel_id,status,revisado_em,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,int(dados["processo_id"]) if dados.get("processo_id") not in (None,"") else None,int(dados["contrato_id"]) if dados.get("contrato_id") not in (None,"") else None,texto(dados.get("titulo"),obrigatorio=True,nome="Título"),texto(dados.get("probabilidade") or "Possível"),texto(dados.get("impacto") or "Médio"),centavos(dados.get("exposicao")),texto(dados.get("justificativa"),maximo=4000),int(ator["id"]),texto(dados.get("status") or "Aberto"),date.today().isoformat(),int(ator["id"])))
        return int(cur.lastrowid)


def listar_riscos(ator:dict)->list[dict]:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT * FROM juridico_riscos WHERE empresa_id=? ORDER BY exposicao_centavos DESC,id DESC",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def criar_provisao(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"juridico","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("INSERT INTO juridico_provisoes (empresa_id,filial_id,processo_id,risco_id,referencia,valor_centavos,status,observacoes,criado_por) VALUES (?,?,?,?,?,?,?,?,?)",(empresa_id,filial_id,int(dados["processo_id"]) if dados.get("processo_id") not in (None,"") else None,int(dados["risco_id"]) if dados.get("risco_id") not in (None,"") else None,texto(dados.get("referencia"),obrigatorio=True,nome="Referência"),centavos(dados.get("valor")),texto(dados.get("status") or "Proposta"),texto(dados.get("observacoes"),maximo=3000),int(ator["id"])))
        return int(cur.lastrowid)


def listar_provisoes(ator:dict)->list[dict]:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT * FROM juridico_provisoes WHERE empresa_id=? ORDER BY id DESC",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def resumo_juridico(ator:dict)->dict:
    exigir_permissao(ator,"juridico","ler"); empresa_id,_=escopo(ator); hoje=date.today(); limite=(hoje+timedelta(days=30)).isoformat()
    with conectar() as con:
        contratos=con.execute("SELECT COUNT(*) total,SUM(CASE WHEN status='Ativo' THEN 1 ELSE 0 END) ativos FROM juridico_contratos WHERE empresa_id=?",(empresa_id,)).fetchone()
        processos=con.execute("SELECT COUNT(*) total,COALESCE(SUM(valor_causa_centavos),0) valor FROM juridico_processos WHERE empresa_id=? AND status='Ativo'",(empresa_id,)).fetchone()
        prazos=con.execute("SELECT COUNT(*) n FROM juridico_prazos WHERE empresa_id=? AND status='Pendente' AND vencimento<=?",(empresa_id,limite)).fetchone()
        riscos=con.execute("SELECT COUNT(*) n,COALESCE(SUM(exposicao_centavos),0) exposicao FROM juridico_riscos WHERE empresa_id=? AND status='Aberto'",(empresa_id,)).fetchone()
        provisao=con.execute("SELECT COALESCE(SUM(valor_centavos),0) valor FROM juridico_provisoes WHERE empresa_id=? AND status IN ('Proposta','Aprovada')",(empresa_id,)).fetchone()
    return {"contratos":int(contratos["total"] or 0),"contratos_ativos":int(contratos["ativos"] or 0),"processos_ativos":int(processos["total"] or 0),"valor_causas_centavos":int(processos["valor"] or 0),"prazos_30_dias":int(prazos["n"] or 0),"riscos_abertos":int(riscos["n"] or 0),"exposicao_centavos":int(riscos["exposicao"] or 0),"provisoes_centavos":int(provisao["valor"] or 0)}


def analisar_juridico(ator:dict)->dict:
    r=resumo_juridico(ator); alertas=[]
    if r["prazos_30_dias"]: alertas.append(f"{r['prazos_30_dias']} prazos jurídicos vencem nos próximos 30 dias.")
    if r["riscos_abertos"] and r["exposicao_centavos"]: alertas.append("Há riscos jurídicos abertos com exposição financeira registrada.")
    return {"resumo":r,"alertas":alertas}


def exportar_dataframe_juridico(ator:dict)->pd.DataFrame:
    rows=listar_processos(ator)
    for x in rows: x["valor_causa"]=int(x.get("valor_causa_centavos") or 0)/100
    return pd.DataFrame(rows)

from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
