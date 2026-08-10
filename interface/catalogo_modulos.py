"""Catálogo visual de módulos e permissões da V7."""

from __future__ import annotations

import tkinter as tk

from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS, ORDEM_MODULOS
from enterprise.contexto import listar_modulos_permitidos
from interface.componentes import (
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_chip,
    criar_sidebar,
)
from interface.tema import CORES, FONTES, LAYOUT


class TelaCatalogoModulos:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="modulos",
            rodape_texto="Sair com segurança",
            rodape_comando=self.navegacao.get("sair"),
        )
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(24, 20),
        )
        permitidos = set(listar_modulos_permitidos(SESSAO.usuario))
        cab_acoes = tk.Frame(conteudo, bg=CORES["bg"])
        criar_chip(
            cab_acoes,
            f"{len(permitidos)} MÓDULO(S) AUTORIZADO(S)",
            cor=CORES["success"],
            fundo=CORES["success_soft"],
        ).pack(side="right")
        criar_cabecalho(
            conteudo,
            "Módulos empresariais",
            "Escolha uma área para acessar seu painel especializado. Módulos sem permissão permanecem visíveis para contextualizar a plataforma.",
            acao=cab_acoes,
            breadcrumb="CENTRAL DA APLICAÇÃO  /  MÓDULOS",
        )

        grade = tk.Frame(conteudo, bg=CORES["bg"])
        grade.pack(fill="both", expand=True)
        colunas = 4
        for indice, chave in enumerate(ORDEM_MODULOS):
            modulo = MODULOS[chave]
            autorizado = chave in permitidos
            card = criar_card(grade, destaque=chave == "analytics" and autorizado)
            card.grid(
                row=indice // colunas,
                column=indice % colunas,
                sticky="nsew",
                padx=(0, 10) if indice % colunas < colunas - 1 else 0,
                pady=(0, 10),
            )
            topo = tk.Frame(card, bg=CORES["card"])
            topo.pack(fill="x", padx=17, pady=(14, 8))
            tk.Label(
                topo,
                text=modulo["icone"],
                font=("Segoe UI Symbol", 17, "bold"),
                fg=modulo["cor"],
                bg=CORES["primary_soft"],
                width=3,
                height=2,
            ).pack(side="left")
            criar_chip(
                topo,
                "AUTORIZADO" if autorizado else "RESTRITO",
                cor=CORES["success"] if autorizado else CORES["danger_muted"],
                fundo=CORES["success_soft"] if autorizado else CORES["danger_soft"],
            ).pack(side="right")
            tk.Label(
                card,
                text=modulo["nome"],
                font=("Segoe UI", 10, "bold"),
                fg=CORES["text"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=17)
            descricao = tk.Label(
                card,
                text=modulo["descricao"],
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                justify="left",
                anchor="nw",
            )
            descricao.pack(fill="x", padx=17, pady=(4, 8))
            descricao.bind(
                "<Configure>",
                lambda evento, label=descricao: label.configure(
                    wraplength=max(120, evento.width - 4)
                ),
            )
            if autorizado:
                destino = (
                    self.navegacao.get("analytics")
                    if chave == "analytics"
                    else lambda codigo=chave: self.navegacao["modulo"](codigo)
                )
                criar_botao(
                    card,
                    "ABRIR PAINEL  →",
                    destino,
                    tipo="secundario",
                    compacto=True,
                ).pack(side="bottom", fill="x", padx=17, pady=(0, 14))
            else:
                tk.Label(
                    card,
                    text="Seu perfil não possui permissão para acessar este módulo.",
                    font=FONTES["micro"],
                    fg=CORES["danger_muted"],
                    bg=CORES["card"],
                    justify="left",
                    anchor="w",
                    wraplength=215,
                ).pack(side="bottom", fill="x", padx=17, pady=(0, 14))

        total_linhas = (len(ORDEM_MODULOS) + colunas - 1) // colunas
        for coluna in range(colunas):
            grade.grid_columnconfigure(coluna, weight=1, uniform="modulos")
        for linha in range(total_linhas):
            grade.grid_rowconfigure(linha, weight=1, uniform="linhas")
