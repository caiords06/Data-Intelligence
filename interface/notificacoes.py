"""Central de alertas e notificações autorizadas."""

import tkinter as tk
from tkinter import messagebox, ttk

from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS
from enterprise.central import listar_notificacoes, marcar_notificacao_lida
from interface.componentes import (
    AreaRolavel, criar_botao, criar_cabecalho, criar_card,
    criar_estado_vazio, criar_sidebar,
)
from interface.tema import (
    CORES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


class TelaNotificacoes:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.registros = []
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()
        self.carregar()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="notificacoes",
            rodape_texto="←   Voltar ao cockpit",
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
            "Central de notificações",
            "Alertas globais dos módulos que seu perfil está autorizado a consultar.",
            breadcrumb="CENTRAL DA APLICAÇÃO  /  NOTIFICAÇÕES GLOBAIS",
            etiqueta="CENTRAL GLOBAL",
        )

        painel = criar_card(conteudo)
        painel.pack(fill="both", expand=True)
        area_tabela = tk.Frame(painel, bg=CORES["card"])
        area_tabela.pack(fill="both", expand=True, padx=16, pady=16)
        colunas = ("nivel", "modulo", "titulo", "mensagem", "data", "estado")
        self.tabela = ttk.Treeview(
            area_tabela,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        for coluna, titulo, largura in (
            ("nivel", "Nível", 80),
            ("modulo", "Módulo", 110),
            ("titulo", "Alerta", 190),
            ("mensagem", "Descrição", 330),
            ("data", "Data", 140),
            ("estado", "Estado", 85),
        ):
            self.tabela.heading(coluna, text=titulo)
            self.tabela.column(coluna, width=largura, anchor="w")
        barra = ttk.Scrollbar(
            area_tabela,
            orient="vertical",
            command=self.tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            area_tabela, orient="horizontal", command=self.tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.tabela.configure(
            yscrollcommand=barra.set, xscrollcommand=barra_horizontal.set
        )
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        area_tabela.grid_rowconfigure(0, weight=1, minsize=310)
        area_tabela.grid_columnconfigure(0, weight=1)
        self.estado_vazio = criar_estado_vazio(
            area_tabela,
            "◌",
            "Nenhuma notificação disponível",
            "Novos alertas autorizados aparecerão aqui.",
        )
        adicionar_divisorias_treeview(
            self.tabela, sobreposicao=self.estado_vazio
        )

        rodape = tk.Frame(conteudo, bg=CORES["bg"])
        rodape.pack(fill="x", pady=(14, 0))
        criar_botao(rodape, "ATUALIZAR", self.carregar, tipo="secundario").pack(side="left")
        criar_botao(rodape, "MARCAR COMO LIDA", self.marcar_lida).pack(side="left", padx=10)
        self.status = tk.Label(
            rodape,
            text="",
            font=("Segoe UI", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        )
        self.status.pack(side="right")

    def carregar(self):
        self.registros = listar_notificacoes(SESSAO.usuario, limite=200)
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in self.registros:
            self.tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(
                    registro["nivel"].upper(),
                    MODULOS[registro["modulo"]]["nome"],
                    registro["titulo"],
                    registro["mensagem"],
                    str(registro["criado_em"])[:19],
                    "Lida" if registro["lida"] else "Nova",
                ),
            )
        if self.registros:
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()
        self.status.configure(text=f"{len(self.registros)} notificação(ões)")

    def marcar_lida(self):
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showwarning("Notificações", "Selecione um alerta.", parent=self.root)
            return
        try:
            marcar_notificacao_lida(int(selecao[0]), SESSAO.usuario)
        except PermissionError as erro:
            messagebox.showerror("Notificações", str(erro), parent=self.root)
            return
        self.carregar()
        self.status.configure(text="Notificação marcada como lida.", fg=CORES["success"])
