"""Busca Ctrl+K em todos os módulos autorizados."""

import tkinter as tk

from auth.sessao import SESSAO
from services.central import busca_universal
from interface.componentes import preparar_janela_secundaria
from interface.tema import CORES


class JanelaBuscaUniversal:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.resultados = []
        self.after_id = None
        self.janela = tk.Toplevel(root)
        self.janela.title("Busca universal")
        preparar_janela_secundaria(
            self.janela, root, 720, 520, minimo=(620, 420)
        )
        self.janela.configure(bg=CORES["bg"])
        self.criar_interface()

    def criar_interface(self):
        tk.Label(
            self.janela,
            text="Busca universal",
            font=("Inter", 20, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(24, 4))
        tk.Label(
            self.janela,
            text="Pesquise colaboradores, itens, lançamentos, chamados, contratos e oportunidades.",
            font=("Inter", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(0, 14))

        moldura = tk.Frame(self.janela, bg=CORES["primary"], padx=1, pady=1)
        moldura.pack(fill="x", padx=28)
        self.termo = tk.StringVar()
        entry = tk.Entry(
            moldura,
            textvariable=self.termo,
            font=("Inter", 12),
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            relief="flat",
            bd=0,
        )
        entry.pack(fill="x", padx=12, ipady=10)
        entry.bind("<KeyRelease>", self._agendar_busca)
        entry.bind("<Escape>", lambda _evento: self.janela.destroy())
        entry.focus_set()

        self.lista = tk.Listbox(
            self.janela,
            bg=CORES["input"],
            fg=CORES["text"],
            selectbackground=CORES["primary_hover"],
            selectforeground="#FFFFFF",
            relief="flat",
            bd=0,
            font=("Inter", 10),
            activestyle="none",
        )
        self.lista.pack(fill="both", expand=True, padx=28, pady=(14, 8))
        self.lista.bind("<Double-Button-1>", self.abrir_resultado)
        self.lista.bind("<Return>", self.abrir_resultado)
        self.status = tk.Label(
            self.janela,
            text="Digite ao menos dois caracteres.",
            font=("Inter", 8),
            fg=CORES["text_muted"],
            bg=CORES["bg"],
        )
        self.status.pack(anchor="w", padx=28, pady=(0, 20))

    def _agendar_busca(self, _evento=None):
        if self.after_id:
            self.janela.after_cancel(self.after_id)
        self.after_id = self.janela.after(180, self.pesquisar)

    def pesquisar(self):
        self.after_id = None
        termo = self.termo.get().strip()
        self.lista.delete(0, tk.END)
        if len(termo) < 2:
            self.resultados = []
            self.status.configure(text="Digite ao menos dois caracteres.")
            return
        self.resultados = busca_universal(termo, SESSAO.usuario)
        for item in self.resultados:
            detalhe = f"  ·  {item['detalhe']}" if item["detalhe"] else ""
            self.lista.insert(
                tk.END,
                f"{item['modulo_nome'].upper()}   |   {item['titulo']}{detalhe}",
            )
        texto = (
            f"{len(self.resultados)} resultado(s). Pressione Enter ou clique duas vezes."
            if self.resultados
            else "Nenhum resultado encontrado nas áreas autorizadas."
        )
        self.status.configure(text=texto)

    def abrir_resultado(self, _evento=None):
        selecao = self.lista.curselection()
        if not selecao:
            return
        resultado = self.resultados[int(selecao[0])]
        self.janela.destroy()
        self.navegacao["modulo"](resultado["modulo"])
