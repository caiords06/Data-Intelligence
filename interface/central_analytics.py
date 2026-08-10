"""Central visual do motor analítico V7."""

from __future__ import annotations

import tkinter as tk

from auth.sessao import SESSAO
from historico.repositorio import listar_historico
from interface.componentes import (
    acao_em_preparacao,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_card_acao,
    criar_chip,
    criar_sidebar,
    criar_titulo_secao,
)
from interface.tema import CORES, FONTES, LAYOUT


MENU_ANALYTICS = (
    ("visao", "⌂", "Dashboard"),
    ("nova", "+", "Nova análise"),
    ("importacoes", "↓", "Importações"),
    ("conjuntos", "▣", "Conjuntos de dados"),
    ("relatorios", "▤", "Relatórios"),
    ("agendamentos", "◷", "Agendamentos"),
    ("alertas", "!", "Alertas analíticos"),
    ("modelos", "◈", "Modelos"),
    ("perfis", "◎", "Perfis de análise"),
    ("assistente", "✦", "IA Assistente"),
)


class TelaCentralAnalytics:
    def __init__(self, root, navegacao, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.secao = secao
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        itens = []
        for chave, icone, titulo in MENU_ANALYTICS:
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
            titulo_customizado="ANALYTICS",
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
            self._dashboard(conteudo)
        else:
            self._preview(conteudo)

    def abrir_secao(self, secao):
        if secao == "nova":
            self.navegacao["nova"]()
            return
        if secao == "perfis":
            self.navegacao["perfis"]()
            return
        self.container.destroy()
        TelaCentralAnalytics(self.root, self.navegacao, secao=secao)

    def _dashboard(self, parent):
        acoes = tk.Frame(parent, bg=CORES["bg"])
        criar_botao(
            acoes,
            "+  NOVA ANÁLISE",
            lambda: self.navegacao["nova"](),
        ).pack(side="right")
        criar_cabecalho(
            parent,
            "Central analítica",
            "Importe dados, execute o motor analítico e transforme resultados em decisões.",
            acao=acoes,
            breadcrumb="MÓDULOS  /  ANALYTICS",
            etiqueta="MOTOR DISPONÍVEL",
        )
        grade = tk.Frame(parent, bg=CORES["bg"])
        grade.pack(fill="x")
        atalhos = (
            ("+", "Nova análise", "Configure fonte, categoria, período e módulos do processamento.", lambda: self.navegacao["nova"](), CORES["primary"], None),
            ("↓", "Importar dados", "Prepare arquivos e conexões para novos conjuntos de dados.", lambda: self.abrir_secao("importacoes"), CORES["teal"], "PRÉVIA"),
            ("◷", "Histórico", "Consulte análises concluídas e seus resumos persistidos.", self.navegacao.get("historico"), CORES["purple"], None),
            ("▤", "Relatórios", "Monte relatórios executivos, exportações e agendamentos.", lambda: self.abrir_secao("relatorios"), CORES["success"], "PRÉVIA"),
        )
        for indice, (icone, titulo, descricao, acao, cor, etiqueta) in enumerate(atalhos):
            card = criar_card_acao(
                grade,
                icone=icone,
                titulo=titulo,
                descricao=descricao,
                acao=acao,
                cor=cor,
                etiqueta=etiqueta,
            )
            card.pack(side="left", fill="both", expand=True, padx=(0, 10) if indice < 3 else 0)

        corpo = tk.Frame(parent, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, pady=(14, 0))
        esquerda = tk.Frame(corpo, bg=CORES["bg"])
        esquerda.pack(side="left", fill="both", expand=True, padx=(0, 7))
        direita = tk.Frame(corpo, bg=CORES["bg"], width=330)
        direita.pack(side="right", fill="y", padx=(7, 0))
        direita.pack_propagate(False)
        self._recentes(esquerda)
        self._motor(direita)
        self._pipeline(direita)

    def _recentes(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True)
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=18, pady=16)
        botao = criar_botao(
            interior,
            "VER HISTÓRICO  →",
            self.navegacao.get("historico"),
            tipo="fantasma",
            compacto=True,
        )
        criar_titulo_secao(
            interior,
            "Análises recentes",
            "Execuções armazenadas sem preservar as planilhas originais.",
            acao=botao,
        )
        cab = tk.Frame(interior, bg=CORES["card_secundario"])
        cab.pack(fill="x", pady=(4, 2))
        for texto, largura in (("ANÁLISE", 36), ("DATA", 15), ("REGISTROS", 12), ("STATUS", 12)):
            tk.Label(
                cab,
                text=texto,
                font=("Segoe UI", 7, "bold"),
                fg=CORES["text_muted"],
                bg=CORES["card_secundario"],
                anchor="w",
                width=largura,
            ).pack(side="left", fill="x", expand=texto == "ANÁLISE", padx=9, pady=8)
        registros = listar_historico(SESSAO.usuario, limite=8)
        if not registros:
            tk.Label(
                interior,
                text="◇\n\nNenhuma análise registrada\nInicie um processamento para preencher esta área.",
                font=FONTES["texto_pequeno"],
                fg=CORES["text_muted"],
                bg=CORES["input"],
                justify="center",
            ).pack(fill="both", expand=True)
            return
        for registro in registros[:7]:
            linha = tk.Frame(interior, bg=CORES["card"])
            linha.pack(fill="x")
            tk.Label(
                linha,
                text=str(registro.get("categoria", "Análise")).replace("_", " ").title(),
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text"],
                bg=CORES["card"],
                anchor="w",
                width=36,
            ).pack(side="left", fill="x", expand=True, padx=9, pady=9)
            tk.Label(
                linha,
                text=str(registro.get("criado_em", ""))[:10],
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                width=15,
            ).pack(side="left")
            tk.Label(
                linha,
                text=f"{int(registro.get('total_registros') or 0):,}".replace(",", "."),
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                width=12,
            ).pack(side="left")
            criar_chip(
                linha,
                "CONCLUÍDA",
                cor=CORES["success"],
                fundo=CORES["success_soft"],
            ).pack(side="left", padx=8)
            tk.Frame(interior, bg=CORES["divider"], height=1).pack(fill="x")

    def _motor(self, parent):
        card = criar_card(parent, destaque=True)
        card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=18, pady=16)
        criar_titulo_secao(interior, "Motor analítico", "Serviço central de processamento.")
        tk.Label(
            interior,
            text="✓",
            font=("Segoe UI Symbol", 31, "bold"),
            fg=CORES["success"],
            bg=CORES["success_soft"],
            width=3,
            height=2,
        ).pack(pady=(6, 9))
        tk.Label(
            interior,
            text="Ativo e disponível",
            font=("Segoe UI", 11, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack()
        tk.Label(
            interior,
            text="Motores universais e departamentais carregados.",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(pady=(4, 13))
        for titulo, valor in (
            ("Categorias", "11"),
            ("Qualidade", "Disponível"),
            ("Jobs", "Monitorados"),
        ):
            linha = tk.Frame(interior, bg=CORES["card"])
            linha.pack(fill="x", pady=4)
            tk.Label(linha, text=titulo, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card"]).pack(side="left")
            tk.Label(linha, text=valor, font=("Segoe UI", 8, "bold"), fg=CORES["success"], bg=CORES["card"]).pack(side="right")

    def _pipeline(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(14, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=17, pady=16)
        criar_titulo_secao(interior, "Pipeline analítico")
        etapas = (
            ("Leitura e validação", CORES["primary"]),
            ("Tratamento", CORES["teal"]),
            ("Indicadores", CORES["purple"]),
            ("Qualidade", CORES["success"]),
            ("Relatório executivo", CORES["warning"]),
        )
        for indice, (titulo, cor) in enumerate(etapas, 1):
            linha = tk.Frame(interior, bg=CORES["card"])
            linha.pack(fill="x", pady=5)
            tk.Label(
                linha,
                text=str(indice),
                font=("Segoe UI", 8, "bold"),
                fg=cor,
                bg=CORES["primary_soft"],
                width=3,
                height=1,
            ).pack(side="left", padx=(0, 8))
            tk.Label(
                linha,
                text=titulo,
                font=FONTES["texto_pequeno"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(side="left")

    def _preview(self, parent):
        titulo = next(
            (rotulo for chave, _icone, rotulo in MENU_ANALYTICS if chave == self.secao),
            self.secao.title(),
        )
        acao = tk.Frame(parent, bg=CORES["bg"])
        criar_botao(
            acao,
            "+  NOVO",
            acao_em_preparacao(f"Novo · {titulo}"),
        ).pack(side="right")
        criar_cabecalho(
            parent,
            titulo,
            "Interface preparada para a próxima fase de integração do Analytics.",
            acao=acao,
            breadcrumb=f"MÓDULOS  /  ANALYTICS  /  {titulo.upper()}",
            etiqueta="PRÉVIA FUNCIONAL",
        )
        card = criar_card(parent, destaque=True)
        card.pack(fill="x", pady=(0, 14))
        tk.Label(
            card,
            text="Estrutura visual concluída · integração pendente",
            font=("Segoe UI", 10, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=18, pady=(15, 3))
        tk.Label(
            card,
            text="Os controles abaixo não alteram dados nesta versão de front-end.",
            font=FONTES["texto_pequeno"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(anchor="w", padx=18, pady=(0, 15))
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card_secundario"])
        topo.pack(fill="x", padx=1, pady=1)
        for texto in ("NOME", "ORIGEM", "RESPONSÁVEL", "STATUS", "ATUALIZAÇÃO"):
            tk.Label(
                topo,
                text=texto,
                font=("Segoe UI", 7, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card_secundario"],
            ).pack(side="left", fill="x", expand=True, pady=11)
        tk.Label(
            painel,
            text=f"◇\n\nNenhum item configurado em {titulo}\nUse esta área na próxima etapa para conectar o serviço correspondente.",
            font=FONTES["texto_pequeno"],
            fg=CORES["text_muted"],
            bg=CORES["input"],
            justify="center",
        ).pack(fill="both", expand=True, padx=1, pady=(0, 1))
