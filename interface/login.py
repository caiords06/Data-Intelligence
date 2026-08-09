import tkinter as tk
from interface.tema import CORES, MARCA
from auth.autenticacao import autenticar_usuario
from auth.sessao import SESSAO


class TelaLogin:

    def __init__(self, root, ao_entrar):
        self.root = root
        self.ao_entrar = ao_entrar

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

        self.container.grid_rowconfigure(
            0,
            weight=1
        )

        self.container.grid_columnconfigure(
            0,
            weight=6
        )

        self.container.grid_columnconfigure(
            1,
            weight=5
        )

        # =========================================================
        # ÁREA DE IDENTIDADE
        # =========================================================

        area_marca = tk.Frame(
            self.container,
            bg=self.cores["sidebar"]
        )

        area_marca.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        conteudo_marca = tk.Frame(
            area_marca,
            bg=self.cores["sidebar"]
        )

        conteudo_marca.place(
            relx=0.12,
            rely=0.5,
            anchor="w"
        )

        tk.Label(
            conteudo_marca,
            text=MARCA["simbolo"],
            font=("Segoe UI Symbol", 40),
            fg=self.cores["primary"],
            bg=self.cores["sidebar"]
        ).pack(
            anchor="w"
        )

        tk.Label(
            conteudo_marca,
            text=MARCA["nome"],
            font=("Segoe UI", 32, "bold"),
            fg=self.cores["text"],
            bg=self.cores["sidebar"]
        ).pack(
            anchor="w",
            pady=(5, 0)
        )

        tk.Label(
            conteudo_marca,
            text=MARCA["descricao"],
            font=("Segoe UI", 10, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["sidebar"]
        ).pack(
            anchor="w"
        )

        tk.Frame(
            conteudo_marca,
            bg=self.cores["primary"],
            height=3,
            width=65
        ).pack(
            anchor="w",
            pady=(25, 25)
        )

        tk.Label(
            conteudo_marca,
            text="Transforme dados\nem decisões.",
            font=("Segoe UI", 26, "bold"),
            fg=self.cores["text"],
            bg=self.cores["sidebar"],
            justify="left"
        ).pack(
            anchor="w"
        )

        tk.Label(
            conteudo_marca,
            text=(
                "Automação, análise e inteligência "
                "para dados empresariais."
            ),
            font=("Segoe UI", 10),
            fg=self.cores["text_sec"],
            bg=self.cores["sidebar"],
            justify="left",
            wraplength=420
        ).pack(
            anchor="w",
            pady=(15, 30)
        )

        tk.Label(
            conteudo_marca,
            text="ANÁLISE  •  AUTOMAÇÃO  •  INTELIGÊNCIA",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["text_muted"],
            bg=self.cores["sidebar"]
        ).pack(
            anchor="w"
        )


        # =========================================================
        # ÁREA DE LOGIN
        # =========================================================

        area_login = tk.Frame(
            self.container,
            bg=self.cores["bg"]
        )

        area_login.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        card = tk.Frame(
            area_login,
            bg=self.cores["card"],
            width=390,
            height=470,
            highlightthickness=1,
            highlightbackground=self.cores["border"]
        )

        card.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        card.pack_propagate(False)

        tk.Label(
            card,
            text="ACESSO CORPORATIVO",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=40,
            pady=(40, 8)
        )

        tk.Label(
            card,
            text="Bem-vindo",
            font=("Segoe UI", 22, "bold"),
            fg=self.cores["text"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=40
        )

        tk.Label(
            card,
            text="Entre com suas credenciais para acessar a plataforma.",
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["card"],
            wraplength=300,
            justify="left"
        ).pack(
            anchor="w",
            padx=40,
            pady=(5, 25)
        )

        self.entry_usuario = self.criar_campo(
            card,
            "Usuário"
        )

        self.entry_senha = self.criar_campo(
            card,
            "Senha",
            mostrar="•"
        )

        tk.Button(
            card,
            text="ENTRAR NA PLATAFORMA  →",
            font=("Segoe UI", 9, "bold"),
            bg=self.cores["primary"],
            fg="#FFFFFF",
            activebackground=self.cores["primary_hover"],
            activeforeground="#FFFFFF",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.entrar
        ).pack(
            fill="x",
            padx=40,
            pady=(25, 12),
            ipady=9
        )

        self.label_status = tk.Label(
            card,
            text="●  Ambiente protegido",
            font=("Segoe UI", 8),
            fg=self.cores["success"],
            bg=self.cores["card"]
        )

        self.label_status.pack(
            anchor="w",
            padx=40
        )

        tk.Label(
            card,
            text="Data Intelligence Platform",
            font=("Segoe UI", 8),
            fg=self.cores["text_muted"],
            bg=self.cores["card"]
        ).pack(
            side="bottom",
            pady=25
        )

        self.entry_usuario.focus_set()

        self.root.bind(
            "<Return>",
            lambda event: self.entrar()
        )

    def criar_campo(
            self,
            parent,
            titulo,
            mostrar=None
        ):

            frame = tk.Frame(
                parent,
                bg=self.cores["card"]
            )

            frame.pack(
                fill="x",
                padx=40,
                pady=8
            )

            tk.Label(
                frame,
                text=titulo.upper(),
                font=("Segoe UI", 8, "bold"),
                fg=self.cores["text_sec"],
                bg=self.cores["card"]
            ).pack(
                anchor="w",
                pady=(0, 6)
            )

            entrada_frame = tk.Frame(
                frame,
                bg=self.cores["border"]
            )

            entrada_frame.pack(
                fill="x"
            )

            entry = tk.Entry(
                entrada_frame,
                font=("Segoe UI", 11),
                bg=self.cores["input"],
                fg=self.cores["text"],
                insertbackground=self.cores["primary"],
                relief="flat",
                bd=0,
                show=mostrar
            )

            entry.pack(
                fill="x",
                padx=1,
                pady=1,
                ipady=9
            )

            return entry

    def entrar(self):

        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get()

        if not usuario or not senha:

            self.label_status.configure(
                text="Informe usuário e senha.",
                fg=self.cores["warning"]
            )

            return

        try:

            usuario_autenticado = autenticar_usuario(
                usuario,
                senha
            )

        except (
            ValueError,
            PermissionError
        ) as erro:

            self.label_status.configure(
                text=str(erro),
                fg=self.cores["danger"]
            )

            return

        SESSAO.iniciar(
            usuario_autenticado
        )

        self.destruir()

        self.ao_entrar()

    def destruir(self):
            self.container.destroy()
