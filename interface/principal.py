import tkinter as tk
from interface.tema import CORES, MARCA
from auth.sessao import SESSAO

class TelaPrincipal:

    def __init__(self, root, abrir_analise, sair, abrir_usuarios=None):
        self.root = root
        self.abrir_analise_callback = abrir_analise
        self.sair_callback = sair
        self.abrir_usuarios_callback = abrir_usuarios

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

        self.criar_botao_menu(
            sidebar,
            "⌂   Início"
        )

        self.criar_botao_menu(
            sidebar,
            "▣   Nova análise",
            self.abrir_analise
        )

        self.criar_botao_menu(
            sidebar,
            "◷   Histórico"
        )

        self.criar_botao_menu(
            sidebar,
            "⚙   Configurações"
        )

        if SESSAO.eh_admin():

            self.criar_botao_menu(
                sidebar,
                "♙   Usuários",
                self.abrir_usuarios
            )

        tk.Button(
            sidebar,
            text="Sair",
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["sidebar"],
            activebackground=self.cores["sidebar"],
            activeforeground=self.cores["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
            command=self.sair
        ).pack(
            side="bottom",
            fill="x",
            padx=20,
            pady=25
        )

        # CONTEÚDO PRINCIPAL
        conteudo = tk.Frame(
            self.container,
            bg=self.cores["bg"]
        )

        conteudo.pack(
            side="left",
            fill="both",
            expand=True,
            padx=40,
            pady=35
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
            text="Central da aplicação",
            font=("Segoe UI", 24, "bold"),
            fg=self.cores["text"],
            bg=self.cores["bg"]
        ).pack(
            anchor="w"
        )

        tk.Label(
            cabecalho,
            text="Configure e execute suas análises de dados.",
            font=("Segoe UI", 10),
            fg=self.cores["text_sec"],
            bg=self.cores["bg"]
        ).pack(
            anchor="w",
            pady=(5, 30)
        )

        status_frame = tk.Frame(
            cabecalho,
            bg=self.cores["card"],
            highlightthickness=1,
            highlightbackground=self.cores["border"]
        )

        status_frame.place(
            relx=1.0,
            rely=0.0,
            anchor="ne"
        )

        tk.Label(
            status_frame,
            text="●",
            font=("Segoe UI", 9),
            fg=self.cores["success"],
            bg=self.cores["card"]
        ).pack(
            side="left",
            padx=(12, 5),
            pady=8
        )

        tk.Label(
            status_frame,
            text="Motor analítico disponível",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            side="left",
            padx=(0, 12),
            pady=8
        )

        usuario = SESSAO.usuario

        if usuario:

            tk.Label(
                cabecalho,
                text=(
                    f'{usuario["nome"]}  •  '
                    f'{usuario["perfil"].upper()}'
                ),
                font=("Segoe UI", 8),
                fg=self.cores["text_sec"],
                bg=self.cores["bg"]
            ).pack(
                anchor="e"
            )

        tk.Label(
            conteudo,
            text="ACESSO RÁPIDO",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["bg"]
        ).pack(
            anchor="w",
            pady=(10, 10)
        )

        area_cards = tk.Frame(
            conteudo,
            bg=self.cores["bg"]
        )

        area_cards.pack(
            fill="x"
        )

        self.criar_card_acao(
            area_cards,
            "NOVA ANÁLISE",
            "Importe arquivos, configure a análise e execute o motor analítico.",
            "INICIAR ANÁLISE",
            self.abrir_analise
        )

        self.criar_card_acao(
            area_cards,
            "CONFIGURAÇÕES",
            "Configure fontes de dados, preferências e opções da aplicação.",
            "CONFIGURAR"
        )

        area_status = tk.Frame(
                conteudo,
                bg=self.cores["card"],
                highlightthickness=1,
                highlightbackground=self.cores["border"]
            )

        area_status.pack(
                    fill="x",
                    pady=(25, 0)
                )

        tk.Label(
            area_status,
                    text="AMBIENTE DE ANÁLISE",
                    font=("Segoe UI", 8, "bold"),
                    fg=self.cores["primary"],
                    bg=self.cores["card"]
                ).pack(
                    anchor="w",
                    padx=20,
                    pady=(18, 5)
                )

        tk.Label(
                    area_status,
                    text="Plataforma pronta para receber uma nova fonte de dados.",
                    font=("Segoe UI", 11, "bold"),
                    fg=self.cores["text"],
                    bg=self.cores["card"]
                ).pack(
                    anchor="w",
                    padx=20
                )

        tk.Label(
                    area_status,
                    text=(
                        "Selecione Nova análise para configurar arquivos, categoria, "
                        "período e módulos do motor analítico."
                    ),
                    font=("Segoe UI", 9),
                    fg=self.cores["text_sec"],
                    bg=self.cores["card"],
                    wraplength=700,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=20,
                    pady=(5, 18)
                )
    def criar_botao_menu(self, parent, texto, comando=None):

            botao = tk.Button(
                parent,
                text=texto,
                font=("Segoe UI", 10),
                fg=self.cores["text_sec"],
                bg=self.cores["sidebar"],
                activebackground=self.cores["card"],
                activeforeground=self.cores["text"],
                relief="flat",
                bd=0,
                anchor="w",
                cursor="hand2",
                command=comando
            )

            botao.pack(
                fill="x",
                padx=15,
                pady=3,
                ipady=8
            )

    def criar_card_acao(
            self,
            parent,
            titulo,
            descricao,
            texto_botao,
            comando=None
        ):

            card = tk.Frame(
                parent,
                bg=self.cores["card"],
                highlightthickness=1,
                highlightbackground=self.cores["border"],
                width=370,
                height=230
            )

            card.pack(
                side="left",
                padx=(0, 20)
            )

            card.pack_propagate(False)

            tk.Label(
                card,
                text=titulo,
                font=("Segoe UI", 12, "bold"),
                fg=self.cores["text"],
                bg=self.cores["card"]
            ).pack(
                anchor="w",
                padx=20,
                pady=(30, 10)
            )

            tk.Label(
                card,
                text=descricao,
                font=("Segoe UI", 9),
                fg=self.cores["text_sec"],
                bg=self.cores["card"],
                justify="left",
                wraplength=300
            ).pack(
                anchor="w",
                padx=20
            )

            tk.Button(
                card,
                text=texto_botao,
                font=("Segoe UI", 9, "bold"),
                bg=self.cores["primary"],
                fg="#FFFFFF",
                activebackground=self.cores["primary_hover"],
                activeforeground="#FFFFFF",
                bd=0,
                cursor="hand2",
                command=comando
            ).pack(
                anchor="w",
                padx=20,
                pady=(25, 0),
                ipadx=12,
                ipady=6
            )

    def abrir_analise(self):
            self.container.destroy()
            self.abrir_analise_callback()

    def abrir_usuarios(self):

        if not self.abrir_usuarios_callback:
                return

        self.container.destroy()

        self.abrir_usuarios_callback()

    def sair(self):
            self.container.destroy()
            self.sair_callback()
