"""Workspace especializado e funcional do Estoque 2.0."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from enterprise.contexto import tem_permissao
from enterprise.estoque import (
    ACOES_ESTOQUE,
    agendar_relatorio,
    analisar_estoque,
    aprovar_inventario,
    aprovar_operacao,
    atualizar_item,
    calcular_reposicao,
    cancelar_operacao,
    conferir_operacao,
    confirmar_operacao,
    criar_categoria,
    criar_deposito,
    criar_fornecedor,
    criar_item,
    criar_localizacao,
    criar_operacao,
    criar_reserva,
    criar_solicitacao,
    decidir_solicitacao,
    encaminhar_reposicao_compras,
    finalizar_inventario,
    gerar_alertas_estoque,
    gerar_relatorio_estoque,
    iniciar_inventario,
    itens_inventario,
    liberar_reserva,
    listar_auditoria_estoque,
    listar_catalogos,
    listar_inventarios,
    listar_itens,
    listar_movimentacoes,
    listar_operacoes,
    listar_reservas,
    listar_secao,
    obter_item,
    obter_primeiro_item_operacao,
    receber_transferencia,
    registrar_contagem,
    registrar_ocorrencia,
    resolver_alerta,
    resumo_estoque,
    tem_permissao_estoque,
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
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_ESTOQUE = "#F59E0B"

GRUPOS_MENU = (
    ("ESTOQUE", (("visao", "⌂", "Visão geral"),)),
    ("CADASTROS", (
        ("itens", "□", "Itens e produtos"),
        ("categorias", "▦", "Categorias"),
        ("patrimonio", "▣", "Patrimônio e ativos"),
        ("fornecedores", "◇", "Fornecedores"),
    )),
    ("OPERAÇÕES", (
        ("movimentacoes", "⇄", "Movimentações"),
        ("recebimentos", "↓", "Recebimentos"),
        ("saidas", "↑", "Saídas e expedição"),
        ("reservas", "○", "Reservas"),
        ("transferencias", "↔", "Transferências"),
        ("devolucoes", "↩", "Devoluções"),
    )),
    ("CONTROLE", (
        ("inventario", "✓", "Inventários"),
        ("depositos", "▦", "Depósitos e endereços"),
        ("lotes", "◫", "Lotes e validade"),
        ("avarias", "!", "Avarias e perdas"),
    )),
    ("PLANEJAMENTO", (
        ("reposicao", "↻", "Reposição e cobertura"),
        ("alertas", "!", "Central de alertas"),
        ("solicitacoes", "◎", "Solicitações"),
    )),
    ("GESTÃO", (
        ("relatorios", "▤", "Relatórios"),
        ("auditoria", "◉", "Auditoria"),
        ("configuracoes", "⚙", "Configurações"),
    )),
)

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "itens": "Ficha completa, saldos físico/disponível/reservado, custos, rastreabilidade e regras de reposição.",
    "categorias": "Classificação hierárquica dos materiais, produtos e ativos.",
    "patrimonio": "Séries, patrimônios, responsáveis, garantias, condição e histórico individual.",
    "fornecedores": "Cadastro central, prazo médio, contatos e avaliação dos fornecedores.",
    "movimentacoes": "Razão imutável: toda alteração de quantidade, origem, destino, usuário e documento.",
    "recebimentos": "Recebimento de compra, conferência, divergências, lote/série e armazenagem.",
    "saidas": "Separação, consumo interno, expedição, centro de custo e responsável.",
    "reservas": "Bloqueio de disponibilidade para admissões, solicitações, projetos e operações futuras.",
    "transferencias": "Solicitação, aprovação, separação, trânsito, recebimento e conferência.",
    "devolucoes": "Retorno de colaboradores, clientes, fornecedores, transferências e reentrada controlada.",
    "inventario": "Contagem geral, parcial ou rotativa, contagem cega, recontagem e ajuste auditado.",
    "depositos": "Depósitos, almoxarifados, corredores, prateleiras, posições e capacidade.",
    "lotes": "Fabricação, validade, quarentena, bloqueio e separação FEFO.",
    "avarias": "Perdas, avarias, vencimentos, quarentena, manutenção e destinação.",
    "reposicao": "Cobertura estimada, consumo médio, ponto de pedido e integração com Compras.",
    "alertas": "Estoque crítico, falta, excesso, validade, divergências e ocorrências suspeitas.",
    "solicitacoes": "Pedido interno, aprovação, reserva, separação e entrega ao solicitante.",
}


def _moeda(centavos):
    if centavos is None:
        return "Acesso restrito"
    return "R$ " + f"{int(centavos or 0)/100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _numero(valor):
    if valor is None: return "—"
    try:
        numero = float(valor)
        return f"{numero:,.3f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return str(valor)


def _formatar(valor, campo=""):
    if valor in (None, ""): return "—"
    if "centavos" in campo: return _moeda(valor)
    if isinstance(valor, float): return _numero(valor)
    if campo in {"ativo", "contagem_cega", "controla_lote", "controla_validade", "controla_serie", "eh_patrimonio"}:
        return "Sim" if valor else "Não"
    return str(valor)


class TelaEstoque:
    def __init__(self, root, navegacao, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.secao = secao if secao in ROTULOS else "visao"
        self.tabela = None
        self.registros = []
        if not tem_permissao(SESSAO.usuario, "estoque", "ler"):
            raise PermissionError("Seu perfil não possui acesso ao Estoque.")
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar_interface()

    def _criar_interface(self):
        configurar_estilos_ttk(self.root)
        grupos = [(grupo, tuple((chave, icone, titulo, lambda destino=chave: self.abrir_secao(destino)) for chave, icone, titulo in itens)) for grupo, itens in GRUPOS_MENU]
        grupos.append(("COLABORAÇÃO", (("correio", "✉", "Correio interno", lambda: self.navegacao["correio"]("estoque")),)))
        criar_sidebar(
            self.container, self.navegacao, ativo=self.secao,
            grupos_customizados=tuple(grupos), titulo_customizado="ESTOQUE",
            rodape_texto="Voltar aos módulos", rodape_comando=self.navegacao.get("modulos"),
            grupos_recolhiveis=True,
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
        self.conteudo = viewport.conteudo
        renderizadores = {
            "visao": self._visao, "relatorios": self._relatorios,
            "auditoria": self._auditoria, "configuracoes": self._configuracoes,
        }
        renderizadores.get(self.secao, self._secao_operacional)()

    def abrir_secao(self, secao):
        self.container.destroy()
        TelaEstoque(self.root, self.navegacao, secao=secao)

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
        grade = GradeResponsiva(self.conteudo, max_colunas=4, largura_minima=220, gap=9, bg=CORES["bg"])
        grade.pack(fill="x")
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
        for titulo, valor, icone, detalhe in metricas:
            grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=COR_ESTOQUE, detalhe=detalhe))
        self._atalhos()
        self._fluxo(resumo)
        self._painel_alertas()

    def _atalhos(self):
        card = criar_card(self.conteudo); card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Acesso rápido", "Operações recorrentes de armazenagem e logística interna.")
        grade = GradeResponsiva(interior, max_colunas=5, largura_minima=180, gap=8, bg=CORES["card"]); grade.pack(fill="x")
        for icone, titulo, detalhe, comando in (
            ("↓", "Entrada de itens", "Receber, conferir e armazenar.", lambda: self._nova_entrada("Entrada")),
            ("↑", "Saída de itens", "Separar, consumir ou expedir.", self._nova_saida),
            ("↔", "Transferir estoque", "Origem, trânsito e destino.", self._nova_transferencia),
            ("✓", "Iniciar inventário", "Contagem cega e divergências.", self._novo_inventario),
            ("▣", "Ler código", "Consultar por SKU, barras ou QR.", self._scanner),
        ):
            quadro = criar_card(grade, fundo=CORES["card_secundario"])
            tk.Label(quadro, text=icone, font=("Segoe UI Symbol", 18, "bold"), fg=COR_ESTOQUE, bg=CORES["card_secundario"]).pack(anchor="w", padx=14, pady=(13, 5))
            tk.Label(quadro, text=titulo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w", padx=14)
            tk.Label(quadro, text=detalhe, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card_secundario"], wraplength=180, justify="left").pack(anchor="w", padx=14, pady=(5, 10))
            criar_botao(quadro, "ABRIR  →", comando, tipo="fantasma", compacto=True).pack(anchor="w", padx=14, pady=(0, 13))
            grade.adicionar(quadro)

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
            tk.Label(quadro, text=nome.upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text"], bg=CORES["input"]).pack(pady=(14, 5))
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
        pesquisa = tk.Entry(filtros, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_ESTOQUE, relief="flat")
        pesquisa.insert(0, "Pesquisar nesta seção..."); pesquisa.pack(side="left", fill="x", expand=True, ipady=8)
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
        pesquisa.bind("<KeyRelease>", lambda _e: self._preencher_tabela(pesquisa.get()))
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
        if termo == "pesquisar nesta seção...": termo = ""
        for registro in self.registros:
            if termo and termo not in " ".join(str(v).lower() for v in registro.values()): continue
            iid = str(registro.get("id") or registro.get("item_id") or len(self.tabela.get_children()) + 1)
            if self.tabela.exists(iid): iid = f"{iid}-{len(self.tabela.get_children())}"
            self.tabela.insert("", "end", iid=iid, values=tuple(_formatar(registro.get(c), c) for c in self.tabela["columns"]))
        if self.tabela.get_children(): self.estado_vazio.place_forget()
        else: self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)

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

    def _formulario(self, titulo, campos, callback, *, largura=620):
        janela = tk.Toplevel(self.root); janela.title(titulo); janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, largura, min(820, 190 + len(campos) * 52), minimo=(520, 380))
        viewport = AreaRolavel(janela); viewport.pack(fill="both", expand=True, padx=22, pady=18)
        corpo = viewport.conteudo
        tk.Label(corpo, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", pady=(0, 14))
        entradas = {}
        for chave, rotulo, tipo, opcoes in campos:
            linha = tk.Frame(corpo, bg=CORES["bg"]); linha.pack(fill="x", pady=4)
            tk.Label(linha, text=rotulo.upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=25, anchor="w").pack(side="left")
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
            tk.Label(linha, text=rotulo.upper(), width=24, anchor="w", font=("Segoe UI", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card_secundario"]).pack(side="left", padx=10, pady=8)
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
            compra_id = encaminhar_reposicao_compras(identificador, SESSAO.usuario)
            messagebox.showinfo("Reposição", f"Solicitação de compra #{compra_id} criada com sucesso.", parent=self.root); self.abrir_secao("reposicao")
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
        caminho = filedialog.asksaveasfilename(parent=self.root, defaultextension=f".{formato.lower()}", initialfile=f"estoque_{tipo.lower().replace(' ', '_')}.{formato.lower()}")
        if not caminho: return
        try: gerar_relatorio_estoque(tipo, formato, caminho, SESSAO.usuario); messagebox.showinfo("Relatórios", f"Relatório salvo em:\n{caminho}", parent=self.root)
        except (ValueError, PermissionError, OSError) as erro: messagebox.showerror("Relatórios", str(erro), parent=self.root)

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
            tk.Label(linha, text=acao.replace("_", " ").upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text"], bg=CORES["card_secundario"], anchor="w").pack(fill="x", padx=12, pady=8)
        tk.Label(interior, text="Política ativa: razão imutável, saldo negativo bloqueado, transferências em trânsito, FEFO para lotes e aprovação para ajustes sensíveis.", font=FONTES["texto"], fg=COR_ESTOQUE, bg=CORES["card"], wraplength=900, justify="left").pack(anchor="w", pady=(14, 0))
