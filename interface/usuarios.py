import tkinter as tk

from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog

from auth.autenticacao import (
    criar_usuario,
    obter_usuarios,
    definir_status_usuario,
    redefinir_senha
)

from auth.sessao import SESSAO

from interface.tema import (
    CORES,
    MARCA
)


class TelaUsuarios:

    def __init__(
        self,
        root,
        voltar
    ):

        self.root = root
        self.voltar_callback = voltar
        self.cores = CORES

        self.criar_interface()
        self.carregar_usuarios()


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
            cursor="hand2",
            anchor="w",
            command=self.voltar
        ).pack(
            fill="x",
            padx=15,
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
            pady=35
        )

        tk.Label(
            conteudo,
            text="Gerenciamento de usuários",
            font=("Segoe UI", 24, "bold"),
            fg=self.cores["text"],
            bg=self.cores["bg"]
        ).pack(
            anchor="w"
        )

        tk.Label(
            conteudo,
            text="Cadastre funcionários e gerencie acessos à plataforma.",
            font=("Segoe UI", 10),
            fg=self.cores["text_sec"],
            bg=self.cores["bg"]
        ).pack(
            anchor="w",
            pady=(5, 25)
        )

        area = tk.Frame(
            conteudo,
            bg=self.cores["bg"]
        )

        area.pack(
            fill="both",
            expand=True
        )

        # LISTA
        esquerda = tk.Frame(
            area,
            bg=self.cores["card"],
            highlightthickness=1,
            highlightbackground=self.cores["border"]
        )

        esquerda.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        tk.Label(
            esquerda,
            text="USUÁRIOS CADASTRADOS",
            font=("Segoe UI", 9, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.configurar_tabela()

        self.tabela = ttk.Treeview(
            esquerda,
            columns=(
                "nome",
                "usuario",
                "perfil",
                "status"
            ),
            show="headings",
            style="Usuarios.Treeview"
        )

        self.tabela.heading(
            "nome",
            text="Nome"
        )

        self.tabela.heading(
            "usuario",
            text="Usuário"
        )

        self.tabela.heading(
            "perfil",
            text="Perfil"
        )

        self.tabela.heading(
            "status",
            text="Status"
        )

        self.tabela.column(
            "nome",
            width=180
        )

        self.tabela.column(
            "usuario",
            width=120
        )

        self.tabela.column(
            "perfil",
            width=90
        )

        self.tabela.column(
            "status",
            width=80
        )

        self.tabela.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 15)
        )

        botoes = tk.Frame(
            esquerda,
            bg=self.cores["card"]
        )

        botoes.pack(
            fill="x",
            padx=20,
            pady=(0, 20)
        )

        tk.Button(
            botoes,
            text="ATIVAR / DESATIVAR",
            font=("Segoe UI", 8, "bold"),
            bg=self.cores["card_hover"],
            fg=self.cores["text"],
            bd=0,
            command=self.alternar_status
        ).pack(
            side="left",
            ipadx=8,
            ipady=6
        )

        tk.Button(
            botoes,
            text="REDEFINIR SENHA",
            font=("Segoe UI", 8, "bold"),
            bg=self.cores["card_hover"],
            fg=self.cores["text"],
            bd=0,
            command=self.alterar_senha
        ).pack(
            side="left",
            padx=10,
            ipadx=8,
            ipady=6
        )

        # NOVO USUÁRIO
        direita = tk.Frame(
            area,
            bg=self.cores["card"],
            width=330,
            highlightthickness=1,
            highlightbackground=self.cores["border"]
        )

        direita.pack(
            side="left",
            fill="y",
            padx=(10, 0)
        )

        direita.pack_propagate(False)

        tk.Label(
            direita,
            text="NOVO USUÁRIO",
            font=("Segoe UI", 9, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 10)
        )

        self.entry_nome = self.criar_campo(
            direita,
            "Nome completo"
        )

        self.entry_usuario = self.criar_campo(
            direita,
            "Usuário"
        )

        self.entry_senha = self.criar_campo(
            direita,
            "Senha inicial",
            "*"
        )

        tk.Label(
            direita,
            text="PERFIL",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(15, 5)
        )

        self.perfil_var = tk.StringVar(
            value="usuario"
        )

        menu = tk.OptionMenu(
            direita,
            self.perfil_var,
            "usuario",
            "admin"
        )

        menu.configure(
            bg=self.cores["input"],
            fg=self.cores["text"],
            activebackground=self.cores["card_hover"],
            activeforeground=self.cores["text"],
            highlightthickness=0,
            bd=0,
            width=20
        )

        menu["menu"].configure(
            bg=self.cores["input"],
            fg=self.cores["text"]
        )

        menu.pack(
            anchor="w",
            padx=25
        )

        self.label_status = tk.Label(
            direita,
            text="",
            font=("Segoe UI", 8),
            fg=self.cores["warning"],
            bg=self.cores["card"],
            wraplength=270
        )

        self.label_status.pack(
            anchor="w",
            padx=25,
            pady=(20, 0)
        )

        tk.Button(
            direita,
            text="+  CADASTRAR USUÁRIO",
            font=("Segoe UI", 9, "bold"),
            bg=self.cores["primary"],
            fg="#FFFFFF",
            activebackground=self.cores["primary_hover"],
            activeforeground="#FFFFFF",
            bd=0,
            command=self.cadastrar
        ).pack(
            fill="x",
            padx=25,
            pady=20,
            ipady=8
        )


    def configurar_tabela(self):

        estilo = ttk.Style()

        estilo.theme_use("clam")

        estilo.configure(
            "Usuarios.Treeview",
            background=self.cores["input"],
            foreground=self.cores["text"],
            fieldbackground=self.cores["input"],
            borderwidth=0,
            rowheight=30
        )

        estilo.configure(
            "Usuarios.Treeview.Heading",
            background=self.cores["card_hover"],
            foreground=self.cores["text"],
            relief="flat"
        )

        estilo.map(
            "Usuarios.Treeview",
            background=[
                (
                    "selected",
                    self.cores["primary_hover"]
                )
            ]
        )


    def criar_campo(
        self,
        parent,
        titulo,
        mostrar=None
    ):

        tk.Label(
            parent,
            text=titulo.upper(),
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["text_sec"],
            bg=self.cores["card"]
        ).pack(
            anchor="w",
            padx=25,
            pady=(12, 5)
        )

        entry = tk.Entry(
            parent,
            font=("Segoe UI", 10),
            bg=self.cores["input"],
            fg=self.cores["text"],
            insertbackground=self.cores["primary"],
            show=mostrar,
            bd=0
        )

        entry.pack(
            fill="x",
            padx=25,
            ipady=8
        )

        return entry


    def carregar_usuarios(self):

        for item in self.tabela.get_children():

            self.tabela.delete(
                item
            )

        for usuario in obter_usuarios():

            self.tabela.insert(
                "",
                tk.END,
                iid=str(usuario["id"]),
                values=(
                    usuario["nome"],
                    usuario["usuario"],
                    usuario["perfil"].upper(),
                    (
                        "Ativo"
                        if usuario["ativo"]
                        else "Desativado"
                    )
                )
            )


    def cadastrar(self):

        try:

            criar_usuario(
                self.entry_nome.get(),
                self.entry_usuario.get(),
                self.entry_senha.get(),
                self.perfil_var.get()
            )

        except ValueError as erro:

            self.label_status.configure(
                text=str(erro),
                fg=self.cores["danger"]
            )

            return

        self.label_status.configure(
            text="Usuário cadastrado com sucesso.",
            fg=self.cores["success"]
        )

        self.entry_nome.delete(
            0,
            tk.END
        )

        self.entry_usuario.delete(
            0,
            tk.END
        )

        self.entry_senha.delete(
            0,
            tk.END
        )

        self.carregar_usuarios()


    def alternar_status(self):

        selecao = self.tabela.selection()

        if not selecao:
            return

        usuario_id = int(
            selecao[0]
        )

        if (
            SESSAO.usuario
            and
            usuario_id == SESSAO.usuario["id"]
        ):

            messagebox.showwarning(
                "Operação não permitida",
                "Você não pode desativar sua própria conta."
            )

            return

        usuarios = obter_usuarios()

        usuario = next(
            (
                item
                for item in usuarios
                if item["id"] == usuario_id
            ),
            None
        )

        if usuario is None:
            return

        definir_status_usuario(
            usuario_id,
            not bool(usuario["ativo"])
        )

        self.carregar_usuarios()


    def alterar_senha(self):

        selecao = self.tabela.selection()

        if not selecao:
            return

        usuario_id = int(
            selecao[0]
        )

        nova_senha = simpledialog.askstring(
            "Redefinir senha",
            "Digite a nova senha:",
            show="*"
        )

        if not nova_senha:
            return

        try:

            redefinir_senha(
                usuario_id,
                nova_senha
            )

        except ValueError as erro:

            messagebox.showerror(
                "Senha inválida",
                str(erro)
            )

            return

        messagebox.showinfo(
            "Senha alterada",
            "A senha foi redefinida com sucesso."
        )


    def voltar(self):

        self.container.destroy()

        self.voltar_callback()
