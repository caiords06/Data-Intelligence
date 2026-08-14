"""Controles visuais básicos compartilhados da interface V9.8."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from collections.abc import Callable

from interface.tema import CORES, FONTES, LAYOUT
from interface.componentes_acoes import _montar_acao

def criar_card(parent, *, destaque=False, fundo=None):
    return tk.Frame(
        parent,
        bg=fundo or CORES["card"],
        highlightthickness=1,
        highlightbackground=CORES["primary"] if destaque else CORES["border"],
        highlightcolor=CORES["primary"] if destaque else CORES["border"],
    )

def criar_botao(parent, texto, comando, *, tipo="primario", compacto=False):
    fundos = {
        "primario": CORES["primary"],
        "secundario": CORES["card_secundario"],
        "fantasma": CORES["card"],
        "perigo": CORES["danger"],
        "sucesso": CORES["success"],
        "aviso": CORES["warning"],
    }
    cor_texto = {
        "primario": CORES.get("on_primary", "#FFFFFF"),
        "sucesso": CORES.get("on_success", "#FFFFFF"),
        "aviso": CORES.get("on_warning", "#FFFFFF"),
        "perigo": CORES.get("on_danger", "#FFFFFF"),
    }.get(tipo, CORES["text"])
    return tk.Button(
        parent,
        text=texto,
        command=comando,
        font=("Inter", 8 if compacto else 9, "bold"),
        bg=fundos.get(tipo, CORES["primary"]),
        fg=cor_texto,
        activebackground=CORES["primary_hover"] if tipo == "primario" else CORES["card_hover"],
        activeforeground=CORES["text"],
        relief="flat",
        bd=0,
        cursor="hand2" if comando else "arrow",
        padx=11 if compacto else 16,
        pady=6 if compacto else 9,
        disabledforeground=CORES["text_disabled"],
        takefocus=True,
        highlightthickness=2,
        highlightbackground=fundos.get(tipo, CORES["primary"]),
        highlightcolor=CORES["accent"],
    )

def criar_chip(parent, texto, *, cor=None, fundo=None):
    cor = cor or CORES["primary"]
    return tk.Label(
        parent,
        text=texto,
        font=("Inter", 9, "bold"),
        fg=cor,
        bg=fundo or CORES["primary_soft"],
        padx=8,
        pady=4,
    )

def criar_campo_pesquisa(
    parent,
    *,
    placeholder="Pesquisar...",
    cor_cursor=None,
    ao_alterar=None,
    atraso_ms=180,
    largura=None,
):
    """Cria um campo de busca com placeholder real e debounce opcional.

    O placeholder nunca é tratado como conteúdo digitado. Isso evita o bug em
    que o usuário clicava e começava a escrever depois do texto de ajuda.
    """
    opcoes = {
        "bg": CORES["input"],
        "fg": CORES["text"],
        "insertbackground": cor_cursor or CORES["primary"],
        "relief": "flat",
    }
    if largura is not None:
        opcoes["width"] = largura
    campo = tk.Entry(parent, **opcoes)
    estado = {"placeholder": False, "after": None}

    def mostrar_placeholder():
        if campo.get():
            return
        estado["placeholder"] = True
        campo.configure(fg=CORES["text_muted"])
        campo.insert(0, placeholder)

    def limpar_placeholder(_evento=None):
        if estado["placeholder"]:
            campo.delete(0, "end")
            campo.configure(fg=CORES["text"])
            estado["placeholder"] = False

    def ao_sair(_evento=None):
        if not campo.get().strip():
            campo.delete(0, "end")
            mostrar_placeholder()

    def termo():
        return "" if estado["placeholder"] else campo.get().strip()

    def disparar(_evento=None):
        if ao_alterar is None:
            return
        if estado["after"] is not None:
            try:
                campo.after_cancel(estado["after"])
            except tk.TclError:
                pass
        estado["after"] = campo.after(max(0, int(atraso_ms)), lambda: ao_alterar(termo()))

    def limpar(_evento=None):
        campo.delete(0, "end")
        estado["placeholder"] = False
        campo.configure(fg=CORES["text"])
        disparar()
        return "break"

    campo.bind("<FocusIn>", limpar_placeholder, add="+")
    campo.bind("<FocusOut>", ao_sair, add="+")
    campo.bind("<KeyRelease>", disparar, add="+")
    campo.bind("<Escape>", limpar, add="+")
    campo.obter_termo = termo
    mostrar_placeholder()
    return campo

def criar_estado_vazio(parent, icone, titulo, subtitulo, *, cor=None):
    """Cria uma sobreposição integral; divisórias nunca atravessam a mensagem."""
    fundo = CORES["input"]
    sobreposicao = tk.Frame(parent, bg=fundo, height=176)
    # `place()` não participa do cálculo do tamanho requisitado do Frame. Nas
    # versões anteriores isso fazia estados vazios colapsarem para 1 px quando
    # usados fora de uma grade/tabela. `pack(expand=True)` mantém a mensagem
    # visível em todos os viewports da matriz V10.2.1.
    sobreposicao.pack_propagate(False)
    conteudo = tk.Frame(sobreposicao, bg=fundo)
    conteudo.pack(expand=True, fill="both", padx=24, pady=28)
    tk.Label(
        conteudo,
        text=icone,
        font=("Segoe UI Symbol", 28, "bold"),
        fg=cor or CORES["primary"],
        bg=fundo,
    ).pack()
    tk.Label(
        conteudo,
        text=titulo,
        font=FONTES["subtitulo"],
        fg=CORES["text"],
        bg=fundo,
        justify="center",
    ).pack(pady=(8, 4))
    tk.Label(
        conteudo,
        text=subtitulo,
        font=FONTES["micro"],
        fg=CORES["text_sec"],
        bg=fundo,
        justify="center",
        wraplength=520,
    ).pack()
    return sobreposicao

def criar_titulo_secao(parent, titulo, subtitulo=None, acao=None):
    linha = tk.Frame(parent, bg=parent.cget("bg"))
    linha.pack(fill="x", pady=(0, 10))
    textos = tk.Frame(linha, bg=linha.cget("bg"))
    textos.pack(side="left", fill="x", expand=True)
    tk.Label(
        textos,
        text=titulo,
        font=FONTES["subtitulo"],
        fg=CORES["text"],
        bg=textos.cget("bg"),
    ).pack(anchor="w")
    if subtitulo:
        label_subtitulo = tk.Label(
            textos,
            text=subtitulo,
            font=FONTES["micro"],
            fg=CORES["text_muted"],
            bg=textos.cget("bg"),
            justify="left",
            anchor="w",
        )
        label_subtitulo.pack(fill="x", anchor="w", pady=(2, 0))
        textos.bind(
            "<Configure>",
            lambda evento, label=label_subtitulo: label.configure(
                wraplength=max(160, evento.width - 4)
            ),
            add="+",
        )
    area_acoes = tk.Frame(linha, bg=linha.cget("bg"))
    area_acoes.pack(side="right", padx=(12, 0))
    _montar_acao(area_acoes, acao)
    return linha

def criar_metrica(parent, titulo, valor, *, icone="◇", cor=None, detalhe=None):
    cor = cor or CORES["primary"]
    card = criar_card(parent)
    topo = tk.Frame(card, bg=CORES["card"])
    topo.pack(fill="x", padx=18, pady=(15, 4))
    tk.Label(
        topo,
        text=icone,
        font=("Segoe UI Symbol", 13, "bold"),
        fg=cor,
        bg=CORES["primary_soft"],
        width=3,
        height=1,
    ).pack(side="left")
    tk.Label(
        topo,
        text=titulo,
        font=("Inter", 8, "bold"),
        fg=CORES["text_sec"],
        bg=CORES["card"],
    ).pack(side="left", padx=9)
    tk.Label(
        card,
        text=valor,
        font=FONTES["numero"],
        fg=CORES["text"],
        bg=CORES["card"],
    ).pack(anchor="w", padx=18, pady=(5, 1))
    tk.Label(
        card,
        text=detalhe or "Dados do contexto atual",
        font=FONTES["micro"],
        fg=cor if detalhe else CORES["text_muted"],
        bg=CORES["card"],
    ).pack(anchor="w", padx=18, pady=(2, 15))
    return card

def criar_card_acao(parent, *, icone, titulo, descricao, acao, cor=None, etiqueta=None):
    cor = cor or CORES["primary"]
    card = criar_card(parent)
    topo = tk.Frame(card, bg=CORES["card"])
    topo.pack(fill="x", padx=19, pady=(18, 10))
    tk.Label(
        topo,
        text=icone,
        font=("Segoe UI Symbol", 18, "bold"),
        fg=cor,
        bg=CORES["primary_soft"],
        width=3,
        height=2,
    ).pack(side="left")
    if etiqueta:
        criar_chip(topo, etiqueta, cor=cor).pack(side="right")
    tk.Label(
        card,
        text=titulo,
        font=("Inter", 11, "bold"),
        fg=CORES["text"],
        bg=CORES["card"],
    ).pack(anchor="w", padx=19)
    tk.Label(
        card,
        text=descricao,
        font=FONTES["texto_pequeno"],
        fg=CORES["text_sec"],
        bg=CORES["card"],
        wraplength=230,
        justify="left",
        anchor="w",
        padx=2,
    ).pack(anchor="w", padx=17, pady=(6, 14))
    tk.Button(
        card,
        text="Acessar  →",
        command=acao,
        font=("Inter", 9, "bold"),
        fg=cor,
        bg=CORES["card"],
        activebackground=CORES["card_hover"],
        activeforeground=CORES["text"],
        relief="flat",
        bd=0,
        cursor="hand2",
        anchor="w",
    ).pack(side="bottom", fill="x", padx=15, pady=(0, 13), ipady=5)
    return card
