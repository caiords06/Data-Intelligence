"""Componentes visuais extraídos de interface/estoque.py na V9.7."""

from interface.estoque_shared import *  # noqa: F401,F403
from interface.estoque_shared import _formatar, _moeda, _numero


class TelaEstoqueViewsMixin:
        def _acoes_cabecalho(self, parent):
            bloco = tk.Frame(parent, bg=CORES["bg"])
            titulo = {
                "itens": "+  NOVO ITEM", "categorias": "+  CATEGORIA", "fornecedores": "+  FORNECEDOR",
                "recebimentos": "+  RECEBIMENTO", "saidas": "+  SAÍDA", "reservas": "+  RESERVA",
                "transferencias": "+  TRANSFERÊNCIA", "devolucoes": "+  DEVOLUÇÃO",
                "inventario": "+  INVENTÁRIO", "depositos": "+  DEPÓSITO", "avarias": "+  OCORRÊNCIA",
                "solicitacoes": "+  SOLICITAÇÃO", "reposicao": "↻  RECALCULAR",
            }.get(self.secao, "+  NOVA OPERAÇÃO")
            criar_botao(bloco, titulo, self._nova_operacao, compacto=True).pack(side="right")
            criar_botao(bloco, "◈  ANALISAR ESTOQUE", self._mostrar_analise, tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
            return bloco

        def _cabecalho(self, titulo, subtitulo, *, acoes=True):
            criar_cabecalho(
                self.conteudo, titulo, subtitulo,
                acao=self._acoes_cabecalho if acoes else None,
                breadcrumb=f"MÓDULOS  /  ESTOQUE  /  {titulo.upper()}", etiqueta="ESTOQUE 2.0",
            )

        def _visao(self):
            self._cabecalho("Gestão de estoque", "Central de materiais, produtos, ativos, rastreabilidade, inventário e logística interna.")
            resumo = resumo_estoque(SESSAO.usuario)
            metricas = (
                ("ITENS CADASTRADOS", resumo["itens"], "□", "SKUs ativos no contexto"),
                ("UNIDADES FÍSICAS", _numero(resumo["unidades"]), "▦", "Saldo físico consolidado"),
                ("VALOR DO ESTOQUE", _moeda(resumo["valor_centavos"]), "$", "Custo médio × saldo"),
                ("ITENS CRÍTICOS", resumo["criticos"], "!", "Abaixo do estoque mínimo"),
                ("SEM ESTOQUE", resumo["zerados"], "×", "Sem disponibilidade"),
                ("RESERVADAS", _numero(resumo["reservadas"]), "○", "Separadas para demandas"),
                ("LOTES VENCENDO", resumo["vencendo"], "◷", "Próximos 30 dias"),
                ("ALERTAS ABERTOS", resumo["alertas"], "!", "Exigem acompanhamento"),
            )
            renderizar_metricas(self.conteudo, metricas, cor=COR_ESTOQUE)
            self._atalhos()
            self._fluxo(resumo)
            self._painel_alertas()

        def _atalhos(self):
            renderizar_acessos_rapidos(
                self.conteudo,
                (
                    ("↓", "Entrada de itens", "Receber, conferir e armazenar.", lambda: self._nova_entrada("Entrada")),
                    ("↑", "Saída de itens", "Separar, consumir ou expedir.", self._nova_saida),
                    ("↔", "Transferir estoque", "Origem, trânsito e destino.", self._nova_transferencia),
                    ("✓", "Iniciar inventário", "Contagem cega e divergências.", self._novo_inventario),
                    ("▣", "Ler código", "Consultar por SKU, barras ou QR.", self._scanner),
                ),
                cor=COR_ESTOQUE,
                descricao="Operações recorrentes de armazenagem e logística interna.",
            )

        def _fluxo(self, resumo):
            card = criar_card(self.conteudo); card.pack(fill="x", pady=(13, 0))
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=17, pady=15)
            criar_titulo_secao(interior, "Fluxo de movimentação", "Cada etapa abre as operações correspondentes.")
            grade = GradeResponsiva(interior, max_colunas=5, largura_minima=165, gap=6, bg=CORES["card"]); grade.pack(fill="x")
            etapas = (
                ("Recebimento", resumo["recebimentos"], "recebimentos"),
                ("Conferência", len([x for x in listar_operacoes(SESSAO.usuario, status="Em conferência")]), "recebimentos"),
                ("Armazenagem", resumo["entradas_mes"], "movimentacoes"),
                ("Reserva", int(round(resumo["reservadas"])), "reservas"),
                ("Expedição", resumo["saidas_mes"], "saidas"),
            )
            for nome, quantidade, destino in etapas:
                quadro = criar_card(grade, fundo=CORES["input"])
                tk.Frame(quadro, bg=COR_ESTOQUE, height=3).pack(fill="x")
                tk.Label(quadro, text=nome.upper(), font=("Inter", 8, "bold"), fg=CORES["text"], bg=CORES["input"]).pack(pady=(14, 5))
                tk.Label(quadro, text=str(quantidade), font=FONTES["titulo"], fg=COR_ESTOQUE, bg=CORES["input"]).pack()
                criar_botao(quadro, "VER ETAPA", lambda s=destino: self.abrir_secao(s), tipo="fantasma", compacto=True).pack(pady=(6, 12))
                grade.adicionar(quadro)

        def _painel_alertas(self):
            card = criar_card(self.conteudo); card.pack(fill="x", pady=(13, 0))
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=17, pady=15)
            alertas = listar_secao("alertas", SESSAO.usuario, limite=5)
            criar_titulo_secao(
                interior,
                "Pontos de atenção",
                "Alertas automáticos mais recentes.",
                acao=lambda parent: criar_botao(
                    parent,
                    "VER TODOS",
                    lambda: self.abrir_secao("alertas"),
                    tipo="fantasma",
                    compacto=True,
                ),
            )
            if not alertas:
                tk.Label(interior, text="✓ Nenhum alerta aberto no contexto atual.", font=FONTES["texto"], fg=CORES["success"], bg=CORES["card"]).pack(anchor="w", pady=8)
            for alerta in alertas:
                tk.Label(interior, text=f"• {alerta['titulo']}: {alerta['mensagem']}", font=FONTES["texto"], fg=CORES["danger_muted"] if alerta["severidade"] == "Crítico" else CORES["warning"], bg=CORES["card"], anchor="w", justify="left", wraplength=1000).pack(fill="x", pady=3)

        def _dados_secao(self):
            if self.secao == "itens":
                return listar_itens(SESSAO.usuario, por_pagina=200)["registros"], (
                    ("codigo", "Código", 105), ("nome", "Item / produto", 230),
                    ("categoria_nome", "Categoria", 125), ("fisico", "Físico", 80),
                    ("reservado", "Reservado", 85), ("disponivel", "Disponível", 90),
                    ("estoque_minimo", "Mínimo", 75), ("status", "Status", 85),
                )
            if self.secao == "categorias":
                return listar_catalogos(SESSAO.usuario)["categorias"], (("codigo", "Código", 130), ("nome", "Categoria", 260), ("descricao", "Descrição", 340), ("ativo", "Ativa", 80))
            if self.secao == "fornecedores":
                return listar_catalogos(SESSAO.usuario)["fornecedores"], (("nome", "Fornecedor", 230), ("documento", "Documento", 140), ("email", "E-mail", 220), ("prazo_medio_dias", "Prazo", 80), ("avaliacao", "Avaliação", 90))
            if self.secao == "patrimonio":
                return listar_secao("patrimonio", SESSAO.usuario), (("patrimonio", "Patrimônio", 125), ("numero_serie", "Número de série", 155), ("item_nome", "Ativo", 210), ("colaborador_nome", "Responsável", 170), ("deposito_nome", "Local", 140), ("garantia_ate", "Garantia", 105), ("status", "Status", 100))
            if self.secao == "movimentacoes":
                return listar_movimentacoes(SESSAO.usuario), (("numero", "Movimentação", 155), ("criado_em", "Data / hora", 145), ("item_nome", "Item", 210), ("tipo", "Tipo", 145), ("quantidade", "Quantidade", 95), ("deposito_nome", "Depósito", 140), ("usuario_nome", "Usuário", 130))
            if self.secao in {"recebimentos", "saidas", "transferencias", "devolucoes"}:
                tipos = {"recebimentos": ("Entrada", "Recebimento de compra"), "saidas": ("Saída", "Consumo interno"), "transferencias": ("Transferência",), "devolucoes": ("Devolução ao estoque", "Devolução ao fornecedor")}[self.secao]
                registros = [x for x in listar_operacoes(SESSAO.usuario) if x["tipo"] in tipos]
                return registros, (("numero", "Operação", 155), ("tipo", "Tipo", 150), ("deposito_origem", "Origem", 145), ("deposito_destino", "Destino", 145), ("itens", "Itens", 65), ("unidades", "Unidades", 80), ("etapa", "Etapa", 120), ("status", "Status", 130))
            if self.secao == "reservas":
                return listar_reservas(SESSAO.usuario), (("numero", "Reserva", 150), ("item_nome", "Item", 220), ("deposito_nome", "Depósito", 150), ("quantidade", "Quantidade", 95), ("finalidade", "Finalidade", 260), ("expira_em", "Expira", 105), ("status", "Status", 95))
            if self.secao == "inventario":
                return listar_inventarios(SESSAO.usuario), (("numero", "Inventário", 160), ("tipo", "Tipo", 130), ("deposito_nome", "Depósito", 170), ("itens", "Itens", 70), ("divergencias", "Divergências", 100), ("etapa", "Etapa", 110), ("status", "Status", 135))
            if self.secao == "depositos":
                return listar_secao("depositos", SESSAO.usuario), (("codigo", "Código", 110), ("nome", "Depósito", 220), ("tipo", "Tipo", 140), ("endereco", "Endereço", 260), ("capacidade", "Capacidade", 100), ("responsavel_nome", "Responsável", 140), ("ativo", "Ativo", 70))
            if self.secao == "lotes":
                return listar_secao("lotes", SESSAO.usuario), (("numero", "Lote", 130), ("item_nome", "Item", 220), ("fabricacao", "Fabricação", 105), ("validade", "Validade", 105), ("quantidade_original", "Original", 85), ("quantidade_restante", "Restante", 85), ("status", "Status", 120))
            if self.secao == "avarias":
                return listar_secao("avarias", SESSAO.usuario), (("numero", "Ocorrência", 150), ("tipo", "Tipo", 110), ("item_nome", "Item", 210), ("deposito_nome", "Depósito", 140), ("quantidade", "Quantidade", 90), ("motivo", "Motivo", 250), ("destino", "Destino", 110), ("status", "Status", 90))
            if self.secao == "reposicao":
                calcular_reposicao(SESSAO.usuario)
                return listar_secao("reposicao", SESSAO.usuario), (("item_nome", "Item", 220), ("deposito_nome", "Depósito", 150), ("saldo_disponivel", "Disponível", 95), ("cobertura_dias", "Cobertura/dias", 110), ("quantidade_sugerida", "Sugestão", 95), ("justificativa", "Justificativa", 280), ("status", "Status", 100))
            if self.secao == "alertas":
                gerar_alertas_estoque(SESSAO.usuario)
                return listar_secao("alertas", SESSAO.usuario), (("severidade", "Severidade", 100), ("tipo", "Tipo", 130), ("item_nome", "Item", 200), ("deposito_nome", "Depósito", 140), ("mensagem", "Mensagem", 390), ("status", "Status", 90), ("criado_em", "Criado em", 145))
            if self.secao == "solicitacoes":
                return listar_secao("solicitacoes", SESSAO.usuario), (("numero", "Solicitação", 155), ("solicitante_nome", "Solicitante", 150), ("item_nome", "Item", 220), ("quantidade", "Quantidade", 90), ("prioridade", "Prioridade", 90), ("justificativa", "Justificativa", 250), ("status", "Status", 105))
            return [], ()

        def _secao_operacional(self):
            self._cabecalho(ROTULOS[self.secao], SUBTITULOS.get(self.secao, "Operação especializada do Estoque 2.0."))
            filtros = tk.Frame(self.conteudo, bg=CORES["bg"]); filtros.pack(fill="x", pady=(0, 10))
            pesquisa = criar_campo_pesquisa(
                filtros, placeholder="Pesquisar nesta seção...", cor_cursor=COR_ESTOQUE,
                ao_alterar=self._preencher_tabela,
            )
            pesquisa.pack(side="left", fill="x", expand=True, ipady=8)
            criar_botao(filtros, "ATUALIZAR", lambda: self.abrir_secao(self.secao), tipo="fantasma", compacto=True).pack(side="right", padx=(8, 0))
            self.registros, colunas = self._dados_secao()
            card = criar_card(self.conteudo); card.pack(fill="both", expand=True)
            area = tk.Frame(card, bg=CORES["input"]); area.pack(fill="both", expand=True, padx=1, pady=1)
            self.tabela = ttk.Treeview(area, columns=[x[0] for x in colunas], show="headings", height=20, style="Dark.Treeview")
            for chave, titulo, largura in colunas:
                self.tabela.heading(chave, text=titulo); self.tabela.column(chave, width=largura, minwidth=55, anchor="w", stretch=True)
            barra_y = ttk.Scrollbar(area, orient="vertical", command=self.tabela.yview, style="Dark.Vertical.TScrollbar")
            barra_x = ttk.Scrollbar(area, orient="horizontal", command=self.tabela.xview, style="Dark.Horizontal.TScrollbar")
            self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
            area.grid_rowconfigure(0, weight=1)
            area.grid_columnconfigure(0, weight=1)
            self.tabela.grid(row=0, column=0, sticky="nsew")
            barra_y.grid(row=0, column=1, sticky="ns")
            barra_x.grid(row=1, column=0, sticky="ew")
            adicionar_divisorias_treeview(self.tabela, cor=CORES["border"])
            self.estado_vazio = criar_estado_vazio(area, "▣", f"Nenhum registro em {ROTULOS[self.secao]}", "Utilize a ação contextual para iniciar esta operação.", cor=COR_ESTOQUE)
            self._preencher_tabela()
            if self.secao == "itens":
                self.editor_grade = EditorGrade(
                    self.tabela, colunas_editaveis={"nome", "estoque_minimo", "status"},
                    salvar=self._salvar_edicao_item, parent=self.root, titulo="Itens de estoque",
                )
                barra_grade = tk.Frame(card, bg=CORES["card"]); barra_grade.pack(fill="x", padx=12, pady=(5,8))
                tk.Label(barra_grade, text="Duplo clique em item, mínimo ou status para editar.", bg=CORES["card"], fg=CORES["text_muted"], font=FONTES["micro"]).pack(side="left")
                criar_botao(barra_grade, "XLSX", lambda: self.editor_grade.exportar_xlsx(), tipo="fantasma", compacto=True).pack(side="right", padx=(5,0))
                criar_botao(barra_grade, "CSV", lambda: self.editor_grade.exportar_csv(), tipo="fantasma", compacto=True).pack(side="right")
            self._barra_acoes()

        def _salvar_edicao_item(self, iid, coluna, valor):
            atualizar_item(int(str(iid).split("-")[0]), {coluna: valor}, SESSAO.usuario)

        def _preencher_tabela(self, termo=""):
            if not self.tabela: return
            for item in self.tabela.get_children(): self.tabela.delete(item)
            termo = termo.strip().lower()
            for registro in self.registros:
                if termo and termo not in " ".join(str(v).lower() for v in registro.values()): continue
                iid = str(registro.get("id") or registro.get("item_id") or len(self.tabela.get_children()) + 1)
                if self.tabela.exists(iid): iid = f"{iid}-{len(self.tabela.get_children())}"
                self.tabela.insert("", "end", iid=iid, values=tuple(_formatar(registro.get(c), c) for c in self.tabela["columns"]))
            if self.tabela.get_children(): self.estado_vazio.place_forget()
            else:
                self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
                self.estado_vazio.lift()

        def _selecionado(self):
            if self.tabela is None or not self.tabela.selection():
                messagebox.showwarning("Estoque", "Selecione um registro.", parent=self.root); return None
            iid = self.tabela.selection()[0]
            try: return int(iid.split("-")[0])
            except ValueError: return None

        def _barra_acoes(self):
            linha = tk.Frame(self.conteudo, bg=CORES["bg"]); linha.pack(fill="x", pady=(10, 0))
            if self.secao == "itens":
                criar_botao(linha, "VER FICHA", self._ver_item, tipo="secundario", compacto=True).pack(side="left")
                criar_botao(linha, "EDITAR PARÂMETROS", self._editar_item, tipo="fantasma", compacto=True).pack(side="left", padx=5)
            if self.secao in {"recebimentos", "saidas", "devolucoes"}:
                criar_botao(linha, "CONFERIR", self._conferir_selecionada, tipo="fantasma", compacto=True).pack(side="left")
                criar_botao(linha, "CONFIRMAR", self._confirmar_selecionada, tipo="sucesso", compacto=True).pack(side="left", padx=5)
                criar_botao(linha, "CANCELAR", self._cancelar_selecionada, tipo="perigo", compacto=True).pack(side="left")
            if self.secao == "transferencias":
                criar_botao(linha, "APROVAR", lambda: self._aprovar_operacao(True), tipo="sucesso", compacto=True).pack(side="left")
                criar_botao(linha, "CONFIRMAR SAÍDA", self._confirmar_selecionada, tipo="secundario", compacto=True).pack(side="left", padx=5)
                criar_botao(linha, "RECEBER", self._receber_transferencia, tipo="aviso", compacto=True).pack(side="left")
            if self.secao == "reservas":
                criar_botao(linha, "ATENDER", lambda: self._liberar_reserva(True), tipo="sucesso", compacto=True).pack(side="left")
                criar_botao(linha, "LIBERAR", lambda: self._liberar_reserva(False), tipo="fantasma", compacto=True).pack(side="left", padx=5)
            if self.secao == "inventario":
                criar_botao(linha, "ABRIR CONTAGEM", self._abrir_inventario, tipo="secundario", compacto=True).pack(side="left")
                criar_botao(linha, "FINALIZAR", self._finalizar_inventario, tipo="sucesso", compacto=True).pack(side="left", padx=5)
                criar_botao(linha, "APROVAR AJUSTES", self._aprovar_inventario, tipo="aviso", compacto=True).pack(side="left")
            if self.secao == "depositos": criar_botao(linha, "+ ENDEREÇO", self._nova_localizacao, tipo="secundario", compacto=True).pack(side="left")
            if self.secao == "reposicao": criar_botao(linha, "ENCAMINHAR PARA COMPRAS", self._encaminhar_reposicao, tipo="sucesso", compacto=True).pack(side="left")
            if self.secao == "alertas": criar_botao(linha, "MARCAR RESOLVIDO", self._resolver_alerta, tipo="sucesso", compacto=True).pack(side="left")
            if self.secao == "solicitacoes":
                criar_botao(linha, "APROVAR", lambda: self._decidir_solicitacao(True), tipo="sucesso", compacto=True).pack(side="left")
                criar_botao(linha, "REJEITAR", lambda: self._decidir_solicitacao(False), tipo="perigo", compacto=True).pack(side="left", padx=5)

