"""Ações e diálogos extraídos de interface/estoque.py na V9.7."""

from interface.estoque_shared import *  # noqa: F401,F403
from interface.estoque_shared import _formatar, _moeda, _numero
from interface.armazenamento_servidor import escolher_destino_gerado, mensagem_arquivo_gerado


class TelaEstoqueAcoesMixin:
        def _formulario(self, titulo, campos, callback, *, largura=620):
            janela = tk.Toplevel(self.root); janela.title(titulo); janela.configure(bg=CORES["bg"])
            preparar_janela_secundaria(janela, self.root, largura, min(820, 190 + len(campos) * 52), minimo=(520, 380))
            viewport = AreaRolavel(janela); viewport.pack(fill="both", expand=True, padx=22, pady=18)
            corpo = viewport.conteudo
            tk.Label(corpo, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", pady=(0, 14))
            entradas = {}
            for chave, rotulo, tipo, opcoes in campos:
                linha = tk.Frame(corpo, bg=CORES["bg"]); linha.pack(fill="x", pady=4)
                tk.Label(linha, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=25, anchor="w").pack(side="left")
                if tipo == "opcoes":
                    valores = [v[1] if isinstance(v, tuple) else v for v in opcoes]
                    campo = ttk.Combobox(linha, values=valores, state="readonly", style="Dark.TCombobox");
                    if valores: campo.current(0)
                elif tipo == "booleano":
                    variavel = tk.BooleanVar(value=False); campo = tk.Checkbutton(linha, variable=variavel, bg=CORES["bg"], activebackground=CORES["bg"]); campo._variavel = variavel
                else:
                    campo = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_ESTOQUE, relief="flat")
                campo.pack(side="left", fill="x", expand=True, ipady=6); entradas[chave] = (campo, opcoes)
            def salvar():
                dados = {}
                for chave, (campo, opcoes) in entradas.items():
                    valor = campo._variavel.get() if hasattr(campo, "_variavel") else campo.get().strip()
                    if opcoes and isinstance(opcoes[0], tuple): valor = {rotulo: valor_id for valor_id, rotulo in opcoes}.get(valor, valor)
                    dados[chave] = valor
                try:
                    callback(dados); janela.destroy(); self.abrir_secao(self.secao)
                except (ValueError, PermissionError, FileNotFoundError, OSError) as erro:
                    messagebox.showerror("Estoque", str(erro), parent=janela)
            criar_botao(corpo, "SALVAR", salvar).pack(anchor="e", pady=(15, 8))
            return janela

        def _opcoes(self, chave, rotulo="nome"):
            return [(x["id"], x.get(rotulo) or x.get("codigo") or str(x["id"])) for x in listar_catalogos(SESSAO.usuario).get(chave, [])]

        def _opcoes_itens(self):
            return [(x["id"], f"{x['codigo']} · {x['nome']}") for x in listar_itens(SESSAO.usuario, por_pagina=200)["registros"]]

        def _nova_operacao(self):
            acoes = {
                "visao": lambda: self._nova_entrada("Entrada"), "itens": self._novo_item,
                "categorias": self._nova_categoria, "fornecedores": self._novo_fornecedor,
                "recebimentos": lambda: self._nova_entrada("Recebimento de compra"),
                "saidas": self._nova_saida, "reservas": self._nova_reserva,
                "transferencias": self._nova_transferencia, "devolucoes": self._nova_devolucao,
                "inventario": self._novo_inventario, "depositos": self._novo_deposito,
                "avarias": self._nova_ocorrencia, "solicitacoes": self._nova_solicitacao,
                "reposicao": lambda: (calcular_reposicao(SESSAO.usuario), self.abrir_secao("reposicao")),
            }
            acao = acoes.get(self.secao)
            if acao: acao()
            else: messagebox.showinfo("Estoque", "Esta seção é alimentada automaticamente pelas operações do módulo.", parent=self.root)

        def _novo_item(self):
            self._formulario("Cadastrar item ou produto", (
                ("codigo", "Código interno", "texto", ()), ("sku", "SKU", "texto", ()),
                ("codigo_barras", "Código de barras", "texto", ()), ("qr_code", "QR Code", "texto", ()),
                ("nome", "Nome", "texto", ()), ("descricao", "Descrição", "texto", ()),
                ("categoria_id", "Categoria", "opcoes", self._opcoes("categorias")),
                ("unidade_id", "Unidade", "opcoes", self._opcoes("unidades", "codigo")),
                ("marca", "Marca", "texto", ()), ("fabricante", "Fabricante", "texto", ()),
                ("modelo", "Modelo", "texto", ()), ("fornecedor_principal_id", "Fornecedor principal", "opcoes", [("", "Não definido")] + self._opcoes("fornecedores")),
                ("estoque_minimo", "Estoque mínimo", "texto", ()), ("estoque_maximo", "Estoque máximo", "texto", ()),
                ("ponto_reposicao", "Ponto de reposição", "texto", ()), ("estoque_seguranca", "Estoque de segurança", "texto", ()),
                ("consumo_medio_dia", "Consumo médio/dia", "texto", ()), ("lead_time_dias", "Lead time/dias", "texto", ()),
                ("custo", "Custo inicial", "texto", ()), ("preco_referencia", "Preço de referência", "texto", ()),
                ("controla_lote", "Controla lote", "booleano", ()), ("controla_validade", "Controla validade", "booleano", ()),
                ("controla_serie", "Controla número de série", "booleano", ()), ("eh_patrimonio", "É patrimônio", "booleano", ()),
            ), lambda d: criar_item(d, SESSAO.usuario), largura=720)

        def _nova_categoria(self):
            self._formulario("Nova categoria", (("codigo", "Código", "texto", ()), ("nome", "Nome", "texto", ()), ("descricao", "Descrição", "texto", ())), lambda d: criar_categoria(d, SESSAO.usuario), largura=520)

        def _novo_fornecedor(self):
            self._formulario("Novo fornecedor", (("nome", "Nome", "texto", ()), ("documento", "CNPJ/CPF", "texto", ()), ("email", "E-mail", "texto", ()), ("telefone", "Telefone", "texto", ()), ("prazo_medio_dias", "Prazo médio/dias", "texto", ()), ("avaliacao", "Avaliação 0-10", "texto", ())), lambda d: criar_fornecedor(d, SESSAO.usuario))

        def _novo_deposito(self):
            self._formulario("Novo depósito", (("codigo", "Código", "texto", ()), ("nome", "Nome", "texto", ()), ("tipo", "Tipo", "opcoes", ("Depósito", "Almoxarifado", "Loja", "Quarentena", "Manutenção")), ("endereco", "Endereço", "texto", ()), ("capacidade", "Capacidade", "texto", ())), lambda d: criar_deposito(d, SESSAO.usuario))

        def _nova_localizacao(self):
            deposito_id = self._selecionado()
            if not deposito_id: return
            self._formulario("Novo endereço interno", (("codigo", "Código completo", "texto", ()), ("corredor", "Corredor", "texto", ()), ("prateleira", "Prateleira", "texto", ()), ("nivel", "Nível", "texto", ()), ("posicao", "Posição", "texto", ()), ("capacidade", "Capacidade", "texto", ())), lambda d: criar_localizacao(deposito_id, d, SESSAO.usuario))

        def _campos_operacao(self, *, entrada=False, transferencia=False):
            campos = [("item_id", "Item", "opcoes", self._opcoes_itens())]
            if not entrada: campos.append(("deposito_origem_id", "Depósito de origem", "opcoes", self._opcoes("depositos")))
            if entrada or transferencia: campos.append(("deposito_destino_id", "Depósito de destino", "opcoes", self._opcoes("depositos")))
            campos.extend((("quantidade", "Quantidade", "texto", ()), ("documento_numero", "Documento", "texto", ()), ("motivo", "Motivo", "texto", ())))
            if entrada:
                campos.extend((("custo_unitario", "Custo unitário", "texto", ()), ("lote_numero", "Lote", "texto", ()), ("fabricacao", "Fabricação", "texto", ()), ("validade", "Validade", "texto", ()), ("seriais", "Seriais separados por vírgula", "texto", ())))
            return tuple(campos)

        def _criar_operacao_form(self, tipo, dados):
            linha = {"item_id": dados.pop("item_id"), "quantidade": dados.pop("quantidade")}
            for chave in ("custo_unitario", "lote_numero", "fabricacao", "validade"):
                if chave in dados: linha[chave] = dados.pop(chave)
            if "seriais" in dados:
                linha["seriais"] = [x.strip() for x in dados.pop("seriais").replace(";", ",").split(",") if x.strip()]
            dados["tipo"] = tipo
            return criar_operacao(dados, [linha], SESSAO.usuario)

        def _nova_entrada(self, tipo):
            self._formulario(tipo, self._campos_operacao(entrada=True), lambda d: self._criar_operacao_form(tipo, d))

        def _nova_saida(self):
            self._formulario("Nova saída", self._campos_operacao(), lambda d: self._criar_operacao_form("Saída", d))

        def _nova_transferencia(self):
            self._formulario("Nova transferência", self._campos_operacao(transferencia=True), lambda d: self._criar_operacao_form("Transferência", d))

        def _nova_devolucao(self):
            depositos = self._opcoes("depositos")
            self._formulario(
                "Registrar devolução",
                (
                    ("tipo_devolucao", "Tipo", "opcoes", ("Devolução ao estoque", "Devolução ao fornecedor")),
                    ("item_id", "Item", "opcoes", self._opcoes_itens()),
                    ("deposito_origem_id", "Depósito de origem", "opcoes", [("", "Não aplicável")] + depositos),
                    ("deposito_destino_id", "Depósito de destino", "opcoes", [("", "Não aplicável")] + depositos),
                    ("quantidade", "Quantidade", "texto", ()),
                    ("documento_numero", "Documento", "texto", ()),
                    ("motivo", "Motivo", "texto", ()),
                    ("custo_unitario", "Custo unitário (reentrada)", "texto", ()),
                    ("lote_numero", "Lote (reentrada)", "texto", ()),
                ),
                lambda d: self._criar_operacao_form(d.pop("tipo_devolucao"), d),
            )

        def _nova_reserva(self):
            self._formulario("Nova reserva", (("item_id", "Item", "opcoes", self._opcoes_itens()), ("deposito_id", "Depósito", "opcoes", self._opcoes("depositos")), ("quantidade", "Quantidade", "texto", ()), ("departamento_id", "Departamento", "opcoes", [("", "Não definido")] + self._opcoes("departamentos")), ("centro_custo_id", "Centro de custo", "opcoes", [("", "Não definido")] + self._opcoes("centros_custo")), ("finalidade", "Finalidade", "texto", ()), ("expira_em", "Expira em", "texto", ())), lambda d: criar_reserva(d, SESSAO.usuario))

        def _novo_inventario(self):
            self._formulario("Iniciar inventário", (("deposito_id", "Depósito", "opcoes", self._opcoes("depositos")), ("tipo", "Tipo", "opcoes", ("Geral", "Parcial", "Rotativo", "Por categoria", "Por localização", "Por lote")), ("categoria_id", "Categoria", "opcoes", [("", "Todas")] + self._opcoes("categorias")), ("descricao", "Descrição", "texto", ()), ("previsto_inicio", "Início", "texto", ()), ("contagem_cega", "Contagem cega", "booleano", ())), lambda d: iniciar_inventario(d, SESSAO.usuario))

        def _nova_ocorrencia(self):
            self._formulario("Registrar avaria ou perda", (("tipo", "Tipo", "opcoes", ("Avaria", "Perda", "Vencimento", "Quarentena", "Devolução")), ("item_id", "Item", "opcoes", self._opcoes_itens()), ("deposito_id", "Depósito", "opcoes", self._opcoes("depositos")), ("quantidade", "Quantidade", "texto", ()), ("motivo", "Motivo", "texto", ()), ("destino", "Destino", "opcoes", ("Manutenção", "Descarte", "Fornecedor", "Quarentena")), ("foto_caminho", "Caminho da foto", "texto", ())), lambda d: registrar_ocorrencia(d, SESSAO.usuario))

        def _nova_solicitacao(self):
            self._formulario("Nova solicitação interna", (("item_id", "Item", "opcoes", self._opcoes_itens()), ("quantidade", "Quantidade", "texto", ()), ("departamento_id", "Departamento", "opcoes", [("", "Não definido")] + self._opcoes("departamentos")), ("centro_custo_id", "Centro de custo", "opcoes", [("", "Não definido")] + self._opcoes("centros_custo")), ("prioridade", "Prioridade", "opcoes", ("Baixa", "Normal", "Alta", "Urgente")), ("justificativa", "Justificativa", "texto", ())), lambda d: criar_solicitacao(d, SESSAO.usuario))

        def _scanner(self):
            def consultar(dados):
                termo = dados["codigo"]
                resultados = listar_itens(SESSAO.usuario, pesquisa=termo, por_pagina=20)["registros"]
                if not resultados: raise ValueError("Nenhum item identificado pelo código informado.")
                item = resultados[0]
                messagebox.showinfo("Leitor de código", f"{item['nome']}\nSKU: {item['sku']}\nFísico: {_numero(item['fisico'])}\nDisponível: {_numero(item['disponivel'])}", parent=self.root)
            self._formulario("Ler código de barras ou QR", (("codigo", "Código lido", "texto", ()),), consultar, largura=500)

        def _ver_item(self):
            item_id = self._selecionado()
            if not item_id: return
            try: item = obter_item(item_id, SESSAO.usuario); movimentos = listar_movimentacoes(SESSAO.usuario, item_id=item_id, limite=100)
            except (ValueError, PermissionError) as erro: messagebox.showerror("Ficha do item", str(erro), parent=self.root); return
            janela = tk.Toplevel(self.root); janela.title(f"Item · {item['nome']}"); janela.configure(bg=CORES["bg"])
            preparar_janela_secundaria(janela, self.root, 980, 700, minimo=(760, 520))
            topo = tk.Frame(janela, bg=CORES["card"]); topo.pack(fill="x", padx=18, pady=18)
            tk.Label(topo, text=item["nome"], font=FONTES["titulo"], fg=CORES["text"], bg=CORES["card"]).pack(anchor="w", padx=18, pady=(16, 2))
            tk.Label(topo, text=f"{item['codigo']}  ·  {item.get('sku') or '—'}  ·  {item['status']}", font=FONTES["texto"], fg=COR_ESTOQUE, bg=CORES["card"]).pack(anchor="w", padx=18, pady=(0, 16))
            abas = ttk.Notebook(janela, style="Dark.TNotebook"); abas.pack(fill="both", expand=True, padx=18, pady=(0, 18))
            resumo = tk.Frame(abas, bg=CORES["card"]); abas.add(resumo, text="Resumo")
            for rotulo, valor in (("Físico", item.get("fisico")), ("Reservado", item.get("reservado")), ("Bloqueado", item.get("bloqueado")), ("Disponível", item.get("disponivel")), ("Mínimo", item.get("estoque_minimo")), ("Máximo", item.get("estoque_maximo")), ("Custo médio", _moeda(item.get("custo_medio_centavos")))):
                linha = tk.Frame(resumo, bg=CORES["card_secundario"]); linha.pack(fill="x", padx=14, pady=3)
                tk.Label(linha, text=rotulo.upper(), width=24, anchor="w", font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card_secundario"]).pack(side="left", padx=10, pady=8)
                tk.Label(linha, text=_numero(valor) if not isinstance(valor, str) else valor, font=FONTES["texto"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left")
            historico = tk.Frame(abas, bg=CORES["card"]); abas.add(historico, text="Rastreabilidade")
            texto = tk.Text(historico, bg=CORES["input"], fg=CORES["text_sec"], relief="flat", wrap="none")
            texto.pack(fill="both", expand=True)
            for mov in movimentos: texto.insert("end", f"{mov['criado_em']}  {mov['tipo']:<24} {float(mov['quantidade']):>10g}  {mov['deposito_nome']}  {mov['usuario_nome'] or '—'}\n")
            texto.configure(state="disabled")

        def _editar_item(self):
            item_id = self._selecionado()
            if not item_id: return
            self._formulario("Editar parâmetros do item", (("nome", "Nome", "texto", ()), ("estoque_minimo", "Estoque mínimo", "texto", ()), ("estoque_maximo", "Estoque máximo", "texto", ()), ("ponto_reposicao", "Ponto de reposição", "texto", ()), ("estoque_seguranca", "Estoque de segurança", "texto", ()), ("consumo_medio_dia", "Consumo médio/dia", "texto", ()), ("lead_time_dias", "Lead time/dias", "texto", ()), ("status", "Status", "opcoes", ("Ativo", "Inativo", "Bloqueado"))), lambda d: atualizar_item(item_id, d, SESSAO.usuario))

        def _conferir_selecionada(self):
            operacao_id = self._selecionado()
            if not operacao_id: return
            registro = next((x for x in self.registros if int(x["id"]) == operacao_id), None)
            if not registro: return
            self._formulario("Conferir operação", (("quantidade", "Quantidade total conferida", "texto", ()),), lambda d: self._conferir_primeira_linha(operacao_id, d["quantidade"]), largura=500)

        def _conferir_primeira_linha(self, operacao_id, quantidade):
            linha_id = obter_primeiro_item_operacao(operacao_id, SESSAO.usuario)
            conferir_operacao(operacao_id, {int(linha_id): quantidade}, SESSAO.usuario)

        def _confirmar_selecionada(self):
            identificador = self._selecionado()
            if not identificador: return
            try: confirmar_operacao(identificador, SESSAO.usuario); self.abrir_secao(self.secao)
            except (ValueError, PermissionError) as erro: messagebox.showerror("Operação de estoque", str(erro), parent=self.root)

        def _cancelar_selecionada(self):
            identificador = self._selecionado()
            if not identificador: return
            if not messagebox.askyesno("Cancelar operação", "A operação será cancelada e permanecerá na auditoria. Continuar?", parent=self.root): return
            try: cancelar_operacao(identificador, "Cancelada pela interface.", SESSAO.usuario); self.abrir_secao(self.secao)
            except (ValueError, PermissionError) as erro: messagebox.showerror("Cancelar operação", str(erro), parent=self.root)

        def _aprovar_operacao(self, aprovar):
            identificador = self._selecionado()
            if not identificador: return
            try: aprovar_operacao(identificador, aprovar, "Decisão registrada pela interface.", SESSAO.usuario); self.abrir_secao(self.secao)
            except (ValueError, PermissionError) as erro: messagebox.showerror("Aprovação", str(erro), parent=self.root)

        def _receber_transferencia(self):
            identificador = self._selecionado()
            if not identificador: return
            try: receber_transferencia(identificador, SESSAO.usuario); self.abrir_secao("transferencias")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Receber transferência", str(erro), parent=self.root)

        def _liberar_reserva(self, atender):
            identificador = self._selecionado()
            if not identificador: return
            try: liberar_reserva(identificador, SESSAO.usuario, atender=atender); self.abrir_secao("reservas")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Reservas", str(erro), parent=self.root)

        def _abrir_inventario(self):
            inventario_id = self._selecionado()
            if not inventario_id: return
            try: registros = itens_inventario(inventario_id, SESSAO.usuario)
            except (ValueError, PermissionError) as erro: messagebox.showerror("Inventário", str(erro), parent=self.root); return
            janela = tk.Toplevel(self.root); janela.title("Contagem de inventário"); janela.configure(bg=CORES["bg"])
            preparar_janela_secundaria(janela, self.root, 960, 650, minimo=(720, 500))
            tk.Label(janela, text="Contagem física", font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=20, pady=(18, 10))
            colunas = ("codigo", "item_nome", "localizacao_codigo", "lote_numero", "quantidade_sistema", "primeira_contagem", "segunda_contagem", "divergencia")
            tabela = ttk.Treeview(janela, columns=colunas, show="headings", style="Dark.Treeview")
            for c in colunas: tabela.heading(c, text=c.replace("_", " ").upper()); tabela.column(c, width=115, anchor="w")
            tabela.pack(fill="both", expand=True, padx=20, pady=5)
            adicionar_divisorias_treeview(tabela, cor=CORES["border"])
            for item in registros: tabela.insert("", "end", iid=str(item["id"]), values=tuple(_formatar(item.get(c), c) for c in colunas))
            def contar():
                if not tabela.selection(): messagebox.showwarning("Inventário", "Selecione um item.", parent=janela); return
                item_linha = int(tabela.selection()[0])
                quantidade = simpledialog.askstring(
                    "Registrar contagem",
                    "Quantidade encontrada:",
                    parent=janela,
                )
                if quantidade is None:
                    return
                try:
                    registrar_contagem(
                        inventario_id,
                        item_linha,
                        quantidade,
                        SESSAO.usuario,
                    )
                except (ValueError, PermissionError) as erro:
                    messagebox.showerror("Inventário", str(erro), parent=janela)
                    return
                janela.destroy()
                self.abrir_secao("inventario")
            criar_botao(janela, "REGISTRAR CONTAGEM", contar).pack(anchor="e", padx=20, pady=(8, 18))

        def _finalizar_inventario(self):
            identificador = self._selecionado()
            if not identificador: return
            try: finalizar_inventario(identificador, SESSAO.usuario); self.abrir_secao("inventario")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Finalizar inventário", str(erro), parent=self.root)

        def _aprovar_inventario(self):
            identificador = self._selecionado()
            if not identificador: return
            try: aprovar_inventario(identificador, SESSAO.usuario); self.abrir_secao("inventario")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Aprovar inventário", str(erro), parent=self.root)

        def _encaminhar_reposicao(self):
            identificador = self._selecionado()
            if not identificador: return
            try:
                from services.orquestracao import criar_fluxo_reposicao
                resultado = criar_fluxo_reposicao(identificador, SESSAO.usuario)
                messagebox.showinfo("Reposição", f"Solicitação de compra #{resultado['solicitacao_compra_id']} criada e fluxo transversal #{resultado['orquestracao_id']} registrado.", parent=self.root); self.abrir_secao("reposicao")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Reposição", str(erro), parent=self.root)

        def _resolver_alerta(self):
            identificador = self._selecionado()
            if not identificador: return
            try: resolver_alerta(identificador, SESSAO.usuario); self.abrir_secao("alertas")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Alertas", str(erro), parent=self.root)

        def _decidir_solicitacao(self, aprovar):
            identificador = self._selecionado()
            if not identificador: return
            try: decidir_solicitacao(identificador, aprovar, SESSAO.usuario); self.abrir_secao("solicitacoes")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Solicitações", str(erro), parent=self.root)

        def _mostrar_analise(self):
            try: analise = analisar_estoque(SESSAO.usuario)
            except (ValueError, PermissionError) as erro: messagebox.showerror("Análise de Estoque", str(erro), parent=self.root); return
            texto = "RESUMO INTELIGENTE\n\n" + "\n".join(f"• {x}" for x in analise["pontos_atencao"])
            if analise["itens_parados"]:
                texto += "\n\nCAPITAL PARADO\n\n" + "\n".join(f"• {x['nome']}: {_numero(x['saldo'])} unidade(s)" for x in analise["itens_parados"][:5])
            if analise["mais_movimentados"]:
                texto += "\n\nMAIS MOVIMENTADOS\n\n" + "\n".join(f"• {x['nome']}: {_numero(x['movimentado'])}" for x in analise["mais_movimentados"][:5])
            messagebox.showinfo("Inteligência de estoque", texto, parent=self.root)

        def _relatorios(self):
            self._cabecalho("Central de relatórios de Estoque", "Relatórios operacionais, gerenciais, financeiros, de rastreabilidade e auditoria.")
            card = criar_card(self.conteudo); card.pack(fill="x")
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=18, pady=18)
            criar_titulo_secao(interior, "Gerar agora", "PDF informa explicitamente quando precisar limitar grandes volumes; Excel e CSV preservam o universo completo.")
            for tipo in ("Posição atual", "Movimentações", "Inventários", "Lotes", "Alertas", "Rastreabilidade"):
                linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=3)
                tk.Label(linha, text=tipo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left", padx=12, pady=10)
                for formato in ("PDF", "XLSX", "CSV"):
                    criar_botao(linha, formato, lambda t=tipo, f=formato: self._gerar_relatorio(t, f), tipo="fantasma", compacto=True).pack(side="right", padx=3)
            criar_botao(interior, "AGENDAR ENVIO", self._agendar_relatorio, tipo="secundario", compacto=True).pack(anchor="e", pady=(12, 0))

        def _gerar_relatorio(self, tipo, formato):
            extensao = formato.lower()
            nome = f"estoque_{tipo.lower().replace(' ', '_')}.{extensao}"
            caminho, remoto = escolher_destino_gerado(
                parent=self.root, nome_sugerido=nome, titulo="Gerar relatório de Estoque",
                defaultextension=f".{extensao}", filetypes=((formato, f"*.{extensao}"),),
            )
            if not caminho: return
            try:
                resultado = gerar_relatorio_estoque(tipo, formato, caminho, SESSAO.usuario)
                messagebox.showinfo("Relatórios", mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome), parent=self.root)
            except (ValueError, PermissionError, OSError) as erro:
                messagebox.showerror("Relatórios", str(erro), parent=self.root)

        def _agendar_relatorio(self):
            self._formulario("Agendar relatório", (("tipo", "Tipo", "opcoes", ("Posição atual", "Movimentações", "Inventários", "Lotes", "Alertas", "Rastreabilidade")), ("formato", "Formato", "opcoes", ("PDF", "XLSX", "CSV")), ("frequencia", "Frequência", "opcoes", ("Diária", "Semanal", "Mensal", "Trimestral")), ("horario", "Horário", "texto", ()), ("destinatarios", "Destinatários", "texto", ())), lambda d: agendar_relatorio(d, SESSAO.usuario))

        def _auditoria(self):
            self._cabecalho("Auditoria de Estoque", "Quem fez, o quê, quando, onde, valores anteriores, valores posteriores e motivo.", acoes=False)
            try: registros = listar_auditoria_estoque(SESSAO.usuario)
            except PermissionError as erro: messagebox.showerror("Auditoria", str(erro), parent=self.root); return
            card = criar_card(self.conteudo); card.pack(fill="both", expand=True)
            texto = tk.Text(card, bg=CORES["input"], fg=CORES["text_sec"], insertbackground=COR_ESTOQUE, relief="flat", height=30, wrap="word")
            texto.pack(fill="both", expand=True, padx=1, pady=1)
            for r in registros: texto.insert("end", f"{r['criado_em']}  ·  {r['usuario_nome'] or r['usuario_id']}  ·  {r['acao']}  ·  {r['entidade']} #{r['entidade_id']}\n")
            texto.configure(state="disabled")

        def _configuracoes(self):
            self._cabecalho("Configurações de Estoque", "Matriz de ações, regras de saldo, custeio, rastreabilidade e segregação por depósito.", acoes=False)
            if str(SESSAO.usuario.get("perfil", "")).lower() != "admin":
                estado = criar_estado_vazio(self.conteudo, "◇", "Acesso administrativo", "Somente administradores podem alterar as políticas e permissões do Estoque.", cor=COR_ESTOQUE); estado.pack(fill="both", expand=True); return
            card = criar_card(self.conteudo); card.pack(fill="x")
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=18, pady=18)
            criar_titulo_secao(interior, "Matriz de ações", "Permissões granulares prevalecem sobre a permissão genérica do módulo.")
            for acao in sorted(ACOES_ESTOQUE):
                linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=2)
                tk.Label(linha, text=acao.replace("_", " ").upper(), font=("Inter", 8, "bold"), fg=CORES["text"], bg=CORES["card_secundario"], anchor="w").pack(fill="x", padx=12, pady=8)
            tk.Label(interior, text="Política ativa: razão imutável, saldo negativo bloqueado, transferências em trânsito, FEFO para lotes e aprovação para ajustes sensíveis.", font=FONTES["texto"], fg=COR_ESTOQUE, bg=CORES["card"], wraplength=900, justify="left").pack(anchor="w", pady=(14, 0))

