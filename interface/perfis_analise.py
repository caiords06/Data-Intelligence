"""Tela de escolha de perfis reutilizáveis de análise."""

import tkinter as tk

from configuracoes.perfis import obter_perfis
from interface.componentes import acao_em_preparacao, criar_sidebar
from interface.tema import CORES


class TelaPerfisAnalise:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        itens = (
            ("visao", "⌂", "Dashboard", self.navegacao.get("analytics")),
            ("nova", "+", "Nova análise", self.navegacao.get("nova")),
            ("importacoes", "↓", "Importações", acao_em_preparacao("Importações")),
            ("conjuntos", "▣", "Conjuntos de dados", acao_em_preparacao("Conjuntos de dados")),
            ("relatorios", "▤", "Relatórios", acao_em_preparacao("Relatórios")),
            ("perfis", "◎", "Perfis de análise", None),
        )
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="perfis",
            itens_customizados=itens,
            titulo_customizado="ANALYTICS",
            rodape_texto="Voltar à central analítica",
            rodape_comando=self.navegacao.get("analytics"),
        )
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(side="left", fill="both", expand=True, padx=42, pady=34)

        tk.Label(
            conteudo,
            text="Perfis de análise",
            font=("Segoe UI", 24, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w")
        tk.Label(
            conteudo,
            text=(
                "Escolha um conjunto reutilizável de módulos. Os arquivos e a "
                "categoria ainda poderão ser ajustados na próxima tela."
            ),
            font=("Segoe UI", 10),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", pady=(5, 25))

        grade = tk.Frame(conteudo, bg=CORES["bg"])
        grade.pack(fill="both", expand=True)
        for indice, (chave, perfil) in enumerate(obter_perfis().items()):
            card = tk.Frame(
                grade,
                bg=CORES["card"],
                highlightthickness=1,
                highlightbackground=CORES["border"],
                width=400,
                height=220,
            )
            card.grid(
                row=indice // 2,
                column=indice % 2,
                sticky="nsew",
                padx=(0, 18) if indice % 2 == 0 else (0, 0),
                pady=(0, 18),
            )
            card.grid_propagate(False)
            tk.Label(
                card,
                text=perfil["nome"].upper(),
                font=("Segoe UI", 12, "bold"),
                fg=CORES["text"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=24, pady=(25, 8))
            tk.Label(
                card,
                text=perfil["descricao"],
                font=("Segoe UI", 9),
                fg=CORES["text_sec"],
                bg=CORES["card"],
                justify="left",
                wraplength=330,
            ).pack(anchor="w", padx=24)
            ativos = sum(perfil["configuracao"]["modulos"].values())
            tk.Label(
                card,
                text=f"{ativos} módulos ativos",
                font=("Segoe UI", 8, "bold"),
                fg=CORES["primary"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=24, pady=(14, 0))
            tk.Button(
                card,
                text="USAR ESTE PERFIL",
                font=("Segoe UI", 9, "bold"),
                bg=CORES["primary"],
                fg="#FFFFFF",
                activebackground=CORES["primary_hover"],
                activeforeground="#FFFFFF",
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda config=perfil["configuracao"]: self.navegacao["nova"](
                    config
                ),
            ).pack(anchor="w", padx=24, pady=(18, 0), ipadx=10, ipady=6)
        grade.grid_columnconfigure(0, weight=1)
        grade.grid_columnconfigure(1, weight=1)
        grade.grid_rowconfigure(0, weight=1)
        grade.grid_rowconfigure(1, weight=1)
