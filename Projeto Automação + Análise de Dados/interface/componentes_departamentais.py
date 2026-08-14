"""Componentes visuais reutilizáveis para workspaces departamentais.

V9.7: centraliza padrões de métricas e atalhos para impedir que cada módulo
reimplemente a mesma composição Tkinter.
"""
from __future__ import annotations

import tkinter as tk
from collections.abc import Iterable

from interface.componentes import GradeResponsiva, criar_botao, criar_card, criar_metrica, criar_titulo_secao
from interface.tema import CORES, FONTES


def renderizar_metricas(parent, metricas: Iterable[tuple], *, cor: str, max_colunas: int = 4):
    """Renderiza uma grade responsiva de KPIs departamentais."""
    grade = GradeResponsiva(parent, max_colunas=max_colunas, largura_minima=220, gap=9, bg=CORES["bg"])
    grade.pack(fill="x")
    for titulo, valor, icone, detalhe in metricas:
        grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=cor, detalhe=detalhe))
    return grade


def renderizar_acessos_rapidos(
    parent,
    itens: Iterable[tuple],
    *,
    cor: str,
    descricao: str,
    max_colunas: int = 5,
):
    """Renderiza cartões de ações rápidas com aparência uniforme."""
    card = criar_card(parent)
    card.pack(fill="x", pady=(13, 0))
    interior = tk.Frame(card, bg=CORES["card"])
    interior.pack(fill="x", padx=17, pady=15)
    criar_titulo_secao(interior, "Acesso rápido", descricao)
    grade = GradeResponsiva(interior, max_colunas=max_colunas, largura_minima=180, gap=8, bg=CORES["card"])
    grade.pack(fill="x")
    for icone, titulo, detalhe, comando in itens:
        quadro = criar_card(grade, fundo=CORES["card_secundario"])
        tk.Label(quadro, text=icone, font=("Segoe UI Symbol", 18, "bold"), fg=cor, bg=CORES["card_secundario"]).pack(anchor="w", padx=14, pady=(13, 5))
        tk.Label(quadro, text=titulo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w", padx=14)
        tk.Label(quadro, text=detalhe, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card_secundario"], wraplength=180, justify="left").pack(anchor="w", padx=14, pady=(5, 10))
        criar_botao(quadro, "ABRIR  →", comando, tipo="fantasma", compacto=True).pack(anchor="w", padx=14, pady=(0, 13))
        grade.adicionar(quadro)
    return card
