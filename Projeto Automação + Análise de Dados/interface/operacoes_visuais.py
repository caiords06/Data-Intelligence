"""Operações departamentais em cartões, timelines e workspaces.

Usada nos módulos em que uma planilha não é a melhor metáfora. Os cadastros
que realmente pedem comparação tabular continuam no painel de grade.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from auth.sessao import SESSAO
from services.catalogo import obter_modulo
from services.contexto import tem_permissao
from services.recursos import alterar_estado_recurso, atualizar_recurso, criar_recurso, listar_recursos
from interface.componentes import AreaRolavel, GradeResponsiva, criar_botao, criar_cabecalho, criar_card, criar_chip, criar_sidebar, preparar_janela_secundaria
from interface.configuracao_modulos_ui import PAINEIS_MODULOS, obter_esquema_recurso
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import CORES, FONTES, LAYOUT, configurar_estilos_ttk


TITULOS_OPERACIONAIS = {
    "marketing": {"calendario": "Calendário editorial", "conteudo": "Estúdio de conteúdo", "automacao": "Automações de campanha", "registros": "Campanhas em execução"},
    "administrativo": {"facilities": "Central de facilities", "viagens": "Jornadas corporativas", "reembolsos": "Fila de reembolsos", "salas": "Agenda de espaços", "veiculos": "Frota operacional", "registros": "Solicitações internas"},
    "juridico": {"processos": "Carteira de processos", "prazos": "Agenda de prazos", "audiencias": "Agenda de audiências", "riscos": "Mapa de riscos", "registros": "Contratos e instrumentos"},
    "comercial": {"crm": "Relacionamentos", "pipeline": "Pipeline de receita", "propostas": "Propostas em negociação", "metas": "Ritmo das metas", "registros": "Oportunidades"},
}


def _valor(registro, chave):
    dados = registro.get("dados") or {}
    valor = dados.get(chave)
    if valor in (None, ""):
        mapa = {
            "status": "status", "responsavel": "responsavel", "valor": "valor",
        }
        valor = registro.get(mapa.get(chave, chave))
    return valor


def _payload(esquema, extras):
    primeiro = esquema[0][0]
    identificacao = str(extras.get(primeiro, "")).strip()
    if len(identificacao) < 2:
        raise ValueError(f"Preencha {esquema[0][1]} com ao menos 2 caracteres.")
    responsavel = next((extras.get(x) for x in ("responsavel", "gestor", "advogado", "proprietario") if extras.get(x)), "")
    valor = next((extras.get(c[0]) for c in esquema if c[2] == "moeda" and extras.get(c[0]) not in (None, "")), 0)
    data_ref = next((extras.get(c[0]) for c in esquema if c[2] == "data" and extras.get(c[0])), None)
    return {
        "identificacao": identificacao,
        "descricao": str(extras.get("descricao") or extras.get("objetivo") or extras.get("finalidade") or ""),
        "responsavel": responsavel or "",
        "status": str(extras.get("status") or "Pendente"),
        "prioridade": str(extras.get("prioridade") or extras.get("criticidade") or "Média"),
        "valor": valor or 0,
        "data_referencia": data_ref,
        "dados": extras,
    }


class TelaOperacaoVisual:
    def __init__(self, root, navegacao, modulo, secao):
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            raise PermissionError("Seu perfil não possui acesso a este módulo.")
        self.root, self.navegacao, self.modulo, self.secao = root, navegacao, modulo, secao
        self.modulo_config = obter_modulo(modulo)
        self.ui = PAINEIS_MODULOS[modulo]
        self.cor = self.modulo_config["cor"]
        self.esquema = obter_esquema_recurso(secao)
        self.container = tk.Frame(root, bg=CORES["bg"]); self.container.pack(fill="both", expand=True)
        self._criar()

    def _criar(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_modulo(
            self.container, self.navegacao, modulo=self.modulo,
            titulo=self.modulo_config["nome"].upper(), ativo=self.secao,
            itens_menu=self.ui["menu"],
        )
        viewport=AreaRolavel(self.container); viewport.pack(side="left",fill="both",expand=True,padx=LAYOUT["conteudo_padx"],pady=(22,20)); area=viewport.conteudo
        titulo = TITULOS_OPERACIONAIS.get(self.modulo, {}).get(self.secao, self.secao.replace("_"," ").title())
        criar_cabecalho(area, titulo, "Workspace operacional orientado ao objetivo do processo, sem aparência de planilha.", breadcrumb=f"MÓDULOS / {self.modulo_config['nome'].upper()} / {titulo.upper()}", etiqueta="OPERAÇÃO VISUAL")
        topo=tk.Frame(area,bg=CORES["bg"]); topo.pack(fill="x",pady=(0,12))
        self.pesquisa=tk.StringVar(); e=tk.Entry(topo,textvariable=self.pesquisa,bg=CORES["input"],fg=CORES["text"],insertbackground=self.cor,relief="flat"); e.pack(side="left",fill="x",expand=True,ipady=8); e.bind("<Return>",lambda _e:self._carregar(area_cards))
        criar_botao(topo,"PESQUISAR",lambda:self._carregar(area_cards),tipo="fantasma",compacto=True).pack(side="left",padx=6)
        self.estado=tk.StringVar(value="Ativo")
        seletor=ttk.Combobox(topo,textvariable=self.estado,values=("Ativo","Arquivado","Lixeira"),state="readonly",width=12,style="Dark.TCombobox")
        seletor.pack(side="left",padx=(0,8)); seletor.bind("<<ComboboxSelected>>",lambda _e:self._carregar(area_cards))
        criar_botao(topo,"+ NOVO",lambda:self._formulario(),compacto=True).pack(side="right")
        area_cards=GradeResponsiva(area,max_colunas=3,largura_minima=280,gap=10,bg=CORES["bg"]); area_cards.pack(fill="both",expand=True); self.area_cards=area_cards
        self._carregar(area_cards)

    def _carregar(self, parent=None):
        parent=parent or self.area_cards
        for w in list(parent.winfo_children()): w.destroy()
        try:
            resultado=listar_recursos(self.modulo,self.secao,SESSAO.usuario,tamanho=200,pesquisa=self.pesquisa.get() if hasattr(self,"pesquisa") else "",estado=self.estado.get() if hasattr(self,"estado") else "Ativo")
        except (ValueError,PermissionError) as erro:
            messagebox.showerror("Operação",str(erro),parent=self.root); return
        registros=resultado["registros"]
        if not registros:
            card=criar_card(parent); parent.adicionar(card); tk.Label(card,text="Nenhum item neste workspace",font=FONTES["subtitulo"],fg=CORES["text"],bg=CORES["card"]).pack(anchor="w",padx=18,pady=(18,5)); tk.Label(card,text="Use + NOVO para iniciar o fluxo.",font=FONTES["texto_pequeno"],fg=CORES["text_sec"],bg=CORES["card"]).pack(anchor="w",padx=18,pady=(0,18)); return
        for registro in registros:
            self._card(parent,registro)

    def _card(self,parent,registro):
        card=criar_card(parent); parent.adicionar(card); tk.Frame(card,bg=self.cor,height=3).pack(fill="x")
        status=str(registro.get("status") or "Pendente"); criar_chip(card,status,cor=self.cor).pack(anchor="e",padx=13,pady=(10,0))
        tk.Label(card,text=str(registro.get("identificacao") or "Sem identificação"),font=("Inter",11,"bold"),fg=CORES["text"],bg=CORES["card"],wraplength=260,justify="left").pack(anchor="w",padx=16,pady=(2,8))
        exibidos=0
        for campo in self.esquema[1:]:
            chave,rotulo=campo[0],campo[1]; valor=_valor(registro,chave)
            if valor in (None,""): continue
            tk.Label(card,text=f"{rotulo}: {valor}",font=FONTES["micro"],fg=CORES["text_sec"],bg=CORES["card"],wraplength=270,justify="left").pack(anchor="w",padx=16,pady=2)
            exibidos += 1
            if exibidos>=4: break
        rod=tk.Frame(card,bg=CORES["card"]); rod.pack(fill="x",padx=12,pady=13)
        estado=str(registro.get("estado_registro") or "Ativo")
        if estado == "Ativo":
            criar_botao(rod,"EDITAR",lambda r=registro:self._formulario(r),tipo="fantasma",compacto=True).pack(side="left")
            criar_botao(rod,"REMOVER",lambda r=registro:self._alterar_estado(r,"Lixeira"),tipo="perigo",compacto=True).pack(side="right")
            criar_botao(rod,"ARQUIVAR",lambda r=registro:self._alterar_estado(r,"Arquivado"),tipo="fantasma",compacto=True).pack(side="right",padx=5)
        else:
            criar_botao(rod,"RESTAURAR",lambda r=registro:self._alterar_estado(r,"Ativo"),tipo="sucesso",compacto=True).pack(side="right")
            if estado == "Arquivado":
                criar_botao(rod,"REMOVER",lambda r=registro:self._alterar_estado(r,"Lixeira"),tipo="perigo",compacto=True).pack(side="right",padx=5)

    def _formulario(self, registro=None):
        if not tem_permissao(SESSAO.usuario,self.modulo,"escrever"):
            messagebox.showerror("Acesso negado","Seu perfil não pode editar este workspace.",parent=self.root); return
        j=tk.Toplevel(self.root); j.title("Editar" if registro else "Novo registro"); j.configure(bg=CORES["bg"]); preparar_janela_secundaria(j,self.root,680,650,minimo=(580,460),modal=True)
        area=AreaRolavel(j); area.pack(fill="both",expand=True,padx=20,pady=20); vars={}; dados_antigos=(registro or {}).get("dados") or {}
        for campo in self.esquema:
            chave,rotulo,tipo,*cfg=campo; tk.Label(area.conteudo,text=rotulo.upper(),font=("Inter",8,"bold"),fg=CORES["text_sec"],bg=CORES["bg"]).pack(anchor="w",pady=(10,4))
            inicial=dados_antigos.get(chave, _valor(registro or {},chave) or "")
            var=tk.StringVar(value=str(inicial)); vars[chave]=var
            if tipo in {"opcoes","combo"} and cfg:
                w=ttk.Combobox(area.conteudo,textvariable=var,values=cfg[0],state="readonly",style="Dark.TCombobox")
            else:
                w=tk.Entry(area.conteudo,textvariable=var,bg=CORES["input"],fg=CORES["text"],insertbackground=self.cor,relief="flat")
            w.pack(fill="x",ipady=7)
        def salvar():
            extras={k:v.get().strip() for k,v in vars.items()}
            try:
                payload=_payload(self.esquema,extras)
                if registro: atualizar_recurso(self.modulo,self.secao,int(registro["id"]),payload,SESSAO.usuario)
                else: criar_recurso(self.modulo,self.secao,payload,SESSAO.usuario)
            except (ValueError,PermissionError) as erro: messagebox.showerror("Salvar",str(erro),parent=j); return
            j.destroy(); self._carregar()
        criar_botao(area.conteudo,"SALVAR",salvar).pack(anchor="e",pady=18)

    def _alterar_estado(self,registro,estado):
        verbo = "remover" if estado == "Lixeira" else "arquivar" if estado == "Arquivado" else "restaurar"
        if not messagebox.askyesno(
            "Confirmar alteração",
            f"Deseja {verbo} este registro? A operação ficará auditada.",
            parent=self.root,
        ):
            return
        try: alterar_estado_recurso(self.modulo,self.secao,int(registro["id"]),estado,SESSAO.usuario)
        except (ValueError,PermissionError) as erro: messagebox.showerror("Alterar registro",str(erro),parent=self.root); return
        self._carregar()
