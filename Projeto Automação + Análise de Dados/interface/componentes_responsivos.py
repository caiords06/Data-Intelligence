"""Containers responsivos compartilhados da interface V9.8."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from interface.tema import CORES

class AreaRolavel(tk.Frame):
    """Viewport vertical com barra na borda e margem apenas no conteúdo.

    O ``padx`` informado em ``pack()`` é convertido em recuo do conteúdo
    dentro do canvas. Assim, cards e textos preservam a margem visual sem
    afastar a barra de rolagem da extremidade direita da janela.
    """

    def __init__(self, parent, *, bg=None, **kwargs):
        fundo = bg or CORES["bg"]
        super().__init__(parent, bg=fundo, **kwargs)
        self.canvas = tk.Canvas(
            self,
            bg=fundo,
            bd=0,
            highlightthickness=0,
            yscrollincrement=28,
        )
        self.barra = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.conteudo = tk.Frame(self.canvas, bg=fundo)
        self._conteudo_padx = 0
        self._janela = self.canvas.create_window(
            (0, 0), window=self.conteudo, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self._ao_rolar_canvas)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.conteudo.bind("<Configure>", self._sincronizar, add="+")
        self.canvas.bind("<Configure>", self._sincronizar, add="+")
        self.canvas.bind("<Enter>", self._ativar_roda)
        self.canvas.bind("<Leave>", self._desativar_roda)
        self.bind("<Destroy>", self._ao_destruir, add="+")

    def pack(self, cnf=None, **kwargs):
        """Mantém ``pady`` externo e transforma ``padx`` em margem interna."""
        opcoes = {}
        if cnf:
            opcoes.update(cnf)
        opcoes.update(kwargs)
        padx = opcoes.pop("padx", 0)
        try:
            self._conteudo_padx = max(0, int(float(padx)))
        except (TypeError, ValueError):
            try:
                self._conteudo_padx = max(0, self.winfo_pixels(padx))
            except tk.TclError:
                self._conteudo_padx = 0
        resultado = super().pack(**opcoes)
        self.after_idle(self._sincronizar)
        return resultado

    def _sincronizar(self, _evento=None):
        try:
            largura = max(
                1,
                self.canvas.winfo_width() - (self._conteudo_padx * 2),
            )
            self.canvas.coords(self._janela, self._conteudo_padx, 0)
            self.canvas.itemconfigure(self._janela, width=largura)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self._atualizar_visibilidade_barra()
        except tk.TclError:
            return

    def _ao_rolar_canvas(self, primeiro, ultimo):
        try:
            if not self._widgets_disponiveis():
                return
            self.barra.set(primeiro, ultimo)
            self._atualizar_visibilidade_barra(float(primeiro), float(ultimo))
        except tk.TclError:
            return

    def _widgets_disponiveis(self):
        """Evita callbacks tardios apontando para widgets já destruídos.

        ``bind_all`` permanece ativo até recebermos ``Leave`` ou ``Destroy``.
        Em uma navegação rápida, o Windows pode entregar um evento de roda
        depois que a tela anterior já foi destruída. Consultar ``winfo`` nesse
        instante gerava ``bad window path name``. Toda rolagem passa agora por
        esta guarda e é silenciosamente descartada quando a área não existe.
        """
        try:
            return bool(
                self.winfo_exists()
                and self.canvas.winfo_exists()
                and self.barra.winfo_exists()
            )
        except tk.TclError:
            return False

    def _atualizar_visibilidade_barra(self, primeiro=None, ultimo=None):
        try:
            if not self._widgets_disponiveis():
                return
            if primeiro is None or ultimo is None:
                primeiro, ultimo = self.canvas.yview()
            # A comparação geométrica evita o estado em que o canvas aceita a
            # roda, mas a barra permanece invisível após uma troca de tela/DPI.
            altura_conteudo = max(
                self.conteudo.winfo_reqheight(),
                int((self.canvas.bbox("all") or (0, 0, 0, 0))[3]),
            )
            altura_viewport = max(1, self.canvas.winfo_height())
            precisa = altura_conteudo > altura_viewport + 2
            if precisa and not self.barra.winfo_ismapped():
                self.barra.pack(side="right", fill="y")
            elif not precisa and self.barra.winfo_ismapped():
                self.barra.pack_forget()
        except tk.TclError:
            return

    def _ativar_roda(self, _evento=None):
        if not self._widgets_disponiveis():
            return
        try:
            self.canvas.bind_all("<MouseWheel>", self._rolar)
            self.canvas.bind_all("<Button-4>", self._rolar_linux)
            self.canvas.bind_all("<Button-5>", self._rolar_linux)
            self.canvas.bind_all("<Prior>", self._rolar_pagina)
            self.canvas.bind_all("<Next>", self._rolar_pagina)
        except tk.TclError:
            return

    def _desativar_roda(self, _evento=None):
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Prior>", "<Next>"):
            try:
                self.canvas.unbind_all(evento)
            except tk.TclError:
                return

    def _ao_destruir(self, evento):
        if evento.widget is self:
            self._desativar_roda()

    def _rolar(self, evento):
        try:
            if not self._widgets_disponiveis():
                return "break"
            if self.barra.winfo_ismapped():
                self.canvas.yview_scroll(-1 if evento.delta > 0 else 1, "units")
        except tk.TclError:
            return "break"
        return "break"

    def _rolar_linux(self, evento):
        try:
            if not self._widgets_disponiveis():
                return "break"
            if self.barra.winfo_ismapped():
                self.canvas.yview_scroll(-1 if evento.num == 4 else 1, "units")
        except tk.TclError:
            return "break"
        return "break"

    def _rolar_pagina(self, evento):
        try:
            if not self._widgets_disponiveis():
                return "break"
            if self.barra.winfo_ismapped():
                self.canvas.yview_scroll(
                    -1 if evento.keysym == "Prior" else 1,
                    "pages",
                )
        except tk.TclError:
            return "break"
        return "break"

class GradeResponsiva(tk.Frame):
    """Grade que reorganiza filhos por breakpoint, sem recriá-los."""

    def __init__(
        self,
        parent,
        *,
        max_colunas=4,
        largura_minima=245,
        gap=10,
        bg=None,
        **kwargs,
    ):
        super().__init__(parent, bg=bg or parent.cget("bg"), **kwargs)
        self.max_colunas = max(1, int(max_colunas))
        self.largura_minima = max(140, int(largura_minima))
        self.gap = max(0, int(gap))
        self.itens = []
        self._colunas = 0
        self.bind("<Configure>", self._reorganizar, add="+")

    def adicionar(self, widget):
        self.itens.append(widget)
        self.after_idle(self._reorganizar)
        return widget

    def _reorganizar(self, _evento=None):
        if not self.itens:
            return
        largura = max(self.winfo_width(), self.winfo_reqwidth())
        colunas = max(
            1,
            min(self.max_colunas, (largura + self.gap) // (self.largura_minima + self.gap)),
        )
        if colunas == self._colunas and all(item.winfo_manager() == "grid" for item in self.itens):
            return
        for coluna in range(self.max_colunas):
            self.grid_columnconfigure(coluna, weight=0, uniform="")
        for indice, item in enumerate(self.itens):
            linha, coluna = divmod(indice, colunas)
            item.grid(
                row=linha,
                column=coluna,
                sticky="nsew",
                padx=(0, self.gap if coluna < colunas - 1 else 0),
                pady=(0, self.gap),
            )
        for coluna in range(colunas):
            self.grid_columnconfigure(coluna, weight=1, uniform="responsiva")
        self._colunas = colunas
