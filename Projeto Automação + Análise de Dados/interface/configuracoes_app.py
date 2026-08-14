"""Tela de preferências globais e segurança da conta atual."""

from core.versao import VERSAO_INTERFACE
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.autenticacao import alterar_propria_senha
from auth.sessao import SESSAO
from core.nodo import usa_servidor_remoto
from configuracoes.preferencias import (
    PREFERENCIAS_PADRAO,
    carregar_preferencias,
    salvar_preferencias,
)
from services.backups import criar_backup
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_cabecalho,
    criar_sidebar,
)
from interface.gerenciador_tema import aplicar_tema
from interface.icones import icone
from interface.tema import CORES, LAYOUT, configurar_estilos_ttk

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
            "Configurações da aplicação",
            (
                "Preferências globais, comportamento da interface e segurança da conta. "
                "Estas opções não alteram o motor da análise atual."
            ),
            breadcrumb="GESTÃO  /  CONFIGURAÇÕES",
            etiqueta=f"PREFERÊNCIAS {VERSAO_INTERFACE}",
        )

        grade = GradeResponsiva(
            conteudo,
            max_colunas=2,
            largura_minima=390,
            gap=18,
        )
        grade.pack(fill="both", expand=True)
        esquerda = self._card(grade, "EXPERIÊNCIA E PADRÕES")
        direita = self._card(grade, "FONTES E SEGURANÇA")
        grade.adicionar(esquerda)
        grade.adicionar(direita)

        self.tema_var = tk.StringVar(
            value="Escuro tecnológico" if self.preferencias.get("tema_interface") == "escuro" else "Claro suave"
        )
        self._campo_tema(esquerda)

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
            font=("Inter", 9),
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
            font=("Inter", 9, "bold"),
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
                font=("Inter", 9, "bold"),
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
                font=("Inter", 9, "bold"),
                bg=CORES["card_secundario"],
                fg=CORES["text"],
                activebackground=CORES["card_hover"],
                activeforeground=CORES["text"],
                relief="flat",
                bd=0,
                cursor="hand2",
            ).pack(anchor="w", padx=22, pady=(10, 0), ipadx=10, ipady=7)
            if usa_servidor_remoto():
                tk.Button(
                    direita,
                    text="ARQUIVOS DO SERVIDOR CORPORATIVO",
                    command=self.abrir_servidor_corporativo,
                    font=("Inter", 9, "bold"),
                    bg=CORES["primary"],
                    fg="#FFFFFF",
                    activebackground=CORES["primary_hover"],
                    activeforeground="#FFFFFF",
                    relief="flat", bd=0, cursor="hand2",
                ).pack(anchor="w", padx=22, pady=(10, 0), ipadx=10, ipady=7)

        rodape = tk.Frame(conteudo, bg=CORES["bg"])
        rodape.pack(fill="x", pady=(16, 0))
        tk.Button(
            rodape,
            text="SALVAR CONFIGURAÇÕES",
            command=self.salvar,
            font=("Inter", 9, "bold"),
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
            font=("Inter", 9, "bold"),
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
            font=("Inter", 9),
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
            font=("Inter", 10, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=22, pady=(22, 16))
        return card

    def _rotulo_campo(self, parent, texto):
        tk.Label(
            parent,
            text=texto,
            font=("Inter", 9, "bold"),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=22, pady=(10, 5))

    def _campo_tema(self, parent):
        self._rotulo_campo(parent, "Aparência")
        linha = tk.Frame(parent, bg=CORES["card"])
        linha.pack(fill="x", padx=22, pady=(0, 4))
        opcoes = ("Escuro tecnológico", "Claro suave")
        ttk.Combobox(
            linha, textvariable=self.tema_var, values=opcoes, state="readonly",
            font=("Inter", 10), style="App.TCombobox",
        ).pack(side="left", fill="x", expand=True, ipady=4)
        tk.Label(
            linha, text=icone("tema_escuro") + " / " + icone("tema_claro"),
            font=("Segoe UI Symbol", 11), fg=CORES["primary"], bg=CORES["card"],
        ).pack(side="right", padx=(10, 2))
        tk.Label(
            parent,
            text="O tema é salvo no seu perfil corporativo e aplicado em todas as telas.",
            font=("Inter", 8), fg=CORES["text_muted"], bg=CORES["card"],
            justify="left", wraplength=330,
        ).pack(anchor="w", padx=22, pady=(2, 8))

    def _campo_spin(self, parent, texto, variavel, minimo, maximo):
        self._rotulo_campo(parent, texto)
        tk.Spinbox(
            parent,
            from_=minimo,
            to=maximo,
            textvariable=variavel,
            font=("Inter", 10),
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
            font=("Inter", 10),
            style="App.TCombobox",
        ).pack(fill="x", padx=22, ipady=4)

    def _campo_texto(self, parent, texto, variavel):
        self._rotulo_campo(parent, texto)
        tk.Entry(
            parent,
            textvariable=variavel,
            font=("Inter", 10),
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
            font=("Inter", 10),
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
            font=("Inter", 11, "bold"),
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
        remoto = usa_servidor_remoto()
        destino = None
        if not remoto:
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

        if remoto:
            tamanho = int(resultado.get("tamanho_bytes") or 0)
            tamanho_texto = (
                f"{tamanho / 1024 / 1024:.2f} MB"
                if tamanho >= 1024 * 1024
                else f"{tamanho / 1024:.1f} KB"
            )
            mensagem = (
                "O backup foi criado e verificado no Servidor Corporativo.\n\n"
                f"Tamanho: {tamanho_texto}\n"
                f"SHA-256: {resultado.get('hash_sha256', '—')}\n\n"
                "Use ‘Arquivos do Servidor Corporativo’ para consultar os backups centrais."
            )
        else:
            mensagem = (
                "O backup foi criado e passou pela verificação de integridade.\n\n"
                f"Arquivo: {resultado['arquivo']}"
            )
        messagebox.showinfo("Backup concluído", mensagem, parent=self.root)

    def abrir_servidor_corporativo(self):
        try:
            from interface.servidor_corporativo import JanelaServidorCorporativo
            JanelaServidorCorporativo(self.root)
        except (PermissionError, ValueError, ConnectionError) as erro:
            messagebox.showerror("Servidor corporativo", str(erro), parent=self.root)

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
                    "tema_interface": "escuro" if self.tema_var.get() == "Escuro tecnológico" else "claro",
                }
            )
        except (KeyError, TypeError, ValueError) as erro:
            self.status.configure(text=str(erro), fg=CORES["danger"])
            return
        self.preferencias = salvas
        tema_anterior = "claro" if self.tema_var.get() == "Claro suave" else "escuro"
        aplicar_tema(tema_anterior, self.root)
        # Recria a tela porque widgets Tk clássicos capturam as cores no momento
        # da construção. O roteador garante uma troca limpa e sem artefatos.
        callback = self.navegacao.get("configuracoes")
        if callable(callback):
            callback()
            return
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
        self.tema_var.set("Escuro tecnológico" if self.preferencias.get("tema_interface") == "escuro" else "Claro suave")
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
