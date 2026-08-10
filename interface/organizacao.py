"""Administração visual do núcleo multiempresa e multifilial."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from enterprise.organizacao import (
    criar_centro_custo,
    criar_departamento,
    criar_empresa,
    criar_filial,
    definir_contexto_empresa,
    listar_centros_custo,
    listar_departamentos,
    listar_empresas,
    listar_filiais,
)
from interface.componentes import criar_botao, criar_card, criar_sidebar
from interface.tema import CORES, LAYOUT, configurar_estilos_ttk


class TelaOrganizacao:
    def __init__(self, root, navegacao):
        if not SESSAO.eh_admin():
            raise PermissionError("Somente administradores podem alterar a organização.")
        self.root = root
        self.navegacao = navegacao
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()
        self.carregar()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="configuracoes",
            rodape_texto="←   Voltar às configurações",
            rodape_comando=self.navegacao.get("configuracoes"),
        )
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(28, 24),
        )
        tk.Label(
            conteudo,
            text="Estrutura organizacional",
            font=("Segoe UI", 24, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w")
        tk.Label(
            conteudo,
            text=(
                "Empresas, filiais, departamentos e centros de custo compartilhados por todos os módulos."
            ),
            font=("Segoe UI", 10),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", pady=(5, 18))

        seletor = criar_card(conteudo)
        seletor.pack(fill="x", pady=(0, 14))
        tk.Label(
            seletor,
            text="EMPRESA ATIVA NESTA SESSÃO",
            font=("Segoe UI", 8, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(side="left", padx=(18, 12), pady=14)
        self.empresa_var = tk.StringVar()
        self.combo_empresa = ttk.Combobox(
            seletor,
            textvariable=self.empresa_var,
            state="readonly",
            style="Dark.TCombobox",
            width=34,
        )
        self.combo_empresa.pack(side="left", pady=10)
        criar_botao(
            seletor,
            "USAR EMPRESA",
            self.alterar_contexto,
            tipo="secundario",
        ).pack(side="left", padx=8, pady=8)
        criar_botao(seletor, "+ EMPRESA", self.nova_empresa).pack(
            side="right", padx=14, pady=8
        )

        grade = tk.Frame(conteudo, bg=CORES["bg"])
        grade.pack(fill="both", expand=True)
        self.listas = {}
        for indice, (chave, titulo, comando) in enumerate(
            (
                ("filiais", "FILIAIS", self.nova_filial),
                ("departamentos", "DEPARTAMENTOS", self.novo_departamento),
                ("centros", "CENTROS DE CUSTO", self.novo_centro),
            )
        ):
            card = criar_card(grade)
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 10) if indice < 2 else (0, 0),
            )
            tk.Label(
                card,
                text=titulo,
                font=("Segoe UI", 9, "bold"),
                fg=CORES["primary"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=16, pady=(16, 9))
            lista = tk.Listbox(
                card,
                bg=CORES["input"],
                fg=CORES["text"],
                selectbackground=CORES["primary_hover"],
                relief="flat",
                bd=0,
                font=("Segoe UI", 9),
            )
            lista.pack(fill="both", expand=True, padx=16)
            self.listas[chave] = lista
            criar_botao(card, "+ ADICIONAR", comando, tipo="secundario").pack(
                anchor="w", padx=16, pady=14
            )

    def carregar(self):
        self.empresas = [item for item in listar_empresas() if item["ativo"]]
        self.mapa_empresas = {
            f'{item["id"]} · {item["nome"]}': item["id"] for item in self.empresas
        }
        self.combo_empresa.configure(values=list(self.mapa_empresas))
        atual = next(
            (rotulo for rotulo, codigo in self.mapa_empresas.items() if codigo == SESSAO.empresa_id),
            next(iter(self.mapa_empresas), ""),
        )
        self.empresa_var.set(atual)
        for lista in self.listas.values():
            lista.delete(0, tk.END)
        for item in listar_filiais():
            self.listas["filiais"].insert(tk.END, f'{item["codigo"]} · {item["nome"]}')
        for item in listar_departamentos():
            self.listas["departamentos"].insert(tk.END, f'{item["codigo"]} · {item["nome"]}')
        for item in listar_centros_custo():
            self.listas["centros"].insert(tk.END, f'{item["codigo"]} · {item["nome"]}')

    def alterar_contexto(self):
        empresa_id = self.mapa_empresas.get(self.empresa_var.get())
        if empresa_id is None:
            return
        try:
            definir_contexto_empresa(empresa_id)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Organização", str(erro), parent=self.root)
            return
        self.carregar()

    def nova_empresa(self):
        nome = simpledialog.askstring("Nova empresa", "Nome empresarial:", parent=self.root)
        if not nome:
            return
        cnpj = simpledialog.askstring("Nova empresa", "CNPJ opcional:", parent=self.root) or ""
        try:
            criar_empresa(nome, cnpj, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Nova empresa", str(erro), parent=self.root)
            return
        self.carregar()

    def nova_filial(self):
        nome = simpledialog.askstring("Nova filial", "Nome da filial:", parent=self.root)
        codigo = simpledialog.askstring("Nova filial", "Código curto:", parent=self.root)
        if not nome or not codigo:
            return
        try:
            criar_filial(nome, codigo, ator=SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Nova filial", str(erro), parent=self.root)
            return
        self.carregar()

    def novo_departamento(self):
        nome = simpledialog.askstring("Departamento", "Nome:", parent=self.root)
        codigo = simpledialog.askstring("Departamento", "Código curto:", parent=self.root)
        if not nome or not codigo:
            return
        try:
            criar_departamento(nome, codigo, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Departamento", str(erro), parent=self.root)
            return
        self.carregar()

    def novo_centro(self):
        nome = simpledialog.askstring("Centro de custo", "Nome:", parent=self.root)
        codigo = simpledialog.askstring("Centro de custo", "Código curto:", parent=self.root)
        if not nome or not codigo:
            return
        try:
            criar_centro_custo(nome, codigo, ator=SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Centro de custo", str(erro), parent=self.root)
            return
        self.carregar()
