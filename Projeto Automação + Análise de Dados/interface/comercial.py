"""Revenue Workspace — interface especializada Comercial V10.3.1."""
from __future__ import annotations
import tkinter as tk
from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.crm import listar_empresas_crm, listar_contatos, listar_leads
from services.departamentos.comercial import (
    analisar_comercial, criar_oportunidade, criar_proposta, exportar_dataframe_comercial,
    listar_etapas, listar_oportunidades, listar_propostas, registrar_atividade,
    resumo_comercial, salvar_meta,
)
from interface.workspace_especializado import WorkspaceEspecializado, moeda
from interface.tema import CORES

COR_COMERCIAL="#20B8A6"
GRUPOS_MENU=(
    ("COMERCIAL",(("visao","📊","Visão geral"),("pipeline","◇","Pipeline"),("oportunidades","🤝","Oportunidades"))),
    ("RELACIONAMENTO",(("leads","🎯","Leads CRM"),("clientes","◎","Clientes e contatos"),("atividades","☑","Atividades"))),
    ("NEGOCIAÇÃO",(("propostas","▤","Propostas"),("metas","⌁","Metas e forecast"),("relatorios","▥","Relatórios"))),
)
ROTULOS={k:r for _,itens in GRUPOS_MENU for k,_,r in itens}


class TelaComercial(WorkspaceEspecializado):
    modulo="comercial"; titulo_sidebar="COMERCIAL"; etiqueta="REVENUE WORKSPACE 3.1"; cor=COR_COMERCIAL; grupos_menu=GRUPOS_MENU; rotulos=ROTULOS
    def __init__(self,root,navegacao,secao="visao"):
        if not tem_permissao(SESSAO.usuario,"comercial","ler"): raise PermissionError("Seu perfil não possui acesso ao Comercial.")
        self.root=root; self.navegacao=navegacao; self.usuario=SESSAO.usuario; self.secao=secao if secao in ROTULOS else "visao"
        self.container=tk.Frame(root,bg=CORES["bg"]); self.container.pack(fill="both",expand=True); self.montar_base()
        getattr(self,f"_{self.secao}",self._visao)()

    def _visao(self):
        self.cabecalho("Receita e relacionamento","Pipeline comercial conectado ao mesmo CRM utilizado pelo Marketing.",lambda p:self.acoes(p,("+ OPORTUNIDADE",self._nova_oportunidade),("+ PROPOSTA",self._nova_proposta)))
        r=resumo_comercial(self.usuario); a=analisar_comercial(self.usuario)
        self.metricas((("Oportunidades",r["oportunidades"],"◇"),("Abertas",r["abertas"],"↗"),("Pipeline",moeda(r["pipeline_centavos"]),"$"),("Ponderado",moeda(r["ponderado_centavos"]),"≈"),("Ganhos",r["ganhas"],"✓"),("Receita ganha",moeda(r["receita_centavos"]),"$"),("Conversão",f"{r['taxa_conversao']:.1f}%","📊"),("Meta",moeda(r["meta_centavos"]),"⌁")))
        self.painel_alertas(a["alertas"])
        self.tabela(listar_oportunidades(self.usuario)[:12],(("titulo","Oportunidade",220),("empresa_nome","Empresa",170),("etapa_nome","Etapa",120),("valor_centavos","Valor",110),("probabilidade","Prob. %",80),("status","Status",95),("proxima_acao","Próxima ação",180)),moedas={"valor_centavos"},vazio=("🤝","Pipeline vazio","Crie a primeira oportunidade ou converta um lead qualificado."))

    def _pipeline(self):
        self.cabecalho("Pipeline","Carteira ordenada por etapa, valor, probabilidade e próximo passo.",lambda p:self.acoes(p,("+ OPORTUNIDADE",self._nova_oportunidade)))
        dados=listar_oportunidades(self.usuario); etapas=listar_etapas(self.usuario)
        for etapa in etapas:
            itens=[x for x in dados if int(x.get("etapa_id") or 0)==int(etapa["id"]) and x.get("status")=="Aberta"]
            total=sum(int(x.get("valor_centavos") or 0) for x in itens)
            self.tabela(itens,(("titulo",f"{etapa['nome']} · {len(itens)}",240),("empresa_nome","Conta",170),("valor_centavos",f"Valor · {moeda(total)}",140),("probabilidade","Prob. %",90),("proxima_acao","Próxima ação",190)),moedas={"valor_centavos"},vazio=("◇",f"Sem oportunidades em {etapa['nome']}","Nenhuma oportunidade aberta nesta etapa."))

    def _oportunidades(self):
        self.cabecalho("Oportunidades","Negócios ativos e histórico de ganhos/perdas.",lambda p:self.acoes(p,("+ OPORTUNIDADE",self._nova_oportunidade)))
        self.tabela(listar_oportunidades(self.usuario),(("titulo","Oportunidade",230),("empresa_nome","Empresa",170),("contato_nome","Contato",150),("etapa_nome","Etapa",115),("valor_centavos","Valor",110),("probabilidade","Prob. %",85),("fechamento_previsto","Previsão",105),("status","Status",90)),moedas={"valor_centavos"})

    def _leads(self):
        self.cabecalho("Leads CRM","Leads de Marketing prontos para qualificação comercial.")
        self.tabela(listar_leads(self.usuario),(("id","ID",55),("contato_nome","Contato",180),("empresa_nome","Empresa",170),("origem","Origem",120),("score","Score",70),("temperatura","Temperatura",100),("status","Status",100)),vazio=("🎯","Nenhum lead","Os leads criados pelo Marketing aparecem aqui automaticamente."))

    def _clientes(self):
        self.cabecalho("Clientes e contatos","Base CRM compartilhada entre Marketing e Comercial.")
        dados=[]
        contatos=listar_contatos(self.usuario)
        for e in listar_empresas_crm(self.usuario):
            vinculados=sum(1 for c in contatos if c.get("crm_empresa_id")==e["id"]); x=dict(e); x["contatos"]=vinculados; dados.append(x)
        self.tabela(dados,(("nome","Empresa",230),("segmento","Segmento",150),("cidade","Cidade",130),("estado","UF",60),("contatos","Contatos",80),("status","Status",90)))

    def _atividades(self):
        self.cabecalho("Atividades","Próximos passos comerciais ficam vinculados às oportunidades.",lambda p:self.acoes(p,("+ ATIVIDADE",self._nova_atividade)))
        oportunidades=listar_oportunidades(self.usuario)
        self.tabela(oportunidades,(("titulo","Oportunidade",230),("etapa_nome","Etapa",120),("proxima_acao","Próxima ação",260),("status","Status",90)),vazio=("☑","Sem atividades","Cadastre uma oportunidade e registre seu próximo passo."))

    def _propostas(self):
        self.cabecalho("Propostas","Propostas comerciais ligadas ao pipeline.",lambda p:self.acoes(p,("+ PROPOSTA",self._nova_proposta)))
        self.tabela(listar_propostas(self.usuario),(("numero","Número",120),("oportunidade_titulo","Oportunidade",230),("validade","Validade",100),("valor_centavos","Valor",115),("desconto_centavos","Desconto",105),("status","Status",105)),moedas={"valor_centavos","desconto_centavos"})

    def _metas(self):
        self.cabecalho("Metas e forecast","Compare meta cadastrada com pipeline bruto e ponderado.",lambda p:self.acoes(p,("+ DEFINIR META",self._nova_meta)))
        r=resumo_comercial(self.usuario); self.metricas((("Meta",moeda(r["meta_centavos"]),"⌁"),("Pipeline bruto",moeda(r["pipeline_centavos"]),"$"),("Forecast ponderado",moeda(r["ponderado_centavos"]),"≈"),("Receita ganha",moeda(r["receita_centavos"]),"✓")),max_colunas=4)
        self.painel_alertas(analisar_comercial(self.usuario)["alertas"],"Risco de forecast")

    def _relatorios(self):
        self.cabecalho("Relatórios","Resumo comercial pronto para Analytics e exportação.")
        df=exportar_dataframe_comercial(self.usuario); self.tabela(df.to_dict("records"),(("titulo","Oportunidade",230),("empresa_nome","Empresa",170),("etapa_nome","Etapa",120),("valor","Valor",110),("probabilidade","Prob. %",85),("status","Status",90)))

    def _nova_oportunidade(self):
        j,a=self.dialogo("Nova oportunidade"); empresas=listar_empresas_crm(self.usuario); contatos=listar_contatos(self.usuario); leads=listar_leads(self.usuario); etapas=listar_etapas(self.usuario)
        vars={k:tk.StringVar() for k in ("titulo","valor","fechamento_previsto","proxima_acao")}; empresa=tk.StringVar(); contato=tk.StringVar(); lead=tk.StringVar(); etapa=tk.StringVar(); prob=tk.StringVar(value="25")
        map_emp={x["nome"]:x["id"] for x in empresas}; map_cont={x["nome"]:x["id"] for x in contatos}; map_lead={f"#{x['id']} · {x.get('contato_nome') or x.get('empresa_nome') or x.get('origem') or 'Lead'}":x["id"] for x in leads}; map_etapa={x["nome"]:x["id"] for x in etapas}
        for rot,k in (("Título","titulo"),("Valor estimado","valor"),("Fechamento previsto","fechamento_previsto"),("Próxima ação","proxima_acao")): self.campo(a,rot,vars[k])
        self.campo(a,"Empresa CRM",empresa,valores=[""]+list(map_emp)); self.campo(a,"Contato",contato,valores=[""]+list(map_cont)); self.campo(a,"Lead",lead,valores=[""]+list(map_lead)); self.campo(a,"Etapa",etapa,valores=list(map_etapa)); self.campo(a,"Probabilidade",prob)
        from interface.componentes import criar_botao
        criar_botao(a,"CRIAR OPORTUNIDADE",lambda:self.salvar_dialogo(j,criar_oportunidade,{**{k:v.get() for k,v in vars.items()},"crm_empresa_id":map_emp.get(empresa.get()),"contato_id":map_cont.get(contato.get()),"lead_id":map_lead.get(lead.get()),"etapa_id":map_etapa.get(etapa.get()),"probabilidade":prob.get()},"oportunidades")).pack(anchor="e",pady=18)

    def _nova_proposta(self):
        j,a=self.dialogo("Nova proposta",590,610); oportunidades=[x for x in listar_oportunidades(self.usuario) if x.get("status")=="Aberta"]; oportunidade=tk.StringVar(); numero=tk.StringVar(); validade=tk.StringVar(); valor=tk.StringVar(); desconto=tk.StringVar(); mapa={f"#{x['id']} · {x['titulo']}":x["id"] for x in oportunidades}
        self.campo(a,"Oportunidade",oportunidade,valores=list(mapa)); self.campo(a,"Número",numero); self.campo(a,"Validade",validade); self.campo(a,"Valor",valor); self.campo(a,"Desconto",desconto)
        from interface.componentes import criar_botao
        criar_botao(a,"CRIAR PROPOSTA",lambda:self.salvar_dialogo(j,criar_proposta,{"oportunidade_id":mapa.get(oportunidade.get()),"numero":numero.get(),"validade":validade.get(),"valor":valor.get(),"desconto":desconto.get()},"propostas")).pack(anchor="e",pady=18)

    def _nova_atividade(self):
        j,a=self.dialogo("Registrar atividade",580,590); ops=listar_oportunidades(self.usuario); op=tk.StringVar(); tipo=tk.StringVar(value="Contato"); descricao=tk.StringVar(); proxima=tk.StringVar(); mapa={f"#{x['id']} · {x['titulo']}":x["id"] for x in ops}
        self.campo(a,"Oportunidade",op,valores=list(mapa)); self.campo(a,"Tipo",tipo,valores=("Contato","Reunião","E-mail","Ligação","Follow-up","Visita")); self.campo(a,"Descrição",descricao); self.campo(a,"Próxima ação",proxima)
        from interface.componentes import criar_botao
        def salvar():
            try: registrar_atividade(mapa.get(op.get()),{"tipo":tipo.get(),"descricao":descricao.get(),"proxima_acao":proxima.get()},self.usuario)
            except Exception as e:
                from tkinter import messagebox; messagebox.showerror("Comercial",str(e),parent=j); return
            j.destroy(); self.reabrir("atividades")
        criar_botao(a,"REGISTRAR",salvar).pack(anchor="e",pady=18)

    def _nova_meta(self):
        j,a=self.dialogo("Definir meta",540,470); ref=tk.StringVar(value="2026-08"); valor=tk.StringVar(); self.campo(a,"Referência",ref); self.campo(a,"Valor da meta",valor)
        from interface.componentes import criar_botao
        def salvar():
            try: salvar_meta(ref.get(),valor.get(),self.usuario)
            except Exception as e:
                from tkinter import messagebox; messagebox.showerror("Comercial",str(e),parent=j); return
            j.destroy(); self.reabrir("metas")
        criar_botao(a,"SALVAR META",salvar).pack(anchor="e",pady=18)
