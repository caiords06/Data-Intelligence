"""Configuração visual e aquisição de fontes de uma nova análise V9.5."""

from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from configuracoes.preferencias import carregar_preferencias
from dados.fontes import baixar_fonte, importar_sqlite, limpar_arquivo_temporario
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_chip,
    criar_titulo_secao,
)
from interface.navegacao_analytics import criar_sidebar_analytics
from interface.tema import CORES, FONTES, LAYOUT, configurar_estilos_ttk


FONTES_DADOS = (
    ("Computador", "□", "Arquivos locais", True),
    ("Google Drive", "△", "Arquivo público / OAuth", True),
    ("OneDrive", "☁", "Link compartilhado", True),
    ("Banco de dados", "◉", "SQLite local", True),
    ("URL", "∞", "Link direto", True),
)

CATEGORIAS = {
    "Detecção automática": "automatica",
    "Vendas": "vendas",
    "Financeiro": "financeiro",
    "Estoque": "estoque",
    "Cadastro": "cadastro",
    "Recursos Humanos": "recursos_humanos",
    "Compras": "compras",
    "Tecnologia": "ti",
    "Marketing": "marketing",
    "Administrativo": "administrativo",
    "Jurídico": "juridico",
    "Comercial": "comercial",
}

PERIODOS = {
    "Automático": "automatico",
    "Mensal": "mensal",
    "Trimestral": "trimestral",
    "Semestral": "semestral",
    "Anual": "anual",
}

FONTES_CODIGOS = {
    "computador": "Computador",
    "google_drive": "Google Drive",
    "onedrive": "OneDrive",
    "banco_de_dados": "Banco de dados",
    "url": "URL",
}

EXTENSOES_SUPORTADAS = {".xlsx", ".xls", ".csv", ".json", ".parquet", ".txt"}


class TelaNovaAnalise:
    def __init__(
        self,
        root,
        executar_analise,
        voltar=None,
        navegacao=None,
        configuracao_inicial=None,
    ):
        self.root = root
        self.executar_analise_callback = executar_analise
        self.voltar_callback = voltar
        self.navegacao = navegacao or {}
        self.configuracao_inicial = dict(configuracao_inicial or {})
        self.preferencias = carregar_preferencias()
        self.arquivos_selecionados: list[str] = []
        self.arquivos_temporarios: set[str] = set()
        self._arquivos_entregues_ao_motor = False
        self.botoes_fonte = {}
        self._aquisicao_em_andamento = False
        self._destruida = False
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.container.bind("<Destroy>", self._ao_destruir, add="+")
        self.criar_interface()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_analytics(
            self.container,
            self.navegacao,
            ativo="nova",
            voltar=self.navegacao.get("modulos") or self.voltar,
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(22, 20),
        )
        conteudo = viewport.conteudo
        criar_cabecalho(
            conteudo,
            "Nova análise",
            "Importe seus dados e configure os parâmetros antes de iniciar o processamento.",
            acao=lambda area: criar_botao(
                area,
                "?  AJUDA",
                lambda: messagebox.showinfo(
                    "Ajuda da análise",
                    "1. Escolha uma fonte e adicione os dados.\n"
                    "2. Defina categoria, granularidade e componentes.\n"
                    "3. Confira o resumo e inicie o processamento.",
                    parent=self.root,
                ),
                tipo="secundario",
                compacto=True,
            ),
            breadcrumb="MÓDULOS  /  ANALYTICS  /  NOVA ANÁLISE",
            etiqueta="ETAPA 1 DE 3",
        )

        corpo = tk.Frame(conteudo, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True)
        principal = tk.Frame(corpo, bg=CORES["bg"])
        resumo = tk.Frame(corpo, bg=CORES["bg"])
        self._fonte_dados(principal)
        self._configuracao(principal)
        self._resumo(resumo)
        def reorganizar(evento=None):
            largura = evento.width if evento else corpo.winfo_width()
            principal.grid_forget()
            resumo.grid_forget()
            corpo.grid_columnconfigure(0, weight=1)
            corpo.grid_columnconfigure(1, weight=0)
            if largura >= 940:
                corpo.grid_columnconfigure(1, minsize=300)
                principal.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
                resumo.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            else:
                principal.grid(row=0, column=0, columnspan=2, sticky="nsew")
                resumo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        corpo.bind("<Configure>", reorganizar, add="+")
        corpo.after_idle(reorganizar)
        self._selecionar_fonte_inicial()
        self._carregar_arquivos_iniciais()
        self._atualizar_resumo()

    def _fonte_dados(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True)
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=17, pady=15)
        criar_titulo_secao(
            interior,
            "Fonte dos dados",
            "Escolha a origem e adicione os dados que serão processados.",
        )
        fonte_inicial = str(
            self.configuracao_inicial.get("fonte", "computador")
        ).lower().replace(" ", "_")
        self.fonte_var = tk.StringVar(
            value=FONTES_CODIGOS.get(fonte_inicial, "Computador")
        )
        fontes = GradeResponsiva(
            interior,
            max_colunas=5,
            largura_minima=135,
            gap=8,
            bg=CORES["card"],
        )
        fontes.pack(fill="x", pady=(7, 12))
        for indice, (nome, icone, descricao, funcional) in enumerate(FONTES_DADOS):
            bloco = tk.Frame(
                fontes,
                bg=CORES["card_secundario"],
                highlightthickness=1,
                highlightbackground=CORES["border"],
                takefocus=True,
            )
            fontes.adicionar(bloco)
            tk.Label(
                bloco,
                text=icone,
                font=("Segoe UI Symbol", 18, "bold"),
                fg=CORES["primary"] if funcional else CORES["text_sec"],
                bg=CORES["card_secundario"],
            ).pack(pady=(10, 1))
            tk.Label(
                bloco,
                text=nome,
                font=("Inter", 8, "bold"),
                fg=CORES["text"],
                bg=CORES["card_secundario"],
            ).pack()
            tk.Label(
                bloco,
                text=descricao,
                font=FONTES["micro"],
                fg=CORES["text_muted"],
                bg=CORES["card_secundario"],
            ).pack(pady=(1, 0))
            for widget in (bloco, *bloco.winfo_children()):
                widget.bind("<Button-1>", lambda _e, valor=nome: self.selecionar_fonte(valor))
                widget.configure(cursor="hand2")
            bloco.bind("<Return>", lambda _e, valor=nome: self.selecionar_fonte(valor))
            bloco.bind("<space>", lambda _e, valor=nome: self.selecionar_fonte(valor))
            bloco.bind(
                "<FocusIn>",
                lambda _e, item=bloco: item.configure(
                    highlightbackground=CORES["accent"]
                ),
            )
            bloco.bind("<FocusOut>", lambda _e: self._estilizar_fontes())
            self.botoes_fonte[nome] = bloco

        drop = tk.Frame(
            interior,
            bg=CORES["input"],
            highlightthickness=1,
            highlightbackground=CORES["border"],
            height=120,
        )
        drop.pack(fill="x", pady=(0, 12))
        drop.pack_propagate(False)
        tk.Label(
            drop,
            text="⇧",
            font=("Segoe UI Symbol", 22, "bold"),
            fg=CORES["text_sec"],
            bg=CORES["input"],
        ).pack(pady=(14, 2))
        tk.Label(
            drop,
            text="Selecione os arquivos da análise",
            font=("Inter", 10, "bold"),
            fg=CORES["text"],
            bg=CORES["input"],
        ).pack()
        criar_botao(
            drop,
            "+  ADICIONAR ARQUIVOS",
            self.selecionar_arquivos,
            tipo="secundario",
            compacto=True,
        ).pack(pady=8)

        topo_lista = tk.Frame(interior, bg=CORES["card"])
        topo_lista.pack(fill="x", pady=(0, 6))
        tk.Label(
            topo_lista,
            text="Arquivos selecionados",
            font=("Inter", 9, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack(side="left")
        self.label_quantidade = criar_chip(topo_lista, "0 ARQUIVOS")
        self.label_quantidade.pack(side="left", padx=8)
        tk.Button(
            topo_lista,
            text="Limpar todos",
            command=self.limpar_arquivos,
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
            activebackground=CORES["card_hover"],
            activeforeground=CORES["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
        ).pack(side="right")

        tabela_frame = tk.Frame(interior, bg=CORES["input"], height=120)
        tabela_frame.pack(fill="both", expand=True)
        tabela_frame.pack_propagate(False)
        self.tabela_arquivos = ttk.Treeview(
            tabela_frame,
            columns=("arquivo", "tipo", "tamanho", "status"),
            show="headings",
            style="Dark.Treeview",
            height=3,
        )
        for chave, titulo, largura in (
            ("arquivo", "Nome do arquivo", 330),
            ("tipo", "Tipo", 70),
            ("tamanho", "Tamanho", 90),
            ("status", "Status", 90),
        ):
            self.tabela_arquivos.heading(chave, text=titulo)
            self.tabela_arquivos.column(chave, width=largura, anchor="w", stretch=chave == "arquivo")
        barra = ttk.Scrollbar(
            tabela_frame,
            orient="vertical",
            command=self.tabela_arquivos.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            tabela_frame,
            orient="horizontal",
            command=self.tabela_arquivos.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.tabela_arquivos.configure(
            yscrollcommand=barra.set,
            xscrollcommand=barra_horizontal.set,
        )
        self.tabela_arquivos.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        tabela_frame.grid_rowconfigure(0, weight=1)
        tabela_frame.grid_columnconfigure(0, weight=1)
        criar_botao(
            interior,
            "REMOVER SELECIONADO",
            self.remover_arquivo,
            tipo="fantasma",
            compacto=True,
        ).pack(anchor="e", pady=(8, 0))

    def _configuracao(self, parent):
        card = criar_card(parent)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=14)
        criar_titulo_secao(
            interior,
            "Configuração da análise",
            "Defina categoria, granularidade temporal e componentes do motor.",
        )
        seletores = tk.Frame(interior, bg=CORES["card"])
        seletores.pack(fill="x", pady=(5, 9))
        categoria_inicial = self.configuracao_inicial.get(
            "categoria", self.preferencias.get("categoria_padrao", "automatica")
        )
        periodo_inicial = self.configuracao_inicial.get(
            "periodo", self.preferencias.get("periodo_padrao", "automatico")
        )
        self.categoria_var = tk.StringVar(value=self._rotulo_por_codigo(CATEGORIAS, categoria_inicial))
        self.periodo_var = tk.StringVar(value=self._rotulo_por_codigo(PERIODOS, periodo_inicial))
        self._combo(seletores, "Categoria", self.categoria_var, tuple(CATEGORIAS), 0)
        self._combo(
            seletores,
            "Granularidade temporal",
            self.periodo_var,
            tuple(PERIODOS),
            1,
        )

        modulos = self.configuracao_inicial.get("modulos") or {}
        self.tratamento_var = tk.BooleanVar(value=bool(modulos.get("tratamento", True)))
        self.analise_estrutural_var = tk.BooleanVar(value=bool(modulos.get("estrutural", True)))
        self.indicadores_var = tk.BooleanVar(value=bool(modulos.get("indicadores", True)))
        self.temporal_var = tk.BooleanVar(value=bool(modulos.get("temporal", True)))
        self.qualidade_var = tk.BooleanVar(value=bool(modulos.get("qualidade", True)))
        self.ia_var = tk.BooleanVar(value=bool(self.configuracao_inicial.get("ia", False)))
        opcoes = (
            ("Tratamento e validação", self.tratamento_var),
            ("Análise estrutural", self.analise_estrutural_var),
            ("Indicadores", self.indicadores_var),
            ("Análise temporal", self.temporal_var),
            ("Qualidade dos dados", self.qualidade_var),
            ("IA Assistente · requer integração", self.ia_var),
        )
        grade = GradeResponsiva(
            interior,
            max_colunas=3,
            largura_minima=210,
            gap=8,
            bg=CORES["card"],
        )
        grade.pack(fill="x")
        for indice, (texto, variavel) in enumerate(opcoes):
            opcao = tk.Checkbutton(
                grade,
                text=texto,
                variable=variavel,
                command=self._atualizar_resumo,
                font=FONTES["texto_pequeno"],
                fg=CORES["text"],
                bg=CORES["card_secundario"],
                selectcolor=CORES["input"],
                activebackground=CORES["card_hover"],
                activeforeground=CORES["text"],
                anchor="w",
                padx=9,
                pady=7,
            )
            grade.adicionar(opcao)

    def _combo(self, parent, titulo, variavel, valores, coluna):
        bloco = tk.Frame(parent, bg=CORES["card"])
        bloco.grid(row=0, column=coluna, sticky="ew", padx=(0, 10) if coluna == 0 else 0)
        parent.grid_columnconfigure(coluna, weight=1)
        tk.Label(
            bloco,
            text=titulo,
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(anchor="w", pady=(0, 4))
        combo = ttk.Combobox(
            bloco,
            textvariable=variavel,
            values=valores,
            state="readonly",
            style="Dark.TCombobox",
        )
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>", lambda _e: self._atualizar_resumo())

    def _resumo(self, parent):
        card = criar_card(parent, destaque=True)
        card.pack(fill="both", expand=True)
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=18, pady=17)
        topo = tk.Frame(interior, bg=CORES["card"])
        topo.pack(fill="x")
        tk.Label(
            topo,
            text="Resumo da análise",
            font=("Inter", 12, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack(side="left")
        self.chip_pronto = criar_chip(
            topo,
            "CONFIGURANDO",
            cor=CORES["warning"],
            fundo=CORES["warning_soft"],
        )
        self.chip_pronto.pack(side="right")
        tk.Frame(interior, bg=CORES["divider"], height=1).pack(fill="x", pady=13)
        self.resumo_fonte = self._linha_resumo(interior, "Fonte dos dados", "□")
        self.resumo_arquivos = self._linha_resumo(interior, "Arquivos selecionados", "▤")
        self.resumo_categoria = self._linha_resumo(interior, "Categoria", "◇")
        self.resumo_periodo = self._linha_resumo(
            interior, "Granularidade temporal", "◷"
        )
        self.resumo_modulos = self._linha_resumo(interior, "Módulos ativos", "▦")

        rodape = tk.Frame(interior, bg=CORES["card"])
        rodape.pack(side="bottom", fill="x", pady=(10, 0))
        aviso = tk.Frame(
            rodape,
            bg=CORES["warning_soft"],
            highlightthickness=1,
            highlightbackground=CORES["warning"],
        )
        aviso.pack(fill="x", pady=(0, 12))
        tk.Label(
            aviso,
            text="!  IMPORTANTE",
            font=("Inter", 8, "bold"),
            fg=CORES["warning"],
            bg=CORES["warning_soft"],
        ).pack(anchor="w", padx=12, pady=(10, 3))
        tk.Label(
            aviso,
            text="O processamento pode levar alguns minutos conforme o volume e a complexidade dos dados.",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["warning_soft"],
            wraplength=235,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 10))
        self.botao_iniciar = criar_botao(
            rodape,
            "INICIAR PROCESSAMENTO  ▷",
            self.executar,
        )
        self.botao_iniciar.pack(fill="x")
        self.label_status = tk.Label(
            rodape,
            text="Selecione os arquivos para continuar.",
            font=FONTES["micro"],
            fg=CORES["text_muted"],
            bg=CORES["card"],
            wraplength=240,
            justify="left",
        )
        self.label_status.pack(fill="x", pady=(6, 0))

    def _linha_resumo(self, parent, titulo, icone):
        linha = tk.Frame(parent, bg=CORES["card"])
        linha.pack(fill="x", pady=7)
        tk.Label(
            linha,
            text=icone,
            font=("Segoe UI Symbol", 12, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
            width=3,
        ).pack(side="left", padx=(0, 6))
        texto = tk.Frame(linha, bg=CORES["card"])
        texto.pack(side="left", fill="x", expand=True)
        tk.Label(
            texto,
            text=titulo,
            font=FONTES["micro"],
            fg=CORES["text_muted"],
            bg=CORES["card"],
        ).pack(anchor="w")
        valor = tk.Label(
            texto,
            text="—",
            font=("Inter", 9, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
            wraplength=210,
            justify="left",
        )
        valor.pack(anchor="w", pady=(2, 0))
        tk.Frame(parent, bg=CORES["divider"], height=1).pack(fill="x")
        return valor

    def selecionar_fonte(self, fonte):
        self.fonte_var.set(fonte)
        self._estilizar_fontes()
        self.label_status.configure(
            text=(
                "Use Adicionar arquivos para selecionar dados locais."
                if fonte == "Computador"
                else f"Use Adicionar arquivos para configurar a fonte {fonte}."
            ),
            fg=CORES["text_muted"],
        )
        self._atualizar_resumo()

    def _selecionar_fonte_inicial(self):
        self._estilizar_fontes()

    def _estilizar_fontes(self):
        selecionada = self.fonte_var.get()
        for nome, bloco in self.botoes_fonte.items():
            bloco.configure(
                bg=CORES["primary_soft"] if nome == selecionada else CORES["card_secundario"],
                highlightbackground=CORES["primary"] if nome == selecionada else CORES["border"],
            )
            for filho in bloco.winfo_children():
                filho.configure(bg=bloco.cget("bg"))

    def selecionar_arquivos(self):
        fonte = self.fonte_var.get()
        if self._aquisicao_em_andamento:
            return
        try:
            if fonte == "Computador":
                arquivos = filedialog.askopenfilenames(
                    title="Selecionar arquivos para análise",
                    initialdir=self.preferencias.get("pasta_padrao") or None,
                    filetypes=[
                        ("Dados suportados", "*.xlsx *.xls *.csv *.json *.parquet *.txt"),
                        ("Planilhas", "*.xlsx *.xls *.csv"),
                        ("Todos os arquivos", "*.*"),
                    ],
                )
                self._adicionar_arquivos(arquivos)
                return
            elif fonte in {"Google Drive", "OneDrive", "URL"}:
                url = simpledialog.askstring(
                    fonte,
                    "Cole o link do arquivo compartilhado:" if fonte != "URL" else "Cole o link direto do arquivo:",
                    parent=self.root,
                )
                if not url:
                    return
                self.label_status.configure(
                    text=f"Baixando arquivo de {fonte}...",
                    fg=CORES["warning"],
                )
                self._executar_aquisicao(
                    lambda: (baixar_fonte(url, fonte),),
                    f"Baixando arquivo de {fonte}...",
                )
                return
            else:
                banco = filedialog.askopenfilename(
                    title="Selecionar banco SQLite",
                    filetypes=[("Banco SQLite", "*.db *.sqlite *.sqlite3"), ("Todos", "*.*")],
                )
                if not banco:
                    return
                tabela = simpledialog.askstring(
                    "Importar banco de dados",
                    "Informe o nome da tabela ou view:",
                    parent=self.root,
                )
                if not tabela:
                    return
                self._executar_aquisicao(
                    lambda: (importar_sqlite(banco, tabela),),
                    "Importando tabela SQLite...",
                )
                return
        except (OSError, ValueError) as erro:
            self.label_status.configure(text=str(erro), fg=CORES["danger"])
            return

    def _executar_aquisicao(self, operacao, mensagem):
        """Executa download/conversão fora da thread visual do Tkinter."""
        self._aquisicao_em_andamento = True
        self.label_status.configure(text=mensagem, fg=CORES["warning"])
        self.botao_iniciar.configure(state="disabled")

        def worker():
            try:
                resultado = operacao()
                erro = None
            except Exception as excecao:
                resultado = ()
                erro = str(excecao)
            try:
                self.root.after(0, self._concluir_aquisicao, resultado, erro)
            except tk.TclError:
                for caminho in resultado:
                    limpar_arquivo_temporario(caminho)

        threading.Thread(target=worker, daemon=True, name="aquisicao-dados").start()

    def _concluir_aquisicao(self, arquivos, erro=None):
        if self._destruida or not self.container.winfo_exists():
            for caminho in arquivos:
                limpar_arquivo_temporario(caminho)
            return
        self._aquisicao_em_andamento = False
        if erro:
            self.label_status.configure(text=erro, fg=CORES["danger"])
            self._atualizar_resumo()
            return
        self.arquivos_temporarios.update(
            str(Path(item).expanduser().resolve()) for item in arquivos
        )
        self._adicionar_arquivos(arquivos)

    def _adicionar_arquivos(self, arquivos):
        for arquivo in arquivos:
            caminho = Path(arquivo).expanduser().resolve()
            if str(caminho) in self.arquivos_selecionados:
                continue
            self.arquivos_selecionados.append(str(caminho))
        self._reconstruir_tabela()
        self._atualizar_resumo()

    def _carregar_arquivos_iniciais(self):
        arquivos = self.configuracao_inicial.get("arquivos") or ()
        existentes = [arquivo for arquivo in arquivos if Path(arquivo).expanduser().is_file()]
        if existentes:
            self._adicionar_arquivos(existentes)

    def remover_arquivo(self):
        selecao = self.tabela_arquivos.selection()
        if not selecao:
            return
        indices = sorted((int(item) for item in selecao), reverse=True)
        for indice in indices:
            if 0 <= indice < len(self.arquivos_selecionados):
                removido = self.arquivos_selecionados.pop(indice)
                if removido in self.arquivos_temporarios:
                    limpar_arquivo_temporario(removido)
                    self.arquivos_temporarios.discard(removido)
        self._reconstruir_tabela()
        self._atualizar_resumo()

    def limpar_arquivos(self):
        for caminho in tuple(self.arquivos_temporarios):
            limpar_arquivo_temporario(caminho)
        self.arquivos_temporarios.clear()
        self.arquivos_selecionados.clear()
        self._reconstruir_tabela()
        self._atualizar_resumo()

    def _reconstruir_tabela(self):
        for item in self.tabela_arquivos.get_children():
            self.tabela_arquivos.delete(item)
        for indice, arquivo in enumerate(self.arquivos_selecionados):
            caminho = Path(arquivo)
            try:
                tamanho = self._formatar_tamanho(caminho.stat().st_size)
            except OSError:
                tamanho = "—"
            self.tabela_arquivos.insert(
                "",
                tk.END,
                iid=str(indice),
                values=(caminho.name, caminho.suffix.lstrip(".").upper(), tamanho, "Pronto"),
            )

    def _atualizar_resumo(self):
        if not hasattr(self, "resumo_fonte"):
            return
        quantidade = len(self.arquivos_selecionados)
        ativos = sum(
            variavel.get()
            for variavel in (
                self.tratamento_var,
                self.analise_estrutural_var,
                self.indicadores_var,
                self.temporal_var,
                self.qualidade_var,
                self.ia_var,
            )
        )
        self.resumo_fonte.configure(text=self.fonte_var.get())
        self.resumo_arquivos.configure(text=f"{quantidade} arquivo(s)")
        self.resumo_categoria.configure(text=self.categoria_var.get())
        self.resumo_periodo.configure(text=self.periodo_var.get())
        self.resumo_modulos.configure(text=f"{ativos} componente(s)")
        self.label_quantidade.configure(text=f"{quantidade} ARQUIVO(S)")
        validacao = self._validar_configuracao()
        pronto = validacao["valido"] and not self._aquisicao_em_andamento
        self.chip_pronto.configure(
            text="PRONTO PARA INICIAR" if pronto else "CONFIGURANDO",
            fg=CORES["success"] if pronto else CORES["warning"],
            bg=CORES["success_soft"] if pronto else CORES["warning_soft"],
        )
        self.label_status.configure(
            text=(
                "Configuração válida. O motor está pronto."
                if pronto
                else validacao["erros"][0]
            ),
            fg=CORES["success"] if pronto else CORES["text_muted"],
        )
        self.botao_iniciar.configure(state="normal" if pronto else "disabled")

    def _validar_configuracao(self):
        erros = []
        if not self.arquivos_selecionados:
            erros.append("Adicione ao menos uma fonte de dados para iniciar o processamento.")
        for arquivo in self.arquivos_selecionados:
            caminho = Path(arquivo)
            if not caminho.is_file():
                erros.append(f"O arquivo {caminho.name} não está mais disponível.")
                break
            if caminho.suffix.lower() not in EXTENSOES_SUPORTADAS:
                erros.append(f"O formato {caminho.suffix or 'sem extensão'} não é suportado.")
                break
        componentes = (
            self.tratamento_var,
            self.analise_estrutural_var,
            self.indicadores_var,
            self.temporal_var,
            self.qualidade_var,
            self.ia_var,
        )
        if not any(item.get() for item in componentes):
            erros.append("Ative pelo menos um componente do motor analítico.")
        return {"valido": not erros, "erros": erros or [""]}

    def executar(self):
        fonte = self.fonte_var.get()
        validacao = self._validar_configuracao()
        if not validacao["valido"]:
            self.label_status.configure(
                text=validacao["erros"][0],
                fg=CORES["warning"],
            )
            return
        configuracao = {
            "arquivos": list(self.arquivos_selecionados),
            "arquivos_temporarios": list(self.arquivos_temporarios),
            "fonte": fonte.casefold().replace(" ", "_"),
            "categoria": CATEGORIAS.get(self.categoria_var.get(), "automatica"),
            "periodo": PERIODOS.get(self.periodo_var.get(), "automatico"),
            "modulos": {
                "tratamento": self.tratamento_var.get(),
                "estrutural": self.analise_estrutural_var.get(),
                "indicadores": self.indicadores_var.get(),
                "temporal": self.temporal_var.get(),
                "qualidade": self.qualidade_var.get(),
            },
            "ia": self.ia_var.get(),
            "atraso_minimo_segundos": self.preferencias.get("atraso_minimo_segundos", 5),
        }
        self._arquivos_entregues_ao_motor = True
        self.container.destroy()
        self.executar_analise_callback(configuracao)

    def voltar(self):
        self.container.destroy()
        callback = self.voltar_callback or self.navegacao.get("analytics") or self.navegacao.get("modulos")
        if callback:
            callback()

    def _ao_destruir(self, evento):
        if evento.widget is not self.container:
            return
        self._destruida = True
        if self._arquivos_entregues_ao_motor:
            return
        for caminho in tuple(self.arquivos_temporarios):
            limpar_arquivo_temporario(caminho)
        self.arquivos_temporarios.clear()

    @staticmethod
    def _rotulo_por_codigo(mapa, codigo):
        return next((rotulo for rotulo, valor in mapa.items() if valor == codigo), next(iter(mapa)))

    @staticmethod
    def _formatar_tamanho(bytes_total):
        tamanho = float(bytes_total)
        for unidade in ("B", "KB", "MB", "GB"):
            if tamanho < 1024 or unidade == "GB":
                return f"{tamanho:.1f} {unidade}" if unidade != "B" else f"{int(tamanho)} B"
            tamanho /= 1024
        return f"{tamanho:.1f} GB"
