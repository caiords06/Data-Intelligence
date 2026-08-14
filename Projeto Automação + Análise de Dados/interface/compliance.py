"""Central operacional de conformidade, privacidade e evidências."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from auth.sessao import SESSAO
from interface.componentes import criar_botao, criar_cabecalho, criar_card, criar_metrica, criar_sidebar, preparar_janela_secundaria
from interface.tema import CORES, FONTES, LAYOUT, configurar_estilos_ttk
from services.compliance import (
    abrir_incidente_privacidade, atualizar_solicitacao_titular, avaliar_incidente_privacidade,
    criar_solicitacao_titular, definir_bloqueio_retencao, encerrar_bloqueio_retencao,
    listar_bloqueios_retencao, listar_incidentes_privacidade, listar_solicitacoes_titulares,
    listar_decisoes_analiticas, listar_ripd, listar_terceiros, listar_tratamentos, resumo_conformidade,
    salvar_decisao_analitica, salvar_ripd, salvar_terceiro, salvar_tratamento,
)


class TelaCompliance:
    def __init__(self, root, navegacao):
        self.root = root; self.navegacao = navegacao; self.tabelas = {}; self.registros = {}
        configurar_estilos_ttk(root)
        self.container = tk.Frame(root, bg=CORES["bg"]); self.container.pack(fill="both", expand=True)
        criar_sidebar(self.container, navegacao, ativo="compliance")
        self.area = tk.Frame(self.container, bg=CORES["bg"]); self.area.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
        criar_cabecalho(
            self.area, "Conformidade e privacidade",
            "Evidências de governança, direitos de titulares, incidentes, terceiros e retenção. A parametrização deve ser validada pelo encarregado e pela assessoria jurídica.",
            acao=("ATUALIZAR", self._carregar), breadcrumb="MINHA CENTRAL / GOVERNANÇA", etiqueta="LGPD · CONTROLES",
        )
        self.metricas = tk.Frame(self.area, bg=CORES["bg"]); self.metricas.pack(fill="x", pady=(0, 14))
        self.abas = ttk.Notebook(self.area, style="App.TNotebook"); self.abas.pack(fill="both", expand=True)
        self._montar_abas(); self._carregar()

    def _montar_abas(self):
        configuracoes = (
            ("tratamentos", "Tratamentos (RoPA)", ("id", "codigo", "nome", "base_legal", "status", "versao_registro"), (("NOVO", self._novo_tratamento), ("EDITAR", self._editar_tratamento))),
            ("titulares", "Direitos dos titulares", ("id", "protocolo", "tipo", "titular_nome", "status", "prazo_resposta", "versao_registro"), (("NOVA SOLICITAÇÃO", self._nova_solicitacao), ("ATUALIZAR", self._atualizar_solicitacao))),
            ("incidentes", "Incidentes", ("id", "protocolo", "titulo", "risco_dano", "status", "prazo_regulatorio", "versao_registro"), (("ABRIR INCIDENTE", self._novo_incidente), ("AVALIAR", self._avaliar_incidente))),
            ("ripd", "RIPD", ("id", "codigo", "titulo", "risco_residual", "status", "versao"), (("NOVA VERSÃO", self._novo_ripd),)),
            ("terceiros", "Terceiros e transferências", ("id", "nome", "papel", "contrato_dpa", "transferencia_internacional", "status", "versao_registro"), (("NOVO TERCEIRO", self._novo_terceiro), ("EDITAR", self._editar_terceiro))),
            ("decisoes", "Decisões analíticas", ("id", "codigo", "nome", "tipo", "impacto_pessoas", "revisao_humana", "status"), (("NOVA REGRA/MODELO", self._nova_decisao), ("EDITAR", self._editar_decisao))),
            ("retencao", "Retenção e bloqueio legal", ("id", "recurso_tipo", "recurso_id", "motivo", "fundamento", "valido_ate", "status"), (("NOVO BLOQUEIO", self._novo_bloqueio), ("ENCERRAR", self._encerrar_bloqueio))),
        )
        for chave, titulo, colunas, acoes in configuracoes:
            aba = tk.Frame(self.abas, bg=CORES["card"]); self.abas.add(aba, text=titulo)
            barra = tk.Frame(aba, bg=CORES["card"]); barra.pack(fill="x", padx=14, pady=(14, 8))
            for rotulo, comando in acoes:
                criar_botao(barra, rotulo, comando, tipo="secundario", compacto=True).pack(side="left", padx=(0, 7))
            tabela = ttk.Treeview(aba, columns=colunas, show="headings", style="App.Treeview")
            for coluna in colunas:
                tabela.heading(coluna, text=coluna.replace("_", " ").upper())
                tabela.column(coluna, width=150 if coluna not in {"id", "versao_registro"} else 70, minwidth=60, anchor="w")
            sy = ttk.Scrollbar(aba, orient="vertical", command=tabela.yview, style="App.Vertical.TScrollbar")
            sx = ttk.Scrollbar(aba, orient="horizontal", command=tabela.xview, style="App.Horizontal.TScrollbar")
            tabela.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
            tabela.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(0, 14)); sy.pack(side="right", fill="y", padx=(0, 14), pady=(0, 14)); sx.place(relx=0.01, rely=1, relwidth=.96, anchor="sw")
            self.tabelas[chave] = tabela

    def _carregar(self):
        try:
            resumo = resumo_conformidade(SESSAO.usuario)
            dados = {
                "tratamentos": listar_tratamentos(SESSAO.usuario), "titulares": listar_solicitacoes_titulares(SESSAO.usuario),
                "incidentes": listar_incidentes_privacidade(SESSAO.usuario), "ripd": listar_ripd(SESSAO.usuario),
                "terceiros": listar_terceiros(SESSAO.usuario), "decisoes": listar_decisoes_analiticas(SESSAO.usuario),
                "retencao": listar_bloqueios_retencao(SESSAO.usuario, somente_ativos=False),
            }
        except (PermissionError, ValueError, RuntimeError) as erro:
            messagebox.showerror("Conformidade", str(erro), parent=self.root); return
        for filho in self.metricas.winfo_children(): filho.destroy()
        for titulo, valor, cor in (
            ("TRATAMENTOS", resumo["tratamentos"], CORES["primary"]), ("DIREITOS ABERTOS", resumo["solicitacoes_abertas"], CORES["warning"]),
            ("INCIDENTES ABERTOS", resumo["incidentes_abertos"], CORES["danger"]), ("TERCEIROS PENDENTES", resumo["terceiros_pendentes"], CORES["purple"]),
        ):
            criar_metrica(self.metricas, titulo, str(valor), cor=cor).pack(side="left", fill="x", expand=True, padx=(0, 9))
        for chave, registros in dados.items():
            self.registros[chave] = {int(item["id"]): item for item in registros}
            tabela = self.tabelas[chave]; tabela.delete(*tabela.get_children())
            for item in registros:
                tabela.insert("", "end", iid=str(item["id"]), values=[self._valor(item.get(c)) for c in tabela["columns"]])

    @staticmethod
    def _valor(valor):
        if valor is None or valor == "": return "—"
        if isinstance(valor, bool): return "Sim" if valor else "Não"
        return str(valor)

    def _selecionado(self, chave):
        selecionados = self.tabelas[chave].selection()
        if not selecionados:
            messagebox.showinfo("Conformidade", "Selecione um registro.", parent=self.root); return None
        return self.registros[chave].get(int(selecionados[0]))

    def _formulario(self, titulo, campos, ao_salvar, *, inicial=None):
        janela = tk.Toplevel(self.root); janela.configure(bg=CORES["bg"]); preparar_janela_secundaria(janela, self.root, 720, 690, minimo=(600, 520))
        tk.Label(janela, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=24, pady=(22, 10))
        canvas = tk.Canvas(janela, bg=CORES["bg"], highlightthickness=0); canvas.pack(fill="both", expand=True, padx=24)
        barra = ttk.Scrollbar(canvas, orient="vertical", command=canvas.yview, style="App.Vertical.TScrollbar"); barra.pack(side="right", fill="y")
        corpo = tk.Frame(canvas, bg=CORES["bg"]); win = canvas.create_window((0, 0), window=corpo, anchor="nw"); canvas.configure(yscrollcommand=barra.set)
        corpo.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))); canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width-18))
        vars_ = {}
        for chave, rotulo, tipo, opcoes in campos:
            tk.Label(corpo, text=rotulo.upper(), font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["bg"]).pack(anchor="w", pady=(9, 4))
            valor = (inicial or {}).get(chave)
            if tipo == "bool":
                var = tk.BooleanVar(value=bool(valor)); widget = tk.Checkbutton(corpo, text="Sim", variable=var, bg=CORES["bg"], fg=CORES["text"], selectcolor=CORES["input"], activebackground=CORES["bg"])
            elif tipo == "combo":
                var = tk.StringVar(value=str(valor or opcoes[0])); widget = ttk.Combobox(corpo, textvariable=var, values=opcoes, state="readonly", style="App.TCombobox")
            else:
                var = tk.StringVar(value="" if valor is None else str(valor)); widget = tk.Entry(corpo, textvariable=var, font=FONTES["texto"], bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat")
            widget.pack(fill="x", ipady=7 if tipo == "texto" else 0); vars_[chave] = var
        status = tk.Label(janela, text="", font=FONTES["micro"], fg=CORES["danger"], bg=CORES["bg"]); status.pack(anchor="w", padx=24)
        def salvar():
            dados = {k: v.get() for k, v in vars_.items()}
            try: ao_salvar(dados); janela.destroy(); self._carregar()
            except (ValueError, PermissionError, RuntimeError) as erro: status.configure(text=str(erro))
        criar_botao(janela, "SALVAR", salvar).pack(anchor="e", padx=24, pady=18)

    def _campos_tratamento(self):
        return (("codigo", "Código", "texto", ()), ("nome", "Nome", "texto", ()), ("controlador", "Controlador", "texto", ()),
                ("operador", "Operadores", "texto", ()), ("encarregado", "Encarregado / contato", "texto", ()),
                ("finalidade", "Finalidade", "texto", ()), ("base_legal", "Base legal", "texto", ()),
                ("categorias_titulares", "Categorias de titulares", "texto", ()), ("categorias_dados", "Categorias de dados", "texto", ()),
                ("dados_sensiveis", "Há dados sensíveis", "bool", ()), ("compartilhamentos", "Compartilhamentos", "texto", ()),
                ("transferencia_internacional", "Transferência internacional", "bool", ()), ("paises_salvaguardas", "Países e salvaguardas", "texto", ()),
                ("prazo_retencao", "Prazo e critério de retenção", "texto", ()), ("medidas_seguranca", "Medidas de segurança", "texto", ()),
                ("status", "Status", "combo", ("Em revisão", "Ativo", "Suspenso", "Encerrado")))

    def _novo_tratamento(self): self._formulario("Novo tratamento", self._campos_tratamento(), lambda d: salvar_tratamento(d, SESSAO.usuario))
    def _editar_tratamento(self):
        item = self._selecionado("tratamentos")
        if item: self._formulario("Editar tratamento", self._campos_tratamento(), lambda d: salvar_tratamento(d, SESSAO.usuario, tratamento_id=item["id"], versao=item["versao_registro"]), inicial=item)
    def _nova_solicitacao(self):
        campos = (("tipo", "Direito", "combo", ("Confirmação", "Acesso", "Correção", "Anonimização", "Bloqueio", "Eliminação", "Portabilidade", "Informação", "Revogação")), ("titular_nome", "Titular", "texto", ()), ("canal", "Canal", "texto", ()), ("identidade_verificada", "Identidade verificada", "bool", ()), ("escopo", "Escopo da solicitação", "texto", ()))
        self._formulario("Nova solicitação de titular", campos, lambda d: criar_solicitacao_titular(d, SESSAO.usuario))
    def _atualizar_solicitacao(self):
        item = self._selecionado("titulares")
        if not item: return
        campos = (("status", "Status", "combo", ("Recebida", "Identidade pendente", "Em atendimento", "Aguardando titular", "Concluída", "Recusada")), ("identidade_verificada", "Identidade verificada", "bool", ()), ("resposta_resumo", "Resumo da resposta", "texto", ()), ("fundamento_recusa", "Fundamento da recusa", "texto", ()))
        self._formulario("Atualizar direito do titular", campos, lambda d: atualizar_solicitacao_titular(item["id"], d, SESSAO.usuario, versao=item["versao_registro"]), inicial=item)
    def _novo_incidente(self):
        campos = (("titulo", "Título", "texto", ()), ("descricao", "Descrição", "texto", ()), ("dados_afetados", "Dados afetados", "texto", ()), ("titulares_afetados", "Quantidade estimada de titulares", "texto", ()), ("risco_dano", "Risco/dano", "texto", ()), ("medidas_contencao", "Contenção inicial", "texto", ()))
        self._formulario("Abrir incidente de privacidade", campos, lambda d: abrir_incidente_privacidade(d, SESSAO.usuario))
    def _avaliar_incidente(self):
        item = self._selecionado("incidentes")
        if not item: return
        campos = (("status", "Status", "combo", ("Em avaliação", "Contido", "Em comunicação", "Monitoramento", "Encerrado")), ("dados_afetados", "Dados afetados", "texto", ()), ("titulares_afetados", "Titulares afetados", "texto", ()), ("risco_dano", "Risco/dano", "texto", ()), ("medidas_contencao", "Medidas de contenção", "texto", ()), ("comunicar_anpd", "Comunicar ANPD", "bool", ()), ("comunicar_titulares", "Comunicar titulares", "bool", ()), ("justificativa_decisao", "Justificativa da decisão", "texto", ()), ("comunicado_anpd_em", "Comunicação ANPD (ISO)", "texto", ()), ("comunicado_titulares_em", "Comunicação titulares (ISO)", "texto", ()))
        self._formulario("Avaliar incidente", campos, lambda d: avaliar_incidente_privacidade(item["id"], d, SESSAO.usuario, versao=item["versao_registro"]), inicial=item)
    def _novo_ripd(self):
        item = self._selecionado("ripd") if self.tabelas["ripd"].selection() else None
        inicial = dict(item or {})
        if item:
            inicial["riscos"] = "\n".join(item.get("riscos") or ())
            inicial["salvaguardas"] = "\n".join(item.get("salvaguardas") or ())
        campos = (("tratamento_id", "ID do tratamento (opcional)", "texto", ()), ("codigo", "Código", "texto", ()),
                  ("titulo", "Título", "texto", ()), ("necessidade_proporcionalidade", "Necessidade e proporcionalidade", "texto", ()),
                  ("riscos", "Riscos — um por linha", "texto", ()), ("salvaguardas", "Salvaguardas — uma por linha", "texto", ()),
                  ("risco_residual", "Risco residual", "texto", ()),
                  ("status", "Status", "combo", ("Rascunho", "Em revisão", "Aprovado")))
        self._formulario("Nova versão de RIPD", campos, lambda d: salvar_ripd(d, SESSAO.usuario), inicial=inicial)
    def _campos_terceiro(self):
        return (("nome", "Terceiro", "texto", ()), ("papel", "Papel", "combo", ("Operador", "Suboperador", "Controlador conjunto", "Fornecedor")), ("dados_tratados", "Dados tratados", "texto", ()), ("finalidade", "Finalidade", "texto", ()), ("contrato_dpa", "DPA/cláusulas aprovadas", "bool", ()), ("transferencia_internacional", "Transferência internacional", "bool", ()), ("mecanismo_transferencia", "Mecanismo/salvaguarda", "texto", ()), ("avaliacao_seguranca", "Avaliação de segurança", "texto", ()), ("proxima_revisao", "Próxima revisão (AAAA-MM-DD)", "texto", ()), ("status", "Status", "combo", ("Em avaliação", "Aprovado", "Suspenso", "Encerrado")))
    def _novo_terceiro(self): self._formulario("Novo terceiro / operador", self._campos_terceiro(), lambda d: salvar_terceiro(d, SESSAO.usuario))
    def _editar_terceiro(self):
        item = self._selecionado("terceiros")
        if item: self._formulario("Editar terceiro / operador", self._campos_terceiro(), lambda d: salvar_terceiro(d, SESSAO.usuario, terceiro_id=item["id"], versao=item["versao_registro"]), inicial=item)
    def _campos_decisao(self):
        return (("codigo", "Código", "texto", ()), ("nome", "Nome", "texto", ()),
                ("tipo", "Tipo", "combo", ("Regra determinística", "Modelo estatístico", "Modelo de IA", "Indicador")),
                ("finalidade", "Finalidade", "texto", ()), ("dados_entrada", "Dados de entrada", "texto", ()),
                ("logica_resumo", "Lógica / explicação", "texto", ()), ("impacto_pessoas", "Impacto sobre pessoas", "texto", ()),
                ("revisao_humana", "Exige revisão humana", "bool", ()), ("responsavel_id", "ID do responsável (opcional)", "texto", ()),
                ("versao", "Versão", "texto", ()), ("ultima_validacao", "Última validação (AAAA-MM-DD)", "texto", ()),
                ("status", "Status", "combo", ("Em homologação", "Ativo", "Suspenso", "Encerrado")))
    def _nova_decisao(self):
        self._formulario("Catalogar regra ou modelo", self._campos_decisao(), lambda d: salvar_decisao_analitica(d, SESSAO.usuario), inicial={"revisao_humana": True})
    def _editar_decisao(self):
        item = self._selecionado("decisoes")
        if item: self._formulario("Editar regra ou modelo", self._campos_decisao(), lambda d: salvar_decisao_analitica(d, SESSAO.usuario, decisao_id=item["id"]), inicial=item)
    def _novo_bloqueio(self):
        campos = (("recurso_tipo", "Tipo de recurso", "texto", ()), ("recurso_id", "ID do recurso", "texto", ()), ("motivo", "Motivo", "texto", ()), ("fundamento", "Fundamento legal/contratual", "texto", ()), ("valido_ate", "Válido até (opcional)", "texto", ()))
        self._formulario("Novo bloqueio legal de retenção", campos, lambda d: definir_bloqueio_retencao(d["recurso_tipo"], int(d["recurso_id"]), d["motivo"], d["fundamento"], SESSAO.usuario, valido_ate=d.get("valido_ate") or None))
    def _encerrar_bloqueio(self):
        item = self._selecionado("retencao")
        if item and messagebox.askyesno("Bloqueio legal", "Encerrar este bloqueio? A ação ficará auditada.", parent=self.root):
            try: encerrar_bloqueio_retencao(item["id"], SESSAO.usuario); self._carregar()
            except (PermissionError, ValueError) as erro: messagebox.showerror("Bloqueio legal", str(erro), parent=self.root)


__all__ = ("TelaCompliance",)
