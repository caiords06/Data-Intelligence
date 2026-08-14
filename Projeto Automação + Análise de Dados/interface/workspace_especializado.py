"""Infraestrutura visual compartilhada para workspaces departamentais V10.3.x."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from interface.componentes import AreaRolavel, GradeResponsiva, criar_botao, criar_cabecalho, criar_card, criar_estado_vazio, criar_metrica, criar_titulo_secao, preparar_janela_secundaria
from interface.tema import CORES, FONTES, LAYOUT, configurar_estilos_ttk
from interface.navegacao_modulos import criar_sidebar_modulo


def moeda(centavos):
    valor=int(centavos or 0)/100
    return "R$ "+f"{valor:,.2f}".replace(",","_").replace(".",",").replace("_",".")


class WorkspaceEspecializado:
    modulo=""; titulo_sidebar=""; etiqueta=""; cor="#308CFF"; grupos_menu=(); rotulos={}

    def montar_base(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_modulo(self.container,self.navegacao,modulo=self.modulo,titulo=self.titulo_sidebar,ativo=self.secao,grupos_menu=self.grupos_menu,grupos_recolhiveis=True)
        viewport=AreaRolavel(self.container); viewport.pack(side="left",fill="both",expand=True,padx=LAYOUT["conteudo_padx"],pady=(22,20)); self.conteudo=viewport.conteudo

    def cabecalho(self,titulo,subtitulo,acao=None):
        criar_cabecalho(self.conteudo,titulo,subtitulo,breadcrumb=f"MÓDULOS / {self.titulo_sidebar} / {titulo.upper()}",etiqueta=self.etiqueta,acao=acao)

    def acoes(self,parent,*acoes):
        bloco=tk.Frame(parent,bg=CORES["bg"])
        for i,(texto,cmd) in enumerate(reversed(acoes)):
            criar_botao(bloco,texto,cmd,tipo="secundario" if i else "primario",compacto=True).pack(side="right",padx=(8 if i else 0,0))
        return bloco

    def metricas(self,itens,max_colunas=4):
        grade=GradeResponsiva(self.conteudo,max_colunas=max_colunas,largura_minima=185,gap=10,bg=CORES["bg"]); grade.pack(fill="x",pady=(0,16))
        for titulo,valor,icone in itens: grade.adicionar(criar_metrica(grade,titulo,valor,icone=icone,cor=self.cor))

    def tabela(self,dados,colunas,*,moedas=None,vazio=("◇","Nenhum registro","Não há dados para exibir.")):
        if not dados:
            criar_estado_vazio(self.conteudo,*vazio,cor=self.cor).pack(fill="x"); return
        moedas=moedas or set(); card=criar_card(self.conteudo); card.pack(fill="both",expand=True)
        area=tk.Frame(card,bg=CORES["card"]); area.pack(fill="both",expand=True,padx=16,pady=16); nomes=[c[0] for c in colunas]
        tabela=ttk.Treeview(area,columns=nomes,show="headings",style="App.Treeview")
        for chave,titulo,largura in colunas: tabela.heading(chave,text=titulo); tabela.column(chave,width=largura,minwidth=max(65,largura//2),stretch=True)
        for item in dados:
            vals=[]
            for chave,_,_ in colunas:
                valor=item.get(chave)
                if chave in moedas: valor=moeda(valor)
                vals.append("—" if valor in (None,"") else valor)
            tabela.insert("","end",values=vals)
        sy=ttk.Scrollbar(area,orient="vertical",command=tabela.yview,style="App.Vertical.TScrollbar"); sx=ttk.Scrollbar(area,orient="horizontal",command=tabela.xview,style="App.Horizontal.TScrollbar")
        tabela.configure(yscrollcommand=sy.set,xscrollcommand=sx.set); tabela.grid(row=0,column=0,sticky="nsew"); sy.grid(row=0,column=1,sticky="ns"); sx.grid(row=1,column=0,sticky="ew")
        area.grid_rowconfigure(0,weight=1,minsize=280); area.grid_columnconfigure(0,weight=1)

    def painel_alertas(self,alertas,titulo="O que precisa de atenção"):
        card=criar_card(self.conteudo); card.pack(fill="x",pady=(0,16)); criar_titulo_secao(card,titulo,"Exceções e próximos passos calculados a partir do módulo.")
        itens=alertas or ["Nenhuma exceção crítica detectada no momento."]
        for item in itens[:6]:
            tk.Label(card,text=("⚠  " if alertas else "✓  ")+str(item),bg=CORES["card"],fg=CORES["warning"] if alertas else CORES["success"],font=FONTES["texto_pequeno"],justify="left",wraplength=800).pack(anchor="w",padx=18,pady=6)
        tk.Frame(card,bg=CORES["card"],height=8).pack()

    def dialogo(self,titulo,largura=610,altura=700):
        j=tk.Toplevel(self.root); j.title(titulo); j.configure(bg=CORES["bg"]); preparar_janela_secundaria(j,self.root,largura,altura,minimo=(500,440),modal=True)
        area=AreaRolavel(j); area.pack(fill="both",expand=True,padx=24,pady=20); return j,area.conteudo

    def campo(self,parent,rotulo,var,*,valores=None):
        tk.Label(parent,text=rotulo.upper(),bg=CORES["bg"],fg=CORES["text_sec"],font=("Inter",8,"bold")).pack(anchor="w",pady=(9,4))
        if valores is not None:
            w=ttk.Combobox(parent,textvariable=var,values=valores,state="readonly",style="App.TCombobox"); w.pack(fill="x",ipady=3); return w
        w=tk.Entry(parent,textvariable=var,bg=CORES["input"],fg=CORES["text"],insertbackground=self.cor,relief="flat"); w.pack(fill="x",ipady=8); return w

    def salvar_dialogo(self,j,funcao,dados,secao):
        try: funcao(dados,self.usuario)
        except (ValueError,PermissionError,ConnectionError) as erro: messagebox.showerror(self.titulo_sidebar,str(erro),parent=j); return
        j.destroy(); self.reabrir(secao)

    def reabrir(self,secao):
        cb=self.navegacao.get("secao_modulo")
        if callable(cb): cb(self.modulo,secao)
