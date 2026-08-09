import tkinter as tk

from tkinter import messagebox

from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO

from interface.tema import CORES, MARCA


class TelaPrimeiroAcesso:

    def __init__(
        self,
        root,
        ao_concluir
    ):

        self.root = root
        self.ao_concluir = ao_concluir
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

        card = tk.Frame(
            self.container,
            bg=self.cores["card"],
            width=440,
            height=660,
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
            text=f'{MARCA["simbolo"]}  {MARCA["nome"]}',
            font=("Segoe UI", 20, "bold"),
            fg=self.cores["text"],
            bg=self.cores["card"]
        ).pack(
            pady=(35, 5)
        )

        tk.Label(
            card,
            text="CONFIGURAÇÃO INICIAL",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"]
        ).pack()

        tk.Label(
            card,
            text="Criar administrador",
            font=("Segoe UI", 18, "bold"),
            fg=self.cores["text"],
            bg=self.cores["card"]
        ).pack(
            pady=(25, 5)
        )

        tk.Label(
            card,
            text=(
                "Este será o primeiro administrador "
                "da plataforma."
            ),
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            pady=(0, 20)
        )

        self.entry_nome = self.criar_campo(
            card,
            "Nome completo"
        )

        self.entry_usuario = self.criar_campo(
            card,
            "Usuário"
        )

        self.entry_senha = self.criar_campo(
            card,
            "Senha",
            "*"
        )

        self.entry_confirmar = self.criar_campo(
            card,
            "Confirmar senha",
            "*"
        )

        self.label_status = tk.Label(
            card,
            text="",
            font=("Segoe UI", 8),
            fg=self.cores["warning"],
            bg=self.cores["card"]
        )

        self.label_status.pack(
            pady=(10, 0)
        )

        tk.Button(
            card,
            text="CRIAR ADMINISTRADOR",
            font=("Segoe UI", 9, "bold"),
            bg=self.cores["primary"],
            fg="#FFFFFF",
            activebackground=self.cores["primary_hover"],
            activeforeground="#FFFFFF",
            bd=0,
            command=self.criar_admin
        ).pack(
            fill="x",
            padx=45,
            pady=(15, 20),
            ipady=9
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
            padx=45,
            pady=7
        )

        tk.Label(
            frame,
            text=titulo.upper(),
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            pady=(0, 5)
        )

        entry = tk.Entry(
            frame,
            font=("Segoe UI", 10),
            bg=self.cores["input"],
            fg=self.cores["text"],
            insertbackground=self.cores["primary"],
            show=mostrar,
            bd=0
        )

        entry.pack(
            fill="x",
            ipady=8
        )

        return entry


    def criar_admin(self):

        senha = self.entry_senha.get()
        confirmar = self.entry_confirmar.get()

        if senha != confirmar:

            self.label_status.config(
                text="As senhas não coincidem."
            )

            return

        try:

            usuario = criar_admin_inicial(
                self.entry_nome.get(),
                self.entry_usuario.get(),
                senha
            )

        except ValueError as erro:

            self.label_status.config(
                text=str(erro)
            )

            return

        SESSAO.iniciar(
            usuario
        )

        messagebox.showinfo(
            "Configuração concluída",
            "Administrador criado com sucesso."
        )

        self.container.destroy()

        self.ao_concluir()
