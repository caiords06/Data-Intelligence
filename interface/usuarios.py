"""Administração segura de usuários da aplicação."""

from datetime import datetime, timezone
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from auth.autenticacao import (
    criar_usuario,
    definir_perfil_acesso_usuario,
    definir_status_usuario,
    obter_usuarios,
    redefinir_senha,
)
from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS, ORDEM_MODULOS
from enterprise.contexto import (
    aplicar_perfil_padrao_usuario,
    obter_permissoes_usuario,
    salvar_permissoes_usuario,
)
from enterprise.perfis_acesso import (
    nome_perfil_acesso,
    opcoes_perfis_acesso,
)
from interface.componentes import (
    AreaRolavel,
    criar_cabecalho,
    criar_sidebar,
    preparar_janela_secundaria,
)
from interface.tema import (
    CORES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


def _bloqueio_ativo(valor) -> bool:
    if not valor:
        return False
    try:
        instante = datetime.fromisoformat(str(valor))
        if instante.tzinfo is None:
            instante = instante.replace(tzinfo=timezone.utc)
        return instante > datetime.now(timezone.utc)
    except ValueError:
        return False


class TelaUsuarios:
    def __init__(self, root, voltar=None, navegacao=None):
        if not SESSAO.eh_admin():
            raise PermissionError("Somente administradores podem gerenciar usuários.")
        self.root = root
        self.navegacao = navegacao or {"inicio": voltar}
        self.usuarios = []
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()
        self.carregar_usuarios()

    def criar_interface(self):
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="usuarios",
            rodape_texto="←   Voltar ao início",
            rodape_comando=self.navegacao.get("inicio"),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(28, 24),
        )
        conteudo = viewport.conteudo
        criar_cabecalho(
            conteudo,
            "Usuários e acessos",
            (
                "Cadastre acessos, aplique perfis departamentais e personalize "
                "permissões. As operações ficam registradas na auditoria local."
            ),
            breadcrumb="GESTÃO  /  USUÁRIOS E ACESSOS",
            etiqueta="SEGURANÇA V9.0",
        )

        area = tk.Frame(conteudo, bg=CORES["bg"])
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure(0, weight=3, uniform="usuarios")
        area.grid_columnconfigure(1, weight=2, uniform="usuarios")
        self._criar_lista(area)
        self._criar_formulario(area)
        area.bind("<Configure>", self._reorganizar_paineis, add="+")

    def _criar_lista(self, parent):
        painel = tk.Frame(
            parent,
            bg=CORES["card"],
            highlightthickness=1,
            highlightbackground=CORES["border"],
        )
        self.painel_lista = painel
        tk.Label(
            painel,
            text="USUÁRIOS CADASTRADOS",
            font=("Segoe UI", 9, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=20, pady=(20, 10))

        configurar_estilos_ttk(self.root)

        area_tabela = tk.Frame(painel, bg=CORES["card"])
        area_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.tabela = ttk.Treeview(
            area_tabela,
            columns=("nome", "usuario", "email", "perfil", "status"),
            show="headings",
            style="Dark.Treeview",
        )
        for coluna, titulo, largura in (
            ("nome", "Nome", 190),
            ("usuario", "Usuário", 110),
            ("email", "E-mail corporativo", 190),
            ("perfil", "Perfil de acesso", 120),
            ("status", "Status", 105),
        ):
            self.tabela.heading(coluna, text=titulo)
            self.tabela.column(coluna, width=largura, minwidth=max(80, largura // 2), stretch=True)
        barra_vertical = ttk.Scrollbar(
            area_tabela,
            orient="vertical",
            command=self.tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            area_tabela,
            orient="horizontal",
            command=self.tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.tabela.configure(
            yscrollcommand=barra_vertical.set,
            xscrollcommand=barra_horizontal.set,
        )
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra_vertical.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        area_tabela.grid_rowconfigure(0, weight=1, minsize=260)
        area_tabela.grid_columnconfigure(0, weight=1)
        adicionar_divisorias_treeview(self.tabela)

        botoes = tk.Frame(painel, bg=CORES["card"])
        botoes.pack(fill="x", padx=20, pady=(0, 20))
        linha_conta = tk.Frame(botoes, bg=CORES["card"])
        linha_conta.pack(fill="x")
        self._botao_secundario(
            linha_conta, "ATIVAR / DESATIVAR", self.alternar_status
        ).pack(side="left", ipadx=8, ipady=6)
        self._botao_secundario(
            linha_conta, "REDEFINIR SENHA", self.alterar_senha
        ).pack(side="left", padx=10, ipadx=8, ipady=6)
        linha_acesso = tk.Frame(botoes, bg=CORES["card"])
        linha_acesso.pack(fill="x", pady=(8, 0))
        self._botao_secundario(
            linha_acesso, "ALTERAR PERFIL", self.alterar_perfil
        ).pack(side="left", ipadx=8, ipady=6)
        self._botao_secundario(
            linha_acesso, "PERMISSÕES PERSONALIZADAS", self.editar_permissoes
        ).pack(side="left", padx=10, ipadx=8, ipady=6)

    def _criar_formulario(self, parent):
        painel = tk.Frame(
            parent,
            bg=CORES["card"],
            highlightthickness=1,
            highlightbackground=CORES["border"],
        )
        self.painel_formulario = painel
        tk.Label(
            painel,
            text="NOVO USUÁRIO",
            font=("Segoe UI", 9, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=25, pady=(24, 7))

        self.entry_nome = self._criar_campo(painel, "Nome completo")
        self.entry_usuario = self._criar_campo(painel, "Usuário")
        self.entry_email = self._criar_campo(painel, "E-mail corporativo")
        self.entry_senha = self._criar_campo(painel, "Senha inicial", "*")
        self.entry_confirmar = self._criar_campo(painel, "Confirmar senha", "*")
        tk.Label(
            painel,
            text="Mínimo de 10 caracteres, com maiúscula, minúscula, número e símbolo.",
            font=("Segoe UI", 8),
            fg=CORES["text_muted"],
            bg=CORES["card"],
            justify="left",
            wraplength=285,
        ).pack(anchor="w", padx=25, pady=(5, 2))

        tk.Label(
            painel,
            text="PERFIL DE ACESSO",
            font=("Segoe UI", 8, "bold"),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=25, pady=(10, 5))
        self.perfis_opcoes = [("administrador", "Administrador")]
        self.perfis_opcoes.extend(opcoes_perfis_acesso())
        self.perfis_por_nome = {
            nome: codigo for codigo, nome in self.perfis_opcoes
        }
        self.perfil_var = tk.StringVar(value="Analista")
        menu = ttk.Combobox(
            painel,
            textvariable=self.perfil_var,
            values=list(self.perfis_por_nome),
            state="readonly",
            style="Dark.TCombobox",
            width=27,
        )
        menu.pack(fill="x", padx=25, ipady=3)
        tk.Label(
            painel,
            text=(
                "Perfis com + combinam departamentos relacionados. "
                "Permissões específicas podem ser ajustadas depois."
            ),
            font=("Segoe UI", 8),
            fg=CORES["text_muted"],
            bg=CORES["card"],
            justify="left",
            wraplength=285,
        ).pack(anchor="w", padx=25, pady=(5, 0))

        self.label_status = tk.Label(
            painel,
            text="",
            font=("Segoe UI", 8),
            fg=CORES["warning"],
            bg=CORES["card"],
            wraplength=285,
            justify="left",
        )
        self.label_status.pack(anchor="w", padx=25, pady=(12, 0))
        tk.Button(
            painel,
            text="+  CADASTRAR USUÁRIO",
            font=("Segoe UI", 9, "bold"),
            bg=CORES["primary"],
            fg="#FFFFFF",
            activebackground=CORES["primary_hover"],
            activeforeground="#FFFFFF",
            bd=0,
            cursor="hand2",
            command=self.cadastrar,
        ).pack(fill="x", padx=25, pady=16, ipady=8)

    def _reorganizar_paineis(self, evento=None):
        """Mantém o formulário legível sem recortar a lista de usuários."""
        largura = evento.width if evento is not None else 0
        for painel in (self.painel_lista, self.painel_formulario):
            painel.grid_forget()
        if largura >= 900:
            self.painel_lista.grid(
                row=0, column=0, sticky="nsew", padx=(0, 10)
            )
            self.painel_formulario.grid(
                row=0, column=1, sticky="nsew", padx=(10, 0)
            )
        else:
            self.painel_lista.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.painel_formulario.grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="nsew",
                pady=(16, 0),
            )

    @staticmethod
    def _botao_secundario(parent, texto, comando):
        return tk.Button(
            parent,
            text=texto,
            font=("Segoe UI", 8, "bold"),
            bg=CORES["card_hover"],
            fg=CORES["text"],
            activebackground=CORES["border"],
            activeforeground=CORES["text"],
            bd=0,
            cursor="hand2",
            command=comando,
        )

    @staticmethod
    def _criar_campo(parent, titulo, mostrar=None):
        tk.Label(
            parent,
            text=titulo.upper(),
            font=("Segoe UI", 8, "bold"),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=25, pady=(8, 4))
        moldura = tk.Frame(parent, bg=CORES["border"], padx=1, pady=1)
        moldura.pack(fill="x", padx=25)
        entry = tk.Entry(
            moldura,
            font=("Segoe UI", 10),
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            show=mostrar,
            bd=0,
        )
        entry.pack(fill="x", padx=9, ipady=7)
        return entry

    def carregar_usuarios(self):
        try:
            self.usuarios = obter_usuarios(SESSAO.usuario)
        except PermissionError as erro:
            messagebox.showerror("Acesso negado", str(erro))
            self.navegacao.get("inicio", lambda: None)()
            return
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for usuario in self.usuarios:
            if not usuario["ativo"]:
                status = "Desativado"
            elif _bloqueio_ativo(usuario.get("bloqueado_ate")):
                status = "Bloqueado"
            else:
                status = "Ativo"
            self.tabela.insert(
                "",
                tk.END,
                iid=str(usuario["id"]),
                values=(
                    usuario["nome"],
                    usuario["usuario"],
                    usuario.get("email_corporativo") or "—",
                    nome_perfil_acesso(
                        usuario.get("perfil_acesso"),
                        administrador=usuario["perfil"] == "admin",
                    ),
                    status,
                ),
            )

    def cadastrar(self):
        if self.entry_senha.get() != self.entry_confirmar.get():
            self._status("As senhas informadas não coincidem.", "danger")
            return
        perfil_acesso = self.perfis_por_nome.get(self.perfil_var.get())
        if perfil_acesso is None:
            self._status("Selecione um perfil de acesso válido.", "danger")
            return
        perfil_conta = "admin" if perfil_acesso == "administrador" else "usuario"
        if perfil_conta == "admin" and not messagebox.askyesno(
            "Confirmar administrador",
            (
                "Este perfil terá acesso integral a empresas, usuários e módulos. "
                "Deseja continuar?"
            ),
            parent=self.root,
        ):
            return
        try:
            criado = criar_usuario(
                self.entry_nome.get(),
                self.entry_usuario.get(),
                self.entry_senha.get(),
                perfil_conta,
                ator=SESSAO.usuario,
                perfil_acesso=(
                    None if perfil_acesso == "administrador" else perfil_acesso
                ),
                email_corporativo=self.entry_email.get() or None,
            )
            if perfil_conta != "admin":
                aplicar_perfil_padrao_usuario(
                    criado["id"],
                    perfil_acesso,
                    SESSAO.usuario,
                )
        except (ValueError, PermissionError) as erro:
            self._status(str(erro), "danger")
            return
        self._status("Usuário cadastrado com sucesso.", "success")
        for entry in (
            self.entry_nome,
            self.entry_usuario,
            self.entry_email,
            self.entry_senha,
            self.entry_confirmar,
        ):
            entry.delete(0, tk.END)
        self.perfil_var.set("Analista")
        self.carregar_usuarios()

    def alternar_status(self):
        usuario = self._usuario_selecionado()
        if usuario is None:
            return
        acao = "ativar" if not usuario["ativo"] else "desativar"
        if not messagebox.askyesno(
            "Confirmar alteração",
            f"Deseja {acao} o acesso de {usuario['nome']}?",
        ):
            return
        try:
            definir_status_usuario(
                usuario["id"],
                not bool(usuario["ativo"]),
                ator=SESSAO.usuario,
            )
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Operação não permitida", str(erro))
            return
        self.carregar_usuarios()

    def alterar_senha(self):
        usuario = self._usuario_selecionado()
        if usuario is None:
            return
        nova_senha = simpledialog.askstring(
            "Redefinir senha",
            f"Digite a nova senha para {usuario['usuario']}:",
            show="*",
            parent=self.root,
        )
        if not nova_senha:
            return
        confirmacao = simpledialog.askstring(
            "Confirmar senha",
            "Digite a nova senha novamente:",
            show="*",
            parent=self.root,
        )
        if confirmacao != nova_senha:
            messagebox.showerror("Senhas diferentes", "As senhas não coincidem.")
            return
        try:
            redefinir_senha(usuario["id"], nova_senha, ator=SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Senha inválida", str(erro))
            return
        messagebox.showinfo("Senha alterada", "A senha foi redefinida com sucesso.")
        self.carregar_usuarios()

    def alterar_perfil(self):
        usuario = self._usuario_selecionado()
        if usuario is None:
            return
        if usuario["perfil"] == "admin":
            messagebox.showinfo(
                "Perfil de acesso",
                "Administradores possuem um perfil fixo com acesso integral.",
                parent=self.root,
            )
            return

        janela = tk.Toplevel(self.root)
        janela.title(f"Perfil de acesso · {usuario['nome']}")
        preparar_janela_secundaria(
            janela, self.root, 480, 250, redimensionavel=False
        )
        janela.configure(bg=CORES["bg"])

        tk.Label(
            janela,
            text="Alterar perfil de acesso",
            font=("Segoe UI", 18, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(24, 4))
        tk.Label(
            janela,
            text=(
                "O novo perfil substituirá as permissões personalizadas "
                "atuais nesta empresa."
            ),
            font=("Segoe UI", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
            wraplength=410,
            justify="left",
        ).pack(anchor="w", padx=28, pady=(0, 15))

        opcoes = opcoes_perfis_acesso()
        por_nome = {nome: codigo for codigo, nome in opcoes}
        atual = nome_perfil_acesso(usuario.get("perfil_acesso"))
        variavel = tk.StringVar(value=atual)
        ttk.Combobox(
            janela,
            textvariable=variavel,
            values=list(por_nome),
            state="readonly",
            style="Dark.TCombobox",
        ).pack(fill="x", padx=28, ipady=4)

        status = tk.Label(
            janela,
            text="",
            font=("Segoe UI", 8),
            fg=CORES["danger_muted"],
            bg=CORES["bg"],
        )
        status.pack(anchor="w", padx=28, pady=(7, 0))

        def salvar():
            codigo = por_nome.get(variavel.get())
            if not codigo:
                status.configure(text="Selecione um perfil válido.")
                return
            try:
                definir_perfil_acesso_usuario(
                    usuario["id"],
                    codigo,
                    ator=SESSAO.usuario,
                )
                aplicar_perfil_padrao_usuario(
                    usuario["id"],
                    codigo,
                    SESSAO.usuario,
                )
            except (PermissionError, ValueError) as erro:
                status.configure(text=str(erro))
                return
            janela.destroy()
            self.carregar_usuarios()
            messagebox.showinfo(
                "Perfil atualizado",
                "O novo perfil e suas permissões foram aplicados com sucesso.",
                parent=self.root,
            )

        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=28, pady=18)
        tk.Button(
            rodape,
            text="CANCELAR",
            command=janela.destroy,
            font=("Segoe UI", 9, "bold"),
            bg=CORES["card_secundario"],
            fg=CORES["text"],
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
        ).pack(side="right")
        tk.Button(
            rodape,
            text="APLICAR PERFIL",
            command=salvar,
            font=("Segoe UI", 9, "bold"),
            bg=CORES["primary"],
            fg="#FFFFFF",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
        ).pack(side="right", padx=(0, 8))

    def editar_permissoes(self):
        usuario = self._usuario_selecionado()
        if usuario is None:
            return
        if usuario["perfil"] == "admin":
            messagebox.showinfo(
                "Permissões",
                "Administradores possuem acesso integral a todos os módulos.",
                parent=self.root,
            )
            return
        try:
            atuais = obter_permissoes_usuario(usuario["id"], SESSAO.usuario)
        except PermissionError as erro:
            messagebox.showerror("Permissões", str(erro), parent=self.root)
            return

        janela = tk.Toplevel(self.root)
        janela.title(f"Permissões · {usuario['nome']}")
        preparar_janela_secundaria(
            janela, self.root, 650, 590, minimo=(580, 500)
        )
        janela.configure(bg=CORES["bg"])
        tk.Label(
            janela,
            text="Permissões por módulo",
            font=("Segoe UI", 19, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(24, 4))
        tk.Label(
            janela,
            text=(
                "Leitura controla a visibilidade. Escrita permite cadastros; "
                "aprovação autoriza decisões humanas."
            ),
            font=("Segoe UI", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(0, 15))

        painel = tk.Frame(
            janela,
            bg=CORES["card"],
            highlightthickness=1,
            highlightbackground=CORES["border"],
        )
        painel.pack(fill="both", expand=True, padx=28)
        for coluna, texto, largura in ((0, "MÓDULO", 24), (1, "LER", 8), (2, "ESCREVER", 11), (3, "APROVAR", 10)):
            tk.Label(
                painel,
                text=texto,
                font=("Segoe UI", 8, "bold"),
                fg=CORES["primary"],
                bg=CORES["card"],
                width=largura,
                anchor="w" if coluna == 0 else "center",
            ).grid(row=0, column=coluna, sticky="ew", padx=6, pady=(14, 8))
        self.permissoes_vars = {}
        for linha, modulo in enumerate(ORDEM_MODULOS, start=1):
            tk.Label(
                painel,
                text=f'{MODULOS[modulo]["icone"]}  {MODULOS[modulo]["nome"]}',
                font=("Segoe UI", 9),
                fg=CORES["text"],
                bg=CORES["card"],
                anchor="w",
            ).grid(row=linha, column=0, sticky="ew", padx=(12, 6), pady=4)
            self.permissoes_vars[modulo] = {}
            for coluna, chave in enumerate(("ler", "escrever", "aprovar"), start=1):
                variavel = tk.BooleanVar(value=atuais[modulo][chave])
                self.permissoes_vars[modulo][chave] = variavel
                tk.Checkbutton(
                    painel,
                    variable=variavel,
                    bg=CORES["card"],
                    activebackground=CORES["card"],
                    selectcolor=CORES["input"],
                ).grid(row=linha, column=coluna, pady=4)
        painel.grid_columnconfigure(0, weight=1)

        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=28, pady=18)
        tk.Button(
            rodape,
            text="CANCELAR",
            command=janela.destroy,
            font=("Segoe UI", 9, "bold"),
            bg=CORES["card_secundario"],
            fg=CORES["text"],
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
        ).pack(side="right")
        tk.Button(
            rodape,
            text="SALVAR PERMISSÕES",
            command=lambda: self._salvar_permissoes(usuario, janela),
            font=("Segoe UI", 9, "bold"),
            bg=CORES["primary"],
            fg="#FFFFFF",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
        ).pack(side="right", padx=(0, 8))

    def _salvar_permissoes(self, usuario, janela):
        permissoes = {
            modulo: {
                chave: variavel.get()
                for chave, variavel in valores.items()
            }
            for modulo, valores in self.permissoes_vars.items()
        }
        try:
            salvar_permissoes_usuario(
                usuario["id"],
                permissoes,
                SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Permissões", str(erro), parent=janela)
            return
        janela.destroy()
        messagebox.showinfo(
            "Permissões",
            "Permissões atualizadas. Elas serão aplicadas na próxima navegação do usuário.",
            parent=self.root,
        )

    def _usuario_selecionado(self):
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showwarning("Seleção necessária", "Selecione um usuário.")
            return None
        usuario_id = int(selecao[0])
        return next((item for item in self.usuarios if item["id"] == usuario_id), None)

    def _status(self, texto, cor):
        self.label_status.configure(text=texto, fg=CORES[cor])
