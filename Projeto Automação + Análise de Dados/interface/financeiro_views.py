"""Workspace especializado do departamento Financeiro."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.departamentos.financeiro import (
    NATUREZAS,
    STATUS_ABERTOS,
    STATUS_TERMINAIS,
    analisar_financeiro,
    agendar_relatorio,
    anexar_documento,
    atualizar_lancamento,
    atualizar_status_vencidos,
    calcular_dre,
    cancelar_lancamento,
    conciliar_item,
    contabilizar_lancamento,
    criar_categoria,
    criar_conta,
    criar_lancamento,
    criar_parte,
    decidir_aprovacao,
    estornar_lancamento,
    gerar_alertas_financeiros,
    gerar_recorrencias_pendentes,
    gerar_relatorio_financeiro,
    importar_extrato,
    listar_aprovacoes_financeiras,
    listar_auditoria_financeira,
    listar_cartoes,
    listar_catalogos,
    listar_conciliacoes,
    listar_contas_com_saldo,
    listar_lancamentos,
    listar_orcamentos,
    listar_recorrencias,
    listar_relatorios_agendados,
    obter_lancamento,
    projetar_fluxo_caixa,
    registrar_baixa,
    resumo_financeiro,
    salvar_cartao,
    salvar_orcamento,
    salvar_plano_conta,
    submeter_aprovacao,
    tem_permissao_financeira,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_estado_vazio,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
    preparar_janela_secundaria,
)
from interface.grade_editavel import EditorGrade
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_FINANCEIRO = "#34D079"

GRUPOS_MENU = (
    ("FINANCEIRO", (("visao", "⌂", "Visão geral"),)),
    ("OPERAÇÕES", (
        ("lancamentos", "≡", "Lançamentos"),
        ("pagar", "↓", "Contas a pagar"),
        ("receber", "↑", "Contas a receber"),
        ("reembolsos", "$", "Reembolsos"),
        ("transferencias", "⇄", "Transferências"),
        ("recorrencias", "↻", "Recorrências"),
    )),
    ("TESOURARIA", (
        ("fluxo", "≋", "Fluxo de caixa"),
        ("bancos", "▣", "Bancos e contas"),
        ("conciliacao", "✓", "Conciliação"),
        ("cartoes", "▭", "Cartões corporativos"),
    )),
    ("PLANEJAMENTO", (
        ("orcamento", "▥", "Orçamento"),
        ("projecoes", "↗", "Projeções"),
        ("centros_custo", "◇", "Centros de custo"),
    )),
    ("GESTÃO", (
        ("dre", "▤", "DRE"),
        ("relatorios", "↥", "Relatórios"),
        ("aprovacoes_fin", "✓", "Aprovações"),
        ("auditoria_fin", "◎", "Auditoria"),
    )),
    ("CADASTROS", (
        ("plano_contas", "#", "Plano de contas"),
        ("categorias", "◈", "Categorias"),
        ("partes", "◉", "Clientes e fornecedores"),
    )),
)


ROTULOS = {
    chave: titulo
    for _grupo, itens in GRUPOS_MENU
    for chave, _icone, titulo in itens
}


def _moeda(centavos) -> str:
    valor = int(centavos or 0) / 100
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _data_br(valor) -> str:
    texto = str(valor or "")[:10]
    partes = texto.split("-")
    return "/".join(reversed(partes)) if len(partes) == 3 else texto


class FinanceiroViewsMixin:
    def _visao_geral(self):
        self._cabecalho(
            "Central financeira",
            "Posição de caixa, obrigações, recebíveis, orçamento e riscos no contexto empresarial atual.",
        )
        filtros = criar_card(self.conteudo)
        filtros.pack(fill="x", pady=(0, 13))
        linha = tk.Frame(filtros, bg=CORES["card"])
        linha.pack(fill="x", padx=16, pady=12)
        tk.Label(linha, text="PERÍODO", font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(side="left")
        for texto in ("Hoje", "Mês", "Trimestre", "Ano"):
            criar_botao(
                linha, texto.upper(), lambda periodo=texto: self._recarregar_visao(periodo),
                tipo="primario" if texto == self.periodo_visao else "fantasma", compacto=True,
            ).pack(side="left", padx=(7, 0))
        inicio, fim = self._intervalo_visao(self.periodo_visao)
        resumo = resumo_financeiro(SESSAO.usuario, inicio=inicio, fim=fim)
        grade = GradeResponsiva(self.conteudo, max_colunas=4, largura_minima=225, gap=9, bg=CORES["bg"])
        grade.pack(fill="x")
        metricas = (
            ("RECEBIDO", resumo["receitas_centavos"], "↑", COR_FINANCEIRO, "Receitas liquidadas no período"),
            ("PAGO", resumo["despesas_centavos"], "↓", CORES["danger_muted"], "Despesas liquidadas no período"),
            ("SALDO CONSOLIDADO", resumo["saldo_centavos"], "$", CORES["primary"], "Todas as contas ativas"),
            ("RESULTADO", resumo["resultado_centavos"], "◇", COR_FINANCEIRO if resumo["resultado_centavos"] >= 0 else CORES["danger"], "Receitas menos despesas"),
            ("PENDENTES", resumo["pendente_valor_centavos"], "◷", CORES["warning"], f"{resumo['pendentes']} obrigação(ões) aberta(s)"),
            ("VENCIDAS", resumo["vencidas"] * 100, "!", CORES["danger"], f"{resumo['vencidas']} conta(s) requerem atenção"),
            ("PRÓXIMOS 7 DIAS", resumo["proximos_sete"] * 100, "◷", CORES["warning"], f"{resumo['proximos_sete']} vencimento(s)"),
            ("CAIXA PROJETADO", resumo["saldo_minimo_projetado_centavos"], "↗", CORES["danger"] if resumo["risco_caixa"] else COR_FINANCEIRO, f"Menor saldo até {_data_br(resumo['data_saldo_minimo'])}"),
        )
        for titulo, valor, icone, cor, detalhe in metricas:
            exibicao = str(int(valor / 100)) if titulo in {"VENCIDAS", "PRÓXIMOS 7 DIAS"} else _moeda(valor)
            grade.adicionar(criar_metrica(grade, titulo, exibicao, icone=icone, cor=cor, detalhe=detalhe))
        self._atalhos()
        self._ciclo_financeiro()
        self._painel_alertas(resumo)


    def _intervalo_visao(self, periodo):
        hoje = date.today()
        if periodo == "Hoje":
            inicio = fim = hoje.isoformat()
        elif periodo == "Ano":
            inicio, fim = f"{hoje.year}-01-01", hoje.isoformat()
        elif periodo == "Trimestre":
            mes = ((hoje.month - 1) // 3) * 3 + 1
            inicio, fim = f"{hoje.year}-{mes:02d}-01", hoje.isoformat()
        else:
            inicio, fim = hoje.replace(day=1).isoformat(), hoje.isoformat()
        return inicio, fim


    def _recarregar_visao(self, periodo):
        self.container.destroy()
        type(self)(
            self.root, self.navegacao, secao="visao", periodo_visao=periodo,
        )


    def _atalhos(self):
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Acesso rápido", "Operações recorrentes do departamento.")
        grade = GradeResponsiva(interior, max_colunas=5, largura_minima=190, gap=8, bg=CORES["card"])
        grade.pack(fill="x")
        acoes = (
            ("+", "Novo lançamento", "Receita, despesa, ajuste ou título.", lambda: self._form_lancamento()),
            ("↓", "Conta a pagar", "Registre uma nova obrigação.", lambda: self._form_lancamento("Conta a pagar")),
            ("↑", "Conta a receber", "Registre um novo recebível.", lambda: self._form_lancamento("Conta a receber")),
            ("⇄", "Transferência", "Movimente entre contas sem afetar o resultado.", lambda: self._form_lancamento("Transferência")),
            ("↥", "Importar extrato", "OFX, CSV ou Excel para conciliação.", self._importar_extrato),
        )
        for icone, titulo, descricao, comando in acoes:
            bloco = criar_card(grade, fundo=CORES["card_secundario"])
            grade.adicionar(bloco)
            tk.Label(bloco, text=icone, font=("Segoe UI Symbol", 16, "bold"), fg=COR_FINANCEIRO, bg=CORES["card_secundario"]).pack(anchor="w", padx=13, pady=(12, 5))
            tk.Label(bloco, text=titulo, font=("Inter", 9, "bold"), fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w", padx=13)
            tk.Label(bloco, text=descricao, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card_secundario"], wraplength=170, justify="left").pack(anchor="w", padx=13, pady=(4, 8))
            criar_botao(bloco, "ABRIR  →", comando, tipo="fantasma", compacto=True).pack(side="bottom", anchor="w", pady=(0, 5))


    def _ciclo_financeiro(self):
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Ciclo financeiro", "Clique em uma etapa para consultar os registros relacionados.")
        grade = GradeResponsiva(interior, max_colunas=7, largura_minima=125, gap=6, bg=CORES["card"])
        grade.pack(fill="x")
        etapas = (
            ("PREVISTO", "pagar"), ("AGUARDANDO APROVAÇÃO", "aprovacoes_fin"),
            ("APROVADO", "pagar"), ("A VENCER", "pagar"), ("VENCIDO", "pagar"),
            ("LIQUIDADO", "lancamentos"), ("CONCILIADO", "conciliacao"),
        )
        for etapa, destino in etapas:
            botao = tk.Button(
                grade, text=etapa, command=lambda alvo=destino: self.abrir_secao(alvo),
                font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["input"],
                activebackground=CORES["card_hover"], activeforeground=CORES["text"],
                relief="flat", bd=0, cursor="hand2", padx=8, pady=18,
                highlightthickness=1, highlightbackground=CORES["border_soft"],
            )
            grade.adicionar(botao)


    def _painel_alertas(self, resumo):
        card = criar_card(self.conteudo, destaque=bool(resumo["risco_caixa"] or resumo["vencidas"]))
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Alertas e inteligência financeira", "O sistema monitora vencimentos, caixa e consumo orçamentário.")
        analise = analisar_financeiro(SESSAO.usuario)
        for mensagem in analise["alertas"]:
            tk.Label(interior, text=f"●  {mensagem}", font=FONTES["texto_pequeno"], fg=CORES["danger_muted"] if "negativo" in mensagem or "vencida" in mensagem else CORES["warning"], bg=CORES["card"], anchor="w", justify="left", wraplength=1100).pack(fill="x", pady=2)


    def _livro(self):
        presets = {
            "pagar": ({"Conta a pagar", "Despesa"}, "Contas a pagar", "Obrigações, aprovações e pagamentos."),
            "receber": ({"Conta a receber", "Receita"}, "Contas a receber", "Recebíveis, cobranças, pagamentos parciais e saldos."),
            "reembolsos": ({"Reembolso"}, "Reembolsos", "Solicitações aprovadas e pagamentos aos colaboradores."),
            "transferencias": ({"Transferência"}, "Transferências", "Movimentos neutros entre contas da empresa."),
            "lancamentos": (None, "Lançamentos", "Livro operacional completo do Financeiro."),
        }
        naturezas, titulo, subtitulo = presets.get(self.secao, presets["lancamentos"])
        self._cabecalho(titulo, subtitulo)
        self.naturezas_ativas = naturezas
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        filtros = tk.Frame(painel, bg=CORES["card"])
        filtros.pack(fill="x", padx=16, pady=14)
        catalogos = listar_catalogos(SESSAO.usuario)
        self.pesquisa_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Todos")
        self.natureza_var = tk.StringVar(value="Todas")
        self.inicio_var = tk.StringVar()
        self.fim_var = tk.StringVar()
        self.conta_var = tk.StringVar(value="Todas")
        self.categoria_var = tk.StringVar(value="Todas")
        self.centro_var = tk.StringVar(value="Todos")
        self.departamento_var = tk.StringVar(value="Todos")
        self.projeto_var = tk.StringVar(value="Todos")
        self.mapas_filtro = {
            "conta": {item["nome"]: item["id"] for item in catalogos["contas"]},
            "categoria": {item["nome"]: item["id"] for item in catalogos["categorias"]},
            "centro": {f"{item['codigo']} · {item['nome']}": item["id"] for item in catalogos["centros_custo"]},
            "departamento": {item["nome"]: item["id"] for item in catalogos["departamentos"]},
            "projeto": {f"{item['codigo']} · {item['nome']}": item["id"] for item in catalogos["projetos"]},
        }
        grade_filtros = GradeResponsiva(
            filtros, max_colunas=5, largura_minima=170, gap=7, bg=CORES["card"]
        )
        grade_filtros.pack(fill="x")

        def campo(rotulo, variavel, *, valores=None, pesquisa=False):
            grupo = tk.Frame(grade_filtros, bg=CORES["card"])
            tk.Label(
                grupo, text=rotulo.upper(), font=("Inter", 7, "bold"),
                fg=CORES["text_muted"], bg=CORES["card"],
            ).pack(anchor="w", pady=(0, 4))
            if valores is None:
                widget = tk.Entry(
                    grupo, textvariable=variavel, font=FONTES["texto_pequeno"],
                    bg=CORES["input"], fg=CORES["text"],
                    insertbackground=CORES["primary"], relief="flat", bd=0,
                )
                widget.pack(fill="x", ipady=7)
                if pesquisa:
                    widget.bind("<Return>", lambda _e: self._aplicar_filtros())
            else:
                widget = ttk.Combobox(
                    grupo, textvariable=variavel, values=valores,
                    state="readonly", style="Dark.TCombobox",
                )
                widget.pack(fill="x")
            grade_filtros.adicionar(grupo)

        campo("Pesquisar", self.pesquisa_var, pesquisa=True)
        campo("Status", self.status_var, valores=("Todos", *sorted(STATUS_ABERTOS | STATUS_TERMINAIS)))
        if naturezas is None:
            campo("Tipo", self.natureza_var, valores=("Todas", *sorted(NATUREZAS)))
        campo("Competência inicial", self.inicio_var)
        campo("Competência final", self.fim_var)
        campo("Conta", self.conta_var, valores=("Todas", *self.mapas_filtro["conta"].keys()))
        campo("Categoria", self.categoria_var, valores=("Todas", *self.mapas_filtro["categoria"].keys()))
        campo("Centro de custo", self.centro_var, valores=("Todos", *self.mapas_filtro["centro"].keys()))
        campo("Departamento", self.departamento_var, valores=("Todos", *self.mapas_filtro["departamento"].keys()))
        campo("Projeto", self.projeto_var, valores=("Todos", *self.mapas_filtro["projeto"].keys()))
        grupo_acao = tk.Frame(grade_filtros, bg=CORES["card"])
        criar_botao(
            grupo_acao, "APLICAR FILTROS", self._aplicar_filtros,
            tipo="secundario", compacto=True,
        ).pack(fill="x", pady=(17, 0))
        grade_filtros.adicionar(grupo_acao)
        colunas = (
            ("competencia", "COMPETÊNCIA", 105), ("descricao", "DESCRIÇÃO", 260),
            ("natureza", "TIPO", 120), ("parte_nome", "CLIENTE / FORNECEDOR", 165),
            ("categoria_nome", "CATEGORIA", 140), ("centro_custo_nome", "CENTRO DE CUSTO", 145),
            ("valor", "VALOR", 110), ("saldo", "SALDO", 110),
            ("vencimento", "VENCIMENTO", 105), ("status", "STATUS", 145),
        )
        self.tabela = self._criar_tabela(painel, colunas, altura=330)
        self.editor_grade = EditorGrade(
            self.tabela, colunas_editaveis={"competencia", "descricao", "vencimento"},
            salvar=self._salvar_edicao_grade_financeiro, parent=self.root, titulo="Lançamentos financeiros",
        )
        barra_grade = tk.Frame(painel, bg=CORES["card"])
        barra_grade.pack(fill="x", padx=16, pady=(5, 0))
        tk.Label(barra_grade, text="Dica: duplo clique em competência, descrição ou vencimento para editar.", bg=CORES["card"], fg=CORES["text_muted"], font=FONTES["micro"]).pack(side="left")
        criar_botao(barra_grade, "EXPORTAR XLSX", lambda: self.editor_grade.exportar_xlsx(), tipo="fantasma", compacto=True).pack(side="right", padx=(5,0))
        criar_botao(barra_grade, "EXPORTAR CSV", lambda: self.editor_grade.exportar_csv(), tipo="fantasma", compacto=True).pack(side="right")
        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=16, pady=13)
        grade_botoes = GradeResponsiva(
            rodape, max_colunas=7, largura_minima=118, gap=6, bg=CORES["card"]
        )
        grade_botoes.pack(fill="x")
        botoes = (
            ("VER DETALHES", self._detalhes_selecionado, "secundario", "visualizar"),
            ("EDITAR", self._editar_selecionado, "secundario", "editar"),
            ("ENVIAR PARA APROVAÇÃO", self._submeter_selecionado, "secundario", "solicitar_aprovacao"),
            ("APROVAR", lambda: self._decidir_selecionado("Aprovado"), "sucesso", "aprovar"),
            ("REGISTRAR BAIXA", self._baixar_selecionado, "primario", "liquidar"),
            ("CONTABILIZAR", self._contabilizar_selecionado, "secundario", "contabilizar"),
            ("CANCELAR", self._cancelar_selecionado, "perigo", "cancelar"),
            ("ESTORNAR", self._estornar_selecionado, "perigo", "cancelar"),
        )
        for texto, comando, tipo, acao in botoes:
            botao = criar_botao(grade_botoes, texto, comando, tipo=tipo, compacto=True)
            if not tem_permissao_financeira(SESSAO.usuario, acao):
                botao.configure(state="disabled", cursor="arrow")
            grade_botoes.adicionar(botao)
        navegacao_pagina = tk.Frame(rodape, bg=CORES["card"])
        navegacao_pagina.pack(fill="x", pady=(8, 0))
        criar_botao(
            navegacao_pagina, "← ANTERIOR", lambda: self._mudar_pagina(-1),
            tipo="fantasma", compacto=True,
        ).pack(side="left")
        criar_botao(
            navegacao_pagina, "PRÓXIMA →", lambda: self._mudar_pagina(1),
            tipo="fantasma", compacto=True,
        ).pack(side="left", padx=5)
        self.label_pagina = tk.Label(navegacao_pagina, text="Página 1 de 1", font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card"])
        self.label_pagina.pack(side="right")
        self._carregar_livro(naturezas)


    def _aplicar_filtros(self):
        self.pagina = 1
        self._carregar_livro(self.naturezas_ativas)


    def _mudar_pagina(self, deslocamento):
        destino = max(1, min(self.paginas, self.pagina + int(deslocamento)))
        if destino != self.pagina:
            self.pagina = destino
            self._carregar_livro(self.naturezas_ativas)


    def _criar_tabela(self, parent, colunas, *, altura=300):
        area = tk.Frame(parent, bg=CORES["card"])
        area.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        tabela = ttk.Treeview(area, columns=tuple(c[0] for c in colunas), show="headings", style="Dark.Treeview", height=max(5, altura // 34))
        for chave, titulo, largura in colunas:
            tabela.heading(chave, text=titulo)
            tabela.column(chave, width=largura, minwidth=70, anchor="w", stretch=chave in {"descricao", "nome"})
        y = ttk.Scrollbar(area, orient="vertical", command=tabela.yview, style="Dark.Vertical.TScrollbar")
        x = ttk.Scrollbar(area, orient="horizontal", command=tabela.xview, style="Dark.Horizontal.TScrollbar")
        tabela.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        tabela.grid(row=0, column=0, sticky="nsew")
        y.grid(row=0, column=1, sticky="ns")
        x.grid(row=1, column=0, sticky="ew")
        area.grid_rowconfigure(0, weight=1, minsize=altura)
        area.grid_columnconfigure(0, weight=1)
        estado = criar_estado_vazio(area, "$", "Nenhum registro encontrado", "Crie um registro ou altere os filtros para continuar.", cor=COR_FINANCEIRO)
        tabela._estado_vazio = estado
        adicionar_divisorias_treeview(tabela, sobreposicao=estado)
        return tabela


    def _preencher_tabela(self, linhas, valores):
        for iid in self.tabela.get_children():
            self.tabela.delete(iid)
        for indice, linha in enumerate(linhas, 1):
            identificador = linha.get("id") if hasattr(linha, "get") else None
            iid = str(identificador) if identificador not in (None, "") else f"linha-{indice}"
            if self.tabela.exists(iid):
                iid = f"{iid}-{indice}"
            self.tabela.insert("", "end", iid=iid, values=valores(linha))
        if linhas:
            self.tabela._estado_vazio.place_forget()
        else:
            self.tabela._estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.tabela._estado_vazio.lift()


    def _salvar_edicao_grade_financeiro(self, iid, coluna, valor):
        try:
            identificador = int(str(iid).split("-")[0])
        except ValueError as erro:
            raise ValueError("Esta linha é calculada e não pode ser editada diretamente.") from erro
        atualizar_lancamento(identificador, {coluna: valor}, SESSAO.usuario)


    def _carregar_livro(self, naturezas=None):
        natureza = self.natureza_var.get() if naturezas is None else "Todas"
        try:
            resultado = listar_lancamentos(
                SESSAO.usuario, pagina=self.pagina, pesquisa=self.pesquisa_var.get(),
                status=self.status_var.get(), natureza=natureza,
                naturezas=tuple(naturezas or ()), inicio=self.inicio_var.get() or None,
                fim=self.fim_var.get() or None,
                conta_id=self.mapas_filtro["conta"].get(self.conta_var.get()),
                categoria_id=self.mapas_filtro["categoria"].get(self.categoria_var.get()),
                centro_custo_id=self.mapas_filtro["centro"].get(self.centro_var.get()),
                departamento_id=self.mapas_filtro["departamento"].get(self.departamento_var.get()),
                projeto_id=self.mapas_filtro["projeto"].get(self.projeto_var.get()),
            )
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Filtros financeiros", str(erro), parent=self.root)
            return
        registros = resultado["registros"]
        self.registros = registros
        self.pagina = resultado["pagina"]
        self.paginas = resultado["paginas"]
        self._preencher_tabela(registros, lambda r: (
            _data_br(r["competencia"]), r["descricao"], r["natureza"], r.get("parte_nome") or "—",
            r.get("categoria_nome") or "Não classificado", r.get("centro_custo_nome") or "—",
            _moeda(r["valor_original_centavos"]), _moeda(r["saldo_centavos"]),
            _data_br(r["vencimento"]) or "—", r["status"],
        ))
        self.label_pagina.configure(text=f"{resultado['total']} registro(s)  ·  Página {resultado['pagina']} de {resultado['paginas']}")


    def _selecionado(self):
        selecao = self.tabela.selection() if self.tabela else ()
        if not selecao:
            messagebox.showinfo("Financeiro", "Selecione um registro para continuar.", parent=self.root)
            return None
        return int(selecao[0])


    def _detalhes_selecionado(self):
        identificador = self._selecionado()
        if identificador:
            self._janela_detalhes(identificador)


    def _janela_detalhes(self, identificador):
        item = obter_lancamento(identificador, SESSAO.usuario)
        janela = tk.Toplevel(self.root)
        janela.title(f"Lançamento FIN-{abs(int(identificador)):06d}")
        preparar_janela_secundaria(janela, self.root, 830, 650, minimo=(720, 560))
        janela.configure(bg=CORES["bg"])
        tk.Label(janela, text=f"FIN-{abs(int(identificador)):06d}  ·  {item['descricao']}", font=FONTES["titulo_grande"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=26, pady=(22, 4))
        tk.Label(janela, text=f"{item['natureza']}  ·  {item['status']}  ·  {_moeda(item['valor_original_centavos'])}", font=FONTES["texto"], fg=COR_FINANCEIRO, bg=CORES["bg"]).pack(anchor="w", padx=26, pady=(0, 14))
        notebook = ttk.Notebook(janela, style="Dark.TNotebook")
        notebook.pack(fill="both", expand=True, padx=26)
        resumo = tk.Frame(notebook, bg=CORES["card"])
        historico = tk.Frame(notebook, bg=CORES["card"])
        notebook.add(resumo, text="Resumo")
        notebook.add(historico, text="Auditoria")
        dados = (
            ("Competência", _data_br(item["competencia"])), ("Vencimento", _data_br(item["vencimento"]) or "—"),
            ("Liquidado", _moeda(item["valor_liquidado_centavos"])), ("Saldo", _moeda(int(item["valor_original_centavos"]) - int(item["valor_liquidado_centavos"]))),
            ("Categoria", item.get("categoria_nome") or "Não classificado"), ("Centro de custo", item.get("centro_custo_nome") or "—"),
            ("Documento", item.get("documento_numero") or "—"), ("Nota fiscal", item.get("nota_fiscal") or "—"),
            ("Conciliado", "Sim" if item["conciliado"] else "Não"), ("Contabilizado", "Sim" if item["contabilizado"] else "Não"),
        )
        for indice, (rotulo, valor) in enumerate(dados):
            bloco = tk.Frame(resumo, bg=CORES["card_secundario"])
            bloco.grid(row=indice // 2, column=indice % 2, sticky="ew", padx=8, pady=6)
            resumo.grid_columnconfigure(indice % 2, weight=1)
            tk.Label(bloco, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_muted"], bg=CORES["card_secundario"]).pack(anchor="w", padx=12, pady=(8, 2))
            tk.Label(bloco, text=str(valor), font=FONTES["texto"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w", padx=12, pady=(0, 8))
        texto = tk.Text(historico, bg=CORES["input"], fg=CORES["text_sec"], relief="flat", bd=0, font=("Consolas", 9), wrap="word")
        texto.pack(fill="both", expand=True, padx=12, pady=12)
        for evento in item["auditoria"]:
            texto.insert("end", f"{evento['criado_em']}  ·  {evento['acao']}  ·  usuário #{evento['usuario_id']}\n")
        texto.configure(state="disabled")
        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=26, pady=18)
        criar_botao(rodape, "ANEXAR DOCUMENTO", lambda: self._anexar(identificador), tipo="secundario", compacto=True).pack(side="left")
        criar_botao(rodape, "FECHAR", janela.destroy, tipo="secundario", compacto=True).pack(side="right")


    def _editar_selecionado(self):
        identificador = self._selecionado()
        if identificador:
            self._form_lancamento(registro_id=identificador)


    def _baixar_selecionado(self):
        identificador = self._selecionado()
        if identificador:
            self._form_baixa(identificador)


    def _decidir_selecionado(self, decisao):
        identificador = self._selecionado()
        if not identificador:
            return
        try:
            decidir_aprovacao(identificador, decisao, "Decisão registrada pela interface financeira.", SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Aprovação", str(erro), parent=self.root)
            return
        self.abrir_secao(self.secao)


    def _submeter_selecionado(self):
        identificador = self._selecionado()
        if not identificador:
            return
        try:
            submeter_aprovacao(identificador, SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Enviar para aprovação", str(erro), parent=self.root)
            return
        self.abrir_secao(self.secao)


    def _contabilizar_selecionado(self):
        identificador = self._selecionado()
        if not identificador:
            return
        try:
            contabilizar_lancamento(identificador, SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Contabilizar", str(erro), parent=self.root)
            return
        messagebox.showinfo("Contabilizar", "Lançamento contabilizado com rastreabilidade.", parent=self.root)
        self.abrir_secao(self.secao)


    def _cancelar_selecionado(self):
        identificador = self._selecionado()
        if not identificador:
            return
        motivo = self._form_simples_valor("Cancelar lançamento", "Motivo do cancelamento")
        if not motivo:
            return
        try:
            cancelar_lancamento(identificador, motivo, SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Cancelar", str(erro), parent=self.root)
            return
        self.abrir_secao(self.secao)


    def _estornar_selecionado(self):
        identificador = self._selecionado()
        if not identificador:
            return
        motivo = self._form_simples_valor("Estornar lançamento", "Motivo do estorno")
        if not motivo:
            return
        if not messagebox.askyesno(
            "Confirmar estorno",
            "O saldo será revertido, mas o registro e sua auditoria serão preservados. Continuar?",
            parent=self.root,
        ):
            return
        try:
            estornar_lancamento(identificador, motivo, SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Estornar", str(erro), parent=self.root)
            return
        self.abrir_secao(self.secao)


    def _bancos(self):
        self._cabecalho("Bancos e contas", "Saldos atual, conciliado e projetado por conta financeira.")
        criar_botao(self.conteudo, "+  NOVA CONTA", self._form_conta, compacto=True).pack(anchor="e", pady=(0, 10))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("nome", "CONTA", 220), ("banco", "BANCO", 170), ("tipo", "TIPO", 150), ("saldo", "SALDO ATUAL", 150), ("status", "STATUS", 110)), altura=370)
        contas = listar_contas_com_saldo(SESSAO.usuario)
        self._preencher_tabela(contas, lambda r: (r["nome"], r.get("banco") or "—", r["tipo"], _moeda(r["saldo_centavos"]), r["status"]))


    def _orcamentos(self):
        self._cabecalho("Orçamento", "Planejado, realizado, disponível e alertas por centro de custo e categoria.")
        criar_botao(self.conteudo, "+  NOVO ORÇAMENTO", self._form_orcamento, compacto=True).pack(anchor="e", pady=(0, 10))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("competencia", "COMPETÊNCIA", 110), ("centro", "CENTRO DE CUSTO", 190), ("categoria", "CATEGORIA", 170), ("planejado", "PLANEJADO", 130), ("realizado", "REALIZADO", 130), ("disponivel", "DISPONÍVEL", 130), ("uso", "UTILIZADO", 105), ("status", "STATUS", 110)), altura=370)
        itens = listar_orcamentos(SESSAO.usuario)
        self._preencher_tabela(itens, lambda r: (f"{r['mes']:02d}/{r['ano']}", r.get("centro_custo_nome") or "Consolidado", r.get("categoria_nome") or "Todas", _moeda(r["planejado_centavos"]), _moeda(r["realizado_centavos"]), _moeda(r["disponivel_centavos"]), f"{r['utilizado_percentual']:.1f}%", r["status"]))


    def _fluxo_caixa(self, titulo):
        self._cabecalho(titulo, "Saldo atual + entradas futuras − saídas futuras, com cenários de risco.")
        controle = criar_card(self.conteudo)
        controle.pack(fill="x", pady=(0, 12))
        linha = tk.Frame(controle, bg=CORES["card"])
        linha.pack(fill="x", padx=16, pady=12)
        cenario = tk.StringVar(value="Realista")
        dias = tk.StringVar(value="30")
        ttk.Combobox(linha, textvariable=cenario, values=("Realista", "Otimista", "Pessimista"), state="readonly", width=18, style="Dark.TCombobox").pack(side="left")
        ttk.Combobox(linha, textvariable=dias, values=("7", "15", "30", "60", "90", "180", "365"), state="readonly", width=9, style="Dark.TCombobox").pack(side="left", padx=(8, 0))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("data", "DATA", 120), ("entradas", "ENTRADAS", 160), ("saidas", "SAÍDAS", 160), ("saldo", "SALDO PROJETADO", 180), ("cenario", "CENÁRIO", 120)), altura=390)
        def carregar():
            itens = projetar_fluxo_caixa(SESSAO.usuario, dias=int(dias.get()), cenario=cenario.get())
            self._preencher_tabela(itens, lambda r: (_data_br(r["data"]), _moeda(r["entradas_centavos"]), _moeda(r["saidas_centavos"]), _moeda(r["saldo_projetado_centavos"]), r["cenario"]))
        criar_botao(linha, "RECALCULAR", carregar, tipo="secundario", compacto=True).pack(side="left", padx=(8, 0))
        carregar()


    def _conciliacao(self):
        self._cabecalho("Conciliação bancária", "Compare extratos OFX, CSV ou Excel com o livro financeiro e confirme correspondências.")
        criar_botao(self.conteudo, "↑  IMPORTAR EXTRATO", self._importar_extrato, compacto=True).pack(anchor="e", pady=(0, 10))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("data", "DATA", 105), ("descricao", "MOVIMENTAÇÃO BANCÁRIA", 280), ("conta", "CONTA", 150), ("valor", "VALOR", 120), ("lancamento", "CORRESPONDÊNCIA", 250), ("score", "SCORE", 80), ("status", "STATUS", 150)), altura=350)
        itens = listar_conciliacoes(SESSAO.usuario)
        self.registros = itens
        self._preencher_tabela(itens, lambda r: (_data_br(r["data"]), r["descricao"], r["conta_nome"], _moeda(r["valor_centavos"]), r.get("lancamento_descricao") or "Sem correspondência", f"{r['score']}%", r["status"]))
        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=16, pady=13)
        criar_botao(rodape, "CONCILIAR SUGESTÃO", self._conciliar_selecionado, tipo="sucesso", compacto=True).pack(side="left")


    def _conciliar_selecionado(self):
        item_id = self._selecionado()
        if not item_id:
            return
        item = next((r for r in self.registros if int(r["id"]) == item_id), None)
        if not item or not item.get("lancamento_id"):
            messagebox.showinfo("Conciliação", "O item ainda não possui uma correspondência sugerida.", parent=self.root)
            return
        try:
            conciliar_item(item_id, int(item["lancamento_id"]), SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Conciliação", str(erro), parent=self.root)
            return
        self.abrir_secao("conciliacao")


    def _dre(self):
        self._cabecalho("DRE gerencial", "Resultado por competência com classificação contábil e trilha para drill-down.")
        dre = calcular_dre(SESSAO.usuario)
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("linha", "DEMONSTRAÇÃO DO RESULTADO", 520), ("valor", "VALOR", 180)), altura=380)
        itens = [{"id": indice + 1, "linha": nome, "valor": valor} for indice, (nome, valor) in enumerate(dre["linhas"])]
        self._preencher_tabela(itens, lambda r: (r["linha"], _moeda(r["valor"])))
        if dre["nao_classificado_centavos"]:
            tk.Label(painel, text=f"●  Existem {_moeda(abs(dre['nao_classificado_centavos']))} sem classificação no plano de contas.", font=FONTES["texto_pequeno"], fg=CORES["warning"], bg=CORES["card"]).pack(anchor="w", padx=16, pady=12)


    def _relatorios(self):
        self._cabecalho("Central de relatórios financeiros", "Visualize, exporte e prepare relatórios para envio ou agendamento.")
        criar_botao(self.conteudo, "◷  AGENDAR RELATÓRIO", self._form_agendamento_relatorio, tipo="secundario", compacto=True).pack(anchor="e", pady=(0, 10))
        grade = GradeResponsiva(self.conteudo, max_colunas=3, largura_minima=250, gap=10, bg=CORES["bg"])
        grade.pack(fill="x")
        tipos = ("Contas a pagar", "Contas a receber", "Fluxo de caixa", "DRE", "Orçamento x realizado", "Auditoria financeira")
        for tipo in tipos:
            card = criar_card(grade)
            grade.adicionar(card)
            tk.Label(card, text=tipo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card"]).pack(anchor="w", padx=16, pady=(15, 5))
            tk.Label(card, text="Filtros do contexto atual, trilha e exportação.", font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w", padx=16)
            botoes = tk.Frame(card, bg=CORES["card"])
            botoes.pack(fill="x", padx=12, pady=13)
            for formato in ("PDF", "Excel", "CSV", "HTML"):
                criar_botao(botoes, formato.upper(), lambda t=tipo, f=formato: self._gerar_relatorio(t, f), tipo="fantasma", compacto=True).pack(side="left", padx=2)
        agendamentos = listar_relatorios_agendados(SESSAO.usuario)
        if agendamentos:
            painel = criar_card(self.conteudo)
            painel.pack(fill="x", pady=(13, 0))
            interior = tk.Frame(painel, bg=CORES["card"])
            interior.pack(fill="x", padx=16, pady=14)
            criar_titulo_secao(interior, "Envios e gerações agendadas")
            for item in agendamentos:
                tk.Label(interior, text=f"◷  {item['nome']}  ·  {item['frequencia']}  ·  {item['formato']}  ·  próxima: {_data_br(item['proxima_execucao']) or '—'}", font=FONTES["texto_pequeno"], fg=CORES["text_sec"], bg=CORES["card"], anchor="w").pack(fill="x", pady=3)


    def _aprovacoes(self):
        self._cabecalho("Aprovações financeiras", "Alçadas por valor, decisão humana e histórico imutável.")
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("descricao", "DESCRIÇÃO", 280), ("natureza", "TIPO", 120), ("valor", "VALOR", 130), ("nivel", "NÍVEL", 75), ("perfil", "APROVADOR", 130), ("vencimento", "VENCIMENTO", 110), ("status", "STATUS", 120)), altura=350)
        itens = listar_aprovacoes_financeiras(SESSAO.usuario, status="Todos")
        self.registros = itens
        self._preencher_tabela(itens, lambda r: (r["descricao"], r["natureza"], _moeda(r["valor_original_centavos"]), r["nivel"], r["perfil_aprovador"], _data_br(r["vencimento"]) or "—", r["status"]))
        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=16, pady=13)
        criar_botao(rodape, "APROVAR", lambda: self._decidir_aprovacao_lista("Aprovado"), tipo="sucesso", compacto=True).pack(side="left")
        criar_botao(rodape, "SOLICITAR ALTERAÇÃO", lambda: self._decidir_aprovacao_lista("Alteração solicitada"), tipo="secundario", compacto=True).pack(side="left", padx=7)
        criar_botao(rodape, "REJEITAR", lambda: self._decidir_aprovacao_lista("Rejeitado"), tipo="perigo", compacto=True).pack(side="left")


    def _decidir_aprovacao_lista(self, decisao):
        aprovacao_id = self._selecionado()
        if not aprovacao_id:
            return
        item = next((r for r in self.registros if int(r["id"]) == aprovacao_id), None)
        if not item:
            return
        comentario = self._form_simples_valor("Decisão financeira", "Comentário") or "Decisão registrada."
        try:
            decidir_aprovacao(
                int(item["lancamento_id"]), decisao, comentario, SESSAO.usuario,
                aprovacao_id=int(item["id"]),
            )
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Aprovação", str(erro), parent=self.root)
            return
        self.abrir_secao("aprovacoes_fin")


    def _auditoria(self):
        self._cabecalho("Auditoria financeira", "Quem fez o quê, em qual registro e quando. Eventos não são apagados.")
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("data", "DATA / HORA", 160), ("usuario", "USUÁRIO", 180), ("acao", "AÇÃO", 230), ("entidade", "ENTIDADE", 180), ("id", "REGISTRO", 90)), altura=390)
        itens = listar_auditoria_financeira(SESSAO.usuario)
        self._preencher_tabela(itens, lambda r: (str(r["criado_em"])[:19], r.get("usuario_nome") or f"#{r.get('usuario_id', '')}", r["acao"].replace("_", " ").title(), r["entidade"], r["entidade_id"]))


    def _plano_contas(self):
        self._cabecalho("Plano de contas", "Estrutura contábil que classifica lançamentos e alimenta a DRE.")
        criar_botao(self.conteudo, "+  NOVA CONTA CONTÁBIL", self._form_plano, compacto=True).pack(anchor="e", pady=(0, 10))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("codigo", "CÓDIGO", 110), ("nome", "CONTA", 280), ("natureza", "NATUREZA", 120), ("grupo", "GRUPO DRE", 220)), altura=390)
        itens = listar_catalogos(SESSAO.usuario)["plano_contas"]
        self._preencher_tabela(itens, lambda r: (r["codigo"], r["nome"], r["natureza"], r["grupo_dre"]))


    def _categorias(self):
        self._cabecalho("Categorias financeiras", "Classificação operacional vinculada ao plano de contas.")
        criar_botao(self.conteudo, "+  NOVA CATEGORIA", self._form_categoria, compacto=True).pack(anchor="e", pady=(0, 10))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("nome", "CATEGORIA", 300), ("natureza", "NATUREZA", 150), ("plano", "CONTA CONTÁBIL", 130)), altura=390)
        itens = listar_catalogos(SESSAO.usuario)["categorias"]
        self._preencher_tabela(itens, lambda r: (r["nome"], r["natureza"], r.get("plano_conta_id") or "—"))


    def _partes(self):
        self._cabecalho("Clientes e fornecedores", "Cadastro centralizado compartilhável com Compras, Estoque e Comercial.")
        criar_botao(self.conteudo, "+  NOVO CADASTRO", self._form_parte, compacto=True).pack(anchor="e", pady=(0, 10))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("nome", "NOME / RAZÃO SOCIAL", 300), ("tipo", "TIPO", 140), ("documento", "CPF / CNPJ", 160), ("status", "STATUS", 120)), altura=390)
        itens = listar_catalogos(SESSAO.usuario)["partes"]
        self._preencher_tabela(itens, lambda r: (r["nome"], r["tipo"], r.get("documento") or "—", r["status"]))


    def _centros_custo(self):
        self._cabecalho("Centros de custo", "Estrutura organizacional utilizada para apropriar receitas, custos e despesas.")
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("codigo", "CÓDIGO", 120), ("nome", "CENTRO DE CUSTO", 320), ("departamento", "DEPARTAMENTO ID", 160)), altura=390)
        itens = listar_catalogos(SESSAO.usuario)["centros_custo"]
        self._preencher_tabela(itens, lambda r: (r["codigo"], r["nome"], r.get("departamento_id") or "Corporativo"))


    def _cartoes(self):
        self._cabecalho("Cartões corporativos", "Limites, responsáveis, centros de custo e conferência de comprovantes.")
        criar_botao(self.conteudo, "+  NOVO CARTÃO", self._form_cartao, compacto=True).pack(anchor="e", pady=(0, 10))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("nome", "CARTÃO", 230), ("final", "FINAL", 90), ("limite", "LIMITE", 140), ("responsavel", "RESPONSÁVEL", 190), ("centro", "CENTRO DE CUSTO", 170), ("status", "STATUS", 110)), altura=390)
        itens = listar_cartoes(SESSAO.usuario)
        self._preencher_tabela(itens, lambda r: (r["nome"], f"•••• {r['final']}", _moeda(r["limite_centavos"]), r.get("responsavel_nome") or "—", r.get("centro_custo_nome") or "—", r["status"]))


    def _recorrencias(self):
        self._cabecalho("Recorrências", "Modelos de aluguel, assinaturas, folha e demais compromissos periódicos.")
        acoes = tk.Frame(self.conteudo, bg=CORES["bg"])
        acoes.pack(fill="x", pady=(0, 10))
        criar_botao(acoes, "+  NOVO MODELO", lambda: self._form_lancamento("Conta a pagar", recorrente=True), compacto=True).pack(side="right")
        criar_botao(acoes, "GERAR PENDÊNCIAS ATÉ HOJE", self._gerar_recorrencias, tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
        painel = criar_card(self.conteudo)
        painel.pack(fill="both", expand=True)
        self.tabela = self._criar_tabela(painel, (("descricao", "MODELO", 280), ("periodicidade", "FREQUÊNCIA", 130), ("inicio", "INÍCIO", 105), ("fim", "FIM", 105), ("proxima", "PRÓXIMA GERAÇÃO", 155), ("ativo", "STATUS", 100)), altura=360)
        itens = listar_recorrencias(SESSAO.usuario)
        self._preencher_tabela(itens, lambda r: (r["descricao"], r["periodicidade"], _data_br(r["inicio"]), _data_br(r["fim"]) or "Sem limite", _data_br(r["proxima_geracao"]), "Ativa" if r["ativo"] else "Encerrada"))


    def _gerar_recorrencias(self):
        try:
            ids = gerar_recorrencias_pendentes(SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Recorrências", str(erro), parent=self.root)
            return
        messagebox.showinfo("Recorrências", f"{len(ids)} lançamento(s) pendente(s) gerado(s).", parent=self.root)
        self.abrir_secao("recorrencias")
