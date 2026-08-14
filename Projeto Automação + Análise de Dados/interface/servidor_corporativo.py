"""Painel administrativo dos arquivos e backups mantidos no servidor corporativo."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from auth.sessao import SESSAO
from core.nodo import carregar_config_nodo, usa_servidor_remoto
from services.servidor_cliente import excluir_item_servidor, listar_arquivos_servidor, testar_servidor
from interface.componentes import preparar_janela_secundaria
from interface.tema import CORES, configurar_estilos_ttk


class JanelaServidorCorporativo:
    def __init__(self, root):
        if not SESSAO.eh_admin():
            raise PermissionError("Somente administradores podem gerenciar o armazenamento corporativo.")
        if not usa_servidor_remoto():
            raise ValueError("Esta estação não está vinculada a um Servidor Corporativo.")
        self.root=root; self.janela=tk.Toplevel(root); self.janela.title("Servidor corporativo · armazenamento e backups")
        self.janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(self.janela,root,1080,700,minimo=(820,560),modal=False)
        configurar_estilos_ttk(self.janela)
        self.tipo=tk.StringVar(value="Arquivos")
        self._montar(); self.atualizar()

    def _montar(self):
        top=tk.Frame(self.janela,bg=CORES["bg"]); top.pack(fill="x",padx=24,pady=(22,12))
        tk.Label(top,text="Servidor corporativo",font=("Inter",20,"bold"),fg=CORES["text"],bg=CORES["bg"]).pack(anchor="w")
        cfg=carregar_config_nodo()
        self.status=tk.Label(top,text=f"{cfg.servidor_url} · verificando...",font=("Inter",9),fg=CORES["text_sec"],bg=CORES["bg"]); self.status.pack(anchor="w",pady=(4,0))
        actions=tk.Frame(self.janela,bg=CORES["bg"]); actions.pack(fill="x",padx=24,pady=(0,10))
        for nome in ("Arquivos","Backups"):
            tk.Radiobutton(actions,text=nome,variable=self.tipo,value=nome,command=self.atualizar,indicatoron=False,bg=CORES["card_secundario"],fg=CORES["text"],selectcolor=CORES["primary"],activebackground=CORES["card_hover"],activeforeground=CORES["text"],bd=0,padx=14,pady=7).pack(side="left",padx=(0,6))
        tk.Button(actions,text="ATUALIZAR",command=self.atualizar,bg=CORES["card_secundario"],fg=CORES["text"],activebackground=CORES["card_hover"],activeforeground=CORES["text"],bd=0,padx=14,pady=7).pack(side="right")
        tk.Button(actions,text="REMOVER SELECIONADO",command=self.remover,bg=CORES["danger"],fg="#fff",activebackground=CORES["danger"],activeforeground="#fff",bd=0,padx=14,pady=7).pack(side="right",padx=8)
        frame=tk.Frame(self.janela,bg=CORES["border"]); frame.pack(fill="both",expand=True,padx=24,pady=(0,24))
        self.tree=ttk.Treeview(frame,columns=("id","nome","categoria","modulo","tamanho","data"),show="headings",style="Dark.Treeview")
        for c,t,w in (("id","ID",60),("nome","Arquivo / tipo",320),("categoria","Categoria",130),("modulo","Módulo",120),("tamanho","Tamanho",120),("data","Data",180)):
            self.tree.heading(c,text=t); self.tree.column(c,width=w,anchor="w")
        sy=ttk.Scrollbar(frame,orient="vertical",command=self.tree.yview); self.tree.configure(yscrollcommand=sy.set)
        self.tree.pack(side="left",fill="both",expand=True,padx=1,pady=1); sy.pack(side="right",fill="y",pady=1,padx=(0,1))

    def atualizar(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        backup=self.tipo.get()=="Backups"
        try:
            health=testar_servidor(); itens=listar_arquivos_servidor(backups=backup)
            self.status.configure(text=f"Servidor online · v{health.get('versao','?')} · {len(itens)} item(ns)",fg=CORES["success"])
        except Exception as erro:
            self.status.configure(text=str(erro),fg=CORES["danger"]); return
        for item in itens:
            if backup:
                nome=item.get("arquivo_relativo") or item.get("tipo") or "Backup"; categoria=item.get("tipo") or "Completo"; modulo="backup"
            else:
                nome=item.get("nome") or "Arquivo"; categoria=item.get("categoria") or "arquivo"; modulo=item.get("modulo") or "—"
            tamanho=int(item.get("tamanho_bytes") or 0); exib=f"{tamanho/1024/1024:.2f} MB" if tamanho>=1024*1024 else f"{tamanho/1024:.1f} KB"
            self.tree.insert("","end",iid=str(item["id"]),values=(item["id"],nome,categoria,modulo,exib,item.get("criado_em") or "—"))

    def remover(self):
        sel=self.tree.selection()
        if not sel: return
        iid=int(sel[0]); backup=self.tipo.get()=="Backups"
        if not messagebox.askyesno("Servidor corporativo","Remover fisicamente este item do armazenamento central?\n\nA ação é restrita ao administrador.",parent=self.janela): return
        try: excluir_item_servidor(iid,backup=backup)
        except Exception as erro: messagebox.showerror("Servidor corporativo",str(erro),parent=self.janela); return
        self.atualizar()
