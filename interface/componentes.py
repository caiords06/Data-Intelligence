"""Componentes reutilizáveis do front-end empresarial V9."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from collections.abc import Callable

from auth.sessao import SESSAO
from core.nodo import cliente_convencional
from enterprise.contexto import listar_modulos_permitidos, obter_contexto
from enterprise.perfis_acesso import nome_perfil_acesso
from interface.tema import CORES, FONTES, LAYOUT, MARCA, VERSAO_INTERFACE


ITENS_NAVEGACAO = (
    ("inicio", "⌂", "Visão geral"),
    ("modulos", "▦", "Módulos"),
    ("historico", "◷", "Histórico analítico"),
    ("aprovacoes", "✓", "Aprovações"),
    ("notificacoes", "◌", "Central de notificações"),
    ("correio", "✉", "Correio corporativo"),
    ("configuracoes", "⚙", "Configurações"),
    ("organizacao", "◈", "Organização"),
    ("usuarios", "◎", "Usuários e acessos"),
)

GRUPOS_NAVEGACAO = (
    ("OPERACIONAL", ITENS_NAVEGACAO[:6]),
    ("GESTÃO", ITENS_NAVEGACAO[6:]),
)


def _callback_indisponivel(titulo: str, detalhe: str | None = None):
    def mostrar():
        messagebox.showinfo(
            titulo,
            detalhe or (
                "A interface desta funcionalidade já foi preparada. "
                "Este recurso exige configuração adicional antes de ser utilizado."
            ),
        )
    return mostrar


def acao_em_preparacao(titulo: str, detalhe: str | None = None):
    """Retorna uma ação segura para recursos visuais ainda sem backend."""
    return _callback_indisponivel(titulo, detalhe)


def preparar_janela_secundaria(
    janela: tk.Toplevel,
    parent,
    largura: int,
    altura: int,
    *,
    minimo: tuple[int, int] | None = None,
    redimensionavel: bool = True,
    modal: bool = True,
):
    """Dimensiona e centraliza uma janela sem presumir a resolução da tela."""
    janela.transient(parent)
    if minimo:
        janela.minsize(*minimo)
    janela.resizable(redimensionavel, redimensionavel)
    parent.update_idletasks()
    largura_parent = max(parent.winfo_width(), parent.winfo_reqwidth())
    altura_parent = max(parent.winfo_height(), parent.winfo_reqheight())
    x_parent = parent.winfo_rootx()
    y_parent = parent.winfo_rooty()
    x = x_parent + max(0, (largura_parent - largura) // 2)
    y = y_parent + max(0, (altura_parent - altura) // 2)
    limite_x = max(0, janela.winfo_screenwidth() - largura)
    limite_y = max(0, janela.winfo_screenheight() - altura)
    janela.geometry(
        f"{largura}x{altura}+{min(max(0, x), limite_x)}+{min(max(0, y), limite_y)}"
    )
    if modal:
        janela.grab_set()
    return janela


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
        font=("Segoe UI", 9, "bold"),
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
    grupos_customizados=None,
    grupos_recolhiveis=False,
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

    # Cabeçalho e perfil permanecem fixos; apenas o menu central rola. Isso
    # mantém todos os destinos acessíveis em notebooks e com DPI alto.
    navegacao_externa = tk.Frame(sidebar, bg=CORES["sidebar"])
    navegacao_externa.pack(fill="both", expand=True)
    canvas_menu = tk.Canvas(
        navegacao_externa,
        bg=CORES["sidebar"],
        bd=0,
        highlightthickness=0,
        yscrollincrement=24,
    )
    barra_menu = ttk.Scrollbar(
        navegacao_externa,
        orient="vertical",
        command=canvas_menu.yview,
        style="Dark.Vertical.TScrollbar",
    )
    navegacao_area = tk.Frame(canvas_menu, bg=CORES["sidebar"])
    janela_menu = canvas_menu.create_window((0, 0), window=navegacao_area, anchor="nw")
    canvas_menu.configure(yscrollcommand=barra_menu.set)
    canvas_menu.pack(side="left", fill="both", expand=True)

    def _ajustar_menu(_evento=None):
        try:
            canvas_menu.itemconfigure(janela_menu, width=canvas_menu.winfo_width())
            canvas_menu.configure(scrollregion=canvas_menu.bbox("all"))
            inicio, fim = canvas_menu.yview()
            if inicio <= 0 and fim >= 1:
                barra_menu.pack_forget()
            elif not barra_menu.winfo_ismapped():
                barra_menu.pack(side="right", fill="y")
        except tk.TclError:
            pass

    navegacao_area.bind("<Configure>", _ajustar_menu, add="+")
    canvas_menu.bind("<Configure>", _ajustar_menu, add="+")

    def _menu_disponivel():
        try:
            return bool(canvas_menu.winfo_exists())
        except tk.TclError:
            return False

    def _rolar_menu(evento):
        if not _menu_disponivel():
            return "break"
        try:
            delta = -1 if evento.delta > 0 else 1
            canvas_menu.yview_scroll(delta, "units")
        except tk.TclError:
            return "break"

    def _rolar_menu_linux(evento):
        if not _menu_disponivel():
            return "break"
        try:
            canvas_menu.yview_scroll(-1 if evento.num == 4 else 1, "units")
        except tk.TclError:
            return "break"

    def _pagina_menu(evento):
        if not _menu_disponivel():
            return "break"
        try:
            canvas_menu.yview_scroll(
                -1 if evento.keysym == "Prior" else 1,
                "pages",
            )
        except tk.TclError:
            return "break"
        return "break"

    def _ativar_rolagem_menu(_evento=None):
        if not _menu_disponivel():
            return
        try:
            canvas_menu.bind_all("<MouseWheel>", _rolar_menu)
            canvas_menu.bind_all("<Button-4>", _rolar_menu_linux)
            canvas_menu.bind_all("<Button-5>", _rolar_menu_linux)
            canvas_menu.bind_all("<Prior>", _pagina_menu)
            canvas_menu.bind_all("<Next>", _pagina_menu)
        except tk.TclError:
            return

    def _desativar_rolagem_menu(_evento=None):
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Prior>", "<Next>"):
            try:
                canvas_menu.unbind_all(evento)
            except tk.TclError:
                return

    def _ao_destruir_menu(evento):
        if evento.widget is navegacao_externa:
            _desativar_rolagem_menu()

    canvas_menu.bind("<Enter>", _ativar_rolagem_menu)
    canvas_menu.bind("<Leave>", _desativar_rolagem_menu)
    navegacao_externa.bind("<Destroy>", _ao_destruir_menu, add="+")
    permitidos = set(listar_modulos_permitidos(SESSAO.usuario))
    possui_modulos = bool(permitidos - {"analytics"})

    if grupos_customizados:
        grupos = tuple(grupos_customizados)
    elif itens_customizados:
        grupos = ((titulo_customizado or "MÓDULO", itens_customizados),)
    else:
        grupos = GRUPOS_NAVEGACAO

    for secao, itens in grupos:
        conteiner_grupo = navegacao_area
        if grupos_recolhiveis and grupos_customizados:
            corpo_grupo = tk.Frame(navegacao_area, bg=CORES["sidebar"])
            ativo_no_grupo = any(item[0] == ativo for item in itens)
            estado = {"aberto": ativo_no_grupo or secao == grupos[0][0]}
            cabecalho = tk.Button(
                navegacao_area,
                text=("▾  " if estado["aberto"] else "›  ") + secao,
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text_muted"],
                bg=CORES["sidebar"],
                activebackground=CORES["sidebar_hover"],
                activeforeground=CORES["text_sec"],
                relief="flat",
                bd=0,
                anchor="w",
                cursor="hand2",
                padx=14,
                pady=5,
            )
            cabecalho.pack(fill="x", padx=12, pady=(5, 1))

            def alternar(
                corpo=corpo_grupo,
                botao=cabecalho,
                estado_grupo=estado,
                titulo=secao,
            ):
                estado_grupo["aberto"] = not estado_grupo["aberto"]
                botao.configure(
                    text=("▾  " if estado_grupo["aberto"] else "›  ") + titulo
                )
                if estado_grupo["aberto"]:
                    corpo.pack(fill="x", after=botao)
                else:
                    corpo.pack_forget()
                _ajustar_menu()

            cabecalho.configure(command=alternar)
            if estado["aberto"]:
                corpo_grupo.pack(fill="x")
            conteiner_grupo = corpo_grupo
        else:
            tk.Label(
                navegacao_area,
                text=secao,
                font=("Segoe UI", 9, "bold"),
                fg=CORES["text_muted"],
                bg=CORES["sidebar"],
            ).pack(anchor="w", padx=26, pady=(10, 6))
        for item in itens:
            chave, icone, texto = item[:3]
            comando = item[3] if len(item) > 3 else navegacao.get(chave)
            if not itens_customizados and not grupos_customizados:
                if chave == "historico" and "analytics" not in permitidos:
                    continue
                if chave == "aprovacoes" and not (possui_modulos or SESSAO.eh_admin()):
                    continue
                if chave in {"organizacao", "usuarios"} and not SESSAO.eh_admin():
                    continue
                # Estações Cliente são terminais convencionais: mesmo que uma
                # credencial administrativa seja usada por engano, o gerenciamento
                # de usuários permanece reservado à estação Central.
                if chave == "usuarios" and cliente_convencional():
                    continue
            criar_botao_sidebar(
                conteiner_grupo,
                icone,
                texto,
                None if chave == ativo else comando,
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
        font=("Segoe UI", 9),
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
        font=("Segoe UI", 9),
        fg=CORES["text_disabled"],
        bg=CORES["sidebar"],
    ).pack(side="bottom", anchor="w", padx=25, pady=(0, 8))
    return sidebar


def _montar_acao(area, acao):
    """Monta ações no pai correto sem tentar reparentear widgets Tk.

    A API preferida recebe ``lambda parent: widget``. Widgets antigos ainda
    são aceitos por compatibilidade e são empacotados com ``in_``.
    """
    if acao is None:
        return
    if callable(acao) and not isinstance(acao, tk.Misc):
        resultado = acao(area)
        if isinstance(resultado, tk.Misc) and not resultado.winfo_manager():
            resultado.pack(side="right")
        return
    if isinstance(acao, tk.Misc):
        acao.pack(in_=area, side="right")


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
    area_acoes = tk.Frame(linha, bg=CORES["bg"])
    area_acoes.pack(side="right", padx=(16, 0))
    _montar_acao(area_acoes, acao)
    label_subtitulo = tk.Label(
        cabecalho,
        text=subtitulo,
        font=FONTES["texto"],
        fg=CORES["text_sec"],
        bg=CORES["bg"],
        wraplength=850,
        justify="left",
        anchor="w",
    )
    label_subtitulo.pack(fill="x", anchor="w", pady=(6, 0))
    cabecalho.bind(
        "<Configure>",
        lambda evento, label=label_subtitulo: label.configure(
            wraplength=max(180, evento.width - 8)
        ),
        add="+",
    )
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
        font=("Segoe UI", 9, "bold"),
        fg=cor,
        bg=fundo or CORES["primary_soft"],
        padx=8,
        pady=4,
    )


def criar_estado_vazio(parent, icone, titulo, subtitulo, *, cor=None):
    """Cria uma sobreposição integral; divisórias nunca atravessam a mensagem."""
    fundo = CORES["input"]
    sobreposicao = tk.Frame(parent, bg=fundo)
    conteudo = tk.Frame(sobreposicao, bg=fundo)
    conteudo.place(relx=0.5, rely=0.5, anchor="center")
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


class AreaRolavel(tk.Frame):
    """Viewport vertical com barra na borda e margem apenas no conteúdo.

    O ``padx`` informado em ``pack()`` é convertido em recuo do conteúdo
    dentro do canvas. Assim, cards e textos preservam a margem visual sem
    afastar a barra de rolagem da extremidade direita da janela.
    """

    def __init__(self, parent, *, bg=None, **kwargs):
        fundo = bg or CORES["bg"]
        super().__init__(parent, bg=fundo, **kwargs)
        self.canvas = tk.Canvas(
            self,
            bg=fundo,
            bd=0,
            highlightthickness=0,
            yscrollincrement=28,
        )
        self.barra = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.conteudo = tk.Frame(self.canvas, bg=fundo)
        self._conteudo_padx = 0
        self._janela = self.canvas.create_window(
            (0, 0), window=self.conteudo, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self._ao_rolar_canvas)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.conteudo.bind("<Configure>", self._sincronizar, add="+")
        self.canvas.bind("<Configure>", self._sincronizar, add="+")
        self.canvas.bind("<Enter>", self._ativar_roda)
        self.canvas.bind("<Leave>", self._desativar_roda)
        self.bind("<Destroy>", self._ao_destruir, add="+")

    def pack(self, cnf=None, **kwargs):
        """Mantém ``pady`` externo e transforma ``padx`` em margem interna."""
        opcoes = {}
        if cnf:
            opcoes.update(cnf)
        opcoes.update(kwargs)
        padx = opcoes.pop("padx", 0)
        try:
            self._conteudo_padx = max(0, int(float(padx)))
        except (TypeError, ValueError):
            try:
                self._conteudo_padx = max(0, self.winfo_pixels(padx))
            except tk.TclError:
                self._conteudo_padx = 0
        resultado = super().pack(**opcoes)
        self.after_idle(self._sincronizar)
        return resultado

    def _sincronizar(self, _evento=None):
        try:
            largura = max(
                1,
                self.canvas.winfo_width() - (self._conteudo_padx * 2),
            )
            self.canvas.coords(self._janela, self._conteudo_padx, 0)
            self.canvas.itemconfigure(self._janela, width=largura)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self._atualizar_visibilidade_barra()
        except tk.TclError:
            return

    def _ao_rolar_canvas(self, primeiro, ultimo):
        try:
            if not self._widgets_disponiveis():
                return
            self.barra.set(primeiro, ultimo)
            self._atualizar_visibilidade_barra(float(primeiro), float(ultimo))
        except tk.TclError:
            return

    def _widgets_disponiveis(self):
        """Evita callbacks tardios apontando para widgets já destruídos.

        ``bind_all`` permanece ativo até recebermos ``Leave`` ou ``Destroy``.
        Em uma navegação rápida, o Windows pode entregar um evento de roda
        depois que a tela anterior já foi destruída. Consultar ``winfo`` nesse
        instante gerava ``bad window path name``. Toda rolagem passa agora por
        esta guarda e é silenciosamente descartada quando a área não existe.
        """
        try:
            return bool(
                self.winfo_exists()
                and self.canvas.winfo_exists()
                and self.barra.winfo_exists()
            )
        except tk.TclError:
            return False

    def _atualizar_visibilidade_barra(self, primeiro=None, ultimo=None):
        try:
            if not self._widgets_disponiveis():
                return
            if primeiro is None or ultimo is None:
                primeiro, ultimo = self.canvas.yview()
            precisa = float(primeiro) > 0.0 or float(ultimo) < 0.9999
            if precisa and not self.barra.winfo_ismapped():
                self.barra.pack(side="right", fill="y")
            elif not precisa and self.barra.winfo_ismapped():
                self.barra.pack_forget()
        except tk.TclError:
            return

    def _ativar_roda(self, _evento=None):
        if not self._widgets_disponiveis():
            return
        try:
            self.canvas.bind_all("<MouseWheel>", self._rolar)
            self.canvas.bind_all("<Button-4>", self._rolar_linux)
            self.canvas.bind_all("<Button-5>", self._rolar_linux)
            self.canvas.bind_all("<Prior>", self._rolar_pagina)
            self.canvas.bind_all("<Next>", self._rolar_pagina)
        except tk.TclError:
            return

    def _desativar_roda(self, _evento=None):
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Prior>", "<Next>"):
            try:
                self.canvas.unbind_all(evento)
            except tk.TclError:
                return

    def _ao_destruir(self, evento):
        if evento.widget is self:
            self._desativar_roda()

    def _rolar(self, evento):
        try:
            if not self._widgets_disponiveis():
                return "break"
            if self.barra.winfo_ismapped():
                self.canvas.yview_scroll(-1 if evento.delta > 0 else 1, "units")
        except tk.TclError:
            return "break"
        return "break"

    def _rolar_linux(self, evento):
        try:
            if not self._widgets_disponiveis():
                return "break"
            if self.barra.winfo_ismapped():
                self.canvas.yview_scroll(-1 if evento.num == 4 else 1, "units")
        except tk.TclError:
            return "break"
        return "break"

    def _rolar_pagina(self, evento):
        try:
            if not self._widgets_disponiveis():
                return "break"
            if self.barra.winfo_ismapped():
                self.canvas.yview_scroll(
                    -1 if evento.keysym == "Prior" else 1,
                    "pages",
                )
        except tk.TclError:
            return "break"
        return "break"


class GradeResponsiva(tk.Frame):
    """Grade que reorganiza filhos por breakpoint, sem recriá-los."""

    def __init__(
        self,
        parent,
        *,
        max_colunas=4,
        largura_minima=245,
        gap=10,
        bg=None,
        **kwargs,
    ):
        super().__init__(parent, bg=bg or parent.cget("bg"), **kwargs)
        self.max_colunas = max(1, int(max_colunas))
        self.largura_minima = max(140, int(largura_minima))
        self.gap = max(0, int(gap))
        self.itens = []
        self._colunas = 0
        self.bind("<Configure>", self._reorganizar, add="+")

    def adicionar(self, widget):
        self.itens.append(widget)
        self.after_idle(self._reorganizar)
        return widget

    def _reorganizar(self, _evento=None):
        if not self.itens:
            return
        largura = max(self.winfo_width(), self.winfo_reqwidth())
        colunas = max(
            1,
            min(self.max_colunas, (largura + self.gap) // (self.largura_minima + self.gap)),
        )
        if colunas == self._colunas and all(item.winfo_manager() == "grid" for item in self.itens):
            return
        for coluna in range(self.max_colunas):
            self.grid_columnconfigure(coluna, weight=0, uniform="")
        for indice, item in enumerate(self.itens):
            linha, coluna = divmod(indice, colunas)
            item.grid(
                row=linha,
                column=coluna,
                sticky="nsew",
                padx=(0, self.gap if coluna < colunas - 1 else 0),
                pady=(0, self.gap),
            )
        for coluna in range(colunas):
            self.grid_columnconfigure(coluna, weight=1, uniform="responsiva")
        self._colunas = colunas


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
