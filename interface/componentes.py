"""Componentes reutilizáveis do front-end empresarial V7."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from auth.sessao import SESSAO
from enterprise.contexto import listar_modulos_permitidos, obter_contexto
from enterprise.perfis_acesso import nome_perfil_acesso
from interface.tema import CORES, FONTES, LAYOUT, MARCA, VERSAO_INTERFACE


ITENS_NAVEGACAO = (
    ("inicio", "⌂", "Visão geral"),
    ("modulos", "▦", "Módulos"),
    ("historico", "◷", "Histórico analítico"),
    ("aprovacoes", "✓", "Aprovações"),
    ("notificacoes", "◌", "Central de alertas"),
    ("configuracoes", "⚙", "Configurações"),
    ("organizacao", "◈", "Organização"),
    ("usuarios", "◎", "Usuários e acessos"),
)

GRUPOS_NAVEGACAO = (
    ("OPERACIONAL", ITENS_NAVEGACAO[:5]),
    ("GESTÃO", ITENS_NAVEGACAO[5:]),
)


def _callback_indisponivel(titulo: str, detalhe: str | None = None):
    def mostrar():
        messagebox.showinfo(
            titulo,
            detalhe or (
                "A interface desta funcionalidade já foi preparada. "
                "A integração com o backend será realizada na próxima etapa."
            ),
        )
    return mostrar


def acao_em_preparacao(titulo: str, detalhe: str | None = None):
    """Retorna uma ação segura para recursos visuais ainda sem backend."""
    return _callback_indisponivel(titulo, detalhe)


def criar_botao_sidebar(parent, icone, texto, comando=None, *, ativo=False):
    fundo = CORES["sidebar_ativo"] if ativo else CORES["sidebar"]
    texto_cor = CORES["text"] if ativo else CORES["text_sec"]
    linha = tk.Frame(parent, bg=fundo, height=45)
    linha.pack(fill="x", padx=12, pady=2)
    linha.pack_propagate(False)
    if ativo:
        tk.Frame(linha, bg=CORES["primary"], width=3).pack(side="left", fill="y")
    botao = tk.Button(
        linha,
        text=f"{icone}    {texto}",
        font=("Segoe UI", 9, "bold" if ativo else "normal"),
        fg=texto_cor,
        bg=fundo,
        activebackground=CORES["sidebar_hover"],
        activeforeground=CORES["text"],
        relief="flat",
        bd=0,
        anchor="w",
        cursor="hand2" if comando else "arrow",
        command=comando,
        padx=13,
    )
    botao.pack(side="left", fill="both", expand=True)
    return botao


def _logo_sidebar(sidebar):
    logo = tk.Frame(sidebar, bg=CORES["sidebar"])
    logo.pack(fill="x", padx=24, pady=(25, 18))
    barras = tk.Frame(logo, bg=CORES["sidebar"], width=38, height=42)
    barras.pack(side="left", padx=(0, 12))
    barras.pack_propagate(False)
    for indice, altura in enumerate((15, 27, 38)):
        tk.Frame(
            barras,
            bg=CORES["primary"] if indice < 2 else CORES["accent"],
            width=7,
            height=altura,
        ).place(x=indice * 11 + 2, rely=1, anchor="sw")
    textos = tk.Frame(logo, bg=CORES["sidebar"])
    textos.pack(side="left")
    tk.Label(
        textos,
        text=MARCA["nome"],
        font=("Segoe UI", 13, "bold"),
        fg=CORES["text"],
        bg=CORES["sidebar"],
    ).pack(anchor="w")
    tk.Label(
        textos,
        text=MARCA["descricao"],
        font=("Segoe UI", 7, "bold"),
        fg=CORES["primary"],
        bg=CORES["sidebar"],
    ).pack(anchor="w", pady=(2, 0))


def criar_sidebar(
    parent,
    navegacao: dict,
    *,
    ativo: str,
    rodape_texto: str = "Sair",
    rodape_comando=None,
    itens_customizados=None,
    titulo_customizado=None,
):
    """Cria a navegação global ou uma navegação contextual de módulo."""
    sidebar = tk.Frame(parent, bg=CORES["sidebar"], width=LAYOUT["sidebar_largura"])
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)
    _logo_sidebar(sidebar)

    try:
        contexto = obter_contexto()
        contexto_texto = contexto["empresa_nome"]
        if contexto.get("filial_nome"):
            contexto_texto += f"  ·  {contexto['filial_nome']}"
        tk.Label(
            sidebar,
            text=contexto_texto,
            font=FONTES["micro"],
            fg=CORES["text_muted"],
            bg=CORES["sidebar"],
            wraplength=205,
            justify="left",
        ).pack(anchor="w", padx=25, pady=(0, 18))
    except (PermissionError, RuntimeError, TypeError):
        pass

    navegacao_area = tk.Frame(sidebar, bg=CORES["sidebar"])
    navegacao_area.pack(fill="both", expand=True)
    permitidos = set(listar_modulos_permitidos(SESSAO.usuario))
    possui_modulos = bool(permitidos - {"analytics"})

    if itens_customizados:
        grupos = ((titulo_customizado or "MÓDULO", itens_customizados),)
    else:
        grupos = GRUPOS_NAVEGACAO

    for secao, itens in grupos:
        tk.Label(
            navegacao_area,
            text=secao,
            font=("Segoe UI", 7, "bold"),
            fg=CORES["text_muted"],
            bg=CORES["sidebar"],
        ).pack(anchor="w", padx=26, pady=(10, 6))
        for item in itens:
            chave, icone, texto = item[:3]
            comando = item[3] if len(item) > 3 else navegacao.get(chave)
            if not itens_customizados:
                if chave == "historico" and "analytics" not in permitidos:
                    continue
                if chave == "aprovacoes" and not (possui_modulos or SESSAO.eh_admin()):
                    continue
                if chave in {"organizacao", "usuarios"} and not SESSAO.eh_admin():
                    continue
            criar_botao_sidebar(
                navegacao_area,
                icone,
                texto,
                comando,
                ativo=chave == ativo,
            )

    usuario = SESSAO.usuario or {}
    perfil = nome_perfil_acesso(
        usuario.get("perfil_acesso"),
        administrador=usuario.get("perfil") == "admin",
    )
    perfil_area = tk.Frame(
        sidebar,
        bg=CORES["bg_elevado"],
        highlightthickness=1,
        highlightbackground=CORES["border_soft"],
    )
    perfil_area.pack(side="bottom", fill="x", padx=14, pady=(0, 10))
    avatar = tk.Label(
        perfil_area,
        text=(usuario.get("nome") or "U")[:2].upper(),
        font=("Segoe UI", 9, "bold"),
        fg=CORES["text"],
        bg=CORES["primary_soft"],
        width=4,
        height=2,
    )
    avatar.pack(side="left", padx=10, pady=10)
    dados = tk.Frame(perfil_area, bg=CORES["bg_elevado"])
    dados.pack(side="left", fill="x", expand=True, pady=9)
    tk.Label(
        dados,
        text=usuario.get("nome", "Usuário"),
        font=("Segoe UI", 8, "bold"),
        fg=CORES["text"],
        bg=CORES["bg_elevado"],
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        dados,
        text=perfil,
        font=("Segoe UI", 7),
        fg=CORES["text_muted"],
        bg=CORES["bg_elevado"],
        anchor="w",
    ).pack(fill="x")

    rotulo_rodape = str(rodape_texto).replace("←", "").strip()
    tk.Button(
        sidebar,
        text=f"←    {rotulo_rodape}",
        font=FONTES["texto_pequeno"],
        fg=CORES["text_sec"],
        bg=CORES["sidebar"],
        activebackground=CORES["sidebar_hover"],
        activeforeground=CORES["text"],
        relief="flat",
        bd=0,
        cursor="hand2",
        anchor="w",
        command=rodape_comando or navegacao.get("sair"),
        padx=14,
    ).pack(side="bottom", fill="x", padx=12, pady=(0, 10), ipady=7)
    tk.Label(
        sidebar,
        text=f"Interface {VERSAO_INTERFACE}  ·  ambiente protegido",
        font=("Segoe UI", 7),
        fg=CORES["text_disabled"],
        bg=CORES["sidebar"],
    ).pack(side="bottom", anchor="w", padx=25, pady=(0, 8))
    return sidebar


def criar_cabecalho(parent, titulo, subtitulo, acao=None, *, breadcrumb=None, etiqueta=None):
    cabecalho = tk.Frame(parent, bg=CORES["bg"])
    cabecalho.pack(fill="x", pady=(0, 20))
    if breadcrumb:
        tk.Label(
            cabecalho,
            text=breadcrumb,
            font=("Segoe UI", 8, "bold"),
            fg=CORES["primary"],
            bg=CORES["bg"],
        ).pack(anchor="w", pady=(0, 7))
    linha = tk.Frame(cabecalho, bg=CORES["bg"])
    linha.pack(fill="x")
    tk.Label(
        linha,
        text=titulo,
        font=FONTES["display"],
        fg=CORES["text"],
        bg=CORES["bg"],
    ).pack(side="left", anchor="w")
    if etiqueta:
        criar_chip(linha, etiqueta, cor=CORES["primary"]).pack(side="left", padx=12)
    if acao:
        acao.pack(side="right")
    tk.Label(
        cabecalho,
        text=subtitulo,
        font=FONTES["texto"],
        fg=CORES["text_sec"],
        bg=CORES["bg"],
        wraplength=850,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    return cabecalho


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
    cor_texto = CORES["bg"] if tipo in {"sucesso", "aviso"} else CORES["text"]
    return tk.Button(
        parent,
        text=texto,
        command=comando,
        font=("Segoe UI", 8 if compacto else 9, "bold"),
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
    )


def criar_chip(parent, texto, *, cor=None, fundo=None):
    cor = cor or CORES["primary"]
    return tk.Label(
        parent,
        text=texto,
        font=("Segoe UI", 7, "bold"),
        fg=cor,
        bg=fundo or CORES["primary_soft"],
        padx=8,
        pady=4,
    )


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
        tk.Label(
            textos,
            text=subtitulo,
            font=FONTES["micro"],
            fg=CORES["text_muted"],
            bg=textos.cget("bg"),
        ).pack(anchor="w", pady=(2, 0))
    if acao:
        acao.pack(side="right")
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
        font=("Segoe UI", 8, "bold"),
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


def criar_estado_vazio(parent, titulo, descricao, *, icone="◇", cor=None):
    fundo = parent.cget("bg")
    bloco = tk.Frame(parent, bg=fundo)
    tk.Label(
        bloco,
        text=icone,
        font=("Segoe UI Symbol", 25, "bold"),
        fg=cor or CORES["primary"],
        bg=fundo,
    ).pack()
    tk.Label(
        bloco,
        text=titulo,
        font=FONTES["subtitulo"],
        fg=CORES["text"],
        bg=fundo,
    ).pack(pady=(8, 3))
    tk.Label(
        bloco,
        text=descricao,
        font=FONTES["texto_pequeno"],
        fg=CORES["text_sec"],
        bg=fundo,
        wraplength=420,
        justify="center",
    ).pack()
    return bloco


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
        font=("Segoe UI", 11, "bold"),
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
    ).pack(anchor="w", padx=19, pady=(6, 14))
    tk.Button(
        card,
        text="Acessar  →",
        command=acao,
        font=("Segoe UI", 9, "bold"),
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
