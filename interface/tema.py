"""Design system compartilhado da plataforma empresarial.

O front-end V7 permanece em Tkinter para preservar compatibilidade com o
backend atual, mas concentra cores, tipografia, espaçamento e estilos ttk em
um único lugar. Isso evita que cada tela crie uma identidade própria.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


VERSAO_INTERFACE = "V7"

CORES = {
    # Estrutura
    "bg": "#07111F",
    "bg_elevado": "#0A1626",
    "sidebar": "#06101D",
    "sidebar_hover": "#10233A",
    "sidebar_ativo": "#132943",
    # Superfícies
    "card": "#0F1D30",
    "card_secundario": "#14253B",
    "card_hover": "#1A304A",
    "input": "#0A1728",
    "overlay": "#0C1A2C",
    # Contornos
    "border": "#263A55",
    "border_soft": "#1B2D45",
    "divider": "#20344E",
    # Texto
    "text": "#F4F8FF",
    "text_sec": "#A9B7CC",
    "text_muted": "#70839E",
    "text_disabled": "#53657D",
    # Ações
    "primary": "#2F8CFF",
    "primary_hover": "#1878E8",
    "primary_soft": "#12345D",
    "accent": "#59C3FF",
    "success": "#48D978",
    "success_soft": "#123B2A",
    "warning": "#F6B94A",
    "warning_soft": "#3A2C12",
    "danger": "#F05B65",
    "danger_soft": "#3A1E28",
    "danger_muted": "#D9878D",
    "purple": "#9B8AFB",
    "teal": "#31C7B2",
}

LAYOUT = {
    "sidebar_largura": 258,
    "conteudo_padx": 34,
    "conteudo_pady": 28,
    "card_padx": 22,
    "card_pady": 20,
    "gap": 14,
    "topbar_altura": 72,
}

FONTES = {
    "display": ("Segoe UI", 25, "bold"),
    "titulo_grande": ("Segoe UI", 23, "bold"),
    "titulo": ("Segoe UI", 16, "bold"),
    "subtitulo": ("Segoe UI", 11, "bold"),
    "texto": ("Segoe UI", 10),
    "texto_pequeno": ("Segoe UI", 9),
    "micro": ("Segoe UI", 8),
    "destaque": ("Segoe UI", 10, "bold"),
    "numero": ("Segoe UI", 19, "bold"),
}

MARCA = {
    "nome": "Data Intelligence",
    "descricao": "ENTERPRISE PLATFORM",
    "simbolo": "▂▅█",
    "monograma": "DI",
}


def configurar_estilos_ttk(root=None):
    """Aplica estilos escuros consistentes antes da criação dos widgets ttk."""
    estilo = ttk.Style(root)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    estilo.configure(
        "Dark.Treeview",
        background=CORES["input"],
        fieldbackground=CORES["input"],
        foreground=CORES["text"],
        bordercolor=CORES["border"],
        lightcolor=CORES["border"],
        darkcolor=CORES["border"],
        borderwidth=0,
        relief="flat",
        rowheight=34,
        font=FONTES["texto_pequeno"],
    )
    estilo.configure(
        "Dark.Treeview.Heading",
        background=CORES["card_secundario"],
        foreground=CORES["text_sec"],
        bordercolor=CORES["border"],
        lightcolor=CORES["border"],
        darkcolor=CORES["border"],
        relief="flat",
        padding=(10, 9),
        font=("Segoe UI", 8, "bold"),
    )
    estilo.map(
        "Dark.Treeview",
        background=[("selected", CORES["primary_soft"])],
        foreground=[("selected", CORES["text"])],
    )
    estilo.map(
        "Dark.Treeview.Heading",
        background=[("active", CORES["card_hover"])],
        foreground=[("active", CORES["text"])],
    )

    for orientacao in ("Vertical", "Horizontal"):
        estilo.configure(
            f"Dark.{orientacao}.TScrollbar",
            troughcolor=CORES["input"],
            background=CORES["card_secundario"],
            bordercolor=CORES["border_soft"],
            arrowcolor=CORES["text_sec"],
            relief="flat",
        )

    estilo.configure(
        "Dark.TCombobox",
        fieldbackground=CORES["input"],
        background=CORES["card_secundario"],
        foreground=CORES["text"],
        arrowcolor=CORES["text_sec"],
        bordercolor=CORES["border"],
        lightcolor=CORES["border"],
        darkcolor=CORES["border"],
        padding=7,
    )
    estilo.map(
        "Dark.TCombobox",
        fieldbackground=[("readonly", CORES["input"])],
        foreground=[("readonly", CORES["text"])],
        selectbackground=[("readonly", CORES["input"])],
        selectforeground=[("readonly", CORES["text"])],
    )

    estilo.configure(
        "Primary.Horizontal.TProgressbar",
        troughcolor=CORES["border_soft"],
        background=CORES["primary"],
        borderwidth=0,
        thickness=8,
    )
    estilo.configure(
        "Success.Horizontal.TProgressbar",
        troughcolor=CORES["border_soft"],
        background=CORES["success"],
        borderwidth=0,
        thickness=8,
    )
    estilo.configure(
        "Dark.TNotebook",
        background=CORES["bg"],
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    estilo.configure(
        "Dark.TNotebook.Tab",
        background=CORES["bg"],
        foreground=CORES["text_sec"],
        padding=(14, 9),
        borderwidth=0,
        font=FONTES["texto_pequeno"],
    )
    estilo.map(
        "Dark.TNotebook.Tab",
        background=[("selected", CORES["card_secundario"])],
        foreground=[("selected", CORES["primary"])],
    )
    return estilo


def adicionar_divisorias_treeview(tabela, *, cor=None, sobreposicao=None):
    """Desenha separadores verticais estáveis entre colunas do Treeview."""
    cor_linha = cor or CORES["divider"]
    linhas: list[tk.Frame] = []
    agendamento = {"id": None}

    def _limpar():
        for linha in linhas[:]:
            try:
                linha.destroy()
            except tk.TclError:
                pass
        linhas.clear()

    def _desenhar():
        agendamento["id"] = None
        try:
            if not tabela.winfo_exists() or not tabela.winfo_ismapped():
                return
            tabela.update_idletasks()
            _limpar()
            largura = tabela.winfo_width()
            altura = tabela.winfo_height()
            if largura <= 2 or altura <= 2:
                return
            pai = tabela.master
            x = tabela.winfo_rootx() - pai.winfo_rootx()
            y = tabela.winfo_rooty() - pai.winfo_rooty()
            acumulado = 0
            for coluna in tuple(tabela.cget("columns"))[:-1]:
                acumulado += int(tabela.column(coluna, "width"))
                posicao = x + acumulado
                if posicao >= x + largura:
                    break
                linha = tk.Frame(pai, bg=cor_linha, bd=0, highlightthickness=0)
                linha.place(x=posicao, y=y, width=1, height=altura)
                linha.lift()
                linhas.append(linha)
            if sobreposicao is not None and sobreposicao.winfo_exists():
                sobreposicao.lift()
        except tk.TclError:
            _limpar()

    def redesenhar(_evento=None, atraso=30):
        try:
            if agendamento["id"] is not None:
                tabela.after_cancel(agendamento["id"])
            agendamento["id"] = tabela.after(max(0, int(atraso)), _desenhar)
        except tk.TclError:
            return

    for evento in ("<Configure>", "<Map>", "<Expose>", "<ButtonRelease-1>"):
        tabela.bind(evento, redesenhar, add="+")
    tabela.master.bind("<Configure>", redesenhar, add="+")
    tabela.after_idle(lambda: redesenhar(atraso=0))
    tabela.after(90, redesenhar)
    tabela.after(240, redesenhar)
    return redesenhar
