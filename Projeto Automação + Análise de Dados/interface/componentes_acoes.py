"""Ações de cabeçalho compartilhadas V9.8."""
from collections.abc import Callable
import tkinter as tk

def _montar_acao(area, acao):
    """Monta ações no pai correto sem tentar reparentear widgets Tk.

    A API preferida recebe ``lambda parent: widget``. Widgets antigos ainda
    são aceitos por compatibilidade e são empacotados com ``in_``.
    """
    if acao is None:
        return
    if callable(acao) and not isinstance(acao, tk.Misc):
        resultado = acao(area)
        if isinstance(resultado, tk.Misc) and not resultado.winfo_manager():
            resultado.pack(side="right")
        return
    if isinstance(acao, tk.Misc):
        acao.pack(in_=area, side="right")
