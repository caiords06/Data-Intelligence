"""Catálogo visual de módulos e permissões da V8."""

from __future__ import annotations

import tkinter as tk

from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS, ORDEM_MODULOS
from enterprise.contexto import listar_modulos_permitidos
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
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
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(24, 20),
        )
        conteudo = viewport.conteudo
        permitidos = set(listar_modulos_permitidos(SESSAO.usuario))
        criar_cabecalho(
            conteudo,
            "Módulos empresariais",
            "Escolha uma área para acessar seu painel especializado. Módulos sem permissão permanecem visíveis para contextualizar a plataforma.",
            acao=lambda area: criar_chip(
                area,
                f"{len(permitidos)} MÓDULO(S) AUTORIZADO(S)",
                cor=CORES["success"],
                fundo=CORES["success_soft"],
            ),
            breadcrumb="CENTRAL DA APLICAÇÃO  /  MÓDULOS",
        )

        grade = GradeResponsiva(
            conteudo,
            max_colunas=4,
            largura_minima=255,
            gap=10,
            bg=CORES["bg"],
        )
        grade.pack(fill="both", expand=True)
        for indice, chave in enumerate(ORDEM_MODULOS):
            modulo = MODULOS[chave]
            autorizado = chave in permitidos
            suporte_ti = chave == "ti" and not autorizado
            acessivel = autorizado or suporte_ti
            card = criar_card(grade, destaque=chave == "analytics" and autorizado)
            grade.adicionar(card)
            card.grid_columnconfigure(0, weight=1)
            topo = tk.Frame(card, bg=CORES["card"])
            topo.grid(row=0, column=0, sticky="ew", padx=17, pady=(14, 8))
            tk.Label(
                topo,
                text=modulo["icone"],
                font=("Segoe UI Symbol", 17, "bold"),
                fg=modulo["cor"],
                bg=CORES["primary_soft"],
                width=3,
                height=2,
            ).pack(side="left")
            if suporte_ti:
                chip_texto = "SUPORTE DISPONÍVEL"
                chip_cor = CORES["primary"]
                chip_fundo = CORES["primary_soft"]
            else:
                chip_texto = "AUTORIZADO" if autorizado else "RESTRITO"
                chip_cor = CORES["success"] if autorizado else CORES["danger_muted"]
                chip_fundo = CORES["success_soft"] if autorizado else CORES["danger_soft"]
            criar_chip(
                topo,
                chip_texto,
                cor=chip_cor,
                fundo=chip_fundo,
            ).pack(side="right")
            tk.Label(
                card,
                text=modulo["nome"],
                font=("Segoe UI", 10, "bold"),
                fg=CORES["text"],
                bg=CORES["card"],
            ).grid(row=1, column=0, sticky="w", padx=17)
            descricao = tk.Label(
                card,
                text=modulo["descricao"],
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                justify="left",
                anchor="nw",
            )
            descricao.grid(row=2, column=0, sticky="nsew", padx=17, pady=(4, 10))
            card.grid_rowconfigure(2, weight=1, minsize=52)
            descricao.bind(
                "<Configure>",
                lambda evento, label=descricao: label.configure(
                    wraplength=max(120, evento.width - 4)
                ),
            )
            if acessivel:
                destino = (
                    self.navegacao.get("analytics")
                    if chave == "analytics"
                    else lambda codigo=chave: self.navegacao["modulo"](codigo)
                )
                criar_botao(
                    card,
                    "ABRIR SUPORTE  →" if suporte_ti else "ABRIR PAINEL  →",
                    destino,
                    tipo="secundario",
                    compacto=True,
                ).grid(row=3, column=0, sticky="ew", padx=17, pady=(0, 14))
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
                ).grid(row=3, column=0, sticky="ew", padx=17, pady=(0, 14))
