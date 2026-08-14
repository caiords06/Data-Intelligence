"""Design System V10.2.0 da Data Intelligence.

A interface continua em Tkinter, mas passa a trabalhar com tokens semânticos e
paletas intercambiáveis. ``CORES`` é mantido como o mesmo objeto mutável para
preservar compatibilidade com módulos que fazem ``from interface.tema import
CORES``: ao trocar o tema o dicionário é atualizado in-place e a tela atual é
recriada pelo roteador.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.versao import VERSAO_INTERFACE

TEMA_PADRAO = "escuro"
TEMAS_VALIDOS = ("escuro", "claro")

# Azul tecnológico sem preto puro. Os tons de texto foram escolhidos para
# manter contraste confortável em uso prolongado.
TEMA_ESCURO = {
    "bg": "#07111F",
    "bg_elevado": "#0A1626",
    "sidebar": "#071A2D",
    "sidebar_hover": "#123354",
    "sidebar_ativo": "#174A78",
    "card": "#0E1D2E",
    "card_secundario": "#14283E",
    "card_hover": "#1A3552",
    "input": "#0A1828",
    "overlay": "#0C1B2D",
    "border": "#28415F",
    "border_soft": "#1B3049",
    "divider": "#203852",
    "text": "#F1F6FD",
    "text_sec": "#B0BED1",
    "text_muted": "#7D90A8",
    "text_disabled": "#5A6C82",
    "primary": "#2775D8",
    "primary_hover": "#1F66C4",
    "primary_soft": "#12345D",
    "accent": "#59C3FF",
    "accent_soft": "#103452",
    "success": "#49C978",
    "success_soft": "#123A2A",
    "warning": "#E9B54B",
    "warning_soft": "#3A2D14",
    "danger": "#E55E6A",
    "danger_soft": "#3A2028",
    "danger_muted": "#D98D94",
    "purple": "#9B8AFB",
    "teal": "#38C6B3",
    "on_primary": "#FFFFFF",
    "on_success": "#07111F",
    "on_warning": "#07111F",
    "on_danger": "#FFFFFF",
}

# Claro suavizado: fundo cinza-azulado e superfícies quase brancas, evitando
# grandes áreas de branco puro e o efeito de "flashbang" em ambientes escuros.
TEMA_CLARO = {
    "bg": "#EAF1F8",
    "bg_elevado": "#E1EBF5",
    "sidebar": "#DCE9F6",
    "sidebar_hover": "#C8DDF1",
    "sidebar_ativo": "#AFCDEA",
    "card": "#F7FAFD",
    "card_secundario": "#E2EDF7",
    "card_hover": "#D6E6F5",
    "input": "#F2F5F8",
    "overlay": "#E9EEF4",
    "border": "#AFC3D8",
    "border_soft": "#C5D6E6",
    "divider": "#B9CCE0",
    "text": "#1B2735",
    "text_sec": "#56677D",
    "text_muted": "#64758A",
    "text_disabled": "#8290A2",
    "primary": "#135FAD",
    "primary_hover": "#0B4F96",
    "primary_soft": "#C8E0F7",
    "accent": "#007FBF",
    "accent_soft": "#CDEAF7",
    "success": "#16824A",
    "success_soft": "#DCEFE3",
    "warning": "#A66300",
    "warning_soft": "#F4E9CB",
    "danger": "#B53F4B",
    "danger_soft": "#F4DEE1",
    "danger_muted": "#9D5660",
    "purple": "#6541C7",
    "teal": "#008477",
    "on_primary": "#FFFFFF",
    "on_success": "#FFFFFF",
    "on_warning": "#FFFFFF",
    "on_danger": "#FFFFFF",
}

TEMAS = {"escuro": TEMA_ESCURO, "claro": TEMA_CLARO}
CORES = dict(TEMA_ESCURO)
_TEMA_ATUAL = TEMA_PADRAO

LAYOUT = {
    "sidebar_largura": 252,
    "conteudo_padx": 34,
    "conteudo_pady": 28,
    "card_padx": 22,
    "card_pady": 20,
    "gap": 14,
    "topbar_altura": 72,
    "raio_visual": 10,
}

FONTE_MARCA = "Manrope"
FONTE_INTERFACE = "Inter"

FONTES = {
    "marca": (FONTE_MARCA, 18, "bold"),
    "display": (FONTE_MARCA, 25, "bold"),
    "titulo_grande": (FONTE_MARCA, 23, "bold"),
    "titulo": (FONTE_MARCA, 16, "bold"),
    "subtitulo": (FONTE_MARCA, 11, "bold"),
    "texto": (FONTE_INTERFACE, 10),
    "texto_pequeno": (FONTE_INTERFACE, 9),
    "micro": (FONTE_INTERFACE, 9),
    "destaque": (FONTE_INTERFACE, 10, "bold"),
    "numero": (FONTE_MARCA, 19, "bold"),
}

MARCA = {
    "nome": "Data Intelligence",
    "descricao": "OPERATIONS · ANALYTICS · AUTOMATION",
    "descricao_curta": "ENTERPRISE PLATFORM",
    "simbolo": "DI",
    "monograma": "DI",
    "assinatura": "Enterprise Intelligence Platform",
}


def normalizar_tema(nome: str | None) -> str:
    valor = str(nome or TEMA_PADRAO).strip().lower()
    return valor if valor in TEMAS else TEMA_PADRAO


def tema_atual() -> str:
    return _TEMA_ATUAL


def aplicar_paleta(nome: str | None) -> str:
    """Troca os tokens de cor sem substituir a referência global ``CORES``."""
    global _TEMA_ATUAL
    nome = normalizar_tema(nome)
    CORES.clear()
    CORES.update(TEMAS[nome])
    _TEMA_ATUAL = nome
    return nome


def _configurar_estilo(estilo: ttk.Style, prefixo: str) -> None:
    estilo.configure(
        f"{prefixo}.Treeview",
        background=CORES["input"], fieldbackground=CORES["input"],
        foreground=CORES["text"], bordercolor=CORES["border"],
        lightcolor=CORES["border"], darkcolor=CORES["border"],
        borderwidth=0, relief="flat", rowheight=34,
        font=FONTES["texto_pequeno"],
    )
    estilo.configure(
        f"{prefixo}.Treeview.Heading",
        background=CORES["card_secundario"], foreground=CORES["text_sec"],
        bordercolor=CORES["border"], lightcolor=CORES["border"],
        darkcolor=CORES["border"], relief="flat", padding=(10, 9),
        font=("Inter", 8, "bold"),
    )
    estilo.map(
        f"{prefixo}.Treeview",
        background=[("selected", CORES["primary_soft"])],
        foreground=[("selected", CORES["text"])],
    )
    estilo.map(
        f"{prefixo}.Treeview.Heading",
        background=[("active", CORES["card_hover"])],
        foreground=[("active", CORES["text"])],
    )
    for orientacao in ("Vertical", "Horizontal"):
        estilo.configure(
            f"{prefixo}.{orientacao}.TScrollbar",
            troughcolor=CORES["bg_elevado"], background=CORES["primary"],
            bordercolor=CORES["border"], arrowcolor=CORES["on_primary"],
            darkcolor=CORES["primary"], lightcolor=CORES["accent"],
            relief="flat", width=13,
        )
        estilo.map(
            f"{prefixo}.{orientacao}.TScrollbar",
            background=[("active", CORES["accent"]), ("pressed", CORES["primary_hover"])],
        )
    estilo.configure(
        f"{prefixo}.TCombobox",
        fieldbackground=CORES["input"], background=CORES["card_secundario"],
        foreground=CORES["text"], arrowcolor=CORES["text_sec"],
        bordercolor=CORES["border"], lightcolor=CORES["border"],
        darkcolor=CORES["border"], padding=7,
    )
    estilo.map(
        f"{prefixo}.TCombobox",
        fieldbackground=[("readonly", CORES["input"])],
        foreground=[("readonly", CORES["text"])],
        selectbackground=[("readonly", CORES["input"])],
        selectforeground=[("readonly", CORES["text"])],
    )
    estilo.configure(
        f"{prefixo}.TNotebook", background=CORES["bg"], borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    estilo.configure(
        f"{prefixo}.TNotebook.Tab", background=CORES["bg"],
        foreground=CORES["text_sec"], padding=(14, 9), borderwidth=0,
        font=FONTES["texto_pequeno"],
    )
    estilo.map(
        f"{prefixo}.TNotebook.Tab",
        background=[("selected", CORES["card_secundario"])],
        foreground=[("selected", CORES["primary"])],
    )


def configurar_estilos_ttk(root=None):
    """Aplica o tema atual aos componentes ttk.

    ``App.*`` é a nomenclatura canônica da V10.2. ``Dark.*`` permanece como
    alias de compatibilidade para telas legadas e recebe exatamente a mesma
    paleta, inclusive no modo claro.
    """
    if root is not None:
        # Aplica Inter também aos widgets que não declaram fonte própria. Tk
        # usa fallback nativo caso a família ainda não esteja instalada; o
        # instalador/documentação valida as famílias antes da homologação.
        root.option_add("*Font", FONTES["texto"])
    estilo = ttk.Style(root)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    _configurar_estilo(estilo, "App")
    _configurar_estilo(estilo, "Dark")
    estilo.configure(
        "Primary.Horizontal.TProgressbar", troughcolor=CORES["border_soft"],
        background=CORES["primary"], borderwidth=0, thickness=8,
    )
    estilo.configure(
        "Success.Horizontal.TProgressbar", troughcolor=CORES["border_soft"],
        background=CORES["success"], borderwidth=0, thickness=8,
    )
    if root is not None:
        try:
            root.configure(bg=CORES["bg"])
        except tk.TclError:
            pass
    return estilo


def adicionar_divisorias_treeview(tabela, *, cor=None, sobreposicao=None):
    """Compatibilidade para grids legados sem sobrepor linhas artificiais."""
    try:
        tabela.configure(takefocus=True)
        if sobreposicao is not None and sobreposicao.winfo_exists():
            sobreposicao.lift()
    except tk.TclError:
        pass

    def redesenhar(_evento=None, atraso=0):
        try:
            if sobreposicao is not None and sobreposicao.winfo_exists():
                sobreposicao.lift()
        except tk.TclError:
            pass

    return redesenhar
