"""Componente central_analytics_datasets.py V9.8."""
from interface.central_analytics_shared import *

class CentralAnalyticsDatasetsMixin:
    def _biblioteca_dados(self, parent):
        titulo = "Importações" if self.secao == "importacoes" else "Explorar dados"
        subtitulo = (
            "Importe, valide e armazene fontes para reutilização em novas análises."
            if self.secao == "importacoes"
            else (
                "Consulte os conjuntos de dados administrados e escolha quais serão usados "
                "pelo motor analítico."
            )
        )

        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            criar_botao(
                bloco,
                "?  AJUDA",
                lambda: messagebox.showinfo(
                    titulo,
                    "A biblioteca preserva uma cópia administrada do arquivo, "
                    "valida sua integridade e registra metadados para reutilização.",
                    parent=self.root,
                ),
                tipo="secundario",
                compacto=True,
            ).pack(side="right")
            criar_botao(
                bloco,
                "+  IMPORTAR ARQUIVO",
                self._importar_dataset,
                compacto=True,
            ).pack(side="right", padx=(0, 8))
            return bloco

        criar_cabecalho(
            parent,
            titulo,
            subtitulo,
            acao=acoes,
            breadcrumb=f"MÓDULOS  /  ANALYTICS  /  {titulo.upper()}",
            etiqueta=f"BIBLIOTECA {VERSAO_INTERFACE}",
        )
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=16, pady=(14, 10))
        self.dataset_status = tk.Label(
            topo,
            text="Carregando biblioteca...",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.dataset_status.pack(side="right")
        tk.Label(
            topo,
            text="FONTES ADMINISTRADAS",
            font=("Inter", 9, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(side="left")

        area = tk.Frame(painel, bg=CORES["card"])
        area.pack(fill="both", expand=True, padx=16)
        colunas = (
            "nome", "arquivo", "tipo", "tamanho", "registros", "colunas",
            "categoria", "status", "responsavel", "atualizacao",
        )
        self.dataset_tabela = ttk.Treeview(
            area, columns=colunas, show="headings", style="Dark.Treeview"
        )
        definicoes = (
            ("nome", "CONJUNTO", 210),
            ("arquivo", "ARQUIVO", 210),
            ("tipo", "TIPO", 65),
            ("tamanho", "TAMANHO", 90),
            ("registros", "REGISTROS", 95),
            ("colunas", "COLUNAS", 80),
            ("categoria", "CATEGORIA", 125),
            ("status", "STATUS", 90),
            ("responsavel", "RESPONSÁVEL", 150),
            ("atualizacao", "ATUALIZAÇÃO", 145),
        )
        for chave, rotulo, largura in definicoes:
            self.dataset_tabela.heading(chave, text=rotulo)
            self.dataset_tabela.column(
                chave,
                width=largura,
                minwidth=min(80, largura),
                stretch=chave in {"nome", "arquivo"},
                anchor="w",
            )
        vertical = ttk.Scrollbar(
            area,
            orient="vertical",
            command=self.dataset_tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        horizontal = ttk.Scrollbar(
            area,
            orient="horizontal",
            command=self.dataset_tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.dataset_tabela.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )
        self.dataset_tabela.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        area.grid_rowconfigure(0, weight=1, minsize=280)
        area.grid_columnconfigure(0, weight=1)
        self.dataset_vazio = criar_estado_vazio(
            area,
            "◇",
            "Nenhum conjunto de dados importado",
            "Use Importar arquivo para iniciar a biblioteca.",
        )
        adicionar_divisorias_treeview(
            self.dataset_tabela, sobreposicao=self.dataset_vazio
        )

        rodape = GradeResponsiva(
            painel,
            max_colunas=5,
            largura_minima=160,
            gap=8,
            bg=CORES["card"],
        )
        rodape.pack(fill="x", padx=16, pady=14)
        for texto, comando, tipo in (
            ("VISUALIZAR", self._visualizar_dataset, "secundario"),
            ("USAR EM NOVA ANÁLISE", self._usar_dataset, "primario"),
            ("EDITAR METADADOS", self._editar_dataset, "secundario"),
            ("SUBSTITUIR ARQUIVO", self._substituir_dataset, "secundario"),
            ("EXCLUIR", self._excluir_dataset, "perigo"),
        ):
            botao = criar_botao(
                rodape, texto, comando, tipo=tipo, compacto=True
            )
            botao.configure(anchor="center")
            rodape.adicionar(botao)
        self._carregar_datasets()

    @staticmethod
    def _tamanho_dataset(total):
        valor = float(total or 0)
        for unidade in ("B", "KB", "MB", "GB"):
            if valor < 1024 or unidade == "GB":
                return f"{valor:.1f} {unidade}" if unidade != "B" else f"{int(valor)} B"
            valor /= 1024

    def _carregar_datasets(self):
        self.datasets = listar_conjuntos(SESSAO.usuario)
        for item in self.dataset_tabela.get_children():
            self.dataset_tabela.delete(item)
        for registro in self.datasets:
            self.dataset_tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(
                    registro["nome"],
                    registro["nome_original"],
                    registro["extensao"].lstrip(".").upper(),
                    self._tamanho_dataset(registro["tamanho_bytes"]),
                    f"{int(registro['total_registros']):,}".replace(",", "."),
                    registro["total_colunas"],
                    str(registro["categoria"]).replace("_", " ").title(),
                    registro["status"],
                    registro.get("responsavel_nome") or "—",
                    str(registro["atualizado_em"])[:19],
                ),
            )
        if self.datasets:
            self.dataset_vazio.place_forget()
        else:
            self.dataset_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.dataset_vazio.lift()
        self.dataset_status.configure(text=f"{len(self.datasets)} conjunto(s)")

    def _dataset_selecionado(self):
        selecao = self.dataset_tabela.selection()
        if not selecao:
            messagebox.showinfo(
                "Biblioteca de dados",
                "Selecione um conjunto de dados para continuar.",
                parent=self.root,
            )
            return None
        return int(selecao[0])

    def _importar_dataset(self):
        caminho = filedialog.askopenfilename(
            parent=self.root,
            title="Importar conjunto de dados",
            filetypes=[
                ("Dados suportados", "*.xlsx *.xls *.csv *.json *.parquet *.txt"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return
        nome = simpledialog.askstring(
            "Nome do conjunto",
            "Informe um nome para a biblioteca:",
            initialvalue=Path(caminho).stem,
            parent=self.root,
        )
        if nome is None:
            return
        self.dataset_status.configure(text="Validando e importando...", fg=CORES["warning"])
        ator = self._ator_congelado()

        def worker():
            try:
                importar_conjunto(caminho, nome=nome, ator=ator)
                erro = None
            except Exception as excecao:
                erro = str(excecao)
            try:
                self.root.after(0, self._importacao_concluida, erro)
            except tk.TclError:
                pass
        threading.Thread(target=worker, daemon=True, name="importacao-dataset").start()

    def _importacao_concluida(self, erro=None):
        if not self._ativa:
            return
        if erro:
            self.dataset_status.configure(text="Falha na importação", fg=CORES["danger"])
            messagebox.showerror("Importação", erro, parent=self.root)
            return
        self.dataset_status.configure(text="Importação concluída", fg=CORES["success"])
        self._carregar_datasets()

    @staticmethod
    def _ator_congelado():
        ator = dict(SESSAO.usuario or {})
        ator["_empresa_id"] = SESSAO.empresa_id
        ator["_filial_id"] = SESSAO.filial_id
        return ator

    def _editar_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        atual = next(item for item in self.datasets if item["id"] == conjunto_id)
        nome = simpledialog.askstring(
            "Metadados do conjunto",
            "Nome do conjunto:",
            initialvalue=atual["nome"],
            parent=self.root,
        )
        if nome is None:
            return
        descricao = simpledialog.askstring(
            "Metadados do conjunto",
            "Descrição:",
            initialvalue=atual.get("descricao") or "",
            parent=self.root,
        )
        if descricao is None:
            return
        tags = simpledialog.askstring(
            "Metadados do conjunto",
            "Tags separadas por vírgula:",
            initialvalue=atual.get("tags") or "",
            parent=self.root,
        )
        if tags is None:
            return
        try:
            atualizar_metadados_conjunto(
                conjunto_id,
                nome=nome,
                descricao=descricao,
                tags=tags,
                ator=SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Conjunto de dados", str(erro), parent=self.root)
            return
        self.dataset_status.configure(
            text="Metadados atualizados", fg=CORES["success"]
        )
        self._carregar_datasets()

    def _substituir_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        caminho = filedialog.askopenfilename(
            parent=self.root,
            title="Substituir arquivo do conjunto",
            filetypes=[
                ("Dados suportados", "*.xlsx *.xls *.csv *.json *.parquet *.txt"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return
        if not messagebox.askyesno(
            "Substituir arquivo",
            "O novo arquivo criará uma nova versão deste conjunto. Continuar?",
            parent=self.root,
        ):
            return
        self.dataset_status.configure(
            text="Validando nova versão...", fg=CORES["warning"]
        )
        ator = self._ator_congelado()

        def worker():
            try:
                substituir_arquivo_conjunto(conjunto_id, caminho, ator)
                erro = None
            except Exception as excecao:
                erro = str(excecao)
            try:
                self.root.after(0, self._substituicao_concluida, erro)
            except tk.TclError:
                pass

        threading.Thread(
            target=worker,
            daemon=True,
            name="substituicao-dataset",
        ).start()

    def _substituicao_concluida(self, erro=None):
        if not self._ativa:
            return
        if erro:
            self.dataset_status.configure(
                text="Falha na substituição", fg=CORES["danger"]
            )
            messagebox.showerror("Substituir conjunto", erro, parent=self.root)
            return
        self.dataset_status.configure(
            text="Nova versão importada", fg=CORES["success"]
        )
        self._carregar_datasets()

    def _visualizar_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        registro = obter_conjunto(conjunto_id, SESSAO.usuario)
        messagebox.showinfo(
            registro["nome"],
            f"Arquivo: {registro['nome_original']}\n"
            f"Categoria: {registro['categoria']}\n"
            f"Registros: {registro['total_registros']}\n"
            f"Colunas: {registro['total_colunas']}\n"
            f"Versão: {registro['versao']}\n"
            f"Status: {registro['status']}",
            parent=self.root,
        )

    def _usar_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        from core.nodo import usa_servidor_remoto
        if usa_servidor_remoto():
            from services.servidor_cliente import baixar_conjunto_remoto
            registro = baixar_conjunto_remoto(conjunto_id, SESSAO.usuario)
        else:
            registro = obter_conjunto(conjunto_id, SESSAO.usuario)
        self.navegacao["nova"](
            {
                "fonte": "computador",
                "arquivos": [registro["caminho"]],
                "categoria": registro["categoria"] or "automatica",
            }
        )

    def _excluir_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        if not messagebox.askyesno(
            "Excluir conjunto",
            "Mover o conjunto selecionado para a lixeira? O histórico será preservado.",
            parent=self.root,
        ):
            return
        excluir_conjunto(conjunto_id, SESSAO.usuario)
        self._carregar_datasets()
