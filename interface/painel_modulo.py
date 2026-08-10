"""Painel departamental adaptativo da V7.

Cada módulo recebe navegação, atalhos e mapa operacional específicos. As
rotas de registros e Analytics continuam funcionais; as demais apresentam a
experiência prevista para a etapa seguinte sem alterar dados.
"""

from __future__ import annotations

import tkinter as tk

from auth.sessao import SESSAO
from enterprise.catalogo import obter_modulo
from enterprise.contexto import tem_permissao
from enterprise.modulos import calcular_resumo_modulo
from interface.componentes import (
    acao_em_preparacao,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_chip,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
)
from interface.configuracao_modulos_ui import PAINEIS_MODULOS
from interface.tema import CORES, FONTES, LAYOUT


class TelaPainelModulo:
    def __init__(self, root, navegacao, modulo, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.modulo = modulo
        self.secao = secao
        self.modulo_config = obter_modulo(modulo)
        self.ui = PAINEIS_MODULOS[modulo]
        self.cor = self.modulo_config["cor"]
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            raise PermissionError("Seu perfil não possui acesso a este módulo.")
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        itens = []
        for chave, icone, titulo in self.ui["menu"]:
            itens.append((
                chave,
                icone,
                titulo,
                lambda destino=chave: self.abrir_secao(destino),
            ))
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo=self.secao,
            itens_customizados=tuple(itens),
            titulo_customizado=self.modulo_config["nome"].upper(),
            rodape_texto="Voltar aos módulos",
            rodape_comando=self.navegacao.get("modulos"),
        )
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(24, 22),
        )
        if self.secao == "visao":
            self._visao_geral(conteudo)
        else:
            self._preview_secao(conteudo)

    def abrir_secao(self, secao):
        if secao == "registros":
            self.navegacao["registros_modulo"](self.modulo)
            return
        self.container.destroy()
        TelaPainelModulo(self.root, self.navegacao, self.modulo, secao)

    def _visao_geral(self, parent):
        acoes = tk.Frame(parent, bg=CORES["bg"])
        if tem_permissao(SESSAO.usuario, self.modulo, "escrever"):
            criar_botao(
                acoes,
                "+  NOVO REGISTRO",
                lambda: self.navegacao["registros_modulo"](self.modulo),
            ).pack(side="right", padx=(8, 0))
        if tem_permissao(SESSAO.usuario, "analytics", "escrever"):
            criar_botao(
                acoes,
                "◈  ANALISAR MÓDULO",
                lambda: self.navegacao["analisar_modulo"](self.modulo),
                tipo="secundario",
            ).pack(side="right")
        criar_cabecalho(
            parent,
            self.ui["titulo"],
            self.ui["resumo"],
            acao=acoes,
            breadcrumb=f"MÓDULOS  /  {self.modulo_config['nome'].upper()}",
            etiqueta="PAINEL DEPARTAMENTAL",
        )
        self._metricas(parent)
        corpo = tk.Frame(parent, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, pady=(15, 0))
        esquerda = tk.Frame(corpo, bg=CORES["bg"])
        esquerda.pack(side="left", fill="both", expand=True, padx=(0, 7))
        direita = tk.Frame(corpo, bg=CORES["bg"], width=300)
        direita.pack(side="right", fill="y", padx=(7, 0))
        direita.pack_propagate(False)
        self._acoes_rapidas(esquerda)
        self._fluxo(esquerda)
        self._status_integracao(direita)
        self._recursos_planejados(direita)

    def _metricas(self, parent):
        area = tk.Frame(parent, bg=CORES["bg"])
        area.pack(fill="x")
        try:
            cards = calcular_resumo_modulo(self.modulo, SESSAO.usuario)["cards"][:4]
        except (PermissionError, ValueError, TypeError):
            cards = []
        while len(cards) < 4:
            cards.append(("SEM DADOS", 0, "inteiro"))
        for indice, (titulo, valor, formato) in enumerate(cards):
            card = criar_metrica(
                area,
                titulo,
                self._formatar(valor, formato),
                icone=self.modulo_config["icone"],
                cor=self.cor,
                detalhe="Atualizado no contexto selecionado",
            )
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 10) if indice < 3 else 0,
            )

    def _acoes_rapidas(self, parent):
        card = criar_card(parent)
        card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", padx=18, pady=16)
        criar_titulo_secao(
            interior,
            "Acesso rápido",
            "Atalhos específicos do departamento.",
        )
        grade = tk.Frame(interior, bg=CORES["card"])
        grade.pack(fill="x")
        for indice, (titulo, descricao, icone) in enumerate(self.ui["acoes"]):
            if indice == 0:
                acao = lambda modulo=self.modulo: self.navegacao["registros_modulo"](modulo)
            else:
                acao = acao_em_preparacao(titulo)
            bloco = tk.Frame(
                grade,
                bg=CORES["card_secundario"],
                highlightthickness=1,
                highlightbackground=CORES["border_soft"],
            )
            bloco.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 9) if indice < 2 else 0,
            )
            tk.Label(
                bloco,
                text=icone,
                font=("Segoe UI Symbol", 15, "bold"),
                fg=self.cor,
                bg=CORES["card_secundario"],
            ).pack(anchor="w", padx=14, pady=(13, 6))
            tk.Label(
                bloco,
                text=titulo,
                font=("Segoe UI", 9, "bold"),
                fg=CORES["text"],
                bg=CORES["card_secundario"],
            ).pack(anchor="w", padx=14)
            tk.Label(
                bloco,
                text=descricao,
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card_secundario"],
                wraplength=185,
                justify="left",
            ).pack(anchor="w", padx=14, pady=(4, 8))
            criar_botao(
                bloco,
                "ABRIR  →",
                acao,
                tipo="fantasma",
                compacto=True,
            ).pack(anchor="w", padx=4, pady=(0, 7))

    def _fluxo(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(14, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=18, pady=16)
        criar_titulo_secao(
            interior,
            self.ui["fila_titulo"],
            "Estrutura visual preparada para receber indicadores de cada etapa.",
        )
        fluxo = tk.Frame(interior, bg=CORES["card"])
        fluxo.pack(fill="both", expand=True, pady=(8, 0))
        for indice, etapa in enumerate(self.ui["etapas"]):
            coluna = tk.Frame(
                fluxo,
                bg=CORES["input"],
                highlightthickness=1,
                highlightbackground=CORES["border_soft"],
            )
            coluna.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 7) if indice < len(self.ui["etapas"]) - 1 else 0,
            )
            tk.Frame(coluna, bg=self.cor, height=3).pack(fill="x")
            tk.Label(
                coluna,
                text=etapa,
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["input"],
                wraplength=120,
                justify="center",
            ).pack(pady=(16, 7), padx=5)
            tk.Label(
                coluna,
                text="—",
                font=("Segoe UI", 21, "bold"),
                fg=CORES["text_muted"],
                bg=CORES["input"],
            ).pack()
            tk.Label(
                coluna,
                text="Aguardando integração",
                font=("Segoe UI", 7),
                fg=CORES["text_disabled"],
                bg=CORES["input"],
            ).pack(pady=(0, 14))

    def _status_integracao(self, parent):
        card = criar_card(parent, destaque=True)
        card.pack(fill="x")
        tk.Label(
            card,
            text="✓",
            font=("Segoe UI Symbol", 24, "bold"),
            fg=CORES["success"],
            bg=CORES["success_soft"],
            width=3,
            height=2,
        ).pack(pady=(17, 8))
        tk.Label(
            card,
            text="Interface departamental pronta",
            font=("Segoe UI", 10, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack()
        tk.Label(
            card,
            text="Navegação, estados vazios e fluxos foram preparados para a próxima etapa.",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
            wraplength=230,
            justify="center",
        ).pack(padx=20, pady=(6, 13))
        criar_chip(card, "BACKEND PENDENTE", cor=CORES["warning"], fundo=CORES["warning_soft"]).pack(pady=(0, 17))

    def _recursos_planejados(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(14, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=17, pady=16)
        criar_titulo_secao(interior, "Próximas integrações")
        for recurso in self.ui["recursos"]:
            linha = tk.Frame(interior, bg=CORES["card"])
            linha.pack(fill="x", pady=5)
            tk.Label(
                linha,
                text="○",
                font=("Segoe UI", 9),
                fg=self.cor,
                bg=CORES["card"],
            ).pack(side="left", padx=(0, 7))
            tk.Label(
                linha,
                text=recurso,
                font=FONTES["texto_pequeno"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

    def _preview_secao(self, parent):
        rotulo = next(
            (titulo for chave, _icone, titulo in self.ui["menu"] if chave == self.secao),
            self.secao.replace("_", " ").title(),
        )
        acoes = tk.Frame(parent, bg=CORES["bg"])
        criar_botao(
            acoes,
            "+  NOVO",
            acao_em_preparacao(f"Novo registro · {rotulo}"),
        ).pack(side="right")
        criar_cabecalho(
            parent,
            rotulo,
            f"Espaço especializado de {self.modulo_config['nome']} preparado para integração funcional.",
            acao=acoes,
            breadcrumb=f"MÓDULOS  /  {self.modulo_config['nome'].upper()}  /  {rotulo.upper()}",
            etiqueta="PRÉVIA FUNCIONAL",
        )
        aviso = criar_card(parent, destaque=True)
        aviso.pack(fill="x", pady=(0, 14))
        tk.Label(
            aviso,
            text="Esta tela faz parte da nova arquitetura visual",
            font=("Segoe UI", 10, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=18, pady=(15, 3))
        tk.Label(
            aviso,
            text="Filtros, tabela, indicadores e ações estão representados visualmente. Nenhuma operação de dados será executada nesta etapa.",
            font=FONTES["texto_pequeno"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=18, pady=(0, 15))
        filtros = tk.Frame(parent, bg=CORES["bg"])
        filtros.pack(fill="x", pady=(0, 12))
        for texto in ("Pesquisar...", "Status: Todos", "Período: Atual"):
            tk.Label(
                filtros,
                text=texto,
                font=FONTES["texto_pequeno"],
                fg=CORES["text_sec"],
                bg=CORES["input"],
                highlightthickness=1,
                highlightbackground=CORES["border"],
                anchor="w",
                padx=12,
                pady=9,
                width=24,
            ).pack(side="left", padx=(0, 9))
        tabela = criar_card(parent)
        tabela.pack(fill="both", expand=True)
        cab = tk.Frame(tabela, bg=CORES["card_secundario"])
        cab.pack(fill="x", padx=1, pady=1)
        for titulo in ("IDENTIFICAÇÃO", "DESCRIÇÃO", "RESPONSÁVEL", "STATUS", "ATUALIZAÇÃO"):
            tk.Label(
                cab,
                text=titulo,
                font=("Segoe UI", 7, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card_secundario"],
            ).pack(side="left", fill="x", expand=True, pady=11)
        vazio = tk.Frame(tabela, bg=CORES["input"])
        vazio.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        tk.Label(
            vazio,
            text=f"{self.modulo_config['icone']}\n\nNenhum dado integrado em {rotulo}\nO backend desta seção será conectado na próxima etapa.",
            font=FONTES["texto_pequeno"],
            fg=CORES["text_muted"],
            bg=CORES["input"],
            justify="center",
        ).pack(expand=True)

    @staticmethod
    def _formatar(valor, formato):
        try:
            numero = float(valor or 0)
        except (TypeError, ValueError):
            return str(valor or "0")
        if formato == "moeda":
            texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {texto}"
        if formato == "decimal":
            return f"{numero:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{int(numero):,}".replace(",", ".")
