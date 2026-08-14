"""Legal Operations — interface especializada Jurídico V10.3.3."""
from __future__ import annotations
import tkinter as tk
from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.departamentos.juridico import (
    analisar_juridico, criar_audiencia, criar_contrato, criar_prazo, criar_processo, criar_provisao,
    exportar_dataframe_juridico, listar_audiencias, listar_contratos, listar_prazos, listar_processos,
    listar_provisoes, listar_riscos, registrar_risco, resumo_juridico,
)
from interface.workspace_especializado import WorkspaceEspecializado, moeda
from interface.tema import CORES

COR_JURIDICO="#D8A728"
GRUPOS_MENU=(
    ("JURÍDICO",(("visao","📊","Visão geral"),("prazos","📅","Prazos"))),
    ("CONTENCIOSO",(("processos","⚖","Processos"),("audiencias","◷","Audiências"),("riscos","⚠","Riscos"),("provisoes","$","Provisões"))),
    ("CONTRATOS",(("contratos","▤","Contratos"),("relatorios","▥","Relatórios"))),
)
ROTULOS={k:r for _,itens in GRUPOS_MENU for k,_,r in itens}

class TelaJuridico(WorkspaceEspecializado):
    modulo="juridico"; titulo_sidebar="JURÍDICO"; etiqueta="LEGAL OPERATIONS 3.3"; cor=COR_JURIDICO; grupos_menu=GRUPOS_MENU; rotulos=ROTULOS
    def __init__(self,root,navegacao,secao="visao"):
        if not tem_permissao(SESSAO.usuario,"juridico","ler"): raise PermissionError("Seu perfil não possui acesso ao Jurídico.")
        self.root=root; self.navegacao=navegacao; self.usuario=SESSAO.usuario; self.secao=secao if secao in ROTULOS else "visao"
        self.container=tk.Frame(root,bg=CORES["bg"]); self.container.pack(fill="both",expand=True); self.montar_base(); getattr(self,f"_{self.secao}",self._visao)()
    def _visao(self):
        self.cabecalho("Agenda e exposição jurídica","Prazos, processos, contratos, riscos e provisões priorizados pela urgência.",lambda p:self.acoes(p,("+ PRAZO",self._novo_prazo),("+ PROCESSO",self._novo_processo)))
        r=resumo_juridico(self.usuario); a=analisar_juridico(self.usuario)
        self.metricas((("Contratos",r["contratos"],"▤"),("Contratos ativos",r["contratos_ativos"],"✓"),("Processos ativos",r["processos_ativos"],"⚖"),("Prazos 30 dias",r["prazos_30_dias"],"📅"),("Riscos abertos",r["riscos_abertos"],"⚠"),("Exposição",moeda(r["exposicao_centavos"]),"$"),("Provisões",moeda(r["provisoes_centavos"]),"≈")))
        self.painel_alertas(a["alertas"])
        self.tabela(listar_prazos(self.usuario,somente_pendentes=True)[:12],(("titulo","Prazo",250),("vencimento","Vencimento",120),("tipo","Tipo",120),("prioridade","Prioridade",90),("status","Status",95)),vazio=("📅","Agenda em dia","Nenhum prazo jurídico pendente."))
    def _prazos(self):
        self.cabecalho("Prazos","Agenda jurídica com prioridade, vínculo e status.",lambda p:self.acoes(p,("+ PRAZO",self._novo_prazo)))
        self.tabela(listar_prazos(self.usuario),(("titulo","Prazo",250),("vencimento","Vencimento",120),("tipo","Tipo",120),("prioridade","Prioridade",90),("processo_id","Processo ID",90),("contrato_id","Contrato ID",90),("status","Status",100)))
    def _processos(self):
        self.cabecalho("Processos","Carteira contenciosa com fase, risco, probabilidade e valor da causa.",lambda p:self.acoes(p,("+ PROCESSO",self._novo_processo)))
        self.tabela(listar_processos(self.usuario),(("numero","Número",150),("titulo","Processo",220),("tribunal","Tribunal",140),("fase","Fase",110),("probabilidade","Probabilidade",110),("risco","Risco",85),("valor_causa_centavos","Valor causa",120),("status","Status",90)),moedas={"valor_causa_centavos"})
    def _audiencias(self):
        self.cabecalho("Audiências","Agenda de compromissos processuais.",lambda p:self.acoes(p,("+ AUDIÊNCIA",self._nova_audiencia)))
        self.tabela(listar_audiencias(self.usuario),(("processo_numero","Processo",150),("data_hora","Data/hora",150),("local","Local",180),("tipo","Tipo",120),("responsavel","Responsável",150),("status","Status",100)))
    def _riscos(self):
        self.cabecalho("Riscos jurídicos","Probabilidade, impacto e exposição financeira por tema.",lambda p:self.acoes(p,("+ RISCO",self._novo_risco)))
        self.tabela(listar_riscos(self.usuario),(("titulo","Risco",230),("probabilidade","Probabilidade",110),("impacto","Impacto",100),("exposicao_centavos","Exposição",120),("revisado_em","Revisado em",110),("status","Status",90)),moedas={"exposicao_centavos"})
    def _provisoes(self):
        self.cabecalho("Provisões","Valores jurídicos preparados para integração financeira.",lambda p:self.acoes(p,("+ PROVISÃO",self._nova_provisao),("ENVIAR AO FINANCEIRO",self._encaminhar_provisao)))
        self.tabela(listar_provisoes(self.usuario),(("referencia","Referência",120),("processo_id","Processo ID",90),("risco_id","Risco ID",80),("valor_centavos","Valor",120),("status","Status",100),("observacoes","Observações",240)),moedas={"valor_centavos"})
    def _encaminhar_provisao(self):
        from tkinter import simpledialog,messagebox
        from services.orquestracao import encaminhar_provisao_financeiro
        itens=listar_provisoes(self.usuario)
        if not itens: messagebox.showinfo("Jurídico → Financeiro","Não há provisões para encaminhar.",parent=self.root); return
        resumo="\n".join(f"#{x['id']} · {x.get('referencia')} · {moeda(x.get('valor_centavos'))}" for x in itens[:20])
        pid=simpledialog.askinteger("Encaminhar provisão",f"Informe o ID da provisão:\n\n{resumo}",parent=self.root)
        if not pid: return
        try:
            r=encaminhar_provisao_financeiro(pid,self.usuario)
            messagebox.showinfo("Jurídico → Financeiro",f"Fluxo #{r['orquestracao_id']} aberto para análise financeira. Nenhum lançamento foi criado automaticamente.",parent=self.root)
        except Exception as exc: messagebox.showerror("Jurídico → Financeiro",str(exc),parent=self.root)
    def _contratos(self):
        self.cabecalho("Contratos","Ciclo contratual com vencimento, risco, parte e valor.",lambda p:self.acoes(p,("+ CONTRATO",self._novo_contrato)))
        self.tabela(listar_contratos(self.usuario),(("numero","Número",120),("titulo","Contrato",230),("parte","Parte",170),("valor_centavos","Valor",115),("risco","Risco",85),("vencimento","Vencimento",110),("status","Status",100)),moedas={"valor_centavos"})
    def _relatorios(self):
        self.cabecalho("Relatórios","Dados do contencioso prontos para Analytics corporativo.")
        df=exportar_dataframe_juridico(self.usuario); self.tabela(df.to_dict("records"),(("numero","Número",150),("titulo","Processo",230),("fase","Fase",110),("probabilidade","Probabilidade",110),("risco","Risco",85),("valor_causa","Valor causa",120),("status","Status",90)))
    def _novo_contrato(self):
        j,a=self.dialogo("Novo contrato"); vars={k:tk.StringVar() for k in ("numero","titulo","parte","objeto","valor","inicio","vencimento")}; risco=tk.StringVar(value="Baixo"); status=tk.StringVar(value="Elaboração")
        for rot,k in (("Número","numero"),("Título","titulo"),("Parte","parte"),("Objeto","objeto"),("Valor","valor"),("Início","inicio"),("Vencimento","vencimento")): self.campo(a,rot,vars[k])
        self.campo(a,"Risco",risco,valores=("Baixo","Médio","Alto","Crítico")); self.campo(a,"Status",status,valores=("Elaboração","Revisão","Ativo","Encerrado"))
        from interface.componentes import criar_botao
        criar_botao(a,"CRIAR CONTRATO",lambda:self.salvar_dialogo(j,criar_contrato,{**{k:v.get() for k,v in vars.items()},"risco":risco.get(),"status":status.get()},"contratos")).pack(anchor="e",pady=18)
    def _novo_processo(self):
        j,a=self.dialogo("Novo processo"); vars={k:tk.StringVar() for k in ("numero","titulo","tribunal","parte_contraria","advogado_responsavel","tipo","fase","valor_causa")}; prob=tk.StringVar(value="Possível"); risco=tk.StringVar(value="Médio")
        for rot,k in (("Número","numero"),("Título","titulo"),("Tribunal","tribunal"),("Parte contrária","parte_contraria"),("Advogado responsável","advogado_responsavel"),("Tipo","tipo"),("Fase","fase"),("Valor da causa","valor_causa")): self.campo(a,rot,vars[k])
        self.campo(a,"Probabilidade",prob,valores=("Remota","Possível","Provável")); self.campo(a,"Risco",risco,valores=("Baixo","Médio","Alto","Crítico"))
        from interface.componentes import criar_botao
        criar_botao(a,"CRIAR PROCESSO",lambda:self.salvar_dialogo(j,criar_processo,{**{k:v.get() for k,v in vars.items()},"probabilidade":prob.get(),"risco":risco.get()},"processos")).pack(anchor="e",pady=18)
    def _novo_prazo(self):
        j,a=self.dialogo("Novo prazo",590,650); titulo=tk.StringVar(); venc=tk.StringVar(); tipo=tk.StringVar(); prioridade=tk.StringVar(value="Alta"); proc=tk.StringVar(); contrato=tk.StringVar(); procs=listar_processos(self.usuario); contratos=listar_contratos(self.usuario); mp={f"{x['numero']} · {x['titulo']}":x["id"] for x in procs}; mc={f"{x.get('numero') or '#'+str(x['id'])} · {x['titulo']}":x["id"] for x in contratos}
        self.campo(a,"Título",titulo); self.campo(a,"Vencimento",venc); self.campo(a,"Tipo",tipo); self.campo(a,"Prioridade",prioridade,valores=("Baixa","Média","Alta","Crítica")); self.campo(a,"Processo",proc,valores=[""]+list(mp)); self.campo(a,"Contrato",contrato,valores=[""]+list(mc))
        from interface.componentes import criar_botao
        criar_botao(a,"CRIAR PRAZO",lambda:self.salvar_dialogo(j,criar_prazo,{"titulo":titulo.get(),"vencimento":venc.get(),"tipo":tipo.get(),"prioridade":prioridade.get(),"processo_id":mp.get(proc.get()),"contrato_id":mc.get(contrato.get())},"prazos")).pack(anchor="e",pady=18)
    def _nova_audiencia(self):
        j,a=self.dialogo("Nova audiência",570,620); procs=listar_processos(self.usuario); mapa={f"{x['numero']} · {x['titulo']}":x["id"] for x in procs}; proc=tk.StringVar(); data=tk.StringVar(); local=tk.StringVar(); tipo=tk.StringVar(); resp=tk.StringVar()
        self.campo(a,"Processo",proc,valores=list(mapa)); self.campo(a,"Data/hora",data); self.campo(a,"Local",local); self.campo(a,"Tipo",tipo); self.campo(a,"Responsável",resp)
        from interface.componentes import criar_botao
        criar_botao(a,"AGENDAR AUDIÊNCIA",lambda:self.salvar_dialogo(j,criar_audiencia,{"processo_id":mapa.get(proc.get()),"data_hora":data.get(),"local":local.get(),"tipo":tipo.get(),"responsavel":resp.get()},"audiencias")).pack(anchor="e",pady=18)
    def _novo_risco(self):
        j,a=self.dialogo("Novo risco",590,650); titulo=tk.StringVar(); prob=tk.StringVar(value="Possível"); impacto=tk.StringVar(value="Médio"); exposicao=tk.StringVar(); justificativa=tk.StringVar(); proc=tk.StringVar(); procs=listar_processos(self.usuario); mapa={f"{x['numero']} · {x['titulo']}":x["id"] for x in procs}
        self.campo(a,"Título",titulo); self.campo(a,"Processo",proc,valores=[""]+list(mapa)); self.campo(a,"Probabilidade",prob,valores=("Remota","Possível","Provável")); self.campo(a,"Impacto",impacto,valores=("Baixo","Médio","Alto","Crítico")); self.campo(a,"Exposição",exposicao); self.campo(a,"Justificativa",justificativa)
        from interface.componentes import criar_botao
        criar_botao(a,"REGISTRAR RISCO",lambda:self.salvar_dialogo(j,registrar_risco,{"titulo":titulo.get(),"processo_id":mapa.get(proc.get()),"probabilidade":prob.get(),"impacto":impacto.get(),"exposicao":exposicao.get(),"justificativa":justificativa.get()},"riscos")).pack(anchor="e",pady=18)
    def _nova_provisao(self):
        j,a=self.dialogo("Nova provisão",570,590); proc=tk.StringVar(); risco=tk.StringVar(); ref=tk.StringVar(value="2026-08"); valor=tk.StringVar(); procs=listar_processos(self.usuario); riscos=listar_riscos(self.usuario); mp={f"{x['numero']} · {x['titulo']}":x["id"] for x in procs}; mr={f"#{x['id']} · {x['titulo']}":x["id"] for x in riscos}
        self.campo(a,"Processo",proc,valores=[""]+list(mp)); self.campo(a,"Risco",risco,valores=[""]+list(mr)); self.campo(a,"Referência",ref); self.campo(a,"Valor",valor)
        from interface.componentes import criar_botao
        criar_botao(a,"CRIAR PROVISÃO",lambda:self.salvar_dialogo(j,criar_provisao,{"processo_id":mp.get(proc.get()),"risco_id":mr.get(risco.get()),"referencia":ref.get(),"valor":valor.get()},"provisoes")).pack(anchor="e",pady=18)
