"""Componente central_analytics_recursos.py V9.8."""
from interface.central_analytics_shared import *

class CentralAnalyticsRecursosMixin:
    def _recurso_analytics(self, parent):
        titulo = next(
            (rotulo for chave, _icone, rotulo in MENU_ANALYTICS if chave == self.secao),
            self.secao.title(),
        )
        configurar_estilos_ttk(self.root)
        self.analytics_esquema = ESQUEMAS_ANALYTICS.get(
            self.secao,
            (("nome", "Nome", "texto"), ("descricao", "Descrição", "texto"),
             ("responsavel", "Responsável", "texto"),
             ("status", "Situação", "opcoes", ("Ativo", "Inativo"))),
        )
        configuracao_secao = CONFIGURACOES_SECOES_ANALYTICS.get(
            self.secao,
            {
                "subtitulo": "Configurações persistidas e auditadas do motor analítico.",
                "acao": "+  NOVO",
                "vazio": "Registre a primeira configuração.",
            },
        )

        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            criar_botao(
                bloco,
                "?  AJUDA",
                lambda: messagebox.showinfo(
                    titulo,
                    configuracao_secao["subtitulo"],
                    parent=self.root,
                ),
                tipo="secundario",
                compacto=True,
            ).pack(side="right")
            criar_botao(
                bloco,
                configuracao_secao["acao"],
                lambda: self._novo_recurso_analytics(titulo),
                compacto=True,
            ).pack(side="right", padx=(0, 8))
            return bloco

        criar_cabecalho(
            parent,
            titulo,
            configuracao_secao["subtitulo"],
            acao=acoes,
            breadcrumb=f"MÓDULOS  /  ANALYTICS  /  {titulo.upper()}",
            etiqueta=f"OPERACIONAL {VERSAO_INTERFACE}",
        )
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=16, pady=(14, 10))
        self.analytics_total = tk.Label(
            topo,
            text="0 registro(s)",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.analytics_total.pack(side="right")
        tk.Label(
            topo,
            text="CONFIGURAÇÕES DO CONTEXTO ATUAL",
            font=("Inter", 9, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(side="left")
        area = tk.Frame(painel, bg=CORES["card"])
        area.pack(fill="both", expand=True, padx=16)
        colunas = tuple(campo[0] for campo in self.analytics_esquema) + (
            "atualizacao",
        )
        self.analytics_tabela = ttk.Treeview(
            area,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        definicoes = tuple(
            (campo[0], campo[1].upper(), 130 if campo[2] != "texto" else 200)
            for campo in self.analytics_esquema
        ) + (("atualizacao", "ATUALIZAÇÃO", 150),)
        for chave, rotulo, largura in definicoes:
            self.analytics_tabela.heading(chave, text=rotulo)
            self.analytics_tabela.column(
                chave,
                width=largura,
                anchor="w",
                stretch=chave == self.analytics_esquema[0][0],
            )
        barra = ttk.Scrollbar(
            area,
            orient="vertical",
            command=self.analytics_tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            area,
            orient="horizontal",
            command=self.analytics_tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.analytics_tabela.configure(
            yscrollcommand=barra.set,
            xscrollcommand=barra_horizontal.set,
        )
        self.analytics_tabela.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        area.grid_rowconfigure(0, weight=1)
        area.grid_columnconfigure(0, weight=1)
        self.analytics_vazio = criar_estado_vazio(
            area,
            "◇",
            f"Nenhuma configuração em {titulo}",
            configuracao_secao["vazio"],
        )
        adicionar_divisorias_treeview(
            self.analytics_tabela,
            sobreposicao=self.analytics_vazio,
        )
        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=16, pady=14)
        criar_botao(
            rodape,
            "ARQUIVAR SELECIONADO",
            self._arquivar_recurso_analytics,
            tipo="secundario",
            compacto=True,
        ).pack(side="left")
        self._carregar_recursos_analytics()

    def _carregar_recursos_analytics(self):
        resultado = listar_recursos(
            "analytics",
            self.secao,
            SESSAO.usuario,
            tamanho=200,
        )
        self.analytics_registros = resultado["registros"]
        for item in self.analytics_tabela.get_children():
            self.analytics_tabela.delete(item)
        for registro in self.analytics_registros:
            extras = registro.get("dados") or {}
            valores = []
            for chave, _rotulo, _tipo, *_configuracao in self.analytics_esquema:
                valor = extras.get(chave)
                if valor in (None, ""):
                    if chave in {"nome", "titulo"}:
                        valor = registro.get("identificacao", "")
                    elif chave == "descricao":
                        valor = registro.get("descricao", "")
                    elif chave == "responsavel":
                        valor = registro.get("responsavel", "")
                    elif chave == "status":
                        valor = registro.get("status", "")
                valores.append("" if valor is None else str(valor))
            self.analytics_tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(*valores, str(registro.get("atualizado_em") or "")[:19]),
            )
        if self.analytics_registros:
            self.analytics_vazio.place_forget()
        else:
            self.analytics_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.analytics_vazio.lift()
        self.analytics_total.configure(text=f"{resultado['total']} registro(s)")

    def _novo_recurso_analytics(self, titulo):
        janela = tk.Toplevel(self.root)
        janela.title(f"Novo · {titulo}")
        preparar_janela_secundaria(
            janela, self.root, 720, 520, minimo=(620, 470)
        )
        janela.configure(bg=CORES["bg"])
        variaveis = {}
        tk.Label(
            janela,
            text=f"Novo · {titulo}",
            font=FONTES["titulo_grande"],
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=26, pady=(22, 10))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=26)
        card = criar_card(viewport.conteudo)
        card.pack(fill="both", expand=True)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        for indice, campo_def in enumerate(self.analytics_esquema):
            chave, rotulo, tipo, *configuracao = campo_def
            grupo = tk.Frame(card, bg=CORES["card"])
            grupo.grid(
                row=indice // 2,
                column=indice % 2,
                sticky="ew",
                padx=(17, 8) if indice % 2 == 0 else (8, 17),
                pady=(12, 0),
            )
            tk.Label(
                grupo,
                text=rotulo.upper(),
                font=("Inter", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(anchor="w", pady=(0, 4))
            padrao = SESSAO.usuario.get("nome", "") if chave == "responsavel" else ""
            variavel = tk.StringVar(value=padrao)
            variaveis[chave] = variavel
            if tipo == "opcoes":
                opcoes = configuracao[0] if configuracao else ()
                campo = ttk.Combobox(
                    grupo, textvariable=variavel, values=opcoes,
                    state="readonly", style="Dark.TCombobox",
                )
                if opcoes:
                    variavel.set(opcoes[0])
            else:
                campo = tk.Entry(
                    grupo,
                    textvariable=variavel,
                    font=FONTES["texto"],
                    bg=CORES["input"],
                    fg=CORES["text"],
                    insertbackground=CORES["primary"],
                    relief="flat",
                    bd=0,
                )
            campo.pack(fill="x", ipady=7)
        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=26, pady=17)
        status = tk.Label(rodape, text="", fg=CORES["danger"], bg=CORES["bg"])
        status.pack(side="left")

        def salvar():
            extras = {chave: valor.get().strip() for chave, valor in variaveis.items()}
            primeira_chave, primeiro_rotulo, *_ = self.analytics_esquema[0]
            identificacao = extras.get(primeira_chave, "")
            if len(identificacao) < 2:
                status.configure(text=f"Preencha {primeiro_rotulo}.")
                return
            try:
                criar_recurso(
                    "analytics",
                    self.secao,
                    {
                        "identificacao": identificacao,
                        "descricao": extras.get("descricao") or extras.get("pergunta") or titulo,
                        "responsavel": extras.get("responsavel", ""),
                        "status": extras.get("status", "Ativo"),
                        "prioridade": "Média",
                        "dados": extras,
                    },
                    SESSAO.usuario,
                )
            except (PermissionError, ValueError) as erro:
                status.configure(text=str(erro))
                return
            janela.destroy()
            self._carregar_recursos_analytics()

        criar_botao(rodape, "SALVAR", salvar).pack(side="right")
        criar_botao(
            rodape,
            "CANCELAR",
            janela.destroy,
            tipo="secundario",
        ).pack(side="right", padx=(0, 8))
        janela.bind("<Escape>", lambda _evento: janela.destroy())

    def _arquivar_recurso_analytics(self):
        selecao = self.analytics_tabela.selection()
        if not selecao:
            return
        try:
            alterar_estado_recurso(
                "analytics",
                self.secao,
                int(selecao[0]),
                "Arquivado",
                SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Arquivar", str(erro), parent=self.root)
            return
        self._carregar_recursos_analytics()
