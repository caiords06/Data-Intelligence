"""Ações e diálogos extraídos de interface/rh.py na V9.7."""

from interface.rh_shared import *  # noqa: F401,F403
from interface.rh_shared import _formatar
from interface.armazenamento_servidor import escolher_destino_gerado, mensagem_arquivo_gerado


class TelaRHAcoesMixin:
        def _selecionado(self):
            if self.tabela is None or not self.tabela.selection():
                messagebox.showwarning("Recursos Humanos", "Selecione um registro.", parent=self.root); return None
            return int(self.tabela.selection()[0])

        def _nova_operacao(self):
            acoes = {
                "visao": self._nova_admissao, "colaboradores": self._novo_colaborador,
                "admissoes": self._nova_admissao, "desligamentos": self._novo_desligamento,
                "ponto": self._novo_ponto, "ferias": self._novas_ferias,
                "beneficios": self._vincular_beneficio, "folha": self._nova_folha,
                "cargos": self._novo_cargo, "recrutamento": self._nova_vaga,
                "desempenho": self._nova_avaliacao, "treinamentos": self._novo_treinamento,
                "carreira": self._novo_pdi, "documentos": self._novo_documento,
                "solicitacoes": self._nova_solicitacao,
            }
            acao = acoes.get(self.secao)
            if acao: acao()
            else: messagebox.showinfo("Recursos Humanos", "Esta seção é alimentada automaticamente pelas demais operações.", parent=self.root)

        def _formulario(self, titulo, campos, callback, *, largura=570):
            janela = tk.Toplevel(self.root); janela.title(titulo); janela.configure(bg=CORES["bg"])
            preparar_janela_secundaria(janela, self.root, largura, min(760, 190 + len(campos) * 52), minimo=(500, 360))
            corpo = tk.Frame(janela, bg=CORES["bg"]); corpo.pack(fill="both", expand=True, padx=24, pady=20)
            tk.Label(corpo, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", pady=(0, 14))
            entradas = {}
            for chave, rotulo, tipo, opcoes in campos:
                linha = tk.Frame(corpo, bg=CORES["bg"]); linha.pack(fill="x", pady=4)
                tk.Label(linha, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=24, anchor="w").pack(side="left")
                if tipo == "opcoes":
                    campo = ttk.Combobox(linha, values=[v[1] if isinstance(v, tuple) else v for v in opcoes], state="readonly", style="Dark.TCombobox")
                    if opcoes: campo.current(0)
                elif tipo == "booleano":
                    variavel = tk.BooleanVar(value=False); campo = tk.Checkbutton(linha, variable=variavel, bg=CORES["bg"], activebackground=CORES["bg"]); campo._variavel = variavel
                else:
                    campo = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat")
                campo.pack(side="left", fill="x", expand=True, ipady=6)
                entradas[chave] = (campo, opcoes)
            def salvar():
                dados = {}
                for chave, (campo, opcoes) in entradas.items():
                    if hasattr(campo, "_variavel"): valor = campo._variavel.get()
                    else: valor = campo.get().strip()
                    if opcoes and isinstance(opcoes[0], tuple):
                        mapa = {rotulo: valor_id for valor_id, rotulo in opcoes}; valor = mapa.get(valor, valor)
                    dados[chave] = valor
                try:
                    callback(dados); janela.destroy(); self.abrir_secao(self.secao)
                except (ValueError, PermissionError, FileNotFoundError) as erro:
                    messagebox.showerror("Recursos Humanos", str(erro), parent=janela)
            criar_botao(corpo, "SALVAR", salvar).pack(anchor="e", pady=(15, 0))
            return janela

        def _opcoes(self, chave, rotulo="nome"):
            catalogos = listar_catalogos(SESSAO.usuario)
            return [(x["id"], x.get(rotulo) or x.get("nome_completo") or str(x["id"])) for x in catalogos.get(chave, [])]

        def _campos_colaborador(self):
            return (
                ("nome_completo", "Nome completo", "texto", ()), ("nome_social", "Nome social", "texto", ()),
                ("matricula", "Matrícula (opcional)", "texto", ()), ("cpf", "CPF", "texto", ()),
                ("email_corporativo", "E-mail corporativo", "texto", ()), ("telefone", "Telefone", "texto", ()),
                ("cargo_texto", "Cargo", "texto", ()), ("departamento_id", "Departamento", "opcoes", self._opcoes("departamentos")),
                ("centro_custo_id", "Centro de custo", "opcoes", self._opcoes("centros_custo", "nome")),
                ("tipo_contrato", "Contrato", "opcoes", ("CLT", "PJ", "Estágio", "Temporário", "Aprendiz")),
                ("modalidade", "Modalidade", "opcoes", ("Presencial", "Híbrido", "Remoto")),
                ("admissao", "Admissão", "texto", ()), ("salario", "Salário", "texto", ()),
            )

        def _novo_colaborador(self): self._formulario("Novo colaborador", self._campos_colaborador(), lambda d: __import__("enterprise.rh", fromlist=["criar_colaborador"]).criar_colaborador(d, SESSAO.usuario))

        def _nova_admissao(self): self._formulario("Iniciar admissão", self._campos_colaborador(), lambda d: iniciar_admissao(d, SESSAO.usuario))

        def _editar_colaborador(self):
            colaborador_id = self._selecionado()
            if not colaborador_id: return
            self._formulario("Editar dados profissionais", (
                ("cargo_texto", "Cargo", "texto", ()),
                ("departamento_id", "Departamento", "opcoes", self._opcoes("departamentos")),
                ("centro_custo_id", "Centro de custo", "opcoes", self._opcoes("centros_custo", "nome")),
                ("tipo_contrato", "Contrato", "opcoes", ("CLT", "PJ", "Estágio", "Temporário", "Aprendiz")),
                ("modalidade", "Modalidade", "opcoes", ("Presencial", "Híbrido", "Remoto")),
                ("salario", "Salário", "texto", ()),
                ("status", "Status", "opcoes", ("Pré-admissão", "Ativo", "Em desligamento", "Afastado")),
            ), lambda d: atualizar_colaborador(colaborador_id, d, SESSAO.usuario))

        def _alterar_estado_registro(self, remover: bool):
            registro_id = self._selecionado()
            if not registro_id:
                return
            acao = "remover" if remover else "restaurar"
            if not messagebox.askyesno(
                "Confirmar alteração",
                f"Deseja {acao} este registro? A operação será auditada e não apagará evidências.",
                parent=self.root,
            ):
                return
            try:
                alterar_estado_registro_rh(self.secao, registro_id, remover, SESSAO.usuario)
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Recursos Humanos", str(erro), parent=self.root)
                return
            self.abrir_secao(self.secao)

        def _novo_dependente(self):
            colaborador_id = self._selecionado()
            if not colaborador_id: return
            self._formulario("Adicionar dependente", (
                ("nome", "Nome", "texto", ()), ("parentesco", "Parentesco", "texto", ()),
                ("nascimento", "Nascimento", "texto", ()), ("cpf", "CPF", "texto", ()),
                ("dependente_ir", "Dependente no IR", "booleano", ()),
            ), lambda d: adicionar_dependente(colaborador_id, d, SESSAO.usuario))

        def _novo_equipamento(self):
            colaborador_id = self._selecionado()
            if not colaborador_id: return
            self._formulario("Vincular equipamento", (
                ("patrimonio", "Patrimônio", "texto", ()), ("descricao", "Descrição", "texto", ()),
                ("origem_modulo", "Origem", "opcoes", ("estoque", "ti", "administrativo")),
                ("origem_recurso_id", "ID na origem", "texto", ()), ("entregue_em", "Entrega", "texto", ()),
            ), lambda d: vincular_equipamento(colaborador_id, d, SESSAO.usuario))

        def _novo_desligamento(self):
            self._formulario("Iniciar desligamento", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("tipo", "Tipo", "opcoes", ("Pedido de demissão", "Sem justa causa", "Com justa causa", "Término de contrato")), ("data_prevista", "Data prevista", "texto", ()), ("motivo", "Motivo", "texto", ())), lambda d: iniciar_desligamento(int(d.pop("colaborador_id")), d, SESSAO.usuario))

        def _novo_ponto(self):
            self._formulario("Registrar ponto e jornada", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("data", "Data", "texto", ()), ("entrada", "Entrada HH:MM", "texto", ()), ("intervalo_inicio", "Início intervalo", "texto", ()), ("intervalo_fim", "Fim intervalo", "texto", ()), ("saida", "Saída HH:MM", "texto", ()), ("justificativa", "Justificativa", "texto", ())), lambda d: registrar_ponto(int(d.pop("colaborador_id")), d, SESSAO.usuario))

        def _novas_ferias(self):
            self._formulario("Férias ou ausência", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("tipo", "Tipo", "opcoes", ("Férias", "Licença médica", "Licença maternidade", "Licença paternidade", "Ausência justificada", "Outros")), ("inicio", "Início", "texto", ()), ("fim", "Fim", "texto", ()), ("saldo_antes", "Saldo disponível", "texto", ()), ("motivo", "Motivo", "texto", ())), lambda d: solicitar_ferias_ausencia(d, SESSAO.usuario))

        def _novo_beneficio(self):
            self._formulario("Cadastrar benefício", (("nome", "Nome", "texto", ()), ("tipo", "Tipo", "texto", ()), ("fornecedor", "Fornecedor", "texto", ()), ("custo_empresa", "Custo da empresa", "texto", ()), ("desconto_colaborador", "Desconto colaborador", "texto", ()), ("elegibilidade", "Elegibilidade", "texto", ())), lambda d: salvar_beneficio(d, SESSAO.usuario))

        def _vincular_beneficio(self):
            self._formulario("Vincular benefício", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("beneficio_id", "Benefício", "opcoes", self._opcoes("beneficios")), ("inicio", "Início", "texto", ())), lambda d: vincular_beneficio(int(d["colaborador_id"]), int(d["beneficio_id"]), d["inicio"], SESSAO.usuario))

        def _nova_folha(self): self._formulario("Abrir folha", (("competencia", "Competência AAAA-MM", "texto", ()),), lambda d: abrir_folha(d["competencia"], SESSAO.usuario), largura=500)

        def _novo_evento_folha(self):
            folha_id = self._selecionado()
            if not folha_id: return
            self._formulario("Adicionar evento de folha", (
                ("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")),
                ("codigo", "Código", "texto", ()), ("descricao", "Descrição", "texto", ()),
                ("natureza", "Natureza", "opcoes", ("Provento", "Desconto", "Encargo")),
                ("valor", "Valor", "texto", ()),
            ), lambda d: adicionar_evento_folha(folha_id, int(d.pop("colaborador_id")), d, SESSAO.usuario))

        def _novo_cargo(self): self._formulario("Novo cargo", (("codigo", "Código", "texto", ()), ("titulo", "Título", "texto", ()), ("nivel", "Nível", "texto", ()), ("descricao", "Descrição", "texto", ()), ("salario_minimo", "Faixa mínima", "texto", ()), ("salario_referencia", "Referência", "texto", ()), ("salario_maximo", "Faixa máxima", "texto", ())), lambda d: salvar_cargo(d, SESSAO.usuario))

        def _nova_vaga(self): self._formulario("Nova vaga", (("titulo", "Título", "texto", ()), ("departamento_id", "Departamento", "opcoes", self._opcoes("departamentos")), ("cargo_id", "Cargo", "opcoes", self._opcoes("cargos", "titulo")), ("quantidade", "Quantidade", "texto", ()), ("motivo", "Motivo", "texto", ())), lambda d: criar_vaga(d, SESSAO.usuario))

        def _novo_candidato(self):
            vaga = self._selecionado()
            if not vaga: return
            self._formulario("Adicionar candidato", (("nome", "Nome", "texto", ()), ("email", "E-mail", "texto", ()), ("telefone", "Telefone", "texto", ()), ("etapa", "Etapa", "opcoes", ("Inscrição", "Triagem", "Entrevista RH", "Entrevista gestor", "Proposta", "Contratado", "Reprovado")), ("nota", "Nota", "texto", ()), ("observacao", "Observação", "texto", ())), lambda d: adicionar_candidato(vaga, d, SESSAO.usuario))

        def _nova_avaliacao(self): self._formulario("Nova avaliação", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("ciclo", "Ciclo", "texto", ()), ("tipo", "Tipo", "opcoes", ("Gestor", "Autoavaliação", "360 graus")), ("nota", "Nota", "texto", ()), ("feedback", "Feedback", "texto", ()), ("status", "Status", "opcoes", ("Planejada", "Em andamento", "Concluída"))), lambda d: salvar_avaliacao(d, SESSAO.usuario))

        def _novo_treinamento(self): self._formulario("Novo treinamento", (("titulo", "Título", "texto", ()), ("tipo", "Tipo", "opcoes", ("Interno", "Externo", "Online")), ("carga_horaria", "Carga horária", "texto", ()), ("validade_meses", "Validade em meses", "texto", ()), ("obrigatorio", "Obrigatório", "booleano", ()), ("custo", "Custo", "texto", ())), lambda d: salvar_treinamento(d, SESSAO.usuario))

        def _inscrever_treinamento(self):
            treinamento = self._selecionado()
            if not treinamento: return
            self._formulario("Inscrever colaborador", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")),), lambda d: inscrever_treinamento(treinamento, int(d["colaborador_id"]), SESSAO.usuario), largura=500)

        def _novo_pdi(self): self._formulario("Novo PDI", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("titulo", "Título", "texto", ()), ("objetivo", "Objetivo", "texto", ()), ("inicio", "Início", "texto", ()), ("prazo", "Prazo", "texto", ()), ("progresso", "Progresso %", "texto", ())), lambda d: salvar_pdi(d, SESSAO.usuario))

        def _novo_documento(self):
            caminho = filedialog.askopenfilename(parent=self.root, title="Selecionar documento")
            if not caminho: return
            opcoes = [("", "Corporativo")] + self._opcoes("colaboradores", "nome_completo")
            self._formulario("Registrar documento", (("colaborador_id", "Vínculo", "opcoes", opcoes), ("categoria", "Categoria", "opcoes", ("Pessoal", "Contratual", "Benefícios", "Saúde e segurança", "Treinamento", "Outros")), ("titulo", "Título", "texto", ()), ("classificacao", "Classificação", "opcoes", ("Interno", "Confidencial", "Restrito")), ("validade", "Validade", "texto", ()), ("assinatura_status", "Assinatura", "opcoes", ("Não aplicável", "Pendente", "Assinado"))), lambda d: registrar_documento(int(d["colaborador_id"]) if d["colaborador_id"] else None, d, caminho, SESSAO.usuario))

        def _nova_solicitacao(self): self._formulario("Nova solicitação", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("tipo", "Tipo", "opcoes", ("Férias", "Benefício", "Documento", "Reembolso", "Ajuste de ponto", "Geral")), ("titulo", "Título", "texto", ()), ("descricao", "Descrição", "texto", ())), lambda d: criar_solicitacao(d, SESSAO.usuario))

        def _ver_colaborador(self):
            identificador = self._selecionado()
            if not identificador: return
            from interface.funcionario_360 import abrir_funcionario_360
            abrir_funcionario_360(self.root, identificador)

        def _avancar_admissao(self):
            identificador = self._selecionado()
            if not identificador: return
            registro = next((r for r in self.registros if int(r["id"]) == identificador), None)
            etapa = min(8, int(registro.get("etapa_atual") or 1) + 1)
            concluir = etapa == 8 and messagebox.askyesno("Admissão", "Concluir a admissão e ativar o colaborador?", parent=self.root)
            try: atualizar_admissao(identificador, etapa, {"etapa_confirmada": etapa}, SESSAO.usuario, concluir=concluir); self.abrir_secao("admissoes")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Admissão", str(erro), parent=self.root)

        def _concluir_desligamento(self):
            identificador = self._selecionado()
            if not identificador: return
            try: concluir_desligamento(identificador, SESSAO.usuario); self.abrir_secao("desligamentos")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Desligamento", str(erro), parent=self.root)

        def _decidir_ferias(self, aprovar):
            identificador = self._selecionado()
            if not identificador: return
            try: decidir_ferias_ausencia(identificador, aprovar, "Decisão registrada na interface de RH.", SESSAO.usuario); self.abrir_secao("ferias")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Férias e ausências", str(erro), parent=self.root)

        def _fechar_folha(self):
            identificador = self._selecionado()
            if not identificador: return
            if not messagebox.askyesno("Folha", "Fechar esta competência? A operação ficará auditada.", parent=self.root): return
            try: fechar_folha(identificador, SESSAO.usuario); self.abrir_secao("folha")
            except (ValueError, PermissionError) as erro: messagebox.showerror("Folha", str(erro), parent=self.root)

        def _contracheque(self):
            folha_id = self._selecionado()
            if not folha_id: return

            def gerar(dados):
                resultado = gerar_contracheque(folha_id, int(dados["colaborador_id"]), SESSAO.usuario)
                remoto = isinstance(resultado, dict) and resultado.get("armazenamento") == "servidor_corporativo"
                nome = resultado.get("nome", "contracheque.pdf") if isinstance(resultado, dict) else "contracheque.pdf"
                messagebox.showinfo(
                    "Contracheque",
                    mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome),
                    parent=self.root,
                )

            self._formulario(
                "Gerar contracheque",
                (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")),),
                gerar,
                largura=500,
            )

        def _verificar_documento(self):
            documento_id = self._selecionado()
            if not documento_id: return
            try:
                resultado = verificar_documento(documento_id, SESSAO.usuario)
                texto = "Documento íntegro e disponível." if resultado["integro"] else "O arquivo está ausente ou foi alterado."
                messagebox.showinfo("Integridade documental", texto, parent=self.root)
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Integridade documental", str(erro), parent=self.root)

        def _decidir_solicitacao(self, aprovar):
            solicitacao_id = self._selecionado()
            if not solicitacao_id: return
            try:
                decidir_solicitacao(solicitacao_id, aprovar, "Decisão registrada pelo RH.", SESSAO.usuario)
                self.abrir_secao("solicitacoes")
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Solicitações", str(erro), parent=self.root)

        def _mostrar_analise(self):
            try: analise = analisar_rh(SESSAO.usuario)
            except (ValueError, PermissionError) as erro: messagebox.showerror("Análise de RH", str(erro), parent=self.root); return
            texto = "PONTOS DE ATENÇÃO\n\n" + "\n".join(f"• {x}" for x in analise["alertas"]) + "\n\nRECOMENDAÇÕES\n\n" + "\n".join(f"• {x}" for x in analise["recomendacoes"])
            messagebox.showinfo("Análise inteligente de RH", texto, parent=self.root)

        def _relatorios(self):
            self._cabecalho("Central de relatórios de RH", "Gere relatórios operacionais, financeiros e gerenciais em PDF, Excel ou CSV.")
            card = criar_card(self.conteudo); card.pack(fill="x")
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=18, pady=18)
            criar_titulo_secao(interior, "Gerar agora", "O arquivo respeita o contexto e as permissões de dados sensíveis.")
            for tipo in ("Colaboradores", "Férias", "Folha"):
                linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=3)
                tk.Label(linha, text=tipo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left", padx=12, pady=10)
                for formato in ("PDF", "XLSX", "CSV"):
                    criar_botao(linha, formato, lambda t=tipo, f=formato: self._gerar_relatorio(t, f), tipo="fantasma", compacto=True).pack(side="right", padx=3)
            criar_botao(interior, "AGENDAR ENVIO", self._agendar_relatorio, tipo="secundario", compacto=True).pack(anchor="e", pady=(12, 0))

        def _gerar_relatorio(self, tipo, formato):
            extensao = formato.lower()
            nome = f"rh_{tipo.lower()}.{extensao}"
            caminho, remoto = escolher_destino_gerado(
                parent=self.root, nome_sugerido=nome, titulo="Gerar relatório de RH",
                defaultextension=f".{extensao}", filetypes=((formato, f"*.{extensao}"),),
            )
            if not caminho: return
            try:
                resultado = gerar_relatorio_rh(tipo, formato, caminho, SESSAO.usuario)
                messagebox.showinfo("Relatórios", mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome), parent=self.root)
            except (ValueError, PermissionError, OSError, RuntimeError) as erro:
                messagebox.showerror("Relatórios", str(erro), parent=self.root)

        def _agendar_relatorio(self):
            self._formulario("Agendar relatório", (("tipo", "Tipo", "opcoes", ("Colaboradores", "Férias", "Folha")), ("formato", "Formato", "opcoes", ("PDF", "XLSX", "CSV")), ("frequencia", "Frequência", "opcoes", ("Semanal", "Mensal", "Trimestral")), ("destinatarios", "Destinatários", "texto", ())), lambda d: agendar_relatorio(d, SESSAO.usuario))

        def _auditoria(self):
            self._cabecalho("Auditoria de Recursos Humanos", "Rastreabilidade de operações, usuários, dados anteriores e dados posteriores.", acoes=False)
            try: registros = listar_auditoria_rh(SESSAO.usuario)
            except PermissionError as erro: messagebox.showerror("Auditoria", str(erro), parent=self.root); return
            card = criar_card(self.conteudo); card.pack(fill="both", expand=True)
            texto = tk.Text(card, bg=CORES["input"], fg=CORES["text_sec"], insertbackground=CORES["primary"], relief="flat", height=28, wrap="word")
            texto.pack(fill="both", expand=True, padx=1, pady=1)
            for r in registros: texto.insert("end", f"{r['criado_em']}  ·  {r['usuario_nome'] or r['usuario_id']}  ·  {r['acao']}  ·  {r['entidade']} #{r['entidade_id']}\n")
            texto.configure(state="disabled")

        def _configuracoes(self):
            self._cabecalho("Configurações de RH", "Permissões granulares e políticas operacionais do departamento.", acoes=False)
            if str(SESSAO.usuario.get("perfil", "")).lower() != "admin":
                estado = criar_estado_vazio(self.conteudo, "◇", "Acesso administrativo", "Somente administradores podem alterar permissões granulares de RH.", cor=COR_RH); estado.pack(fill="both", expand=True); return
            card = criar_card(self.conteudo); card.pack(fill="x")
            interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=18, pady=18)
            criar_titulo_secao(interior, "Matriz de ações", "A permissão por ação prevalece sobre a permissão genérica do módulo.")
            aviso = tk.Frame(interior, bg=CORES["warning_soft"])
            aviso.pack(fill="x", pady=(4, 14))
            tk.Label(
                aviso,
                text="CONTROLE DE JORNADA · MODO INTEGRAÇÃO/CONSULTA",
                font=FONTES["destaque"], fg=CORES["warning"], bg=CORES["warning_soft"],
            ).pack(anchor="w", padx=12, pady=(10, 3))
            tk.Label(
                aviso,
                text=("Os registros internos apoiam a operação, mas esta versão não se declara REP-P. "
                      "Quando aplicável, importe marcações de solução homologada e preserve o arquivo fiscal e as evidências exigidas pela Portaria MTP nº 671/2021."),
                font=FONTES["texto"], fg=CORES["text"], bg=CORES["warning_soft"],
                wraplength=840, justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 10))
            for acao, base in ACOES_RH.items():
                linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=2)
                tk.Label(linha, text=acao.replace("_", " ").upper(), font=("Inter", 8, "bold"), fg=CORES["text"], bg=CORES["card_secundario"], width=30, anchor="w").pack(side="left", padx=12, pady=8)
                tk.Label(linha, text=f"Base: {base}", font=FONTES["micro"], fg=CORES["text_muted"], bg=CORES["card_secundario"]).pack(side="left")
            tk.Label(interior, text="A gestão por usuário é realizada em Usuários e acessos. Dados de saúde, pessoais e remuneração devem permanecer restritos.", font=FONTES["texto"], fg=CORES["warning"], bg=CORES["card"], wraplength=760, justify="left").pack(anchor="w", pady=(14, 0))
