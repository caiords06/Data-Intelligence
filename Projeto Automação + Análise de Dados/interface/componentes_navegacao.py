"""Navegação e cabeçalhos compartilhados da interface V9.8."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from collections.abc import Callable

from auth.sessao import SESSAO
from core.caminhos import caminho_recurso
from core.nodo import cliente_convencional
from services.contexto import listar_modulos_permitidos, obter_contexto
from services.perfis_acesso import nome_perfil_acesso
from interface.icones import icone
from interface.tema import CORES, FONTES, LAYOUT, MARCA, VERSAO_INTERFACE
from interface.componentes_basicos import criar_chip
from interface.componentes_acoes import _montar_acao

try:
    from PIL import Image, ImageChops, ImageTk
except ImportError:  # pragma: no cover - fallback vetorial
    Image = ImageChops = ImageTk = None

ITENS_NAVEGACAO = (
    ("inicio", icone("inicio"), "Minha Central"),
    ("modulos", icone("modulos"), "Módulos"),
    ("historico", icone("historico"), "Histórico analítico"),
    ("aprovacoes", icone("aprovacoes"), "Aprovações"),
    ("notificacoes", icone("notificacoes"), "Central de notificações"),
    ("correio", icone("correio"), "Correio corporativo"),
    ("configuracoes", icone("configuracoes"), "Configurações"),
    ("compliance", "◆", "Conformidade e privacidade"),
    ("organizacao", icone("organizacao"), "Organização"),
    ("usuarios", icone("usuarios"), "Usuários e acessos"),
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

def criar_botao_sidebar(parent, icone, texto, comando=None, *, ativo=False, cor_icone=None):
    fundo = CORES["sidebar_ativo"] if ativo else CORES["sidebar"]
    texto_cor = CORES["text"] if ativo else CORES["text_sec"]
    cor_icone = CORES["accent"] if ativo else (cor_icone or CORES["primary"])
    linha = tk.Frame(parent, bg=fundo, height=45)
    linha.pack(fill="x", padx=12, pady=2)
    linha.pack_propagate(False)
    if ativo:
        tk.Frame(linha, bg=CORES["primary"], width=3).pack(side="left", fill="y")
    tk.Label(
        linha,
        text=str(icone),
        font=("Segoe UI Symbol", 11, "bold"),
        fg=cor_icone,
        bg=fundo,
        width=3,
        anchor="center",
    ).pack(side="left", padx=(8, 2))
    botao = tk.Button(
        linha,
        text=texto,
        font=("Inter", 9, "bold" if ativo else "normal"),
        fg=texto_cor,
        bg=fundo,
        activebackground=CORES["sidebar_hover"],
        activeforeground=CORES["text"],
        relief="flat",
        bd=0,
        anchor="w",
        cursor="hand2" if comando else "arrow",
        command=comando,
        padx=7,
        takefocus=True,
        highlightthickness=2,
        highlightbackground=fundo,
        highlightcolor=CORES["accent"],
    )
    botao.pack(side="left", fill="both", expand=True)
    return botao

def _logo_sidebar(sidebar):
    logo = tk.Frame(sidebar, bg=CORES["sidebar"])
    logo.pack(fill="x", padx=24, pady=(25, 18))
    if Image is not None and ImageTk is not None:
        try:
            imagem = Image.open(caminho_recurso("assets", "brand", "logo_empresa.png")).convert("RGBA")
            branco = Image.new("RGBA", imagem.size, (255, 255, 255, 255))
            diferenca = ImageChops.difference(imagem, branco).convert("L") if ImageChops is not None else imagem.getchannel("A")
            caixa = diferenca.point(lambda valor: 255 if valor > 10 else 0).getbbox()
            if caixa:
                imagem = imagem.crop(caixa); diferenca = diferenca.crop(caixa)
            imagem.putalpha(diferenca.point(lambda valor: min(255, valor * 4)))
            imagem.thumbnail((196, 65), Image.Resampling.LANCZOS)
            recurso = ImageTk.PhotoImage(imagem)
            rotulo = tk.Label(logo, image=recurso, bg=CORES["sidebar"], bd=0)
            rotulo.image = recurso
            rotulo.pack(anchor="w")
            return
        except (OSError, ValueError, tk.TclError):
            pass
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
        font=FONTES["marca"],
        fg=CORES["text"],
        bg=CORES["sidebar"],
    ).pack(anchor="w")
    tk.Label(
        textos,
        text=MARCA.get("descricao_curta", MARCA["descricao"]),
        font=("Inter", 9, "bold"),
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
    tk.Frame(sidebar, bg=CORES["accent"], height=4).pack(fill="x")
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
        style="App.Vertical.TScrollbar",
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
    usuario = SESSAO.usuario or {}
    permitidos = set(listar_modulos_permitidos(SESSAO.usuario))
    possui_modulos = bool(permitidos - {"analytics"})

    if grupos_customizados:
        grupos = tuple(grupos_customizados)
    elif itens_customizados:
        grupos = ((titulo_customizado or "MÓDULO", itens_customizados),)
    else:
        grupos = GRUPOS_NAVEGACAO

    paleta_grupos = (CORES["primary"], CORES["teal"], CORES["purple"], CORES["warning"], CORES["success"])
    for indice_grupo, (secao, itens) in enumerate(grupos):
        cor_grupo = paleta_grupos[indice_grupo % len(paleta_grupos)]
        conteiner_grupo = navegacao_area
        if grupos_recolhiveis and grupos_customizados:
            corpo_grupo = tk.Frame(navegacao_area, bg=CORES["sidebar"])
            ativo_no_grupo = any(item[0] == ativo for item in itens)
            estado = {"aberto": ativo_no_grupo or secao == grupos[0][0]}
            cabecalho = tk.Button(
                navegacao_area,
                text=("▾  " if estado["aberto"] else "›  ") + secao,
                font=("Inter", 8, "bold"),
                fg=cor_grupo,
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
                font=("Inter", 9, "bold"),
                fg=cor_grupo,
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
                if chave == "compliance" and not (
                    SESSAO.eh_admin() or str(usuario.get("perfil_acesso") or "").lower()
                    in {"compliance", "dpo", "encarregado", "juridico", "diretoria"}
                ):
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
                cor_icone=cor_grupo,
            )

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
        font=("Inter", 9, "bold"),
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
        font=("Inter", 8, "bold"),
        fg=CORES["text"],
        bg=CORES["bg_elevado"],
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        dados,
        text=perfil,
        font=("Inter", 9),
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
        text=f"{VERSAO_INTERFACE}  ·  ambiente protegido",
        font=("Inter", 9),
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
            font=("Inter", 8, "bold"),
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
