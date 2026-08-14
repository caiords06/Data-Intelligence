"""Workplace Operations — domínio Administrativo especializado V10.3.2."""
from __future__ import annotations
from datetime import datetime
import pandas as pd
from auth.banco import conectar
from enterprise.contexto import exigir_permissao
from enterprise._especializado_utils import linha, texto, centavos, escopo

STATUS_SOLICITACAO={"Aberta","Triagem","Aprovação","Execução","Concluída","Rejeitada","Cancelada"}


def criar_solicitacao(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"administrativo","escrever"); empresa_id,filial_id=escopo(ator)
    titulo=texto(dados.get("titulo"),obrigatorio=True,nome="Título"); categoria=texto(dados.get("categoria") or "Outro")
    status=texto(dados.get("status") or "Aberta")
    if status not in STATUS_SOLICITACAO: raise ValueError("Status de solicitação inválido.")
    prioridade=texto(dados.get("prioridade") or "Média"); sla=max(1,min(720,int(dados.get("sla_horas") or 48)))
    with conectar() as con:
        prox=int(con.execute("SELECT COUNT(*) n FROM administrativo_solicitacoes WHERE empresa_id=?",(empresa_id,)).fetchone()["n"] or 0)+1
        numero=texto(dados.get("numero") or f"ADM-{datetime.now():%Y%m}-{prox:05d}")
        cur=con.execute("""INSERT INTO administrativo_solicitacoes
        (empresa_id,filial_id,numero,solicitante_id,solicitante_nome,categoria,titulo,descricao,prioridade,responsavel_id,sla_horas,prazo,valor_centavos,status,centro_custo_id,criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(empresa_id,filial_id,numero,int(ator["id"]),texto(dados.get("solicitante_nome") or ator.get("nome") or ator.get("usuario")),categoria,titulo,texto(dados.get("descricao"),maximo=4000),prioridade,int(ator["id"]),sla,texto(dados.get("prazo")),centavos(dados.get("valor")),status,int(dados["centro_custo_id"]) if dados.get("centro_custo_id") not in (None,"") else None,int(ator["id"])))
        return int(cur.lastrowid)


def _filtro_solicitacoes(ator:dict,*,status=None)->tuple[list[str],list]:
    empresa_id,filial_id=escopo(ator); where=["empresa_id=?"]; params=[empresa_id]
    if filial_id is not None: where.append("(filial_id=? OR filial_id IS NULL)"); params.append(filial_id)
    if status: where.append("status=?"); params.append(str(status))
    return where,params


def contar_solicitacoes(ator:dict,*,status=None)->int:
    exigir_permissao(ator,"administrativo","ler"); where,params=_filtro_solicitacoes(ator,status=status)
    with conectar() as con: row=con.execute(f"SELECT COUNT(*) AS total FROM administrativo_solicitacoes WHERE {' AND '.join(where)}",tuple(params)).fetchone()
    return int(row["total"] or 0)


def listar_solicitacoes(ator:dict,*,status=None,limite=5000,offset=0)->list[dict]:
    exigir_permissao(ator,"administrativo","ler"); where,params=_filtro_solicitacoes(ator,status=status)
    params.extend([max(1,min(5000,int(limite))),max(0,int(offset))])
    with conectar() as con: rows=con.execute(f"SELECT * FROM administrativo_solicitacoes WHERE {' AND '.join(where)} ORDER BY CASE prioridade WHEN 'Crítica' THEN 0 WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,id DESC LIMIT ? OFFSET ?",tuple(params)).fetchall()
    return [linha(r) for r in rows]


def atualizar_status_solicitacao(solicitacao_id:int,status:str,ator:dict)->dict:
    exigir_permissao(ator,"administrativo","escrever"); empresa_id,_=escopo(ator); status=texto(status)
    if status not in STATUS_SOLICITACAO: raise ValueError("Status de solicitação inválido.")
    with conectar() as con:
        cur=con.execute("UPDATE administrativo_solicitacoes SET status=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?",(status,int(solicitacao_id),empresa_id))
        if cur.rowcount!=1: raise ValueError("Solicitação não encontrada.")
    return {"id":int(solicitacao_id),"status":status}


def criar_recurso(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"administrativo","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("INSERT INTO administrativo_recursos (empresa_id,filial_id,tipo,nome,localizacao,capacidade,status,observacoes,criado_por) VALUES (?,?,?,?,?,?,?,?,?)",(empresa_id,filial_id,texto(dados.get("tipo") or "Sala"),texto(dados.get("nome"),obrigatorio=True,nome="Nome do recurso"),texto(dados.get("localizacao")),max(0,int(dados.get("capacidade") or 0)),texto(dados.get("status") or "Disponível"),texto(dados.get("observacoes"),maximo=2000),int(ator["id"])))
        return int(cur.lastrowid)


def listar_recursos(ator:dict)->list[dict]:
    exigir_permissao(ator,"administrativo","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT * FROM administrativo_recursos WHERE empresa_id=? ORDER BY tipo,nome",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def criar_reserva(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"administrativo","escrever"); empresa_id,filial_id=escopo(ator); recurso_id=int(dados.get("recurso_id") or 0)
    inicio=texto(dados.get("inicio"),obrigatorio=True,nome="Início"); fim=texto(dados.get("fim"),obrigatorio=True,nome="Fim")
    if fim<=inicio: raise ValueError("O fim da reserva deve ser posterior ao início.")
    with conectar() as con:
        conflito=con.execute("""SELECT id FROM administrativo_reservas WHERE recurso_id=? AND status='Confirmada' AND NOT (fim<=? OR inicio>=?) LIMIT 1""",(recurso_id,inicio,fim)).fetchone()
        if conflito: raise ValueError("O recurso já possui uma reserva nesse período.")
        cur=con.execute("INSERT INTO administrativo_reservas (empresa_id,filial_id,recurso_id,titulo,inicio,fim,responsavel_id,status,observacoes,criado_por) VALUES (?,?,?,?,?,?,?,?,?,?)",(empresa_id,filial_id,recurso_id,texto(dados.get("titulo"),obrigatorio=True,nome="Título"),inicio,fim,int(ator["id"]),"Confirmada",texto(dados.get("observacoes"),maximo=2000),int(ator["id"])))
        return int(cur.lastrowid)


def listar_reservas(ator:dict)->list[dict]:
    exigir_permissao(ator,"administrativo","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("""SELECT r.*,x.nome AS recurso_nome,x.tipo AS recurso_tipo FROM administrativo_reservas r JOIN administrativo_recursos x ON x.id=r.recurso_id WHERE r.empresa_id=? ORDER BY r.inicio DESC""",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def criar_viagem(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"administrativo","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("INSERT INTO administrativo_viagens (empresa_id,filial_id,viajante,destino,inicio,fim,motivo,custo_estimado_centavos,status,criado_por) VALUES (?,?,?,?,?,?,?,?,?,?)",(empresa_id,filial_id,texto(dados.get("viajante") or ator.get("nome"),obrigatorio=True,nome="Viajante"),texto(dados.get("destino"),obrigatorio=True,nome="Destino"),texto(dados.get("inicio")),texto(dados.get("fim")),texto(dados.get("motivo"),maximo=2000),centavos(dados.get("custo_estimado")),texto(dados.get("status") or "Solicitada"),int(ator["id"])))
        return int(cur.lastrowid)


def listar_viagens(ator:dict)->list[dict]:
    exigir_permissao(ator,"administrativo","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT * FROM administrativo_viagens WHERE empresa_id=? ORDER BY id DESC",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def criar_reembolso(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"administrativo","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("INSERT INTO administrativo_reembolsos (empresa_id,filial_id,solicitante,categoria,descricao,valor_centavos,centro_custo_id,status,criado_por) VALUES (?,?,?,?,?,?,?,?,?)",(empresa_id,filial_id,texto(dados.get("solicitante") or ator.get("nome"),obrigatorio=True,nome="Solicitante"),texto(dados.get("categoria") or "Outro"),texto(dados.get("descricao"),maximo=3000),centavos(dados.get("valor")),int(dados["centro_custo_id"]) if dados.get("centro_custo_id") not in (None,"") else None,"Pendente",int(ator["id"])))
        return int(cur.lastrowid)


def listar_reembolsos(ator:dict)->list[dict]:
    exigir_permissao(ator,"administrativo","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT * FROM administrativo_reembolsos WHERE empresa_id=? ORDER BY id DESC",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def criar_manutencao(dados:dict,ator:dict)->int:
    exigir_permissao(ator,"administrativo","escrever"); empresa_id,filial_id=escopo(ator)
    with conectar() as con:
        cur=con.execute("INSERT INTO administrativo_manutencoes (empresa_id,filial_id,recurso_id,titulo,descricao,prioridade,fornecedor,custo_centavos,status,prazo,criado_por) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(empresa_id,filial_id,int(dados["recurso_id"]) if dados.get("recurso_id") not in (None,"") else None,texto(dados.get("titulo"),obrigatorio=True,nome="Título"),texto(dados.get("descricao"),maximo=3000),texto(dados.get("prioridade") or "Média"),texto(dados.get("fornecedor")),centavos(dados.get("custo")),texto(dados.get("status") or "Aberta"),texto(dados.get("prazo")),int(ator["id"])))
        return int(cur.lastrowid)


def listar_manutencoes(ator:dict)->list[dict]:
    exigir_permissao(ator,"administrativo","ler"); empresa_id,_=escopo(ator)
    with conectar() as con: rows=con.execute("SELECT m.*,r.nome AS recurso_nome FROM administrativo_manutencoes m LEFT JOIN administrativo_recursos r ON r.id=m.recurso_id WHERE m.empresa_id=? ORDER BY m.id DESC",(empresa_id,)).fetchall()
    return [linha(r) for r in rows]


def resumo_administrativo(ator:dict)->dict:
    exigir_permissao(ator,"administrativo","ler"); empresa_id,_=escopo(ator)
    with conectar() as con:
        s=con.execute("""SELECT COUNT(*) total,SUM(CASE WHEN status NOT IN ('Concluída','Rejeitada','Cancelada') THEN 1 ELSE 0 END) abertas,
        SUM(CASE WHEN prioridade IN ('Alta','Crítica') AND status NOT IN ('Concluída','Rejeitada','Cancelada') THEN 1 ELSE 0 END) criticas,
        COALESCE(SUM(valor_centavos),0) valor FROM administrativo_solicitacoes WHERE empresa_id=?""",(empresa_id,)).fetchone()
        reservas=int(con.execute("SELECT COUNT(*) n FROM administrativo_reservas WHERE empresa_id=? AND status='Confirmada'",(empresa_id,)).fetchone()["n"] or 0)
        reemb=con.execute("SELECT COUNT(*) n,COALESCE(SUM(valor_centavos),0) valor FROM administrativo_reembolsos WHERE empresa_id=? AND status='Pendente'",(empresa_id,)).fetchone()
    return {"solicitacoes":int(s["total"] or 0),"abertas":int(s["abertas"] or 0),"criticas":int(s["criticas"] or 0),"valor_solicitado_centavos":int(s["valor"] or 0),"reservas":reservas,"reembolsos_pendentes":int(reemb["n"] or 0),"reembolsos_centavos":int(reemb["valor"] or 0)}


def analisar_administrativo(ator:dict)->dict:
    r=resumo_administrativo(ator); alertas=[]
    if r["criticas"]: alertas.append(f"{r['criticas']} solicitações de alta criticidade aguardam tratamento.")
    if r["reembolsos_pendentes"]>=5: alertas.append("Fila de reembolsos pendentes merece revisão do financeiro/administrativo.")
    return {"resumo":r,"alertas":alertas}


def exportar_dataframe_administrativo(ator:dict)->pd.DataFrame:
    rows=listar_solicitacoes(ator)
    for x in rows: x["valor"]=int(x.get("valor_centavos") or 0)/100
    return pd.DataFrame(rows)

from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
