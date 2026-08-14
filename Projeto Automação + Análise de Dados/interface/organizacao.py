"""Administração visual do núcleo multiempresa e multifilial."""

from core.versao import VERSAO_INTERFACE
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from services.organizacao import (
    criar_centro_custo,
    criar_departamento,
    criar_empresa,
    criar_filial,
    definir_contexto_empresa,
    listar_centros_custo,
    listar_departamentos,
    listar_empresas,
    listar_filiais,
    remover_empresa_criada_sessao,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_sidebar,
)
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
            ativo="organizacao",
            rodape_texto="←   Voltar às configurações",
            rodape_comando=self.navegacao.get("configuracoes"),
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
            "Estrutura organizacional",
            (
                "Empresas, filiais, departamentos e centros de custo "
                "compartilhados por todos os módulos."
            ),
            breadcrumb="GESTÃO  /  ORGANIZAÇÃO",
            etiqueta=f"MULTIEMPRESA {VERSAO_INTERFACE}",
        )

        seletor = criar_card(conteudo)
        seletor.pack(fill="x", pady=(0, 14))
        tk.Label(
            seletor,
            text="EMPRESA ATIVA NESTA SESSÃO",
            font=("Inter", 8, "bold"),
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
        self.combo_empresa.bind(
            "<<ComboboxSelected>>",
            self._atualizar_estado_remocao,
            add="+",
        )
        criar_botao(
            seletor,
            "USAR EMPRESA",
            self.alterar_contexto,
            tipo="secundario",
        ).pack(side="left", padx=8, pady=8)
        criar_botao(seletor, "+ EMPRESA", self.nova_empresa).pack(
            side="right", padx=14, pady=8
        )
        self.botao_remover_empresa = criar_botao(
            seletor,
            "REMOVER EMPRESA",
            self.remover_empresa,
            tipo="perigo",
            compacto=True,
        )
        self.botao_remover_empresa.pack(side="right", padx=(0, 2), pady=8)

        grade = GradeResponsiva(
            conteudo,
            max_colunas=3,
            largura_minima=280,
            gap=12,
        )
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
            grade.adicionar(card)
            tk.Label(
                card,
                text=titulo,
                font=("Inter", 9, "bold"),
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
                font=("Inter", 9),
            )
            lista.pack(fill="both", expand=True, padx=16, ipady=90)
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
        self._atualizar_estado_remocao()

    def _empresa_selecionada(self):
        return self.mapa_empresas.get(self.empresa_var.get())

    def _atualizar_estado_remocao(self, _evento=None):
        empresa_id = self._empresa_selecionada()
        permitida = bool(
            empresa_id is not None
            and SESSAO.empresa_criada_na_sessao(empresa_id)
            and (
                SESSAO.empresa_id is None
                or int(SESSAO.empresa_id) != int(empresa_id)
            )
        )
        self.botao_remover_empresa.configure(
            state="normal" if permitida else "disabled",
            bg=CORES["danger"] if permitida else CORES["input"],
            fg=CORES["text"] if permitida else CORES["text_disabled"],
            cursor="hand2" if permitida else "arrow",
        )

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

    def remover_empresa(self):
        empresa_id = self._empresa_selecionada()
        if empresa_id is None:
            return
        if not SESSAO.empresa_criada_na_sessao(empresa_id):
            messagebox.showwarning(
                "Remover empresa",
                "Somente empresas criadas durante a sessão atual podem ser removidas.",
                parent=self.root,
            )
            return
        if SESSAO.empresa_id is not None and int(SESSAO.empresa_id) == int(empresa_id):
            messagebox.showwarning(
                "Remover empresa",
                "Selecione outra empresa como ativa antes de remover esta.",
                parent=self.root,
            )
            return
        nome = next(
            (
                item["nome"]
                for item in self.empresas
                if int(item["id"]) == int(empresa_id)
            ),
            f"#{empresa_id}",
        )
        if not messagebox.askyesno(
            "Remover empresa",
            (
                f"Remover '{nome}' da operação atual?\n\n"
                "A empresa será desativada com segurança e continuará registrada "
                "na auditoria."
            ),
            parent=self.root,
        ):
            return
        try:
            remover_empresa_criada_sessao(empresa_id, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Remover empresa", str(erro), parent=self.root)
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
