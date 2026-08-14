"""Tabela e paginação do módulo empresarial V9.8."""
from interface.modulo_empresarial_shared import *

class ModuloEmpresarialTabelaMixin:
    def _cabecalho(self, parent):
        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            if tem_permissao(SESSAO.usuario, "analytics", "escrever"):
                criar_botao(
                    bloco,
                    "◈  ANALISAR MÓDULO",
                    lambda: self.navegacao["analisar_modulo"](self.modulo),
                    tipo="secundario",
                    compacto=True,
                ).pack(side="right", padx=(8, 0))
            if tem_permissao(SESSAO.usuario, self.modulo, "escrever"):
                criar_botao(
                    bloco,
                    "+  NOVO REGISTRO",
                    self.abrir_formulario,
                    compacto=True,
                ).pack(side="right")
            if self.modulo == "estoque" and tem_permissao(
                SESSAO.usuario, "estoque", "escrever"
            ):
                criar_botao(
                    bloco,
                    "MOVIMENTAR",
                    self.abrir_movimentacao,
                    tipo="secundario",
                    compacto=True,
                ).pack(side="right", padx=(0, 8))
            return bloco
        criar_cabecalho(
            parent,
            f'{self.configuracao["icone"]}  {self.configuracao["nome"]}',
            self.configuracao["descricao"],
            acao=acoes,
            breadcrumb=(
                f"MÓDULOS  /  {self.configuracao['nome'].upper()}  /  "
                "REGISTROS OPERACIONAIS"
            ),
            etiqueta=f"CADASTRO {VERSAO_INTERFACE}",
        )

    def _tabela(self, parent):
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=18, pady=(15, 10))
        tk.Label(
            topo,
            text="REGISTROS OPERACIONAIS",
            font=("Inter", 9, "bold"),
            fg=self.configuracao["cor"],
            bg=CORES["card"],
        ).pack(side="left")
        self.status = tk.Label(
            topo,
            text="",
            font=("Inter", 8),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.status.pack(side="right")

        filtros = tk.Frame(painel, bg=CORES["card"])
        filtros.pack(fill="x", padx=18, pady=(0, 10))
        self.filtro_pesquisa = tk.StringVar()
        campo_pesquisa = tk.Entry(
            filtros,
            textvariable=self.filtro_pesquisa,
            font=("Inter", 9),
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            relief="flat",
            bd=0,
        )
        campo_pesquisa.pack(side="left", fill="x", expand=True, ipady=7)
        campo_pesquisa.bind("<Return>", lambda _evento: self.aplicar_filtros())
        criar_botao(
            filtros,
            "PESQUISAR",
            self.aplicar_filtros,
            tipo="secundario",
        ).pack(side="left", padx=(8, 0))

        self.filtro_estado = tk.StringVar(value="Ativo")
        estado = ttk.Combobox(
            filtros,
            textvariable=self.filtro_estado,
            values=("Ativo", "Arquivado", "Lixeira", "Todos"),
            state="readonly",
            width=12,
            style="Dark.TCombobox",
        )
        estado.pack(side="left", padx=(8, 0))
        estado.bind("<<ComboboxSelected>>", lambda _evento: self.aplicar_filtros())

        self.tamanho_pagina = tk.StringVar(value="50")
        tamanho = ttk.Combobox(
            filtros,
            textvariable=self.tamanho_pagina,
            values=("25", "50", "100", "200"),
            state="readonly",
            width=5,
            style="Dark.TCombobox",
        )
        tamanho.pack(side="left", padx=(8, 0))
        tamanho.bind("<<ComboboxSelected>>", lambda _evento: self.aplicar_filtros())

        area_tabela = tk.Frame(painel, bg=CORES["card"])
        area_tabela.pack(fill="both", expand=True)

        colunas = tuple(item[0] for item in self.configuracao["colunas_tabela"])
        self.tabela = ttk.Treeview(
            area_tabela,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        for chave, titulo, largura in self.configuracao["colunas_tabela"]:
            self.tabela.heading(
                chave,
                text=titulo,
                command=lambda coluna=chave: self.ordenar(coluna),
            )
            self.tabela.column(chave, width=largura, anchor="w")
        barra = ttk.Scrollbar(
            area_tabela,
            orient="vertical",
            command=self.tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            area_tabela,
            orient="horizontal",
            command=self.tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.tabela.configure(
            yscrollcommand=barra.set,
            xscrollcommand=barra_horizontal.set,
        )
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=(18, 0))
        barra.grid(row=0, column=1, sticky="ns", padx=(0, 18))
        barra_horizontal.grid(row=1, column=0, sticky="ew", padx=(18, 0))
        area_tabela.grid_rowconfigure(0, weight=1, minsize=280)
        area_tabela.grid_columnconfigure(0, weight=1)
        self.tabela.bind("<<TreeviewSelect>>", self._atualizar_acoes)

        self.estado_vazio = criar_estado_vazio(
            area_tabela,
            self.configuracao["icone"],
            "Nenhum registro neste módulo",
            "Utilize Novo registro para iniciar a operação.",
            cor=self.configuracao["cor"],
        )

        adicionar_divisorias_treeview(
            self.tabela,
            sobreposicao=self.estado_vazio,
        )

        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=18, pady=(0, 15))
        self.botao_editar = criar_botao(
            rodape,
            "EDITAR",
            self.editar_selecionado,
            tipo="secundario",
        )
        self.botao_editar.pack(side="left")
        self.botao_arquivar = criar_botao(
            rodape,
            "ARQUIVAR",
            lambda: self.mudar_estado_selecionado("Arquivado"),
            tipo="secundario",
        )
        self.botao_arquivar.pack(side="left", padx=(8, 0))
        self.botao_lixeira = criar_botao(
            rodape,
            "REMOVER",
            lambda: self.mudar_estado_selecionado("Lixeira"),
            tipo="perigo",
        )
        self.botao_lixeira.pack(side="left", padx=(8, 0))
        self.botao_restaurar = criar_botao(
            rodape,
            "RESTAURAR",
            lambda: self.mudar_estado_selecionado("Ativo"),
            tipo="sucesso",
        )
        self.botao_restaurar.pack(side="left", padx=(8, 0))

        self.botao_proxima = criar_botao(
            rodape,
            "PRÓXIMA  →",
            self.proxima_pagina,
            tipo="secundario",
        )
        self.botao_proxima.pack(side="right")
        self.label_pagina = tk.Label(
            rodape,
            text="Página 1 de 1",
            font=("Inter", 8),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.label_pagina.pack(side="right", padx=12)
        self.botao_anterior = criar_botao(
            rodape,
            "←  ANTERIOR",
            self.pagina_anterior,
            tipo="secundario",
        )
        self.botao_anterior.pack(side="right")
        self._atualizar_acoes()

    def carregar(self):
        resultado = listar_registros_paginados(
            self.modulo,
            SESSAO.usuario,
            pagina=self.pagina,
            tamanho=int(self.tamanho_pagina.get()),
            pesquisa=self.filtro_pesquisa.get(),
            estado=self.filtro_estado.get(),
            ordenar_por=self.ordenar_por,
            direcao=self.direcao,
        )
        self.registros = resultado["registros"]
        self.pagina = resultado["pagina"]
        self.paginas = resultado["paginas"]
        self.total = resultado["total"]
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in self.registros:
            valores = []
            for chave, _titulo, _largura in self.configuracao["colunas_tabela"]:
                valores.append(self._formatar_celula(chave, registro.get(chave)))
            self.tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=valores,
            )
        if self.registros:
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()

            # Garante que a mensagem fique acima das divisórias
            self.estado_vazio.lift()

        self.status.configure(text=f"{self.total} registro(s)")
        self.label_pagina.configure(text=f"Página {self.pagina} de {self.paginas}")
        self.botao_anterior.configure(
            state="normal" if self.pagina > 1 else "disabled"
        )
        self.botao_proxima.configure(
            state="normal" if self.pagina < self.paginas else "disabled"
        )
        self._atualizar_acoes()
        self._atualizar_cards()

    def aplicar_filtros(self):
        self.pagina = 1
        self.carregar()

    def ordenar(self, coluna):
        if self.ordenar_por == coluna:
            self.direcao = "ASC" if self.direcao == "DESC" else "DESC"
        else:
            self.ordenar_por = coluna
            self.direcao = "ASC"
        self.pagina = 1
        self.carregar()

    def pagina_anterior(self):
        if self.pagina > 1:
            self.pagina -= 1
            self.carregar()

    def proxima_pagina(self):
        if self.pagina < self.paginas:
            self.pagina += 1
            self.carregar()

    def _id_selecionado(self):
        selecao = self.tabela.selection()
        return int(selecao[0]) if selecao else None

    def _atualizar_acoes(self, _evento=None):
        registro_id = self._id_selecionado()
        selecionado = registro_id is not None
        pode_escrever = tem_permissao(SESSAO.usuario, self.modulo, "escrever")
        registro = next(
            (item for item in self.registros if item["id"] == registro_id),
            None,
        )
        estado_atual = (
            registro.get("estado_registro", "Ativo")
            if registro is not None
            else self.filtro_estado.get()
        )
        normal = "normal" if selecionado and pode_escrever else "disabled"
        self.botao_editar.configure(
            state=normal if estado_atual == "Ativo" else "disabled"
        )
        self.botao_arquivar.configure(
            state=normal if estado_atual == "Ativo" else "disabled"
        )
        self.botao_lixeira.configure(
            state=normal if estado_atual in {"Ativo", "Arquivado"} else "disabled"
        )
        self.botao_restaurar.configure(
            state=normal if estado_atual in {"Arquivado", "Lixeira"} else "disabled"
        )

    def _atualizar_cards(self):
        for filho in self.area_cards.winfo_children():
            filho.destroy()
        resumo = calcular_resumo_modulo(self.modulo, SESSAO.usuario)
        for indice, (titulo, valor, formato) in enumerate(resumo["cards"]):
            card = criar_card(self.area_cards)
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 8) if indice < 3 else (0, 0),
            )
            tk.Label(
                card,
                text=titulo,
                font=("Inter", 8, "bold"),
                fg=self.configuracao["cor"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=16, pady=(13, 5))
            tk.Label(
                card,
                text=self._formatar_valor(valor, formato),
                font=("Inter", 17, "bold"),
                fg=CORES["text"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=16, pady=(0, 13))
