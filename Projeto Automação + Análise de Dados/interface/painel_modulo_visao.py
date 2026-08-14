"""Visão geral dos painéis departamentais V9.8."""
from interface.painel_modulo_shared import *

class PainelModuloVisaoMixin:
    def _visao_geral(self, parent):
        criar_cabecalho(
            parent,
            self.ui["titulo"],
            self.ui["resumo"],
            breadcrumb=f"MÓDULOS  /  {self.modulo_config['nome'].upper()}",
            etiqueta="PAINEL DEPARTAMENTAL",
        )
        self._metricas(parent)

        corpo = tk.Frame(parent, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, pady=(14, 0))
        esquerda = tk.Frame(corpo, bg=CORES["bg"])
        direita = tk.Frame(corpo, bg=CORES["bg"])

        self._acoes_rapidas(esquerda)
        self._fluxo(esquerda)
        self._acoes_modulo(direita)
        self._status_backend(direita)
        self._recursos_disponiveis(direita)

        def reorganizar(evento=None):
            largura = evento.width if evento else corpo.winfo_width()
            esquerda.grid_forget()
            direita.grid_forget()
            corpo.grid_columnconfigure(0, weight=1)
            corpo.grid_columnconfigure(1, weight=0)
            if largura >= 930:
                corpo.grid_columnconfigure(1, minsize=290)
                esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
                direita.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            else:
                esquerda.grid(row=0, column=0, columnspan=2, sticky="nsew")
                direita.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        corpo.bind("<Configure>", reorganizar, add="+")
        corpo.after_idle(reorganizar)

    def _metricas(self, parent):
        area = GradeResponsiva(parent, max_colunas=4, largura_minima=210, gap=9, bg=CORES["bg"])
        area.pack(fill="x")
        try:
            cards = list(
                calcular_resumo_modulo(self.modulo, SESSAO.usuario)["cards"][:4]
            )
        except (PermissionError, ValueError, TypeError):
            cards = []
        while len(cards) < 4:
            cards.append(("SEM DADOS", 0, "inteiro"))
        for indice, (titulo, valor, formato) in enumerate(cards):
            card = criar_metrica(
                area,
                titulo,
                self._formatar(valor, formato),
                icone=self.modulo_config["icone"],
                cor=self.cor,
                detalhe="Contexto empresarial selecionado",
            )
            area.adicionar(card)

    def _acoes_rapidas(self, parent):
        card = criar_card(parent)
        card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", padx=17, pady=15)
        criar_titulo_secao(
            interior,
            "Acesso rápido",
            "Atalhos operacionais do departamento.",
        )
        grade = GradeResponsiva(
            interior,
            max_colunas=3,
            largura_minima=215,
            gap=8,
            bg=CORES["card"],
        )
        grade.pack(fill="x")
        destinos = self.ui.get("acao_destinos", ())
        for indice, (titulo, descricao, icone) in enumerate(self.ui["acoes"]):
            destino = destinos[indice] if indice < len(destinos) else "registros"
            bloco = tk.Frame(
                grade,
                bg=CORES["card_secundario"],
                highlightthickness=1,
                highlightbackground=CORES["border_soft"],
            )
            grade.adicionar(bloco)
            tk.Label(
                bloco,
                text=icone,
                font=("Segoe UI Symbol", 14, "bold"),
                fg=self.cor,
                bg=CORES["card_secundario"],
            ).pack(anchor="w", padx=13, pady=(11, 5))
            tk.Label(
                bloco,
                text=titulo,
                font=("Inter", 9, "bold"),
                fg=CORES["text"],
                bg=CORES["card_secundario"],
            ).pack(anchor="w", padx=13)
            tk.Label(
                bloco,
                text=descricao,
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card_secundario"],
                wraplength=180,
                justify="left",
            ).pack(anchor="w", padx=13, pady=(4, 5))
            criar_botao(
                bloco,
                "ABRIR  →",
                lambda alvo=destino: self.abrir_secao(alvo),
                tipo="fantasma",
                compacto=True,
            ).pack(side="bottom", anchor="w", padx=3, pady=(0, 5))

    def _fluxo(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=17, pady=15)
        resumo = resumo_recursos(self.modulo, SESSAO.usuario)
        criar_titulo_secao(
            interior,
            self.ui["fila_titulo"],
            f"{resumo['total']} registro(s) especializado(s) no contexto atual.",
        )
        fluxo = GradeResponsiva(
            interior,
            max_colunas=5,
            largura_minima=130,
            gap=6,
            bg=CORES["card"],
        )
        fluxo.pack(fill="both", expand=True, pady=(7, 0))
        totais = [
            item["total"]
            for item in resumo["por_recurso"].values()
        ] or [0]
        for indice, etapa in enumerate(self.ui["etapas"]):
            valor = totais[indice] if indice < len(totais) else 0
            coluna = tk.Frame(
                fluxo,
                bg=CORES["input"],
                highlightthickness=1,
                highlightbackground=CORES["border_soft"],
            )
            fluxo.adicionar(coluna)
            tk.Frame(coluna, bg=self.cor, height=3).pack(fill="x")
            tk.Label(
                coluna,
                text=etapa,
                font=("Inter", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["input"],
                wraplength=105,
                justify="center",
            ).pack(pady=(15, 6), padx=5)
            tk.Label(
                coluna,
                text=str(valor),
                font=("Inter", 20, "bold"),
                fg=CORES["text"],
                bg=CORES["input"],
            ).pack()
            tk.Label(
                coluna,
                text="registro(s)",
                font=FONTES["micro"],
                fg=CORES["text_muted"],
                bg=CORES["input"],
            ).pack(pady=(0, 13))

    def _acoes_modulo(self, parent):
        card = criar_card(parent, destaque=True)
        card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=14, pady=14)
        criar_titulo_secao(
            interior,
            "Ações do painel",
            "Operações do módulo selecionado.",
        )
        if tem_permissao(SESSAO.usuario, self.modulo, "escrever"):
            criar_botao(
                interior,
                "+  NOVO REGISTRO",
                lambda: self.navegacao["registros_modulo"](self.modulo),
            ).pack(fill="x", pady=(0, 7))
        if tem_permissao(SESSAO.usuario, "analytics", "escrever"):
            criar_botao(
                interior,
                "◈  ANALISAR MÓDULO",
                lambda: self.navegacao["analisar_modulo"](self.modulo),
                tipo="secundario",
            ).pack(fill="x")

    def _status_backend(self, parent):
        card = criar_card(parent)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=15, pady=14)
        topo = tk.Frame(interior, bg=CORES["card"])
        topo.pack(fill="x")
        tk.Label(
            topo,
            text="✓",
            font=("Segoe UI Symbol", 18, "bold"),
            fg=CORES["success"],
            bg=CORES["success_soft"],
            width=3,
            height=1,
        ).pack(side="left", padx=(0, 9))
        textos = tk.Frame(topo, bg=CORES["card"])
        textos.pack(side="left", fill="x", expand=True)
        tk.Label(
            textos,
            text="Backend departamental ativo",
            font=("Inter", 9, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack(anchor="w")
        tk.Label(
            textos,
            text="Persistência, permissões e auditoria habilitadas.",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
            wraplength=190,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _recursos_disponiveis(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=15, pady=14)
        criar_titulo_secao(interior, "Recursos conectados")
        resumo = resumo_recursos(self.modulo, SESSAO.usuario)["por_recurso"]
        for chave, _icone, titulo in self.ui["menu"]:
            if chave in {"visao", "registros"}:
                continue
            quantidade = resumo.get(chave, {}).get("total", 0)
            linha = tk.Button(
                interior,
                text=f"○  {titulo}    {quantidade}",
                command=lambda destino=chave: self.abrir_secao(destino),
                font=FONTES["texto_pequeno"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                activebackground=CORES["card_hover"],
                activeforeground=CORES["text"],
                relief="flat",
                bd=0,
                anchor="w",
                cursor="hand2",
                padx=4,
                pady=4,
            )
            linha.pack(fill="x")

    def _rotulo_secao(self):
        return next(
            (
                titulo
                for chave, _icone, titulo in self.ui["menu"]
                if chave == self.secao
            ),
            self.secao.replace("_", " ").title(),
        )
