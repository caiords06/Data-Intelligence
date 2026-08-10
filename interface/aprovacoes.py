"""Fila central de aprovações humanas da plataforma."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS
from enterprise.central import (
    decidir_aprovacao,
    listar_aprovacoes,
    remover_aprovacao_da_fila,
)
from enterprise.contexto import tem_permissao
from interface.componentes import criar_botao, criar_card, criar_sidebar
from interface.tema import (
    CORES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


class TelaAprovacoes:
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
            ativo="aprovacoes",
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
            text="Aprovações centralizadas",
            font=("Segoe UI", 24, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w")
        tk.Label(
            conteudo,
            text=(
                "Compras e solicitações sensíveis permanecem pendentes até uma decisão humana autorizada."
            ),
            font=("Segoe UI", 10),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", pady=(5, 20))

        painel = criar_card(conteudo)
        painel.pack(fill="both", expand=True)
        colunas = ("modulo", "titulo", "valor", "solicitante", "data", "status")
        self.tabela = ttk.Treeview(
            painel,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        for coluna, titulo, largura in (
            ("modulo", "Módulo", 115),
            ("titulo", "Solicitação", 245),
            ("valor", "Valor", 115),
            ("solicitante", "Solicitante", 150),
            ("data", "Data", 140),
            ("status", "Status", 120),
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
        self.tabela.bind("<<TreeviewSelect>>", self._selecionou)

        self.estado_vazio = tk.Frame(painel, bg=CORES["input"])
        tk.Label(
            self.estado_vazio,
            text="✓",
            font=("Segoe UI", 28, "bold"),
            fg=CORES["success"],
            bg=CORES["input"],
        ).pack()
        adicionar_divisorias_treeview(
            self.tabela,
            sobreposicao=self.estado_vazio,
        )
        tk.Label(
            self.estado_vazio,
            text="Nenhuma aprovação disponível",
            font=("Segoe UI", 12, "bold"),
            fg=CORES["text"],
            bg=CORES["input"],
        ).pack(pady=(7, 3))
        tk.Label(
            self.estado_vazio,
            text="Novas solicitações de Compras e Administrativo aparecerão aqui.",
            font=("Segoe UI", 8),
            fg=CORES["text_sec"],
            bg=CORES["input"],
        ).pack()

        rodape = tk.Frame(conteudo, bg=CORES["bg"])
        rodape.pack(fill="x", pady=(14, 0))
        criar_botao(rodape, "ATUALIZAR", self.carregar, tipo="secundario").pack(side="left")
        self.botao_aprovar = criar_botao(rodape, "APROVAR", lambda: self.decidir("Aprovado"), tipo="sucesso")
        self.botao_aprovar.pack(side="left", padx=(10, 6))
        self.botao_rejeitar = criar_botao(rodape, "REJEITAR", lambda: self.decidir("Rejeitado"), tipo="perigo")
        self.botao_rejeitar.pack(side="left", padx=6)
        self.botao_alterar = criar_botao(rodape, "SOLICITAR ALTERAÇÃO", lambda: self.decidir("Alteração solicitada"), tipo="secundario")
        self.botao_alterar.pack(side="left", padx=6)
        self.botao_remover = criar_botao(
            rodape,
            "REMOVER DA FILA",
            self.remover,
            tipo="perigo",
        )
        self.botao_remover.pack(side="left", padx=6)
        self.status = tk.Label(
            rodape,
            text="",
            font=("Segoe UI", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        )
        self.status.pack(side="right")
        self._selecionou()

    def carregar(self):
        self.registros = listar_aprovacoes(SESSAO.usuario)
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in self.registros:
            valor = f"R$ {float(registro['valor']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(
                    MODULOS[registro["modulo"]]["nome"],
                    registro["titulo"],
                    valor,
                    registro.get("solicitante_nome") or "Usuário",
                    str(registro["criado_em"])[:19],
                    registro["status"],
                ),
            )
        if self.registros:
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0.5, rely=0.5, anchor="center")
        self.status.configure(text=f"{len(self.registros)} solicitação(ões)")
        self._selecionou()

    def _selecionou(self, _evento=None):
        selecao = self.tabela.selection()
        permitido = False
        if selecao:
            registro = next(
                (item for item in self.registros if item["id"] == int(selecao[0])),
                None,
            )
            permitido = bool(
                registro
                and registro["status"] == "Pendente"
                and tem_permissao(SESSAO.usuario, registro["modulo"], "aprovar")
            )
        estado = "normal" if permitido else "disabled"
        for botao in (self.botao_aprovar, self.botao_rejeitar, self.botao_alterar):
            botao.configure(state=estado)
        self.botao_remover.configure(
            state="normal" if selecao else "disabled"
        )

    def decidir(self, decisao):
        selecao = self.tabela.selection()
        if not selecao:
            return
        observacao = simpledialog.askstring(
            "Decisão da aprovação",
            "Observação ou justificativa:",
            parent=self.root,
        )
        if observacao is None:
            return
        if not messagebox.askyesno(
            "Confirmar decisão",
            f"Confirmar: {decisao}?",
            parent=self.root,
        ):
            return
        try:
            decidir_aprovacao(int(selecao[0]), decisao, observacao, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Aprovação", str(erro), parent=self.root)
            return
        self.carregar()
        self.status.configure(text=f"Decisão registrada: {decisao}.", fg=CORES["success"])

    def remover(self):
        selecao = self.tabela.selection()
        if not selecao:
            return
        if not messagebox.askyesno(
            "Remover da fila",
            (
                "Deseja remover a solicitação selecionada desta fila?\n\n"
                "A decisão e a auditoria serão preservadas."
            ),
            parent=self.root,
        ):
            return
        try:
            remover_aprovacao_da_fila(int(selecao[0]), SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Aprovações", str(erro), parent=self.root)
            return
        self.carregar()
        self.status.configure(
            text="Solicitação removida da fila; auditoria preservada.",
            fg=CORES["success"],
        )
