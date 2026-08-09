import tkinter as tk
from tkinter import filedialog
import os
from interface.tema import CORES, MARCA

class TelaNovaAnalise:

    def __init__(self, root, executar_analise, voltar):

        self.root = root
        self.executar_analise_callback = executar_analise
        self.voltar_callback = voltar

        self.arquivos_selecionados = []

        self.cores = CORES

        self.criar_interface()

    def criar_interface(self):

        self.container = tk.Frame(
            self.root,
            bg=self.cores["bg"]
        )

        self.container.pack(
            fill="both",
            expand=True
        )

        # SIDEBAR
        sidebar = tk.Frame(
            self.container,
            bg=self.cores["sidebar"],
            width=220
        )

        sidebar.pack(
            side="left",
            fill="y"
        )

        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text=f'{MARCA["simbolo"]}  {MARCA["nome"]}',
            font=("Segoe UI", 16, "bold"),
            fg=self.cores["text"],
            bg=self.cores["sidebar"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(30, 0)
        )

        tk.Label(
            sidebar,
            text=MARCA["descricao"],
            font=("Segoe UI", 8),
            fg=self.cores["primary"],
            bg=self.cores["sidebar"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 40)
        )

        tk.Button(
            sidebar,
            text="←   Voltar",
            font=("Segoe UI", 10),
            fg=self.cores["text_sec"],
            bg=self.cores["sidebar"],
            activebackground=self.cores["card"],
            activeforeground=self.cores["text"],
            relief="flat",
            bd=0,
            anchor="w",
            cursor="hand2",
            command=self.voltar
        ).pack(
            fill="x",
            padx=15,
            pady=3,
            ipady=8
        )

        # CONTEÚDO
        conteudo = tk.Frame(
            self.container,
            bg=self.cores["bg"]
        )

        conteudo.pack(
            side="left",
            fill="both",
            expand=True,
            padx=40,
            pady=30
        )

        cabecalho = tk.Frame(
            conteudo,
            bg=self.cores["bg"]
        )

        cabecalho.pack(
            fill="x"
        )

        tk.Label(
            cabecalho,
            text="Nova análise",
            font=("Segoe UI", 24, "bold"),
            fg=self.cores["text"],
            bg=self.cores["bg"]
        ).pack(
            anchor="w"
        )

        tk.Label(
            cabecalho,
            text="Configure a fonte e o comportamento do motor analítico.",
            font=("Segoe UI", 10),
            fg=self.cores["text_sec"],
            bg=self.cores["bg"]
        ).pack(
            anchor="w",
            pady=(5, 25)
        )

        etapa = tk.Frame(
            cabecalho,
            bg=self.cores["card"],
            highlightthickness=1,
            highlightbackground=self.cores["border"]
        )

        etapa.place(
            relx=1.0,
            rely=0.0,
            anchor="ne"
        )

        tk.Label(
            etapa,
            text="ETAPA 1",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"]
        ).pack(
            side="left",
            padx=(12, 5),
            pady=8
        )

        tk.Label(
            etapa,
            text="Preparação",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            side="left",
            padx=(0, 12),
            pady=8
        )

        fluxo = tk.Frame(
            conteudo,
            bg=self.cores["bg"]
        )

        fluxo.pack(
            fill="x",
            pady=(5, 20)
        )

        tk.Label(
            fluxo,
            text="●",
            font=("Segoe UI", 10),
            fg=self.cores["primary"],
            bg=self.cores["bg"]
        ).pack(
            side="left"
        )

        tk.Label(
            fluxo,
            text=" Preparação",
            font=("Segoe UI", 9, "bold"),
            fg=self.cores["text"],
            bg=self.cores["bg"]
        ).pack(
            side="left"
        )

        tk.Label(
            fluxo,
            text="   ─────────   ",
            font=("Segoe UI", 9),
            fg=self.cores["border"],
            bg=self.cores["bg"]
        ).pack(
            side="left"
        )

        tk.Label(
            fluxo,
            text="○ Processamento",
            font=("Segoe UI", 9),
            fg=self.cores["text_muted"],
            bg=self.cores["bg"]
        ).pack(
            side="left"
        )

        tk.Label(
            fluxo,
            text="   ─────────   ",
            font=("Segoe UI", 9),
            fg=self.cores["border"],
            bg=self.cores["bg"]
        ).pack(
            side="left"
        )

        tk.Label(
            fluxo,
            text="○ Resultados",
            font=("Segoe UI", 9),
            fg=self.cores["text_muted"],
            bg=self.cores["bg"]
        ).pack(
            side="left"
        )

        area = tk.Frame(
            conteudo,
            bg=self.cores["bg"]
        )

        area.pack(
            fill="both",
            expand=True
        )

        # COLUNA ESQUERDA
        esquerda = tk.Frame(
            area,
            bg=self.cores["bg"]
        )

        esquerda.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        # COLUNA DIREITA
        direita = tk.Frame(
            area,
            bg=self.cores["bg"]
        )

        direita.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(10, 0)
        )

        self.criar_area_arquivos(esquerda)
        self.criar_area_configuracoes(direita)

        # BOTÃO EXECUTAR
        rodape = tk.Frame(
            conteudo,
            bg=self.cores["bg"]
        )

        rodape.pack(
            fill="x",
            pady=(20, 0)
        )

        self.label_status = tk.Label(
            rodape,
            text="●  Selecione uma fonte de dados para iniciar.",
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["bg"]
        )

        self.label_status.pack(
            side="left"
        )

        tk.Button(
            rodape,
            text="▶  INICIAR PROCESSAMENTO",
            font=("Segoe UI", 10, "bold"),
            bg=self.cores["primary"],
            fg="#FFFFFF",
            activebackground=self.cores["primary_hover"],
            activeforeground="#FFFFFF",
            bd=0,
            cursor="hand2",
            command=self.executar
        ).pack(
            side="right",
            ipadx=18,
            ipady=9
        )

    def criar_area_arquivos(self, parent):

        card = tk.Frame(
            parent,
            bg=self.cores["card"],
            highlightthickness=1,
            highlightbackground=self.cores["border"]
        )

        card.pack(
            fill="both",
            expand=True
        )

        tk.Label(
            card,
            text="01. FONTE DOS DADOS",
            font=("Segoe UI", 10, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        tk.Label(
            card,
            text="Selecione de onde os dados serão obtidos.",
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20
        )

        self.fonte_var = tk.StringVar(
            value="Computador"
        )

        fontes = tk.Frame(
            card,
            bg=self.cores["card"]
        )

        fontes.pack(
            fill="x",
            padx=20,
            pady=15
        )

        for fonte in (
            "Computador",
            "Google Drive",
            "URL"
        ):

            tk.Radiobutton(
                fontes,
                text=fonte,
                variable=self.fonte_var,
                value=fonte,
                font=("Segoe UI", 9),
                fg=self.cores["text"],
                bg=self.cores["card"],
                selectcolor=self.cores["input"],
                activebackground=self.cores["card"],
                activeforeground=self.cores["text"]
            ).pack(
                side="left",
                padx=(0, 15)
            )

        tk.Label(
            card,
            text="Arquivos selecionados",
            font=("Segoe UI", 10, "bold"),
            fg=self.cores["text"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(10, 5)
        )

        self.lista_arquivos = tk.Listbox(
            card,
            bg=self.cores["input"],
            fg=self.cores["text"],
            selectbackground=self.cores["primary"],
            selectforeground="#FFFFFF",
            relief="flat",
            bd=0,
            font=("Segoe UI", 9),
            height=10
        )

        self.lista_arquivos.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 10)
        )

        botoes = tk.Frame(
            card,
            bg=self.cores["card"]
        )

        botoes.pack(
            fill="x",
            padx=20,
            pady=(0, 20)
        )

        tk.Button(
            botoes,
            text="+ ADICIONAR ARQUIVOS",
            font=("Segoe UI", 9, "bold"),
            bg=self.cores["primary"],
            fg="#FFFFFF",
            bd=0,
            cursor="hand2",
            command=self.selecionar_arquivos
        ).pack(
            side="left",
            ipadx=8,
            ipady=6
        )

        tk.Button(
            botoes,
            text="REMOVER",
            font=("Segoe UI", 9),
            bg=self.cores["card_hover"],
            fg=self.cores["text"],
            bd=0,
            cursor="hand2",
            command=self.remover_arquivo
        ).pack(
            side="left",
            padx=10,
            ipadx=8,
            ipady=6
        )

    def criar_area_configuracoes(self, parent):

        card = tk.Frame(
            parent,
            bg=self.cores["card"],
            highlightthickness=1,
            highlightbackground=self.cores["border"]
        )

        card.pack(
            fill="both",
            expand=True
        )

        tk.Label(
            card,
            text="02. MOTOR ANALÍTICO",
            font=("Segoe UI", 10, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        tk.Label(
            card,
            text="Defina como o motor deverá interpretar os dados.",
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

        # CATEGORIA
        self.categoria_var = tk.StringVar(
            value="Detecção automática"
        )

        self.criar_seletor(
            card,
            "Categoria da base",
            self.categoria_var,
            [
                "Detecção automática",
                "Vendas",
                "Financeiro",
                "Estoque",
                "Cadastro",
                "Recursos Humanos"
            ]
        )

        # PERÍODO
        self.periodo_var = tk.StringVar(
            value="Automático"
        )

        self.criar_seletor(
            card,
            "Período",
            self.periodo_var,
            [
                "Automático",
                "Mensal",
                "Trimestral",
                "Semestral",
                "Anual",
                "Personalizado"
            ]
        )

        tk.Label(
            card,
            text="Motor analítico",
            font=("Segoe UI", 10, "bold"),
            fg=self.cores["text"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 8)
        )

        self.analise_estrutural_var = tk.BooleanVar(
            value=True
        )

        self.indicadores_var = tk.BooleanVar(
            value=True
        )

        self.temporal_var = tk.BooleanVar(
            value=True
        )

        self.qualidade_var = tk.BooleanVar(
            value=True
        )

        opcoes = [
            (
                "Análise estrutural",
                self.analise_estrutural_var
            ),
            (
                "Indicadores",
                self.indicadores_var
            ),
            (
                "Análise temporal",
                self.temporal_var
            ),
            (
                "Qualidade dos dados",
                self.qualidade_var
            )
        ]

        for texto, variavel in opcoes:

            tk.Checkbutton(
                card,
                text=texto,
                variable=variavel,
                font=("Segoe UI", 9),
                fg=self.cores["text"],
                bg=self.cores["card"],
                selectcolor=self.cores["input"],
                activebackground=self.cores["card"],
                activeforeground=self.cores["text"]
            ).pack(
                anchor="w",
                padx=20,
                pady=2
            )

        # IA
        self.ia_var = tk.BooleanVar(
            value=False
        )

        tk.Checkbutton(
            card,
            text="Utilizar Inteligência Artificial",
            variable=self.ia_var,
            font=("Segoe UI", 9),
            fg=self.cores["text"],
            bg=self.cores["card"],
            selectcolor=self.cores["input"],
            activebackground=self.cores["card"],
            activeforeground=self.cores["text"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        tk.Label(
            card,
            text="A IA permanece opcional. O motor analítico funciona independentemente dela.",
            font=("Segoe UI", 8),
            fg=self.cores["text_sec"],
            bg=self.cores["card"],
            wraplength=380,
            justify="left"
        ).pack(
            anchor="w",
            padx=20
        )

    def criar_seletor(
        self,
        parent,
        titulo,
        variavel,
        opcoes
    ):

        tk.Label(
            parent,
            text=titulo,
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(8, 5)
        )

        menu = tk.OptionMenu(
            parent,
            variavel,
            *opcoes
        )

        menu.configure(
            font=("Segoe UI", 9),
            bg=self.cores["input"],
            fg=self.cores["text"],
            activebackground=self.cores["card_hover"],
            activeforeground=self.cores["text"],
            highlightthickness=0,
            bd=0,
            width=25
        )

        menu["menu"].configure(
            bg=self.cores["input"],
            fg=self.cores["text"]
        )

        menu.pack(
            anchor="w",
            padx=20,
            ipady=3
        )

    def selecionar_arquivos(self):

        arquivos = filedialog.askopenfilenames(
            title="Selecionar arquivos para análise",
            filetypes=[
                (
                    "Planilhas",
                    "*.xlsx *.xls *.csv"
                ),
                (
                    "Todos os arquivos",
                    "*.*"
                )
            ]
        )

        for arquivo in arquivos:

            if arquivo not in self.arquivos_selecionados:

                self.arquivos_selecionados.append(
                    arquivo
                )

                self.lista_arquivos.insert(
                    tk.END,
                    os.path.basename(arquivo)
                )

        quantidade = len(
            self.arquivos_selecionados
        )

        if quantidade:

            self.label_status.configure(
                text=(
                    f"{quantidade} arquivo(s) "
                    f"selecionado(s)."
                ),
                fg=self.cores["text_sec"]
            )

    def remover_arquivo(self):

        selecao = self.lista_arquivos.curselection()

        if not selecao:
            return

        indice = selecao[0]

        self.lista_arquivos.delete(
            indice
        )

        del self.arquivos_selecionados[
            indice
        ]

        self.label_status.configure(
            text=(
                f"{len(self.arquivos_selecionados)} "
                f"arquivo(s) selecionado(s)."
            ),
            fg=self.cores["text_sec"]
        )

    def executar(self):

        fonte_selecionada = self.fonte_var.get()

        if fonte_selecionada != "Computador":
            self.label_status.configure(
                text=(
                    f"A fonte {fonte_selecionada} ainda não está "
                    "disponível nesta versão."
                ),
                fg=self.cores["warning"]
            )
            return

        if not self.arquivos_selecionados:

            self.label_status.configure(
                text="Selecione pelo menos um arquivo antes de continuar.",
                fg=self.cores["warning"]
            )

            return

        mapa_categoria = {
            "Detecção automática": "automatica",
            "Vendas": "vendas",
            "Financeiro": "financeiro",
            "Estoque": "estoque",
            "Cadastro": "cadastro",
            "Recursos Humanos": "recursos_humanos"
        }

        mapa_periodo = {
            "Automático": "automatico",
            "Mensal": "mensal",
            "Trimestral": "trimestral",
            "Semestral": "semestral",
            "Anual": "anual",
            "Personalizado": "personalizado"
        }

        configuracao = {
            "arquivos": list(
                self.arquivos_selecionados
            ),

            "fonte": self.fonte_var.get().lower(),

            "categoria": mapa_categoria.get(
                self.categoria_var.get(),
                "automatica"
            ),

            "periodo": mapa_periodo.get(
                self.periodo_var.get(),
                "automatico"
            ),

            "modulos": {
                "estrutural": self.analise_estrutural_var.get(),
                "indicadores": self.indicadores_var.get(),
                "temporal": self.temporal_var.get(),
                "qualidade": self.qualidade_var.get()
            },

            "ia": self.ia_var.get()
        }

        self.container.destroy()

        self.executar_analise_callback(
            configuracao
        )

    def voltar(self):

        self.container.destroy()

        self.voltar_callback()

