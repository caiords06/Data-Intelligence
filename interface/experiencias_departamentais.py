"""Landing pages departamentais sem aparência de planilha.

Cada módulo recebe uma metáfora operacional própria. Tabelas/grades continuam
existindo somente nas seções em que uma visão tabular é realmente útil.
"""

from __future__ import annotations

import tkinter as tk

from auth.sessao import SESSAO
from enterprise.catalogo import obter_modulo
from enterprise.contexto import tem_permissao
from enterprise.modulos import calcular_resumo_modulo
from interface.componentes import AreaRolavel, criar_botao, criar_cabecalho, criar_card, criar_sidebar
from interface.configuracao_modulos_ui import PAINEIS_MODULOS
from interface.tema import CORES, LAYOUT, configurar_estilos_ttk


EXPERIENCIAS = {
    "rh": {
        "titulo": "People Operations",
        "subtitulo": "Pessoas em movimento: jornada, cuidado, desenvolvimento e decisões de RH.",
        "metafora": "JORNADA DAS PESSOAS",
        "etapas": (("admissoes", "Pré-admissão"), ("colaboradores", "Ativos"), ("ferias", "Ausências"), ("desempenho", "Desenvolvimento"), ("desligamentos", "Offboarding")),
        "atalhos": (("+ NOVA ADMISSÃO", "admissoes"), ("PLANEJAR FÉRIAS", "ferias"), ("FECHAR FOLHA", "folha"), ("CORREIO RH", "correio")),
        "bloco": "Sinais humanos",
        "mensagem": "Use o painel como uma jornada de pessoas; consulte grades somente quando precisar comparar muitos colaboradores ou valores.",
    },
    "financeiro": {
        "titulo": "Financial Command Center",
        "subtitulo": "Liquidez, compromissos, recebimentos e decisões financeiras em um único cockpit.",
        "metafora": "MOVIMENTO DO CAIXA",
        "etapas": (("receber", "Entradas"), ("pagar", "Saídas"), ("aprovacoes_fin", "Aprovações"), ("conciliacao", "Conciliação"), ("fluxo", "Projeção")),
        "atalhos": (("+ LANÇAMENTO", "lancamentos"), ("CONCILIAR", "conciliacao"), ("PROJETAR CAIXA", "fluxo"), ("CORREIO FINANCEIRO", "correio")),
        "bloco": "Decisão financeira",
        "mensagem": "Lançamentos e planos de contas podem usar grade editável; caixa, DRE, aprovações e projeções priorizam leitura gerencial.",
    },
    "estoque": {
        "titulo": "Warehouse Control",
        "subtitulo": "Disponibilidade, movimentação, rastreabilidade e exceções do estoque físico.",
        "metafora": "FLUXO DO ARMAZÉM",
        "etapas": (("recebimentos", "Recebimento"), ("itens", "Disponível"), ("reservas", "Reservado"), ("transferencias", "Movimentação"), ("inventario", "Contagem")),
        "atalhos": (("+ RECEBIMENTO", "recebimentos"), ("MOVIMENTAR", "movimentacoes"), ("INVENTÁRIO", "inventario"), ("CORREIO ESTOQUE", "correio")),
        "bloco": "Saúde do estoque",
        "mensagem": "Itens e saldos combinam bem com grade; operações, inventários e alertas são apresentados como fluxos e exceções.",
    },
    "compras": {
        "titulo": "Procurement Desk",
        "subtitulo": "Da necessidade ao recebimento, com concorrência, alçadas e rastreabilidade.",
        "metafora": "PIPELINE DE SUPRIMENTOS",
        "etapas": (("solicitacoes", "Solicitação"), ("aprovacoes", "Aprovação"), ("cotacoes", "Cotação"), ("pedidos", "Pedido"), ("recebimentos", "Recebimento")),
        "atalhos": (("+ SOLICITAÇÃO", "solicitacoes"), ("NOVA COTAÇÃO", "cotacoes"), ("FORNECEDORES", "fornecedores"), ("CORREIO COMPRAS", "correio")),
        "bloco": "Decisões de compra",
        "mensagem": "Solicitações e cotações funcionam como fluxo de decisão; a grade fica reservada a catálogos, fornecedores e comparações extensas.",
    },
    "marketing": {
        "titulo": "Growth Studio",
        "subtitulo": "Campanhas, conteúdo, canais e conversão organizados como uma operação de crescimento.",
        "metafora": "CICLO DA CAMPANHA",
        "etapas": (("registros", "Planejamento"), ("conteudo", "Produção"), ("calendario", "Publicação"), ("leads", "Aquisição"), ("relatorios", "Aprendizado")),
        "atalhos": (("+ CAMPANHA", "registros"), ("CALENDÁRIO", "calendario"), ("CONTEÚDO", "conteudo"), ("CORREIO MARKETING", "correio")),
        "bloco": "Pulso de crescimento",
        "mensagem": "Marketing trabalha melhor com calendário, pipeline criativo e funil; planilhas ficam como apoio para listas e exportações.",
    },
    "administrativo": {
        "titulo": "Workplace Operations",
        "subtitulo": "Solicitações internas, recursos, facilities e serviços compartilhados.",
        "metafora": "CENTRAL DE SERVIÇOS INTERNOS",
        "etapas": (("registros", "Solicitado"), ("facilities", "Triagem"), ("salas", "Recursos"), ("viagens", "Execução"), ("reembolsos", "Fechamento")),
        "atalhos": (("+ SOLICITAÇÃO", "registros"), ("RESERVAR SALA", "salas"), ("VIAGENS", "viagens"), ("CORREIO ADM", "correio")),
        "bloco": "Operação do escritório",
        "mensagem": "A interface prioriza filas, reservas e execução; tabelas ficam para cadastros e consultas consolidadas.",
    },
    "juridico": {
        "titulo": "Legal Operations",
        "subtitulo": "Prazos, contratos, processos e riscos apresentados pela urgência jurídica.",
        "metafora": "AGENDA JURÍDICA",
        "etapas": (("prazos", "Prazos"), ("registros", "Contratos"), ("processos", "Processos"), ("audiencias", "Audiências"), ("riscos", "Riscos")),
        "atalhos": (("+ CONTRATO", "registros"), ("NOVO PRAZO", "prazos"), ("PROCESSOS", "processos"), ("CORREIO JURÍDICO", "correio")),
        "bloco": "Exposição e prazo",
        "mensagem": "Jurídico é orientado por agenda, risco e ciclo documental; a grade é secundária e serve à consulta massiva.",
    },
    "comercial": {
        "titulo": "Revenue Workspace",
        "subtitulo": "Relacionamento, oportunidades e previsão organizados como pipeline comercial.",
        "metafora": "PIPELINE DE RECEITA",
        "etapas": (("leads", "Lead"), ("registros", "Qualificação"), ("propostas", "Proposta"), ("pipeline", "Negociação"), ("clientes", "Cliente")),
        "atalhos": (("+ OPORTUNIDADE", "registros"), ("LEADS", "leads"), ("PROPOSTAS", "propostas"), ("CORREIO COMERCIAL", "correio")),
        "bloco": "Ritmo comercial",
        "mensagem": "O foco é progressão das oportunidades e próximos passos; planilhas ficam para catálogo, importação e exportação de carteira.",
    },
}


def _formatar(valor, tipo):
    if tipo == "moeda":
        return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if tipo == "decimal":
        return f"{float(valor or 0):,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")
    try:
        return f"{int(valor or 0):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor or "—")


class TelaExperienciaDepartamental:
    def __init__(self, root, navegacao, modulo):
        if modulo not in EXPERIENCIAS:
            raise ValueError("Experiência departamental não configurada.")
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            raise PermissionError("Seu perfil não possui acesso a este módulo.")
        self.root = root
        self.navegacao = navegacao
        self.modulo = modulo
        self.config = EXPERIENCIAS[modulo]
        self.modulo_config = obter_modulo(modulo)
        self.cor = self.modulo_config["cor"]
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar()

    def _ir(self, destino):
        if destino == "correio":
            self.navegacao["correio"](self.modulo)
        else:
            self.navegacao["secao_modulo"](self.modulo, destino)

    def _criar(self):
        configurar_estilos_ttk(self.root)
        menu = []
        for chave, icone, titulo in PAINEIS_MODULOS[self.modulo]["menu"]:
            menu.append((chave, icone, titulo, lambda d=chave: self._ir(d)))
        menu.append(("correio", "✉", "Correio interno", lambda: self._ir("correio")))
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="visao",
            itens_customizados=tuple(menu),
            titulo_customizado=self.modulo_config["nome"].upper(),
            rodape_texto="Voltar aos módulos",
            rodape_comando=self.navegacao.get("modulos"),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
        area = viewport.conteudo
        criar_cabecalho(
            area,
            self.config["titulo"],
            self.config["subtitulo"],
            breadcrumb=f"MÓDULOS / {self.modulo_config['nome'].upper()} / OPERAÇÃO",
            etiqueta="EXPERIÊNCIA DEPARTAMENTAL",
        )
        self._metricas(area)
        self._fluxo(area)
        self._operacao(area)

    def _metricas(self, parent):
        try:
            resumo = calcular_resumo_modulo(self.modulo, SESSAO.usuario)
            cards = resumo.get("cards", ())
        except Exception:
            cards = ()
        grade = tk.Frame(parent, bg=CORES["bg"])
        grade.pack(fill="x", pady=(0, 14))
        for i in range(4):
            grade.grid_columnconfigure(i, weight=1, uniform="m")
        for i, item in enumerate(cards[:4]):
            titulo, valor, tipo = item
            card = criar_card(grade)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6))
            tk.Frame(card, bg=self.cor, height=3).pack(fill="x")
            tk.Label(card, text=titulo, bg=CORES["card"], fg=CORES["text_sec"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 5))
            tk.Label(card, text=_formatar(valor, tipo), bg=CORES["card"], fg=CORES["text"], font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=14, pady=(0, 13))

    def _fluxo(self, parent):
        card = criar_card(parent)
        card.pack(fill="x", pady=(0, 14))
        tk.Label(card, text=self.config["metafora"], bg=CORES["card"], fg=self.cor, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 10))
        faixa = tk.Frame(card, bg=CORES["card"])
        faixa.pack(fill="x", padx=18, pady=(0, 18))
        for i, (destino, titulo) in enumerate(self.config["etapas"]):
            faixa.grid_columnconfigure(i, weight=1, uniform="fluxo")
            bloco = tk.Button(
                faixa, text=f"{i+1:02d}\n{titulo}", command=lambda d=destino: self._ir(d),
                bg=CORES["input"], fg=CORES["text"], activebackground=CORES["card_hover"],
                activeforeground=CORES["text"], relief="flat", bd=0, cursor="hand2",
                font=("Segoe UI", 9, "bold"), padx=10, pady=14,
            )
            bloco.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 0 if i == len(self.config["etapas"])-1 else 4))

    def _operacao(self, parent):
        linha = tk.Frame(parent, bg=CORES["bg"])
        linha.pack(fill="both", expand=True)
        linha.grid_columnconfigure(0, weight=3, uniform="op")
        linha.grid_columnconfigure(1, weight=2, uniform="op")

        acoes = criar_card(linha)
        acoes.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(acoes, text="AÇÕES DE TRABALHO", bg=CORES["card"], fg=CORES["text_sec"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        for texto, destino in self.config["atalhos"]:
            bot = tk.Button(
                acoes, text=texto, command=lambda d=destino: self._ir(d), anchor="w",
                bg=CORES["input"], fg=CORES["text"], activebackground=CORES["card_hover"],
                activeforeground=CORES["text"], relief="flat", bd=0, cursor="hand2",
                font=("Segoe UI", 9, "bold"), padx=14, pady=10,
            )
            bot.pack(fill="x", padx=18, pady=4)
        tk.Frame(acoes, bg=CORES["card"], height=12).pack()

        contexto = criar_card(linha)
        contexto.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(contexto, text=self.config["bloco"].upper(), bg=CORES["card"], fg=self.cor, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        tk.Label(
            contexto, text=self.config["mensagem"], bg=CORES["card"], fg=CORES["text_sec"],
            font=("Segoe UI", 9), justify="left", wraplength=350,
        ).pack(anchor="w", padx=18, pady=(0, 14))
        criar_botao(contexto, "ABRIR CORREIO DO MÓDULO", lambda: self._ir("correio"), tipo="secundario", compacto=True).pack(anchor="w", padx=18, pady=(0, 18))
