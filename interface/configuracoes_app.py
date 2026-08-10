"""Tela de preferências globais e segurança da conta atual."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.autenticacao import alterar_propria_senha
from auth.sessao import SESSAO
from configuracoes.preferencias import (
    PREFERENCIAS_PADRAO,
    carregar_preferencias,
    salvar_preferencias,
)
from enterprise.backups import criar_backup
from interface.componentes import criar_sidebar
from interface.tema import CORES, configurar_estilos_ttk

CATEGORIAS_TELA = {
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
PERIODOS_TELA = {
    "Automático": "automatico",
    "Mensal": "mensal",
    "Trimestral": "trimestral",
    "Semestral": "semestral",
    "Anual": "anual",
}


class TelaConfiguracoesApp:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.preferencias = carregar_preferencias()
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="configuracoes",
            rodape_texto="←   Voltar ao início",
            rodape_comando=self.navegacao.get("inicio"),
        )
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(side="left", fill="both", expand=True, padx=40, pady=30)
        tk.Label(
            conteudo,
            text="Configurações da aplicação",
            font=("Segoe UI", 24, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w")
        tk.Label(
            conteudo,
            text=(
                "Preferências globais, comportamento da interface e segurança da conta. "
                "Estas opções não alteram o motor da análise atual."
            ),
            font=("Segoe UI", 10),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", pady=(5, 22))

        grade = tk.Frame(conteudo, bg=CORES["bg"])
        grade.pack(fill="both", expand=True)
        esquerda = self._card(grade, "EXPERIÊNCIA E PADRÕES")
        direita = self._card(grade, "FONTES E SEGURANÇA")
        esquerda.pack(side="left", fill="both", expand=True, padx=(0, 9))
        direita.pack(side="right", fill="both", expand=True, padx=(9, 0))

        self.delay_var = tk.IntVar(value=self.preferencias["atraso_minimo_segundos"])
        self.timeout_var = tk.IntVar(value=self.preferencias["tempo_sessao_minutos"])
        self.categoria_var = tk.StringVar(
            value=self._rotulo(CATEGORIAS_TELA, self.preferencias["categoria_padrao"])
        )
        self.periodo_var = tk.StringVar(
            value=self._rotulo(PERIODOS_TELA, self.preferencias["periodo_padrao"])
        )
        self._campo_spin(esquerda, "Tempo mínimo do progresso (segundos)", self.delay_var, 0, 15)
        self._campo_combo(esquerda, "Categoria padrão", self.categoria_var, CATEGORIAS_TELA)
        self._campo_combo(esquerda, "Período padrão", self.periodo_var, PERIODOS_TELA)
        self._campo_spin(esquerda, "Expiração da sessão (minutos)", self.timeout_var, 5, 240)

        self.pasta_var = tk.StringVar(value=self.preferencias["pasta_padrao"])
        self.url_var = tk.StringVar(value=self.preferencias["url_validacao"])
        self.confirmar_var = tk.BooleanVar(
            value=self.preferencias["confirmar_exclusao_historico"]
        )
        self._campo_pasta(direita)
        self._campo_texto(direita, "URL usada na validação do navegador", self.url_var)
        tk.Checkbutton(
            direita,
            text="Confirmar antes de excluir um item do histórico",
            variable=self.confirmar_var,
            font=("Segoe UI", 9),
            fg=CORES["text"],
            bg=CORES["card"],
            selectcolor=CORES["input"],
            activebackground=CORES["card"],
            activeforeground=CORES["text"],
        ).pack(anchor="w", padx=22, pady=(15, 8))
        tk.Button(
            direita,
            text="ALTERAR MINHA SENHA",
            command=self.alterar_senha,
            font=("Segoe UI", 9, "bold"),
            bg=CORES["card_secundario"],
            fg=CORES["text"],
            activebackground=CORES["card_hover"],
            activeforeground=CORES["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
        ).pack(anchor="w", padx=22, pady=(12, 0), ipadx=10, ipady=7)
        if SESSAO.eh_admin():
            tk.Button(
                direita,
                text="ESTRUTURA ORGANIZACIONAL",
                command=self.navegacao.get("organizacao"),
                font=("Segoe UI", 9, "bold"),
                bg=CORES["card_secundario"],
                fg=CORES["text"],
                activebackground=CORES["card_hover"],
                activeforeground=CORES["text"],
                relief="flat",
                bd=0,
                cursor="hand2",
            ).pack(anchor="w", padx=22, pady=(10, 0), ipadx=10, ipady=7)
            tk.Button(
                direita,
                text="CRIAR BACKUP VERIFICADO",
                command=self.criar_backup,
                font=("Segoe UI", 9, "bold"),
                bg=CORES["card_secundario"],
                fg=CORES["text"],
                activebackground=CORES["card_hover"],
                activeforeground=CORES["text"],
                relief="flat",
                bd=0,
                cursor="hand2",
            ).pack(anchor="w", padx=22, pady=(10, 0), ipadx=10, ipady=7)

        rodape = tk.Frame(conteudo, bg=CORES["bg"])
        rodape.pack(fill="x", pady=(16, 0))
        tk.Button(
            rodape,
            text="SALVAR CONFIGURAÇÕES",
            command=self.salvar,
            font=("Segoe UI", 9, "bold"),
            bg=CORES["primary"],
            fg="#FFFFFF",
            activebackground=CORES["primary_hover"],
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
        ).pack(side="left", ipadx=16, ipady=8)
        tk.Button(
            rodape,
            text="RESTAURAR PADRÕES",
            command=self.restaurar,
            font=("Segoe UI", 9, "bold"),
            bg=CORES["card_secundario"],
            fg=CORES["text"],
            activebackground=CORES["card_hover"],
            activeforeground=CORES["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
        ).pack(side="left", padx=10, ipadx=12, ipady=8)
        self.status = tk.Label(
            rodape,
            text="",
            font=("Segoe UI", 9),
            fg=CORES["success"],
            bg=CORES["bg"],
        )
        self.status.pack(side="right")

    @staticmethod
    def _rotulo(mapa, valor):
        return next((rotulo for rotulo, codigo in mapa.items() if codigo == valor), next(iter(mapa)))

    def _card(self, parent, titulo):
        card = tk.Frame(
            parent,
            bg=CORES["card"],
            highlightthickness=1,
            highlightbackground=CORES["border"],
        )
        tk.Label(
            card,
            text=titulo,
            font=("Segoe UI", 10, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=22, pady=(22, 16))
        return card

    def _rotulo_campo(self, parent, texto):
        tk.Label(
            parent,
            text=texto,
            font=("Segoe UI", 9, "bold"),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=22, pady=(10, 5))

    def _campo_spin(self, parent, texto, variavel, minimo, maximo):
        self._rotulo_campo(parent, texto)
        tk.Spinbox(
            parent,
            from_=minimo,
            to=maximo,
            textvariable=variavel,
            font=("Segoe UI", 10),
            bg=CORES["input"],
            fg=CORES["text"],
            buttonbackground=CORES["card_secundario"],
            insertbackground=CORES["primary"],
            relief="flat",
            bd=0,
        ).pack(fill="x", padx=22, ipady=7)

    def _campo_combo(self, parent, texto, variavel, valores):
        self._rotulo_campo(parent, texto)
        ttk.Combobox(
            parent,
            textvariable=variavel,
            values=list(valores),
            state="readonly",
            font=("Segoe UI", 10),
            style="Dark.TCombobox",
        ).pack(fill="x", padx=22, ipady=4)

    def _campo_texto(self, parent, texto, variavel):
        self._rotulo_campo(parent, texto)
        tk.Entry(
            parent,
            textvariable=variavel,
            font=("Segoe UI", 10),
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            relief="flat",
            bd=0,
        ).pack(fill="x", padx=22, ipady=8)

    def _campo_pasta(self, parent):
        self._rotulo_campo(parent, "Pasta padrão para selecionar arquivos")
        linha = tk.Frame(parent, bg=CORES["card"])
        linha.pack(fill="x", padx=22)
        tk.Entry(
            linha,
            textvariable=self.pasta_var,
            font=("Segoe UI", 10),
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            relief="flat",
            bd=0,
        ).pack(side="left", fill="x", expand=True, ipady=8)
        tk.Button(
            linha,
            text="…",
            command=self.selecionar_pasta,
            font=("Segoe UI", 11, "bold"),
            bg=CORES["card_secundario"],
            fg=CORES["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
        ).pack(side="right", padx=(6, 0), ipadx=10, ipady=5)

    def selecionar_pasta(self):
        pasta = filedialog.askdirectory(
            title="Selecionar pasta padrão",
            initialdir=self.pasta_var.get() or None,
        )
        if pasta:
            self.pasta_var.set(pasta)

    def criar_backup(self):
        destino = filedialog.askdirectory(
            title="Selecionar pasta do backup",
            initialdir=self.pasta_var.get() or None,
        )
        if not destino:
            return
        try:
            resultado = criar_backup(SESSAO.usuario, destino)
        except (PermissionError, OSError, RuntimeError, ValueError) as erro:
            messagebox.showerror("Backup", str(erro), parent=self.root)
            return
        messagebox.showinfo(
            "Backup concluído",
            (
                "O backup foi criado e passou pela verificação de integridade.\n\n"
                f"Arquivo: {resultado['arquivo']}"
            ),
            parent=self.root,
        )

    def salvar(self):
        try:
            salvas = salvar_preferencias(
                {
                    "atraso_minimo_segundos": self.delay_var.get(),
                    "categoria_padrao": CATEGORIAS_TELA[self.categoria_var.get()],
                    "periodo_padrao": PERIODOS_TELA[self.periodo_var.get()],
                    "pasta_padrao": self.pasta_var.get(),
                    "url_validacao": self.url_var.get(),
                    "tempo_sessao_minutos": self.timeout_var.get(),
                    "confirmar_exclusao_historico": self.confirmar_var.get(),
                }
            )
        except (KeyError, TypeError, ValueError) as erro:
            self.status.configure(text=str(erro), fg=CORES["danger"])
            return
        self.preferencias = salvas
        self.status.configure(text="Configurações salvas.", fg=CORES["success"])

    def restaurar(self):
        self.preferencias = dict(PREFERENCIAS_PADRAO)
        self.delay_var.set(self.preferencias["atraso_minimo_segundos"])
        self.timeout_var.set(self.preferencias["tempo_sessao_minutos"])
        self.categoria_var.set(self._rotulo(CATEGORIAS_TELA, self.preferencias["categoria_padrao"]))
        self.periodo_var.set(self._rotulo(PERIODOS_TELA, self.preferencias["periodo_padrao"]))
        self.pasta_var.set(self.preferencias["pasta_padrao"])
        self.url_var.set(self.preferencias["url_validacao"])
        self.confirmar_var.set(self.preferencias["confirmar_exclusao_historico"])
        self.status.configure(text="Padrões carregados. Clique em salvar.", fg=CORES["warning"])

    def alterar_senha(self):
        atual = simpledialog.askstring("Segurança", "Senha atual:", show="*", parent=self.root)
        if atual is None:
            return
        nova = simpledialog.askstring(
            "Segurança",
            "Nova senha forte:",
            show="*",
            parent=self.root,
        )
        if nova is None:
            return
        confirmar = simpledialog.askstring(
            "Segurança",
            "Repita a nova senha:",
            show="*",
            parent=self.root,
        )
        if nova != confirmar:
            messagebox.showerror("Segurança", "As novas senhas não coincidem.", parent=self.root)
            return
        try:
            alterar_propria_senha(SESSAO.usuario, atual, nova)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Segurança", str(erro), parent=self.root)
            return
        messagebox.showinfo("Segurança", "Senha alterada com sucesso.", parent=self.root)
