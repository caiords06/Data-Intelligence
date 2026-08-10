"""Central de alertas e notificações autorizadas."""

import tkinter as tk
from tkinter import messagebox, ttk

from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS
from enterprise.central import listar_notificacoes, marcar_notificacao_lida
from interface.componentes import criar_botao, criar_card, criar_sidebar
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
            ativo="inicio",
            rodape_texto="←   Voltar ao cockpit",
            rodape_comando=self.navegacao.get("inicio"),
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
            text="Central de notificações",
            font=("Segoe UI", 24, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w")
        tk.Label(
            conteudo,
            text="Alertas dos módulos que seu perfil está autorizado a consultar.",
            font=("Segoe UI", 10),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", pady=(5, 20))

        painel = criar_card(conteudo)
        painel.pack(fill="both", expand=True)
        colunas = ("nivel", "modulo", "titulo", "mensagem", "data", "estado")
        self.tabela = ttk.Treeview(
            painel,
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
            painel,
            orient="vertical",
            command=self.tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        barra.pack(side="right", fill="y", padx=(0, 16), pady=16)
        adicionar_divisorias_treeview(self.tabela)

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
