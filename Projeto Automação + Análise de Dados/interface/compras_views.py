"""Workspace especializado e funcional de Compras e Suprimentos 2.0."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from services.departamentos.compras import (
    ACOES_COMPRAS,
    adicionar_aditivo,
    adicionar_comentario,
    adicionar_contato_fornecedor,
    agendar_relatorio,
    analisar_compras,
    aprovar_pedido,
    atualizar_status_pedido,
    avaliar_fornecedor,
    atualizar_fornecedor,
    criar_categoria,
    criar_contrato,
    criar_cotacao,
    criar_fornecedor,
    criar_item_catalogo,
    criar_pedido,
    criar_solicitacao,
    decidir_solicitacao,
    enviar_pedido,
    enviar_solicitacao,
    gerar_alertas_compras,
    gerar_pdf_pedido,
    gerar_relatorio_compras,
    garantir_catalogos,
    homologar_fornecedor,
    integrar_recebimento_financeiro,
    listar_historico,
    listar_secao,
    obter_fornecedores_cotacao,
    obter_itens_pedido,
    obter_itens_solicitacao,
    registrar_negociacao,
    registrar_documento_fornecedor,
    registrar_divergencia_manual,
    registrar_proposta,
    registrar_recebimento,
    resolver_alerta,
    resolver_divergencia,
    resumo_compras,
    selecionar_fornecedor,
    salvar_regra_aprovacao,
    tem_permissao_compras,
)
from services.contexto import tem_permissao
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_campo_pesquisa,
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


COR_COMPRAS = "#F97316"

GRUPOS_MENU = (
    ("COMPRAS", (("visao", "⌂", "Visão geral"),)),
    ("DEMANDAS", (
        ("minhas_solicitacoes", "◉", "Minhas solicitações"),
        ("solicitacoes", "▣", "Todas as solicitações"),
        ("aprovacoes", "✓", "Aprovações"),
        ("catalogo", "▦", "Catálogo interno"),
    )),
    ("SOURCING", (
        ("cotacoes", "≡", "Cotações"),
        ("comparativo", "≠", "Mapa comparativo"),
        ("negociacoes", "⇄", "Negociações"),
    )),
    ("PEDIDOS", (
        ("pedidos", "▤", "Pedidos de compra"),
        ("entregas", "→", "Acompanhamento"),
    )),
    ("FORNECEDORES", (
        ("fornecedores", "◇", "Cadastro"),
        ("homologacao", "✔", "Homologação"),
        ("avaliacoes", "☆", "Avaliações"),
        ("documentos", "▧", "Documentos"),
    )),
    ("RECEBIMENTO", (
        ("recebimentos", "↓", "Recebimentos"),
        ("divergencias", "!", "Divergências"),
    )),
    ("CONTRATOS", (
        ("contratos", "▦", "Contratos"),
        ("aditivos", "+", "Aditivos"),
    )),
    ("GESTÃO", (
        ("alertas", "!", "Central de alertas"),
        ("relatorios", "▤", "Relatórios"),
        ("auditoria", "◉", "Auditoria"),
        ("configuracoes", "⚙", "Configurações"),
    )),
)

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "minhas_solicitacoes": "Crie, envie e acompanhe as demandas originadas por você.",
    "solicitacoes": "Necessidade, justificativa, itens, prazo, centro de custo e ciclo de aprovação.",
    "aprovacoes": "Fila humana de aprovação por valor, prioridade, departamento e alçada.",
    "catalogo": "Produtos e serviços padronizados de fornecedores homologados.",
    "cotacoes": "Convites, prazo de resposta, propostas e concorrência por solicitação.",
    "comparativo": "Preço, prazo, qualidade e custo-benefício; a escolha continua humana.",
    "negociacoes": "Rodadas, contrapropostas, saving, condições e responsáveis.",
    "pedidos": "Pedido de compra, aprovação, envio, confirmação e documento profissional.",
    "entregas": "Previsão, atraso, produção, transporte e recebimento parcial.",
    "fornecedores": "Cadastro central conectado a Estoque e Financeiro, contatos e categorias.",
    "homologacao": "Documentação, capacidade, restrições, bloqueio e conformidade.",
    "avaliacoes": "Preço, prazo, qualidade, atendimento, conformidade e score histórico.",
    "documentos": "Certidões, documentos fiscais, contratos, propostas e vencimentos.",
    "recebimentos": "Nota fiscal, conferência, aceite, recusa, lote, série, Estoque e Financeiro.",
    "divergencias": "Quantidade, preço, produto, documento, avaria e atraso com resolução auditada.",
    "contratos": "Objeto, fornecedor, vigência, valor, reajuste, renovação e alertas.",
    "aditivos": "Renovação e alterações sem apagar as condições anteriores.",
    "alertas": "Entregas atrasadas, divergências, documentos e contratos vencendo.",
    "auditoria": "Trilha imutável de quem fez, o que mudou, quando e em qual processo.",
}


def _moeda(centavos):
    if centavos is None:
        return "Acesso restrito"
    return "R$ " + f"{int(centavos or 0)/100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _numero(valor):
    if valor is None:
        return "—"
    try:
        numero = float(valor)
        return f"{numero:,.3f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return str(valor)


def _formatar(valor, campo=""):
    if valor in (None, ""):
        return "—"
    if "centavos" in campo:
        return _moeda(valor)
    if isinstance(valor, float):
        return _numero(valor)
    if campo in {"ativo", "selecionado", "possui_divergencia", "homologado", "renovacao_automatica"}:
        return "Sim" if valor else "Não"
    return str(valor)


class ComprasViewsMixin:
    def _visao(self):
        gerar_alertas_compras(SESSAO.usuario)
        self._cabecalho("Compras e suprimentos", "Central operacional do ciclo completo de aquisições, fornecedores, entregas e contratos.")
        resumo = resumo_compras(SESSAO.usuario)
        grade = GradeResponsiva(self.conteudo, max_colunas=4, largura_minima=220, gap=9, bg=CORES["bg"])
        grade.pack(fill="x")
        metricas = (
            ("SOLICITAÇÕES ABERTAS", resumo["solicitacoes_abertas"], "▣", f"{resumo['urgentes']} urgente(s)"),
            ("AGUARDANDO APROVAÇÃO", resumo["aguardando_aprovacao"], "✓", "Decisão humana pendente"),
            ("COTAÇÕES ABERTAS", resumo["cotacoes_abertas"], "≡", "Em concorrência ou negociação"),
            ("PEDIDOS EM ABERTO", resumo["pedidos_abertos"], "▤", f"{resumo['entregas_atrasadas']} entrega(s) atrasada(s)"),
            ("VALOR EM PEDIDOS", _moeda(resumo["valor_pedidos_centavos"]), "$", "Compras não canceladas"),
            ("SAVING NEGOCIADO", _moeda(resumo["saving_centavos"]), "↓", "Referência menos valor escolhido"),
            ("DIVERGÊNCIAS", resumo["divergencias"], "!", "Recebimentos a tratar"),
            ("CONTRATOS VENCENDO", resumo["contratos_vencendo"], "◷", "Próximos 30 dias"),
        )
        for titulo, valor, icone, detalhe in metricas:
            grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=COR_COMPRAS, detalhe=detalhe))
        self._atalhos()
        self._pipeline(resumo)
        self._fila_trabalho()


    def _atalhos(self):
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Acesso rápido", "Atalhos para as operações mais recorrentes de Procurement.")
        grade = GradeResponsiva(interior, max_colunas=5, largura_minima=180, gap=8, bg=CORES["card"])
        grade.pack(fill="x")
        atalhos = (
            ("+", "Nova solicitação", "Necessidade, justificativa e itens.", self._nova_solicitacao),
            ("≡", "Criar cotação", "Convide fornecedores e compare.", self._nova_cotacao),
            ("↓", "Registrar recebimento", "Conferência parcial e divergência.", self._novo_recebimento),
            ("◇", "Novo fornecedor", "Cadastro central e homologação.", self._novo_fornecedor),
            ("≠", "Comparar propostas", "Mapa de preço, prazo e score.", lambda: self.abrir_secao("comparativo")),
        )
        for icone, titulo, detalhe, comando in atalhos:
            quadro = criar_card(grade, fundo=CORES["card_secundario"])
            tk.Label(quadro, text=icone, font=("Segoe UI Symbol", 18, "bold"), fg=COR_COMPRAS, bg=CORES["card_secundario"]).pack(anchor="w", padx=14, pady=(13, 5))
            tk.Label(quadro, text=titulo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w", padx=14)
            tk.Label(quadro, text=detalhe, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card_secundario"], wraplength=180, justify="left").pack(anchor="w", padx=14, pady=(5, 10))
            criar_botao(quadro, "ABRIR  →", comando, tipo="fantasma", compacto=True).pack(anchor="w", padx=14, pady=(0, 13))
            grade.adicionar(quadro)


    def _pipeline(self, resumo):
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Ciclo de suprimentos", "Cada etapa abre a fila correspondente do processo.")
        grade = GradeResponsiva(interior, max_colunas=6, largura_minima=150, gap=6, bg=CORES["card"])
        grade.pack(fill="x")
        etapas = (
            ("Solicitação", resumo["solicitacoes_abertas"], "solicitacoes"),
            ("Aprovação", resumo["aguardando_aprovacao"], "aprovacoes"),
            ("Cotação", resumo["cotacoes_abertas"], "cotacoes"),
            ("Pedido", resumo["pedidos_abertos"], "pedidos"),
            ("Recebimento", resumo["divergencias"], "recebimentos"),
            ("Financeiro", "→", "recebimentos"),
        )
        for etapa, quantidade, secao in etapas:
            quadro = criar_card(grade, fundo=CORES["input"])
            tk.Frame(quadro, bg=COR_COMPRAS, height=3).pack(fill="x")
            tk.Label(quadro, text=etapa.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["input"]).pack(anchor="w", padx=12, pady=(12, 6))
            tk.Label(quadro, text=str(quantidade), font=FONTES["titulo"], fg=CORES["text"], bg=CORES["input"]).pack(anchor="w", padx=12)
            criar_botao(quadro, "VER ETAPA", lambda alvo=secao: self.abrir_secao(alvo), tipo="fantasma", compacto=True).pack(anchor="w", padx=12, pady=(9, 12))
            grade.adicionar(quadro)


    def _fila_trabalho(self):
        resumo = resumo_compras(SESSAO.usuario)
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Minha fila de trabalho", "Pendências operacionais no contexto atual.")
        itens = (
            (resumo["aguardando_aprovacao"], "Solicitações para aprovar", "aprovacoes"),
            (resumo["cotacoes_abertas"], "Cotações abertas", "cotacoes"),
            (resumo["entregas_atrasadas"], "Pedidos atrasados", "entregas"),
            (resumo["divergencias"], "Divergências de recebimento", "divergencias"),
            (resumo["contratos_vencendo"], "Contratos vencendo", "contratos"),
        )
        for quantidade, texto, destino in itens:
            linha = tk.Frame(interior, bg=CORES["card_secundario"])
            linha.pack(fill="x", pady=2)
            tk.Label(linha, text=str(quantidade), font=FONTES["subtitulo"], fg=COR_COMPRAS, bg=CORES["card_secundario"], width=5).pack(side="left", padx=(10, 0), pady=8)
            tk.Label(linha, text=texto, font=FONTES["texto"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left")
            criar_botao(linha, "ABRIR", lambda alvo=destino: self.abrir_secao(alvo), tipo="fantasma", compacto=True).pack(side="right", padx=8)


    def _dados_secao(self):
        secao_backend = "pedidos" if self.secao == "entregas" else self.secao
        if self.secao == "alertas":
            gerar_alertas_compras(SESSAO.usuario)
        registros = listar_secao(secao_backend, SESSAO.usuario)
        colunas = {
            "minhas_solicitacoes": (("numero", "Solicitação", 155), ("titulo", "Necessidade", 260), ("prioridade", "Prioridade", 90), ("necessario_em", "Necessário em", 110), ("valor_estimado_centavos", "Estimado", 115), ("etapa", "Etapa", 140), ("status", "Status", 150)),
            "solicitacoes": (("numero", "Solicitação", 155), ("titulo", "Necessidade", 240), ("solicitante_nome", "Solicitante", 150), ("departamento_nome", "Departamento", 140), ("prioridade", "Prioridade", 90), ("valor_estimado_centavos", "Estimado", 115), ("etapa", "Etapa", 130), ("status", "Status", 150)),
            "aprovacoes": (("numero", "Solicitação", 155), ("titulo", "Necessidade", 280), ("solicitante_nome", "Solicitante", 160), ("prioridade", "Prioridade", 90), ("necessario_em", "Prazo", 105), ("valor_estimado_centavos", "Valor", 120), ("status", "Status", 155)),
            "catalogo": (("codigo", "Código", 130), ("descricao", "Item homologado", 260), ("fornecedor_nome", "Fornecedor", 210), ("categoria_nome", "Categoria", 140), ("unidade", "Un.", 60), ("preco_centavos", "Preço", 110), ("prazo_dias", "Prazo/dias", 90), ("validade_preco", "Validade", 105)),
            "cotacoes": (("numero", "Cotação", 155), ("solicitacao_titulo", "Solicitação", 250), ("resposta_ate", "Resposta até", 105), ("valor_referencia_centavos", "Referência", 120), ("valor_selecionado_centavos", "Selecionado", 120), ("saving_centavos", "Saving", 110), ("fornecedor_selecionado", "Fornecedor", 190), ("status", "Status", 105)),
            "comparativo": (("cotacao_numero", "Cotação", 155), ("razao_social", "Fornecedor", 230), ("status_homologacao", "Homologação", 150), ("valor_total_centavos", "Valor total", 120), ("prazo_entrega_dias", "Prazo", 75), ("garantia", "Garantia", 130), ("score_preco", "Preço", 75), ("score_prazo", "Prazo", 75), ("score_qualidade", "Qualidade", 85), ("score_total", "Score", 75), ("selecionado", "Escolhido", 80)),
            "negociacoes": (("cotacao_numero", "Cotação", 155), ("razao_social", "Fornecedor", 220), ("rodada", "Rodada", 70), ("proposta_anterior_centavos", "Anterior", 110), ("proposta_nova_centavos", "Negociado", 110), ("desconto_obtido_centavos", "Economia", 110), ("prazo_novo_dias", "Prazo", 75), ("responsavel_nome", "Responsável", 145), ("criado_em", "Data", 145)),
            "pedidos": (("numero", "Pedido", 165), ("fornecedor_nome", "Fornecedor", 230), ("comprador_nome", "Comprador", 145), ("previsao_entrega", "Previsão", 105), ("valor_total_centavos", "Valor", 120), ("condicao_pagamento", "Pagamento", 150), ("status", "Status", 180)),
            "entregas": (("numero", "Pedido", 165), ("fornecedor_nome", "Fornecedor", 230), ("previsao_entrega", "Previsão", 110), ("enviado_em", "Enviado", 145), ("confirmado_em", "Confirmado", 145), ("valor_total_centavos", "Valor", 120), ("status", "Status", 180)),
            "fornecedores": (("codigo", "Código", 135), ("razao_social", "Razão social", 250), ("nome_fantasia", "Fantasia", 180), ("cnpj_cpf", "CNPJ/CPF", 145), ("categorias", "Categorias", 190), ("email", "E-mail", 210), ("status_homologacao", "Homologação", 160), ("score", "Score", 75)),
            "homologacao": (("codigo", "Código", 135), ("razao_social", "Fornecedor", 260), ("cnpj_cpf", "CNPJ/CPF", 150), ("categorias", "Categorias", 200), ("status_homologacao", "Status", 180), ("restricoes", "Restrições", 280), ("score", "Score", 75)),
            "avaliacoes": (("razao_social", "Fornecedor", 230), ("preco", "Preço", 75), ("prazo", "Prazo", 75), ("qualidade", "Qualidade", 85), ("atendimento", "Atendimento", 95), ("conformidade", "Conformidade", 100), ("score", "Score", 75), ("avaliador_nome", "Avaliador", 140), ("criado_em", "Data", 145)),
            "documentos": (("razao_social", "Fornecedor", 230), ("tipo", "Tipo", 150), ("titulo", "Documento", 260), ("numero", "Número", 120), ("emissao", "Emissão", 105), ("validade", "Validade", 105), ("status", "Status", 100), ("classificacao", "Classificação", 110), ("documento_criado_em", "Incluído em", 145)),
            "recebimentos": (("numero", "Recebimento", 165), ("pedido_numero", "Pedido", 165), ("fornecedor_nome", "Fornecedor", 220), ("nota_fiscal", "Nota fiscal", 120), ("recebido_em", "Recebido em", 105), ("documento_valor_centavos", "Documento", 120), ("possui_divergencia", "Divergência", 95), ("estoque_operacao_id", "Estoque", 80), ("financeiro_lancamento_id", "Financeiro", 85), ("status", "Status", 160)),
            "divergencias": (("recebimento_numero", "Recebimento", 165), ("pedido_numero", "Pedido", 165), ("tipo", "Tipo", 155), ("descricao", "Descrição", 340), ("severidade", "Severidade", 90), ("status", "Status", 90), ("resolucao", "Resolução", 260), ("criado_em", "Data", 145)),
            "contratos": (("numero", "Contrato", 155), ("fornecedor_nome", "Fornecedor", 220), ("objeto", "Objeto", 280), ("inicio", "Início", 100), ("termino", "Término", 100), ("valor_centavos", "Valor", 120), ("periodicidade", "Periodicidade", 110), ("renovacao_automatica", "Renova", 75), ("status", "Status", 100)),
            "aditivos": (("numero", "Aditivo", 150), ("contrato_numero", "Contrato", 150), ("fornecedor_nome", "Fornecedor", 220), ("tipo", "Tipo", 130), ("descricao", "Descrição", 280), ("valor_anterior_centavos", "Valor anterior", 120), ("valor_novo_centavos", "Novo valor", 120), ("termino_novo", "Novo término", 110), ("criado_em", "Data", 145)),
            "alertas": (("severidade", "Severidade", 100), ("tipo", "Tipo", 150), ("titulo", "Alerta", 260), ("mensagem", "Mensagem", 390), ("status", "Status", 90), ("criado_em", "Criado em", 145)),
        }.get(self.secao, ())
        return registros, colunas


    def _secao_operacional(self):
        self._cabecalho(ROTULOS[self.secao], SUBTITULOS.get(self.secao, "Operação especializada de Compras e Suprimentos 2.0."))
        filtros = tk.Frame(self.conteudo, bg=CORES["bg"])
        filtros.pack(fill="x", pady=(0, 10))
        pesquisa = criar_campo_pesquisa(
            filtros, placeholder="Pesquisar nesta seção...", cor_cursor=COR_COMPRAS,
            ao_alterar=self._preencher_tabela,
        )
        pesquisa.pack(side="left", fill="x", expand=True, ipady=8)
        criar_botao(filtros, "ATUALIZAR", lambda: self.abrir_secao(self.secao), tipo="fantasma", compacto=True).pack(side="right", padx=(8, 0))
        self.registros, colunas = self._dados_secao()
        card = criar_card(self.conteudo)
        card.pack(fill="both", expand=True)
        area = tk.Frame(card, bg=CORES["input"])
        area.pack(fill="both", expand=True, padx=1, pady=1)
        self.tabela = ttk.Treeview(area, columns=[x[0] for x in colunas], show="headings", height=20, style="Dark.Treeview")
        for chave, titulo, largura in colunas:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, minwidth=55, anchor="w", stretch=True)
        barra_y = ttk.Scrollbar(area, orient="vertical", command=self.tabela.yview, style="Dark.Vertical.TScrollbar")
        barra_x = ttk.Scrollbar(area, orient="horizontal", command=self.tabela.xview, style="Dark.Horizontal.TScrollbar")
        self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        area.grid_rowconfigure(0, weight=1)
        area.grid_columnconfigure(0, weight=1)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        adicionar_divisorias_treeview(self.tabela, cor=CORES["border"])
        self.estado_vazio = criar_estado_vazio(area, "▤", f"Nenhum registro em {ROTULOS[self.secao]}", "Utilize a ação contextual para iniciar este processo.", cor=COR_COMPRAS)
        self._preencher_tabela()
        if self.secao == "fornecedores":
            self.editor_grade = EditorGrade(
                self.tabela, colunas_editaveis={"razao_social", "nome_fantasia", "email", "categorias"},
                salvar=self._salvar_edicao_fornecedor, parent=self.root, titulo="Fornecedores",
            )
            barra_grade = tk.Frame(card, bg=CORES["card"]); barra_grade.pack(fill="x", padx=12, pady=(5,8))
            tk.Label(barra_grade, text="Duplo clique em dados cadastrais para editar. Valores críticos continuam em formulários.", bg=CORES["card"], fg=CORES["text_muted"], font=FONTES["micro"]).pack(side="left")
            criar_botao(barra_grade, "XLSX", lambda: self.editor_grade.exportar_xlsx(), tipo="fantasma", compacto=True).pack(side="right", padx=(5,0))
            criar_botao(barra_grade, "CSV", lambda: self.editor_grade.exportar_csv(), tipo="fantasma", compacto=True).pack(side="right")
        self._barra_acoes()


    def _salvar_edicao_fornecedor(self, iid, coluna, valor):
        atualizar_fornecedor(int(str(iid).split("-")[0]), {coluna: valor}, SESSAO.usuario)


    def _preencher_tabela(self, termo=""):
        if self.tabela is None:
            return
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        termo = termo.strip().lower()
        for registro in self.registros:
            if termo and termo not in " ".join(str(valor).lower() for valor in registro.values()):
                continue
            iid = str(registro.get("id") or len(self.tabela.get_children()) + 1)
            if self.tabela.exists(iid):
                iid = f"{iid}-{len(self.tabela.get_children())}"
            self.tabela.insert("", "end", iid=iid, values=tuple(_formatar(registro.get(chave), chave) for chave in self.tabela["columns"]))
        if self.tabela.get_children():
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()


    def _registro_selecionado(self):
        if self.tabela is None or not self.tabela.selection():
            messagebox.showwarning("Compras", "Selecione um registro.", parent=self.root)
            return None
        iid = self.tabela.selection()[0]
        base = int(iid.split("-")[0])
        return next((x for x in self.registros if int(x.get("id") or -1) == base), None)


    def _barra_acoes(self):
        linha = tk.Frame(self.conteudo, bg=CORES["bg"])
        linha.pack(fill="x", pady=(10, 0))
        def botao(texto, comando, tipo="secundario"):
            criar_botao(linha, texto, comando, tipo=tipo, compacto=True).pack(side="left", padx=(0, 5))
        if self.secao in {"minhas_solicitacoes", "solicitacoes"}:
            botao("ENVIAR PARA APROVAÇÃO", self._enviar_solicitacao, "sucesso")
            botao("CRIAR COTAÇÃO", self._nova_cotacao)
            botao("HISTÓRICO", lambda: self._historico("cmp_solicitacoes"), "fantasma")
            botao("COMENTAR", lambda: self._comentar("cmp_solicitacoes"), "fantasma")
        elif self.secao == "aprovacoes":
            botao("APROVAR", lambda: self._decidir_solicitacao("Aprovar"), "sucesso")
            botao("SOLICITAR ALTERAÇÃO", lambda: self._decidir_solicitacao("Solicitar alteração"), "aviso")
            botao("REJEITAR", lambda: self._decidir_solicitacao("Rejeitar"), "perigo")
        elif self.secao == "cotacoes":
            botao("REGISTRAR PROPOSTA", self._nova_proposta, "sucesso")
            botao("CRIAR PEDIDO", self._novo_pedido)
            botao("HISTÓRICO", lambda: self._historico("cmp_cotacoes"), "fantasma")
        elif self.secao == "comparativo":
            botao("NEGOCIAR", self._nova_negociacao)
            botao("SELECIONAR FORNECEDOR", self._selecionar_fornecedor, "sucesso")
        elif self.secao in {"pedidos", "entregas"}:
            botao("APROVAR", lambda: self._aprovar_pedido(True), "sucesso")
            botao("ENVIAR AO FORNECEDOR", self._enviar_pedido)
            botao("ATUALIZAR ETAPA", self._mudar_status_pedido, "aviso")
            botao("GERAR PDF", self._pdf_pedido, "fantasma")
            botao("RECEBER", self._novo_recebimento, "sucesso")
        elif self.secao == "fornecedores":
            botao("NOVO CONTATO", self._novo_contato)
            botao("AVALIAR", self._avaliar_fornecedor, "sucesso")
        elif self.secao == "homologacao":
            botao("HOMOLOGAR", lambda: self._homologar("Homologado"), "sucesso")
            botao("COM RESTRIÇÕES", lambda: self._homologar("Homologado com restrições"), "aviso")
            botao("BLOQUEAR", lambda: self._homologar("Bloqueado"), "perigo")
        elif self.secao == "documentos":
            botao("ADICIONAR DOCUMENTO", self._novo_documento, "sucesso")
            botao("VERIFICAR INTEGRIDADE", self._verificar_documento, "fantasma")
        elif self.secao == "recebimentos":
            botao("GERAR CONTA A PAGAR", self._integrar_financeiro, "sucesso")
            botao("REGISTRAR DIVERGÊNCIA", self._registrar_divergencia, "aviso")
            botao("HISTÓRICO", lambda: self._historico("cmp_recebimentos"), "fantasma")
        elif self.secao == "divergencias":
            botao("RESOLVER DIVERGÊNCIA", self._resolver_divergencia, "sucesso")
        elif self.secao == "contratos":
            botao("NOVO ADITIVO", self._novo_aditivo)
            botao("HISTÓRICO", lambda: self._historico("cmp_contratos"), "fantasma")
        elif self.secao == "alertas":
            botao("MARCAR RESOLVIDO", self._resolver_alerta, "sucesso")

