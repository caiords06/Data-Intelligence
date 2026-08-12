"""Tela de escolha de perfis reutilizáveis de análise."""

import tkinter as tk

from configuracoes.perfis import obter_perfis
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
)
from interface.navegacao_analytics import criar_sidebar_analytics
from interface.tema import CORES, FONTES, LAYOUT


class TelaPerfisAnalise:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        criar_sidebar_analytics(
            self.container,
            self.navegacao,
            ativo="perfis",
            voltar=self.navegacao.get("analytics"),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left", fill="both", expand=True,
            padx=LAYOUT["conteudo_padx"], pady=(24, 22),
        )
        conteudo = viewport.conteudo
        criar_cabecalho(
            conteudo,
            "Perfis de análise",
            (
                "Escolha um conjunto reutilizável de módulos. Os arquivos e a "
                "categoria ainda poderão ser ajustados na próxima tela."
            ),
            breadcrumb="MÓDULOS  /  ANALYTICS  /  PERFIS",
            etiqueta="REUTILIZÁVEIS",
        )

        grade = GradeResponsiva(
            conteudo,
            max_colunas=2,
            largura_minima=340,
            gap=12,
            bg=CORES["bg"],
        )
        grade.pack(fill="both", expand=True)
        for indice, (chave, perfil) in enumerate(obter_perfis().items()):
            card = criar_card(grade)
            grade.adicionar(card)
            tk.Label(
                card,
                text=perfil["nome"].upper(),
                font=FONTES["subtitulo"],
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
                wraplength=430,
            ).pack(anchor="w", padx=24)
            ativos = sum(perfil["configuracao"]["modulos"].values())
            tk.Label(
                card,
                text=f"{ativos} módulos ativos",
                font=("Segoe UI", 8, "bold"),
                fg=CORES["primary"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=24, pady=(14, 0))
            criar_botao(
                card,
                "USAR ESTE PERFIL",
                lambda config=perfil["configuracao"]: self.navegacao["nova"](
                    config
                ),
            ).pack(side="bottom", anchor="w", padx=24, pady=(18, 22))
