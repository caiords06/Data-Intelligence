"""Workplace Operations — interface especializada Administrativo V10.3.2."""
from __future__ import annotations
import tkinter as tk
from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.departamentos.administrativo import (
    analisar_administrativo, criar_manutencao, criar_recurso, criar_reembolso, criar_reserva, criar_solicitacao,
    criar_viagem, exportar_dataframe_administrativo, listar_manutencoes, listar_recursos, listar_reembolsos,
    listar_reservas, listar_solicitacoes, listar_viagens, resumo_administrativo,
)
from interface.workspace_especializado import WorkspaceEspecializado, moeda
from interface.tema import CORES

COR_ADMIN="#7694B8"
GRUPOS_MENU=(
    ("ADMINISTRATIVO",(("visao","📊","Visão geral"),("solicitacoes","📥","Solicitações"))),
    ("OPERAÇÃO",(("facilities","🏢","Facilities"),("reservas","📅","Reservas"),("viagens","✈","Viagens"),("reembolsos","🧾","Reembolsos"),("manutencao","🔧","Manutenção"))),
    ("GESTÃO",(("recursos","▣","Recursos"),("relatorios","▥","Relatórios"))),
)
ROTULOS={k:r for _,itens in GRUPOS_MENU for k,_,r in itens}

class TelaAdministrativo(WorkspaceEspecializado):
    modulo="administrativo"; titulo_sidebar="ADMINISTRATIVO"; etiqueta="WORKPLACE OPS 3.2"; cor=COR_ADMIN; grupos_menu=GRUPOS_MENU; rotulos=ROTULOS
    def __init__(self,root,navegacao,secao="visao"):
        if not tem_permissao(SESSAO.usuario,"administrativo","ler"): raise PermissionError("Seu perfil não possui acesso ao Administrativo.")
        self.root=root; self.navegacao=navegacao; self.usuario=SESSAO.usuario; self.secao=secao if secao in ROTULOS else "visao"
        self.container=tk.Frame(root,bg=CORES["bg"]); self.container.pack(fill="both",expand=True); self.montar_base(); getattr(self,f"_{self.secao}",self._visao)()
    def _visao(self):
        self.cabecalho("Operações do escritório","Solicitações, reservas, viagens, reembolsos e manutenção em uma central de serviços.",lambda p:self.acoes(p,("+ SOLICITAÇÃO",self._nova_solicitacao),("+ RESERVA",self._nova_reserva)))
        r=resumo_administrativo(self.usuario); a=analisar_administrativo(self.usuario)
        self.metricas((("Solicitações",r["solicitacoes"],"📥"),("Abertas",r["abertas"],"◷"),("Alta criticidade",r["criticas"],"⚠"),("Reservas",r["reservas"],"📅"),("Reembolsos",r["reembolsos_pendentes"],"🧾"),("Valor reembolsos",moeda(r["reembolsos_centavos"]),"$")))
        self.painel_alertas(a["alertas"])
        self.tabela(listar_solicitacoes(self.usuario)[:12],(("numero","Número",105),("titulo","Solicitação",230),("categoria","Categoria",120),("solicitante_nome","Solicitante",150),("prioridade","Prioridade",90),("status","Status",105),("prazo","Prazo",105)),vazio=("📥","Fila vazia","Nenhuma solicitação administrativa aberta."))
    def _solicitacoes(self):
        self.cabecalho("Solicitações internas","Fila operacional com prioridade, SLA, prazo e responsável.",lambda p:self.acoes(p,("+ SOLICITAÇÃO",self._nova_solicitacao)))
        self.tabela(listar_solicitacoes(self.usuario),(("numero","Número",105),("titulo","Solicitação",230),("categoria","Categoria",120),("solicitante_nome","Solicitante",150),("prioridade","Prioridade",90),("sla_horas","SLA h",70),("prazo","Prazo",105),("valor_centavos","Valor",110),("status","Status",105)),moedas={"valor_centavos"})
    def _facilities(self):
        self.cabecalho("Facilities","Ocorrências de infraestrutura e serviços físicos do ambiente.",lambda p:self.acoes(p,("+ MANUTENÇÃO",self._nova_manutencao)))
        self.tabela(listar_manutencoes(self.usuario),(("titulo","Ocorrência",230),("recurso_nome","Recurso",150),("prioridade","Prioridade",90),("fornecedor","Fornecedor",150),("custo_centavos","Custo",110),("prazo","Prazo",100),("status","Status",100)),moedas={"custo_centavos"},vazio=("🏢","Facilities sem pendências","Cadastre uma manutenção quando houver uma necessidade física."))
    def _reservas(self):
        self.cabecalho("Reservas","Agenda compartilhada de salas, veículos e outros recursos.",lambda p:self.acoes(p,("+ RESERVA",self._nova_reserva),("+ RECURSO",self._novo_recurso)))
        self.tabela(listar_reservas(self.usuario),(("titulo","Reserva",200),("recurso_nome","Recurso",160),("recurso_tipo","Tipo",100),("inicio","Início",150),("fim","Fim",150),("status","Status",100)))
    def _viagens(self):
        self.cabecalho("Viagens","Solicitações e acompanhamento de viagens corporativas.",lambda p:self.acoes(p,("+ VIAGEM",self._nova_viagem)))
        self.tabela(listar_viagens(self.usuario),(("viajante","Viajante",160),("destino","Destino",180),("inicio","Início",100),("fim","Fim",100),("custo_estimado_centavos","Estimativa",115),("status","Status",105)),moedas={"custo_estimado_centavos"})
    def _reembolsos(self):
        self.cabecalho("Reembolsos","Fila de despesas a validar e encaminhar ao Financeiro.",lambda p:self.acoes(p,("+ REEMBOLSO",self._novo_reembolso)))
        self.tabela(listar_reembolsos(self.usuario),(("solicitante","Solicitante",160),("categoria","Categoria",120),("descricao","Descrição",240),("valor_centavos","Valor",110),("status","Status",100),("pago_em","Pago em",105)),moedas={"valor_centavos"})
    def _manutencao(self): return self._facilities()
    def _recursos(self):
        self.cabecalho("Recursos","Catálogo reservável de salas, veículos e equipamentos.",lambda p:self.acoes(p,("+ RECURSO",self._novo_recurso)))
        self.tabela(listar_recursos(self.usuario),(("tipo","Tipo",110),("nome","Recurso",210),("localizacao","Localização",180),("capacidade","Capacidade",95),("status","Status",105)))
    def _relatorios(self):
        self.cabecalho("Relatórios","Solicitações consolidadas para Analytics corporativo.")
        df=exportar_dataframe_administrativo(self.usuario); self.tabela(df.to_dict("records"),(("numero","Número",105),("titulo","Solicitação",230),("categoria","Categoria",120),("prioridade","Prioridade",90),("valor","Valor",110),("status","Status",100)))
    def _nova_solicitacao(self):
        j,a=self.dialogo("Nova solicitação"); vars={k:tk.StringVar() for k in ("titulo","descricao","prazo","valor")}; categoria=tk.StringVar(value="Facilities"); prioridade=tk.StringVar(value="Média")
        self.campo(a,"Título",vars["titulo"]); self.campo(a,"Categoria",categoria,valores=("Facilities","Viagem","Reembolso","Manutenção","Documento","Sala","Veículo","Outro")); self.campo(a,"Prioridade",prioridade,valores=("Baixa","Média","Alta","Crítica")); self.campo(a,"Descrição",vars["descricao"]); self.campo(a,"Prazo",vars["prazo"]); self.campo(a,"Valor estimado",vars["valor"])
        from interface.componentes import criar_botao
        criar_botao(a,"ABRIR SOLICITAÇÃO",lambda:self.salvar_dialogo(j,criar_solicitacao,{**{k:v.get() for k,v in vars.items()},"categoria":categoria.get(),"prioridade":prioridade.get()},"solicitacoes")).pack(anchor="e",pady=18)
    def _novo_recurso(self):
        j,a=self.dialogo("Novo recurso",560,590); nome=tk.StringVar(); tipo=tk.StringVar(value="Sala"); local=tk.StringVar(); capacidade=tk.StringVar(value="0")
        self.campo(a,"Nome",nome); self.campo(a,"Tipo",tipo,valores=("Sala","Veículo","Equipamento","Auditório","Estação","Outro")); self.campo(a,"Localização",local); self.campo(a,"Capacidade",capacidade)
        from interface.componentes import criar_botao
        criar_botao(a,"CRIAR RECURSO",lambda:self.salvar_dialogo(j,criar_recurso,{"nome":nome.get(),"tipo":tipo.get(),"localizacao":local.get(),"capacidade":capacidade.get()},"recursos")).pack(anchor="e",pady=18)
    def _nova_reserva(self):
        j,a=self.dialogo("Nova reserva",580,620); recursos=listar_recursos(self.usuario); mapa={f"{x['nome']} · {x['tipo']}":x["id"] for x in recursos}; recurso=tk.StringVar(); titulo=tk.StringVar(); inicio=tk.StringVar(); fim=tk.StringVar()
        self.campo(a,"Recurso",recurso,valores=list(mapa)); self.campo(a,"Título",titulo); self.campo(a,"Início (AAAA-MM-DD HH:MM)",inicio); self.campo(a,"Fim (AAAA-MM-DD HH:MM)",fim)
        from interface.componentes import criar_botao
        criar_botao(a,"CONFIRMAR RESERVA",lambda:self.salvar_dialogo(j,criar_reserva,{"recurso_id":mapa.get(recurso.get()),"titulo":titulo.get(),"inicio":inicio.get(),"fim":fim.get()},"reservas")).pack(anchor="e",pady=18)
    def _nova_viagem(self):
        j,a=self.dialogo("Nova viagem",570,650); vars={k:tk.StringVar() for k in ("viajante","destino","inicio","fim","motivo","custo_estimado")}
        for rot,k in (("Viajante","viajante"),("Destino","destino"),("Início","inicio"),("Fim","fim"),("Motivo","motivo"),("Custo estimado","custo_estimado")): self.campo(a,rot,vars[k])
        from interface.componentes import criar_botao
        criar_botao(a,"SOLICITAR VIAGEM",lambda:self.salvar_dialogo(j,criar_viagem,{k:v.get() for k,v in vars.items()},"viagens")).pack(anchor="e",pady=18)
    def _novo_reembolso(self):
        j,a=self.dialogo("Novo reembolso",570,600); solicitante=tk.StringVar(); categoria=tk.StringVar(value="Alimentação"); descricao=tk.StringVar(); valor=tk.StringVar()
        self.campo(a,"Solicitante",solicitante); self.campo(a,"Categoria",categoria,valores=("Alimentação","Transporte","Hospedagem","Material","Outro")); self.campo(a,"Descrição",descricao); self.campo(a,"Valor",valor)
        from interface.componentes import criar_botao
        criar_botao(a,"SOLICITAR REEMBOLSO",lambda:self.salvar_dialogo(j,criar_reembolso,{"solicitante":solicitante.get(),"categoria":categoria.get(),"descricao":descricao.get(),"valor":valor.get()},"reembolsos")).pack(anchor="e",pady=18)
    def _nova_manutencao(self):
        j,a=self.dialogo("Nova manutenção",580,650); recursos=listar_recursos(self.usuario); mapa={x["nome"]:x["id"] for x in recursos}; recurso=tk.StringVar(); titulo=tk.StringVar(); prioridade=tk.StringVar(value="Média"); fornecedor=tk.StringVar(); custo=tk.StringVar(); prazo=tk.StringVar()
        self.campo(a,"Recurso",recurso,valores=[""]+list(mapa)); self.campo(a,"Título",titulo); self.campo(a,"Prioridade",prioridade,valores=("Baixa","Média","Alta","Crítica")); self.campo(a,"Fornecedor",fornecedor); self.campo(a,"Custo",custo); self.campo(a,"Prazo",prazo)
        from interface.componentes import criar_botao
        criar_botao(a,"ABRIR MANUTENÇÃO",lambda:self.salvar_dialogo(j,criar_manutencao,{"recurso_id":mapa.get(recurso.get()),"titulo":titulo.get(),"prioridade":prioridade.get(),"fornecedor":fornecedor.get(),"custo":custo.get(),"prazo":prazo.get()},"facilities")).pack(anchor="e",pady=18)
