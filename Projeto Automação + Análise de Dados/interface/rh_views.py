"""Componentes visuais extraídos de interface/rh.py na V9.7."""

from interface.rh_shared import *  # noqa: F401,F403
from interface.rh_shared import _formatar, _moeda


class TelaRHViewsMixin:
        def _acoes_cabecalho(self, parent):
            bloco = tk.Frame(parent, bg=CORES["bg"])
            botao = criar_botao(bloco, "+  NOVA OPERAÇÃO", self._nova_operacao, compacto=True)
            botao.pack(side="right")
            if not tem_permissao_rh(SESSAO.usuario, "criar_colaborador"):
                botao.configure(state="disabled", cursor="arrow")
            criar_botao(bloco, "◈  ANALISAR RH", self._mostrar_analise, tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
            from interface.funcionario_360 import abrir_meu_funcionario_360
            criar_botao(bloco, "◉  MEU PERFIL 360°", lambda: abrir_meu_funcionario_360(self.root), tipo="fantasma", compacto=True).pack(side="right", padx=(0, 8))
            return bloco

        def _cabecalho(self, titulo, subtitulo, *, acoes=True):
            criar_cabecalho(
                self.conteudo,
                titulo,
                subtitulo,
                acao=self._acoes_cabecalho if acoes else None,
                breadcrumb=f"MÓDULOS  /  RECURSOS HUMANOS  /  {titulo.upper()}",
                etiqueta="RH 360° · V11",
            )

        def _visao(self):
            self._cabecalho(
                "Gestão de pessoas",
                "Central de comando do ciclo completo do colaborador, da admissão ao desenvolvimento e desligamento.",
            )
            resumo = resumo_rh(SESSAO.usuario)
            metricas = (
                ("HEADCOUNT", resumo["total"], "◉", "Pessoas no contexto atual"),
                ("COLAB. ATIVOS", resumo["ativos"], "✓", "Vínculos ativos"),
                ("DEPARTAMENTOS", resumo["departamentos"], "▦", "Estrutura com pessoas alocadas"),
                ("FOLHA BASE", _moeda(resumo["folha_base"]), "$", "Salários base ativos"),
                ("PRÉ-ADMISSÕES", resumo["pre_admissoes"], "+", "Processos em preparação"),
                ("DESLIGAMENTOS", resumo["desligamentos"], "−", "Processos em andamento"),
                ("FÉRIAS PENDENTES", resumo["ferias_pendentes"], "◴", "Aguardando decisão"),
                ("TAREFAS PENDENTES", resumo["tarefas_pendentes"], "✓", "Operações do departamento"),
            )
            renderizar_metricas(self.conteudo, metricas, cor=COR_RH)
            self._atalhos()
            self._jornada(resumo)
            self._pendencias(resumo)

        def _atalhos(self):
            renderizar_acessos_rapidos(
                self.conteudo,
                (
                    ("+", "Nova admissão", "Cadastro, documentos e onboarding.", self._nova_admissao),
                    ("◴", "Planejar férias", "Saldo, conflitos e aprovação.", self._novas_ferias),
                    ("◷", "Registrar jornada", "Ponto, horas extras e atrasos.", self._novo_ponto),
                    ("$", "Abrir folha", "Competência e salários base.", self._nova_folha),
                    ("⇥", "Gerar relatório", "PDF, Excel ou CSV.", lambda: self.abrir_secao("relatorios")),
                ),
                cor=COR_RH,
                descricao="Operações recorrentes do departamento.",
            )

        def _jornada(self, resumo):
            card = criar_card(self.conteudo)
            card.pack(fill="x", pady=(13, 0))
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=17, pady=15)
            criar_titulo_secao(interior, "Jornada do colaborador", "Visão integrada das etapas de pessoas.")
            valores = {x["etapa"]: x["total"] for x in resumo["jornada"]}
            grade = GradeResponsiva(interior, max_colunas=6, largura_minima=145, gap=5, bg=CORES["card"]); grade.pack(fill="x")
            for etapa in ("Pré-admissão", "Documentação", "Onboarding", "Ativo", "Desligamento", "Desligado"):
                quadro = criar_card(grade, fundo=CORES["input"])
                tk.Frame(quadro, bg=COR_RH, height=3).pack(fill="x")
                tk.Label(quadro, text=etapa.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["input"]).pack(pady=(14, 8))
                tk.Label(quadro, text=str(valores.get(etapa, 0)), font=FONTES["display"], fg=CORES["text"], bg=CORES["input"]).pack(pady=(0, 14))
                grade.adicionar(quadro)

        def _pendencias(self, resumo):
            card = criar_card(self.conteudo, destaque=bool(resumo["documentos_vencendo"] or resumo["ferias_pendentes"]))
            card.pack(fill="x", pady=(13, 0))
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=17, pady=15)
            criar_titulo_secao(interior, "Pontos de atenção", "Pendências que exigem acompanhamento humano.")
            itens = (
                (f"{resumo['ferias_pendentes']} solicitação(ões) de férias/ausência pendente(s)", "ferias"),
                (f"{resumo['documentos_vencendo']} documento(s) vencendo nos próximos 30 dias", "documentos"),
                (f"{resumo['tarefas_pendentes']} tarefa(s) operacional(is) de RH em aberto", "admissoes"),
            )
            for texto, destino in itens:
                linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=3)
                tk.Label(linha, text="○  " + texto, font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card_secundario"]).pack(side="left", padx=12, pady=9)
                criar_botao(linha, "VER", lambda d=destino: self.abrir_secao(d), tipo="fantasma", compacto=True).pack(side="right", padx=8)

        def _secao_operacional(self):
            titulo = ROTULOS[self.secao]
            self._cabecalho(titulo, SUBTITULOS.get(self.secao, "Operação especializada de Recursos Humanos."))
            topo = criar_card(self.conteudo); topo.pack(fill="x", pady=(0, 12))
            filtros = tk.Frame(topo, bg=CORES["card"]); filtros.pack(fill="x", padx=15, pady=12)
            tk.Label(filtros, text="PESQUISAR", font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(side="left")
            self.pesquisa = tk.Entry(filtros, bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat", width=28)
            self.pesquisa.pack(side="left", padx=(8, 8), ipady=6)
            criar_botao(filtros, "APLICAR", self._filtrar_tabela, tipo="secundario", compacto=True).pack(side="left")
            self.estado_registro_rh = tk.StringVar(value=getattr(self, "_estado_rh_atual", "Ativos"))
            seletor_estado = ttk.Combobox(
                filtros, textvariable=self.estado_registro_rh,
                values=("Ativos", "Lixeira"), state="readonly", width=11,
                style="Dark.TCombobox",
            )
            seletor_estado.pack(side="left", padx=(8, 0))
            def mudar_estado(_evento=None):
                self._estado_rh_atual = self.estado_registro_rh.get()
                self.abrir_secao(self.secao)
            seletor_estado.bind("<<ComboboxSelected>>", mudar_estado)
            criar_botao(filtros, "+  NOVO", self._nova_operacao, compacto=True).pack(side="right")
            self._carregar_tabela()
            self._barra_acoes()

        def _carregar_tabela(self):
            try:
                estado = self.estado_registro_rh.get() if hasattr(self, "estado_registro_rh") else "Ativos"
                self.registros = listar_secao(self.secao, SESSAO.usuario, estado=estado)
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Recursos Humanos", str(erro), parent=self.root); self.registros = []
            painel = criar_card(self.conteudo); painel.pack(fill="both", expand=True)
            area = tk.Frame(painel, bg=CORES["input"], height=430); area.pack(fill="both", expand=True, padx=1, pady=1); area.pack_propagate(False)
            # A UI possui schema próprio e estável. Nunca derivamos colunas das
            # chaves retornadas pelo banco, evitando ordem variável e exposição de
            # campos técnicos após mudanças no backend.
            colunas = self._colunas_padrao()
            self.tabela = ttk.Treeview(area, columns=colunas, show="headings", style="Dark.Treeview")
            for coluna in colunas:
                titulo = coluna.replace("_centavos", "").replace("_", " ").upper()
                self.tabela.heading(coluna, text=titulo)
                largura = 105
                if coluna in {"nome_completo", "titulo", "motivo", "feedback", "vinculo", "observacao"}: largura = 200
                self.tabela.column(coluna, width=largura, minwidth=70, stretch=True, anchor="w")
            barra_y = ttk.Scrollbar(area, orient="vertical", command=self.tabela.yview, style="Dark.Vertical.TScrollbar")
            barra_x = ttk.Scrollbar(area, orient="horizontal", command=self.tabela.xview, style="Dark.Horizontal.TScrollbar")
            self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
            area.grid_rowconfigure(0, weight=1)
            area.grid_columnconfigure(0, weight=1)
            self.tabela.grid(row=0, column=0, sticky="nsew")
            barra_y.grid(row=0, column=1, sticky="ns")
            barra_x.grid(row=1, column=0, sticky="ew")
            for registro in self.registros:
                self.tabela.insert("", "end", iid=str(registro.get("id")), values=tuple(_formatar(registro.get(c), c) for c in colunas))
            self.estado_vazio = criar_estado_vazio(
                area, "◇", f"Nenhum registro em {ROTULOS[self.secao]}",
                "Use Nova operação para iniciar este processo.", cor=COR_RH,
            )
            if not self.registros:
                self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
                self.estado_vazio.lift()
            adicionar_divisorias_treeview(self.tabela, sobreposicao=self.estado_vazio)
            if self.secao == "colaboradores" and self.registros:
                self.editor_grade = EditorGrade(
                    self.tabela, colunas_editaveis={"nome_completo", "cargo_texto", "status"},
                    salvar=self._salvar_edicao_colaborador, parent=self.root, titulo="Colaboradores",
                )
                barra_grade = tk.Frame(painel, bg=CORES["card"]); barra_grade.pack(fill="x", padx=12, pady=(5,8))
                tk.Label(barra_grade, text="Duplo clique em nome, cargo ou status para editar diretamente.", bg=CORES["card"], fg=CORES["text_muted"], font=FONTES["micro"]).pack(side="left")
                criar_botao(barra_grade, "XLSX", lambda: self.editor_grade.exportar_xlsx(), tipo="fantasma", compacto=True).pack(side="right", padx=(5,0))
                criar_botao(barra_grade, "CSV", lambda: self.editor_grade.exportar_csv(), tipo="fantasma", compacto=True).pack(side="right")

        def _salvar_edicao_colaborador(self, iid, coluna, valor):
            atualizar_colaborador(int(iid), {coluna: valor}, SESSAO.usuario)

        def _colunas_padrao(self):
            mapas = {
                "colaboradores": ("id", "matricula", "nome_completo", "cargo_texto", "status", "etapa_jornada"),
                "admissoes": ("id", "nome_completo", "cargo_texto", "etapa_atual", "status", "previsao_conclusao"),
                "desligamentos": ("id", "nome_completo", "tipo", "data_prevista", "status", "motivo"),
                "movimentacoes": ("id", "nome_completo", "tipo", "vigencia", "observacao", "criado_em"),
                "ponto": ("id", "nome_completo", "data", "entrada", "saida", "minutos_trabalhados", "status"),
                "ferias": ("id", "nome_completo", "tipo", "inicio", "fim", "dias", "status"),
                "beneficios": ("id", "nome_completo", "beneficio", "tipo", "inicio", "status"),
                "folha": ("id", "competencia", "status", "total_proventos_centavos", "total_descontos_centavos", "total_liquido_centavos"),
                "cargos": ("id", "codigo", "titulo", "nivel", "salario_minimo_centavos", "salario_referencia_centavos", "salario_maximo_centavos"),
                "recrutamento": ("id", "titulo", "quantidade", "status", "motivo", "candidatos"),
                "desempenho": ("id", "nome_completo", "ciclo", "tipo", "nota", "status"),
                "treinamentos": ("id", "titulo", "tipo", "carga_horaria", "obrigatorio", "inscritos"),
                "carreira": ("id", "nome_completo", "titulo", "inicio", "prazo", "progresso", "status"),
                "documentos": ("id", "vinculo", "categoria", "titulo", "versao", "classificacao", "validade", "status"),
                "solicitacoes": ("id", "nome_completo", "tipo", "titulo", "status", "criado_em"),
            }
            return mapas.get(self.secao, ("id", "descricao", "status", "atualizado_em"))

        def _filtrar_tabela(self):
            termo = self.pesquisa.get().strip().lower()
            for item in self.tabela.get_children():
                self.tabela.delete(item)
            for registro in self.registros:
                if termo and termo not in " ".join(str(v).lower() for v in registro.values()):
                    continue
                colunas = self.tabela["columns"]
                self.tabela.insert("", "end", iid=str(registro.get("id")), values=tuple(_formatar(registro.get(c), c) for c in colunas))
            if self.estado_vazio is not None:
                if self.tabela.get_children():
                    self.estado_vazio.place_forget()
                else:
                    self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
                    self.estado_vazio.lift()

        def _barra_acoes(self):
            linha = tk.Frame(self.conteudo, bg=CORES["bg"]); linha.pack(fill="x", pady=(10, 0))
            if self.secao == "colaboradores":
                criar_botao(linha, "ABRIR 360°", self._ver_colaborador, tipo="secundario", compacto=True).pack(side="left")
                criar_botao(linha, "EDITAR", self._editar_colaborador, tipo="fantasma", compacto=True).pack(side="left", padx=5)
                criar_botao(linha, "DEPENDENTE", self._novo_dependente, tipo="fantasma", compacto=True).pack(side="left")
                criar_botao(linha, "EQUIPAMENTO", self._novo_equipamento, tipo="fantasma", compacto=True).pack(side="left", padx=5)
            if self.secao == "admissoes": criar_botao(linha, "AVANÇAR ETAPA", self._avancar_admissao, tipo="secundario", compacto=True).pack(side="left")
            if self.secao == "desligamentos": criar_botao(linha, "CONCLUIR DESLIGAMENTO", self._concluir_desligamento, tipo="perigo", compacto=True).pack(side="left")
            if self.secao == "ferias":
                criar_botao(linha, "APROVAR", lambda: self._decidir_ferias(True), tipo="sucesso", compacto=True).pack(side="left")
                criar_botao(linha, "REJEITAR", lambda: self._decidir_ferias(False), tipo="perigo", compacto=True).pack(side="left", padx=6)
            if self.secao == "folha":
                criar_botao(linha, "FECHAR FOLHA", self._fechar_folha, tipo="aviso", compacto=True).pack(side="left")
                criar_botao(linha, "ADICIONAR EVENTO", self._novo_evento_folha, tipo="fantasma", compacto=True).pack(side="left", padx=6)
                criar_botao(linha, "CONTRACHEQUE", self._contracheque, tipo="secundario", compacto=True).pack(side="left", padx=6)
            if self.secao == "beneficios": criar_botao(linha, "NOVO BENEFÍCIO", self._novo_beneficio, tipo="secundario", compacto=True).pack(side="left")
            if self.secao == "recrutamento": criar_botao(linha, "ADICIONAR CANDIDATO", self._novo_candidato, tipo="secundario", compacto=True).pack(side="left")
            if self.secao == "treinamentos": criar_botao(linha, "INSCREVER COLABORADOR", self._inscrever_treinamento, tipo="secundario", compacto=True).pack(side="left")
            if self.secao == "documentos": criar_botao(linha, "VERIFICAR INTEGRIDADE", self._verificar_documento, tipo="secundario", compacto=True).pack(side="left")
            if self.secao == "solicitacoes":
                criar_botao(linha, "APROVAR", lambda: self._decidir_solicitacao(True), tipo="sucesso", compacto=True).pack(side="left")
                criar_botao(linha, "REJEITAR", lambda: self._decidir_solicitacao(False), tipo="perigo", compacto=True).pack(side="left", padx=6)
            if self.secao != "movimentacoes":
                lixeira = hasattr(self, "estado_registro_rh") and self.estado_registro_rh.get() == "Lixeira"
                criar_botao(
                    linha,
                    "RESTAURAR" if lixeira else "REMOVER",
                    lambda remover=not lixeira: self._alterar_estado_registro(remover),
                    tipo="sucesso" if lixeira else "perigo",
                    compacto=True,
                ).pack(side="left", padx=(8, 0))
            criar_botao(linha, "ATUALIZAR", lambda: self.abrir_secao(self.secao), tipo="fantasma", compacto=True).pack(side="right")
