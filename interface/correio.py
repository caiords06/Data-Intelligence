"""Cliente de correio corporativo interno, inspirado em clientes de desktop."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from auth.sessao import SESSAO
from enterprise.correio import (
    atualizar_estado,
    contagem_nao_lidas,
    enviar_mensagem,
    listar_caixa,
    listar_contatos,
    obter_mensagem,
    salvar_rascunho,
)
from interface.componentes import criar_botao, criar_cabecalho, criar_sidebar, preparar_janela_secundaria
from interface.tema import CORES, LAYOUT, configurar_estilos_ttk


CAIXAS = (
    ("entrada", "▣", "Caixa de entrada"),
    ("enviados", "↗", "Enviados"),
    ("rascunhos", "▤", "Rascunhos"),
    ("arquivados", "◇", "Arquivados"),
    ("lixeira", "×", "Lixeira"),
)


class TelaCorreio:
    def __init__(self, root, navegacao, *, modulo_origem=None, caixa="entrada"):
        self.root = root
        self.navegacao = navegacao
        self.modulo_origem = modulo_origem
        self.caixa = caixa if caixa in {x[0] for x in CAIXAS} else "entrada"
        self.mensagens = []
        self.mensagem_atual = None
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar()
        self.carregar()

    def _criar(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="correio",
            rodape_texto="Voltar ao módulo" if self.modulo_origem else "Voltar ao início",
            rodape_comando=(
                (lambda: self.navegacao["modulo"](self.modulo_origem))
                if self.modulo_origem
                else self.navegacao.get("inicio")
            ),
        )
        principal = tk.Frame(self.container, bg=CORES["bg"])
        principal.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(24, 20))

        criar_cabecalho(
            principal,
            "Correio corporativo",
            "Mensagens internas vinculadas ao diretório de usuários da empresa.",
            breadcrumb=(f"MÓDULOS / {self.modulo_origem.upper()} / CORREIO" if self.modulo_origem else "CENTRAL / CORREIO"),
            etiqueta="MENSAGENS INTERNAS",
        )

        barra = tk.Frame(principal, bg=CORES["bg"])
        barra.pack(fill="x", pady=(0, 12))
        criar_botao(barra, "+  NOVA MENSAGEM", self.compor, compacto=True).pack(side="left")
        self.busca = tk.StringVar()
        entrada = tk.Entry(
            barra, textvariable=self.busca, bg=CORES["input"], fg=CORES["text"],
            insertbackground=CORES["primary"], relief="flat", font=("Segoe UI", 9),
        )
        entrada.pack(side="right", fill="x", expand=True, padx=(18, 0), ipady=7)
        entrada.bind("<Return>", lambda _e: self.carregar())

        corpo = tk.Frame(principal, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True)
        corpo.grid_columnconfigure(0, weight=0)
        corpo.grid_columnconfigure(1, weight=3)
        corpo.grid_columnconfigure(2, weight=5)
        corpo.grid_rowconfigure(0, weight=1)

        self.pastas = tk.Frame(corpo, bg=CORES["card"], width=175, highlightthickness=1, highlightbackground=CORES["border"])
        self.pastas.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.pastas.grid_propagate(False)
        self._render_pastas()

        lista_frame = tk.Frame(corpo, bg=CORES["card"], highlightthickness=1, highlightbackground=CORES["border"])
        lista_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        lista_frame.grid_rowconfigure(1, weight=1)
        lista_frame.grid_columnconfigure(0, weight=1)
        self.rotulo_caixa = tk.Label(lista_frame, text="", bg=CORES["card"], fg=CORES["text"], font=("Segoe UI", 10, "bold"), anchor="w")
        self.rotulo_caixa.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        self.lista = tk.Listbox(
            lista_frame, bg=CORES["input"], fg=CORES["text"], selectbackground=CORES["sidebar_ativo"],
            selectforeground=CORES["text"], relief="flat", borderwidth=0, activestyle="none", font=("Segoe UI", 9)
        )
        y = ttk.Scrollbar(lista_frame, orient="vertical", command=self.lista.yview, style="Dark.Vertical.TScrollbar")
        self.lista.configure(yscrollcommand=y.set)
        self.lista.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        y.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10))
        self.lista.bind("<<ListboxSelect>>", self._selecionar)

        self.preview = tk.Frame(corpo, bg=CORES["card"], highlightthickness=1, highlightbackground=CORES["border"])
        self.preview.grid(row=0, column=2, sticky="nsew")
        self._preview_vazio()

    def _render_pastas(self):
        for w in self.pastas.winfo_children():
            w.destroy()
        tk.Label(self.pastas, text="PASTAS", bg=CORES["card"], fg=CORES["text_muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        nao_lidas = 0
        try:
            nao_lidas = contagem_nao_lidas(SESSAO.usuario)
        except Exception:
            pass
        for chave, icone, titulo in CAIXAS:
            texto = f"{icone}  {titulo}"
            if chave == "entrada" and nao_lidas:
                texto += f"  ({nao_lidas})"
            tk.Button(
                self.pastas, text=texto, anchor="w", relief="flat", bd=0,
                bg=CORES["sidebar_ativo"] if chave == self.caixa else CORES["card"],
                fg=CORES["text"] if chave == self.caixa else CORES["text_sec"],
                activebackground=CORES["card_hover"], activeforeground=CORES["text"],
                font=("Segoe UI", 9, "bold" if chave == self.caixa else "normal"),
                cursor="hand2", command=lambda c=chave: self._trocar_caixa(c), padx=12, pady=8,
            ).pack(fill="x", padx=8, pady=2)

    def _trocar_caixa(self, caixa):
        self.caixa = caixa
        self._render_pastas()
        self.carregar()

    def carregar(self):
        try:
            self.mensagens = listar_caixa(SESSAO.usuario, self.caixa, pesquisa=self.busca.get())
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Correio", str(erro), parent=self.root)
            return
        self.lista.delete(0, tk.END)
        for m in self.mensagens:
            marcador = "●" if not bool(m.get("lida", 1)) else " "
            estrela = "★" if bool(m.get("estrela")) else " "
            remetente = m.get("remetente_nome") or "—"
            assunto = m.get("assunto") or "(sem assunto)"
            self.lista.insert(tk.END, f"{marcador}{estrela} {remetente[:22]}\n   {assunto[:42]}")
        titulo = next((t for c, _i, t in CAIXAS if c == self.caixa), self.caixa.title())
        self.rotulo_caixa.configure(text=f"{titulo}  ·  {len(self.mensagens)}")
        self._preview_vazio()
        self._render_pastas()

    def _preview_vazio(self):
        for w in self.preview.winfo_children():
            w.destroy()
        tk.Label(
            self.preview, text="Selecione uma mensagem", bg=CORES["card"], fg=CORES["text_sec"],
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="center", pady=(90, 6))
        tk.Label(
            self.preview, text="O conteúdo aparecerá aqui sem abrir outra janela.", bg=CORES["card"], fg=CORES["text_muted"],
            font=("Segoe UI", 9)
        ).pack(anchor="center")

    def _selecionar(self, _evento=None):
        sel = self.lista.curselection()
        if not sel:
            return
        try:
            resumo = self.mensagens[int(sel[0])]
            self.mensagem_atual = obter_mensagem(int(resumo["id"]), SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Correio", str(erro), parent=self.root)
            return
        self._mostrar_mensagem()
        self._render_pastas()

    def _mostrar_mensagem(self):
        for w in self.preview.winfo_children():
            w.destroy()
        m = self.mensagem_atual or {}
        topo = tk.Frame(self.preview, bg=CORES["card"])
        topo.pack(fill="x", padx=20, pady=(18, 8))
        tk.Label(topo, text=m.get("assunto") or "(sem assunto)", bg=CORES["card"], fg=CORES["text"], font=("Segoe UI", 16, "bold"), wraplength=650, justify="left").pack(anchor="w")
        tk.Label(topo, text=f"De: {m.get('remetente_nome','—')} <{m.get('remetente_email','—')}>", bg=CORES["card"], fg=CORES["text_sec"], font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
        dests = ", ".join(x.get("email_corporativo") or "" for x in m.get("destinatarios", []) if x.get("tipo") == "PARA")
        tk.Label(topo, text=f"Para: {dests or '—'}", bg=CORES["card"], fg=CORES["text_muted"], font=("Segoe UI", 8), wraplength=680, justify="left").pack(anchor="w")
        if m.get("modulo_origem"):
            tk.Label(topo, text=f"Contexto: {m['modulo_origem']}", bg=CORES["card"], fg=CORES["primary"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(3, 0))
        acoes = tk.Frame(self.preview, bg=CORES["card"])
        acoes.pack(fill="x", padx=20, pady=(0, 8))
        if self.caixa not in {"enviados", "rascunhos"}:
            criar_botao(acoes, "RESPONDER", lambda: self.compor(responder=m), tipo="secundario", compacto=True).pack(side="left")
            criar_botao(acoes, "ARQUIVAR", lambda: self._estado(arquivada=True), tipo="fantasma", compacto=True).pack(side="left", padx=6)
            criar_botao(acoes, "LIXEIRA", lambda: self._estado(excluida=True), tipo="perigo", compacto=True).pack(side="left")
        corpo = tk.Text(self.preview, bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat", wrap="word", font=("Segoe UI", 10), padx=14, pady=14)
        corpo.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        corpo.insert("1.0", m.get("corpo") or "")
        corpo.configure(state="disabled")
        if m.get("anexos"):
            tk.Label(self.preview, text="Anexos: " + " · ".join(a["nome"] for a in m["anexos"]), bg=CORES["card"], fg=CORES["text_sec"], font=("Segoe UI", 8)).pack(anchor="w", padx=20, pady=(0, 12))

    def _estado(self, **kwargs):
        if not self.mensagem_atual:
            return
        try:
            atualizar_estado(int(self.mensagem_atual["id"]), SESSAO.usuario, **kwargs)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Correio", str(erro), parent=self.root)
            return
        self.carregar()

    def compor(self, responder=None):
        janela = tk.Toplevel(self.root)
        janela.title("Nova mensagem · Correio corporativo")
        preparar_janela_secundaria(janela, self.root, 820, 650, minimo=(650, 520), modal=False)
        janela.configure(bg=CORES["bg"])
        painel = tk.Frame(janela, bg=CORES["card"], highlightthickness=1, highlightbackground=CORES["border"])
        painel.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(painel, text="NOVA MENSAGEM", bg=CORES["card"], fg=CORES["primary"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 8))

        def campo(rotulo, valor=""):
            tk.Label(painel, text=rotulo, bg=CORES["card"], fg=CORES["text_sec"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(6, 3))
            e=tk.Entry(painel,bg=CORES["input"],fg=CORES["text"],insertbackground=CORES["primary"],relief="flat",font=("Segoe UI",9))
            e.pack(fill="x", padx=18, ipady=6); e.insert(0,valor); return e

        para_val=""
        assunto_val=""
        corpo_inicial=""
        resposta_id=None
        if responder:
            para_val=responder.get("remetente_email") or ""
            assunto_val=responder.get("assunto") or ""
            if not assunto_val.lower().startswith("re:"):
                assunto_val="RE: "+assunto_val
            corpo_inicial=f"\n\n--- Mensagem anterior ---\n{responder.get('corpo','')}"
            resposta_id=int(responder["id"])
        para=campo("PARA",para_val)
        cc=campo("CC")
        assunto=campo("ASSUNTO",assunto_val)
        tk.Label(painel,text="MENSAGEM",bg=CORES["card"],fg=CORES["text_sec"],font=("Segoe UI",8,"bold")).pack(anchor="w",padx=18,pady=(8,3))
        corpo=tk.Text(painel,bg=CORES["input"],fg=CORES["text"],insertbackground=CORES["primary"],relief="flat",wrap="word",font=("Segoe UI",10),height=12,padx=10,pady=8)
        corpo.pack(fill="both",expand=True,padx=18)
        corpo.insert("1.0",corpo_inicial)
        anexos=[]
        label_anexos=tk.Label(painel,text="Nenhum anexo",bg=CORES["card"],fg=CORES["text_muted"],font=("Segoe UI",8))
        label_anexos.pack(anchor="w",padx=18,pady=(6,0))
        botoes=tk.Frame(painel,bg=CORES["card"]); botoes.pack(fill="x",padx=18,pady=14)

        def anexar():
            caminhos=filedialog.askopenfilenames(parent=janela,title="Selecionar anexos")
            anexos[:] = list(caminhos)
            label_anexos.configure(text=(" · ".join(Path(x).name for x in anexos) if anexos else "Nenhum anexo"))

        def enviar():
            try:
                enviar_mensagem(assunto.get(),corpo.get("1.0","end").strip(),para.get(),SESSAO.usuario,cc=cc.get(),modulo_origem=self.modulo_origem,anexos=anexos,resposta_de_id=resposta_id)
            except (ValueError,PermissionError,OSError) as erro:
                messagebox.showerror("Correio",str(erro),parent=janela); return
            janela.destroy(); self.caixa="enviados"; self._render_pastas(); self.carregar()

        def rascunho():
            try:
                salvar_rascunho(assunto.get(),corpo.get("1.0","end").strip(),SESSAO.usuario,modulo_origem=self.modulo_origem)
            except (ValueError,PermissionError) as erro:
                messagebox.showerror("Correio",str(erro),parent=janela); return
            janela.destroy(); self.caixa="rascunhos"; self._render_pastas(); self.carregar()

        criar_botao(botoes,"ENVIAR",enviar,compacto=True).pack(side="left")
        criar_botao(botoes,"ANEXAR",anexar,tipo="secundario",compacto=True).pack(side="left",padx=6)
        criar_botao(botoes,"SALVAR RASCUNHO",rascunho,tipo="fantasma",compacto=True).pack(side="left")
