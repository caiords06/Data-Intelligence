"""Configuração visual de uma nova análise na V7."""

from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from configuracoes.preferencias import carregar_preferencias
from interface.componentes import (
    acao_em_preparacao,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_chip,
    criar_sidebar,
    criar_titulo_secao,
)
from interface.tema import CORES, FONTES, LAYOUT, configurar_estilos_ttk


FONTES_DADOS = (
    ("Computador", "□", "Arquivos locais", True),
    ("Google Drive", "△", "Minha unidade", False),
    ("OneDrive", "☁", "Microsoft", False),
    ("Banco de dados", "◉", "Conexões", False),
    ("URL", "∞", "Link direto", False),
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
    "Personalizado": "personalizado",
}


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
        self.botoes_fonte = {}
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        itens = (
            ("visao", "⌂", "Dashboard", self.voltar),
            ("nova", "+", "Nova análise", None),
            ("importacoes", "↓", "Importações", acao_em_preparacao("Importações")),
            ("conjuntos", "▣", "Conjuntos de dados", acao_em_preparacao("Conjuntos de dados")),
            ("relatorios", "▤", "Relatórios", acao_em_preparacao("Relatórios")),
            ("agendamentos", "◷", "Agendamentos", acao_em_preparacao("Agendamentos")),
            ("alertas", "!", "Alertas analíticos", acao_em_preparacao("Alertas analíticos")),
            ("modelos", "◈", "Modelos", acao_em_preparacao("Modelos")),
            ("perfis", "◎", "Perfis de análise", self.navegacao.get("perfis")),
            ("assistente", "✦", "IA Assistente", acao_em_preparacao("IA Assistente")),
        )
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="nova",
            itens_customizados=itens,
            titulo_customizado="ANALYTICS",
            rodape_texto="Voltar à Central analítica",
            rodape_comando=self.voltar,
        )
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(22, 20),
        )
        ajuda = tk.Frame(conteudo, bg=CORES["bg"])
        criar_botao(
            ajuda,
            "?  AJUDA",
            acao_em_preparacao("Ajuda da análise"),
            tipo="secundario",
            compacto=True,
        ).pack(side="right")
        criar_cabecalho(
            conteudo,
            "Nova análise",
            "Importe seus dados e configure os parâmetros antes de iniciar o processamento.",
            acao=ajuda,
            breadcrumb="MÓDULOS  /  ANALYTICS  /  NOVA ANÁLISE",
            etiqueta="ETAPA 1 DE 3",
        )

        corpo = tk.Frame(conteudo, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True)
        principal = tk.Frame(corpo, bg=CORES["bg"])
        principal.pack(side="left", fill="both", expand=True, padx=(0, 7))
        resumo = tk.Frame(corpo, bg=CORES["bg"], width=300)
        resumo.pack(side="right", fill="y", padx=(7, 0))
        resumo.pack_propagate(False)
        self._fonte_dados(principal)
        self._configuracao(principal)
        self._resumo(resumo)
        self._selecionar_fonte_inicial()
        self._atualizar_resumo()

    def _fonte_dados(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True)
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=17, pady=15)
        criar_titulo_secao(
            interior,
            "Fonte dos dados",
            "Escolha a origem. Apenas arquivos locais processam dados nesta etapa.",
        )
        fonte_inicial = str(self.configuracao_inicial.get("fonte", "computador")).lower()
        mapa = {
            "computador": "Computador",
            "google drive": "Google Drive",
            "onedrive": "OneDrive",
            "banco de dados": "Banco de dados",
            "url": "URL",
        }
        self.fonte_var = tk.StringVar(value=mapa.get(fonte_inicial, "Computador"))
        fontes = tk.Frame(interior, bg=CORES["card"])
        fontes.pack(fill="x", pady=(7, 12))
        for indice, (nome, icone, descricao, funcional) in enumerate(FONTES_DADOS):
            bloco = tk.Frame(
                fontes,
                bg=CORES["card_secundario"],
                highlightthickness=1,
                highlightbackground=CORES["border"],
                height=92,
            )
            bloco.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 8) if indice < len(FONTES_DADOS) - 1 else 0,
            )
            bloco.pack_propagate(False)
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
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text"],
                bg=CORES["card_secundario"],
            ).pack()
            tk.Label(
                bloco,
                text=descricao if funcional else f"{descricao} · prévia",
                font=("Segoe UI", 7),
                fg=CORES["text_muted"],
                bg=CORES["card_secundario"],
            ).pack(pady=(1, 0))
            for widget in (bloco, *bloco.winfo_children()):
                widget.bind("<Button-1>", lambda _e, valor=nome: self.selecionar_fonte(valor))
                widget.configure(cursor="hand2")
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
            font=("Segoe UI", 10, "bold"),
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
            font=("Segoe UI", 9, "bold"),
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
        self.tabela_arquivos.pack(side="left", fill="both", expand=True)
        barra = ttk.Scrollbar(
            tabela_frame,
            orient="vertical",
            command=self.tabela_arquivos.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra.pack(side="right", fill="y")
        self.tabela_arquivos.configure(yscrollcommand=barra.set)
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
            "Defina categoria, período e componentes do motor.",
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
        self._combo(seletores, "Período", self.periodo_var, tuple(PERIODOS), 1)

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
            ("IA Assistente · prévia", self.ia_var),
        )
        grade = tk.Frame(interior, bg=CORES["card"])
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
            opcao.grid(row=indice // 3, column=indice % 3, sticky="ew", padx=(0, 8), pady=4)
        for coluna in range(3):
            grade.grid_columnconfigure(coluna, weight=1, uniform="opcoes")

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
            font=("Segoe UI", 12, "bold"),
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
        self.resumo_periodo = self._linha_resumo(interior, "Período", "◷")
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
            font=("Segoe UI", 8, "bold"),
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
            font=("Segoe UI", 9, "bold"),
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
        if fonte != "Computador":
            self.label_status.configure(
                text=f"{fonte} está visível como prévia e será conectado na próxima etapa.",
                fg=CORES["warning"],
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
        if self.fonte_var.get() != "Computador":
            self.selecionar_fonte("Computador")
        arquivos = filedialog.askopenfilenames(
            title="Selecionar arquivos para análise",
            initialdir=self.preferencias.get("pasta_padrao") or None,
            filetypes=[
                ("Dados suportados", "*.xlsx *.xls *.csv *.json *.parquet *.txt"),
                ("Planilhas", "*.xlsx *.xls *.csv"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        for arquivo in arquivos:
            if arquivo in self.arquivos_selecionados:
                continue
            self.arquivos_selecionados.append(arquivo)
            caminho = Path(arquivo)
            try:
                tamanho = self._formatar_tamanho(caminho.stat().st_size)
            except OSError:
                tamanho = "—"
            self.tabela_arquivos.insert(
                "",
                tk.END,
                iid=str(len(self.arquivos_selecionados) - 1),
                values=(caminho.name, caminho.suffix.lstrip(".").upper(), tamanho, "Pronto"),
            )
        self._reconstruir_tabela()
        self._atualizar_resumo()

    def remover_arquivo(self):
        selecao = self.tabela_arquivos.selection()
        if not selecao:
            return
        indices = sorted((int(item) for item in selecao), reverse=True)
        for indice in indices:
            if 0 <= indice < len(self.arquivos_selecionados):
                del self.arquivos_selecionados[indice]
        self._reconstruir_tabela()
        self._atualizar_resumo()

    def limpar_arquivos(self):
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
        pronto = self.fonte_var.get() == "Computador" and quantidade > 0
        self.chip_pronto.configure(
            text="PRONTO PARA INICIAR" if pronto else "CONFIGURANDO",
            fg=CORES["success"] if pronto else CORES["warning"],
            bg=CORES["success_soft"] if pronto else CORES["warning_soft"],
        )
        self.label_status.configure(
            text=(
                "Configuração válida. O motor está pronto."
                if pronto
                else "Selecione arquivos locais para iniciar o processamento."
            ),
            fg=CORES["success"] if pronto else CORES["text_muted"],
        )

    def executar(self):
        fonte = self.fonte_var.get()
        if fonte != "Computador":
            messagebox.showinfo(
                "Fonte preparada",
                f"A interface de {fonte} já está pronta. A conexão será implementada na próxima etapa.",
                parent=self.root,
            )
            return
        if not self.arquivos_selecionados:
            self.label_status.configure(
                text="Selecione pelo menos um arquivo antes de continuar.",
                fg=CORES["warning"],
            )
            return
        configuracao = {
            "arquivos": list(self.arquivos_selecionados),
            "fonte": "computador",
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
        self.container.destroy()
        self.executar_analise_callback(configuracao)

    def voltar(self):
        self.container.destroy()
        callback = self.voltar_callback or self.navegacao.get("analytics") or self.navegacao.get("modulos")
        if callback:
            callback()

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
