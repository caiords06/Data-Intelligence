from core.versao import VERSAO_INTERFACE
import queue
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from automacao.driver import criar_driver
from auth.sessao import SESSAO
from configuracoes.settings import (
    TEMPO_ABERTURA_NAVEGADOR,
    TEMPO_CARREGAMENTO_PAGINA,
    obter_link_validacao,
)
from core.orquestrador import (
        OrquestradorAnalise,
        ProcessamentoCancelado,
        normalizar_configuracao,
)
from dados.fontes import limpar_arquivo_temporario
from services.central import registrar_atividade_analytics
from services.jobs import (
        atualizar_job,
        cancelamento_solicitado,
        cancelar_job,
        concluir_job,
        criar_job,
        falhar_job,
        iniciar_job,
)
from historico.repositorio import registrar_analise
from sistema.idbrowser import identificar_tipo_navegador, localizar_navegador_padrao
from sistema.iduser import identificar_usuario
from sistema.opsystemcheck import verificar_sistema_operacional
from interface.tema import CORES
from interface.navegacao_analytics import criar_sidebar_analytics


class AppLayoutMixin:
    def criar_interface(self):


            # ==========================================================
            # TEMA / CORES
            # ==========================================================

            self.cores = dict(CORES)
            self.cores["terminal"] = CORES["input"]

            self.root.configure(
                    bg=self.cores["bg"]
            )

            self.root.title(
                    f"Data Intelligence · Dashboard analítico · {VERSAO_INTERFACE}"
            )

            # ==========================================================
            # ESTILO TTK
            # ==========================================================

            estilo = ttk.Style()

            estilo.theme_use("clam")

            estilo.configure(
                    "TProgressbar",
                    troughcolor=self.cores["border"],
                    background=self.cores["primary"],
                    borderwidth=0,
                    thickness=7
            )

            estilo.configure(
                    "Modern.TButton",
                    font=("Inter", 10, "bold"),
                    padding=(15, 10),
                    background=self.cores["primary"],
                    foreground="#FFFFFF",
                    borderwidth=0
            )

            estilo.map(
                    "Modern.TButton",
                    background=[
                    ("active", "#0EA5E9")
                    ]
            )

            # ==========================================================
            # CONTAINER PRINCIPAL
            # ==========================================================

            container = self.container = tk.Frame(
                    self.root,
                    bg=self.cores["bg"]
            )

            container.pack(
                    fill="both",
                    expand=True
            )

            # ==========================================================
            # SIDEBAR ANALYTICS ÚNICA
            # ==========================================================

            # O dashboard de resultados usava um menu próprio. Ao abrir
            # Explorar dados, Relatórios ou Visualizações a aplicação
            # reconstruía a sidebar com outro conjunto de itens. Todas as
            # páginas analíticas passam agora pelo mesmo componente.
            navegacao_sidebar = dict(self.navegacao)
            navegacao_sidebar["analytics_secao"] = self._navegar_secao_analytics
            for destino in (
                    "nova",
                    "perfis",
                    "inicio",
                    "modulos",
                    "historico",
                    "aprovacoes",
                    "configuracoes",
                    "usuarios",
            ):
                    if self.navegacao.get(destino) is not None:
                            navegacao_sidebar[destino] = (
                                    lambda alvo=destino: self._navegar(alvo)
                            )
            criar_sidebar_analytics(
                    container,
                    navegacao_sidebar,
                    ativo="visao",
                    voltar=lambda: self._navegar("modulos"),
            )

            # ==========================================================
            # ÁREA DIREITA
            # ==========================================================

            conteudo = tk.Frame(
                    container,
                    bg=self.cores["bg"]
            )

            conteudo.pack(
                    side="right",
                    fill="both",
                    expand=True
            )

            # ==========================================================
            # HEADER
            # ==========================================================

            header = tk.Frame(
                    conteudo,
                    bg=self.cores["bg"]
            )

            header.pack(
                    fill="x",
                    padx=30,
                    pady=(25, 15)
            )

            titulo_area = tk.Frame(
                    header,
                    bg=self.cores["bg"]
            )

            titulo_area.pack(
                    side="left"
            )

            tk.Label(
                    titulo_area,
                    text="Dashboard analítico",
                    font=("Inter", 23, "bold"),
                    fg=self.cores["text"],
                    bg=self.cores["bg"]
            ).pack(
                    anchor="w"
            )

            tk.Label(
                    titulo_area,
                    text="Indicadores, qualidade, diagnósticos e logs do processamento atual.",
                    font=("Inter", 10),
                    fg=self.cores["text_sec"],
                    bg=self.cores["bg"]
            ).pack(
                    anchor="w",
                    pady=(3, 0)
            )

            # ----------------------------------------------------------
            # STATUS
            # ----------------------------------------------------------

            status_area = tk.Frame(
                    header,
                    bg=self.cores["card"]
            )

            status_area.pack(
                    side="right"
            )

            # A validação web continua disponível, mas deixa de fazer
            # parte da navegação. Assim a sidebar permanece idêntica em
            # todas as telas do contexto analítico.
            self.botao_iniciar = tk.Button(
                    header,
                    text="▶  VALIDAR AUTOMAÇÃO WEB",
                    command=self.iniciar_automacao,
                    font=("Inter", 8, "bold"),
                    bg=self.cores["primary"],
                    fg="#FFFFFF",
                    activebackground=self.cores["primary_hover"],
                    activeforeground="#FFFFFF",
                    relief="flat",
                    bd=0,
                    cursor="hand2",
                    padx=11,
                    pady=8,
            )
            self.botao_iniciar.pack(side="right", padx=(0, 10))

            tk.Label(
                    status_area,
                    text="●",
                    font=("Inter", 10),
                    fg=self.cores["success"],
                    bg=self.cores["card"]
            ).pack(
                    side="left",
                    padx=(12, 5),
                    pady=8
            )

            self.status = tk.StringVar(
                    value="Aguardando execução..."
            )

            tk.Label(
                    status_area,
                    textvariable=self.status,
                    font=("Inter", 9, "bold"),
                    fg=self.cores["text"],
                    bg=self.cores["card"]
            ).pack(
                    side="left",
                    padx=(0, 12),
                    pady=8
            )

            # ==========================================================
            # ÁREA SCROLLÁVEL
            # ==========================================================

            corpo = tk.Frame(
                    conteudo,
                    bg=self.cores["bg"]
            )

            corpo.pack(
                    fill="both",
                    expand=True,
                    padx=30,
                    pady=(5, 20)
            )

            # ==========================================================
            # CARDS DE INDICADORES
            # ==========================================================

            cards = tk.Frame(
                    corpo,
                    bg=self.cores["bg"]
            )

            cards.pack(
                    fill="x",
                    pady=(0, 15)
            )

            (
                    self.card_faturamento,
                    self.card_faturamento_titulo,
            ) = self.criar_card(
                    cards,
                    "FATURAMENTO",
                    "R$ 0,00",
                    "▣"
            )

            (
                    self.card_vendas,
                    self.card_vendas_titulo,
            ) = self.criar_card(
                    cards,
                    "VENDAS",
                    "0",
                    "↗"
            )

            (
                    self.card_quantidade,
                    self.card_quantidade_titulo,
            ) = self.criar_card(
                    cards,
                    "ITENS VENDIDOS",
                    "0",
                    "▤"
            )

            (
                    self.card_ticket,
                    self.card_ticket_titulo,
            ) = self.criar_card(
                    cards,
                    "TICKET MÉDIO",
                    "R$ 0,00",
                    "◉"
            )

            # ==========================================================
            # LINHA CENTRAL
            # ==========================================================

            linha = tk.Frame(
                    corpo,
                    bg=self.cores["bg"]
            )

            linha.pack(
                    fill="both",
                    expand=True
            )

            # ==========================================================
            # ARQUIVOS
            # ==========================================================

            arquivos_frame = self.criar_painel(
                    linha,
                    "Arquivos selecionados"
            )

            arquivos_frame.pack(
                    side="left",
                    fill="both",
                    expand=True,
                    padx=(0, 8)
            )
            self.label_arquivo = tk.Label(
                    arquivos_frame,
                    text="Nenhum arquivo selecionado",
                    font=("Inter", 9),
                    fg=self.cores["text_sec"],
                    bg=self.cores["card"],
                    anchor="w"
            )

            self.label_arquivo.pack(
                    fill="x",
                    padx=15,
                    pady=(0, 5)
            )

            self.lista_arquivos = tk.Listbox(
                    arquivos_frame,
                    bg=self.cores["terminal"],
                    fg=self.cores["text"],
                    selectbackground=self.cores["primary"],
                    selectforeground="#FFFFFF",
                    relief="flat",
                    bd=0,
                    font=("Inter", 9),
                    highlightthickness=0
            )

            self.lista_arquivos.pack(
                    fill="both",
                    expand=True,
                    padx=15,
                    pady=(5, 15)
            )

            tk.Button(
                    arquivos_frame,
                    text="+  Adicionar arquivos",
                    command=self.selecionar_arquivos,
                    font=("Inter", 9, "bold"),
                    bg=self.cores["card"],
                    fg=self.cores["primary"],
                    activebackground=self.cores["card_hover"],
                    activeforeground=self.cores["primary"],
                    relief="flat",
                    bd=0,
                    cursor="hand2"
            ).pack(
                    fill="x",
                    padx=15,
                    pady=(0, 15)
            )

            # ==========================================================
            # DESTAQUES
            # ==========================================================

            destaques = self.criar_painel(
                    linha,
                    "Destaques da análise"
            )
            destaques.pack(
                    side="right",
                    fill="both",
                    expand=True,
                    padx=(8, 0)
            )


            # ==========================================================
            # PRODUTO LÍDER
            # ==========================================================

            self.label_produto_titulo = tk.Label(
                    destaques,
                    text="Produto líder",
                    font=("Inter", 12, "bold"),
                    fg=self.cores["text"],
                    bg=self.cores["card"],
                    justify="left"
            )

            self.label_produto_titulo.pack(
                    anchor="w",
                    padx=20,
                    pady=(20, 2)
            )


            self.label_produto = tk.Label(
                    destaques,
                    text="—",
                    font=("Inter", 11, "bold"),
                    fg=self.cores["text_sec"],
                    bg=self.cores["card"],
                    justify="left"
            )

            self.label_produto.pack(
                    anchor="w",
                    padx=20,
                    pady=(0, 20)
            )


            # ==========================================================
            # LOJA LÍDER
            # ==========================================================

            self.label_loja_titulo = tk.Label(
                    destaques,
                    text="Loja líder",
                    font=("Inter", 12, "bold"),
                    fg=self.cores["text"],
                    bg=self.cores["card"],
                    justify="left"
            )

            self.label_loja_titulo.pack(
                    anchor="w",
                    padx=20,
                    pady=(5, 2)
            )


            self.label_loja = tk.Label(
                    destaques,
                    text="—",
                    font=("Inter", 11, "bold"),
                    fg=self.cores["text_sec"],
                    bg=self.cores["card"],
                    justify="left"
            )

            self.label_loja.pack(
                    anchor="w",
                    padx=20,
                    pady=(0, 15)
            )
            # ==========================================================
            # LOG
            # ==========================================================

            log_painel = self.criar_painel(
                    corpo,
                    "Atividade da automação"
            )

            log_painel.pack(
                    fill="both",
                    expand=True,
                    pady=(15, 0)
            )

            self.log = ScrolledText(
                    log_painel,
                    height=10,
                    bg=self.cores["terminal"],
                    fg="#CBD5E1",
                    insertbackground="#FFFFFF",
                    selectbackground=self.cores["primary"],
                    relief="flat",
                    bd=0,
                    font=("Consolas", 9),
                    state="disabled"
            )

            self.log.pack(
                    fill="both",
                    expand=True,
                    padx=15,
                    pady=(5, 15)
            )

            # ==========================================================
            # PROGRESSO
            # ==========================================================

            progresso_frame = tk.Frame(
                    corpo,
                    bg=self.cores["bg"]
            )

            progresso_frame.pack(
                    fill="x",
                    pady=(12, 0)
            )

            self.progresso = ttk.Progressbar(
                    progresso_frame,
                    mode="determinate",
                    maximum=100,
                    style="TProgressbar"
            )

            self.progresso.pack(
                    fill="x"
            )

            # ==========================================================
            # MENSAGENS INICIAIS
            # ==========================================================

            self.adicionar_log(
                    "Sistema inicializado."
            )

            self.adicionar_log(
                    "Aguardando configuração da automação."
            )


    def criar_menu_item(self, parent, icone, texto, comando=None, ativo=False):

            fundo = self.cores["card"] if ativo else self.cores["sidebar"]
            cor_texto = self.cores["text"] if ativo else self.cores["text_sec"]

            frame = tk.Frame(
                    parent,
                    bg=fundo,
                    cursor="hand2" if comando else "arrow",
            )

            frame.pack(
                    fill="x",
                    padx=12,
                    pady=2
            )

            icone_label = tk.Label(
                    frame,
                    text=icone,
                    font=("Inter", 13),
                    fg=cor_texto,
                    bg=fundo,
            )
            icone_label.pack(
                    side="left",
                    padx=(18, 10),
                    pady=10
            )

            texto_label = tk.Label(
                    frame,
                    text=texto,
                    font=("Inter", 10, "bold" if ativo else "normal"),
                    fg=cor_texto,
                    bg=fundo,
            )
            texto_label.pack(
                    side="left",
                    pady=10
            )

            if comando:
                    for widget in (frame, icone_label, texto_label):
                            widget.bind("<Button-1>", lambda _evento: comando())

            return frame


    def criar_card(self, parent, titulo, valor, icone):

            card = tk.Frame(
                    parent,
                    bg=self.cores["card"],
                    height=105
            )

            card.pack(
                    side="left",
                    fill="both",
                    expand=True,
                    padx=5
            )

            card.pack_propagate(
                    False
            )

            topo = tk.Frame(
                    card,
                    bg=self.cores["card"]
            )

            topo.pack(
                    fill="x",
                    padx=15,
                    pady=(15, 5)
            )

            tk.Label(
                    topo,
                    text=icone,
                    font=("Inter", 14),
                    fg=self.cores["primary"],
                    bg=self.cores["card"]
            ).pack(
                    side="left"
            )

            titulo_label = tk.Label(
                    topo,
                    text=titulo,
                    font=("Inter", 8, "bold"),
                    fg=self.cores["text_sec"],
                    bg=self.cores["card"]
            )

            titulo_label.pack(
                    side="left",
                    padx=8
            )

            valor_label = tk.Label(
                    card,
                    text=valor,
                    font=("Inter", 17, "bold"),
                    fg=self.cores["text"],
                    bg=self.cores["card"]
            )

            valor_label.pack(
                    anchor="w",
                    padx=15
            )

            return valor_label, titulo_label


    def criar_painel(self, parent, titulo):

            painel = tk.Frame(
                    parent,
                    bg=self.cores["card"],
                    highlightbackground=self.cores["border"],
                    highlightthickness=1
            )

            titulo_label = tk.Label(
                    painel,
                    text=titulo,
                    font=("Inter", 10, "bold"),
                    fg=self.cores["text"],
                    bg=self.cores["card"]
            )

            titulo_label.pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 8)
            )

            return painel


    def configurar_dashboard_categoria(self, categoria):
            self.categoria_atual = categoria or "desconhecida"
            configuracoes = {
                    "vendas": {
                            "cards": (
                                    ("FATURAMENTO", "faturamento_total", "moeda"),
                                    ("VENDAS", "total_vendas", "inteiro"),
                                    ("ITENS VENDIDOS", "quantidade_total", "inteiro"),
                                    ("TICKET MÉDIO", "ticket_medio", "moeda"),
                            ),
                            "destaques": (
                                    ("Produto líder", "produto_maior_faturamento", "texto", "valor_produto_lider", "moeda"),
                                    ("Loja líder", "loja_maior_faturamento", "texto", "valor_loja_lider", "moeda"),
                            ),
                    },
                    "financeiro": {
                            "cards": (
                                    ("RECEITA", "receita_total", "moeda"),
                                    ("DESPESA", "despesa_total", "moeda"),
                                    ("SALDO", "saldo", "moeda"),
                                    ("MARGEM", "margem_operacional", "percentual"),
                            ),
                            "destaques": (
                                    ("Maior movimentação", "categoria_maior_movimentacao", "texto", "valor_categoria_lider", "moeda"),
                                    ("Maior despesa", "maior_despesa", "moeda", None, None),
                            ),
                    },
                    "estoque": {
                            "cards": (
                                    ("ESTOQUE TOTAL", "estoque_total", "inteiro"),
                                    ("PRODUTOS", "produtos_distintos", "inteiro"),
                                    ("BAIXO ESTOQUE", "produtos_baixo_estoque", "inteiro"),
                                    ("VALOR DO ESTOQUE", "valor_estoque", "moeda"),
                            ),
                            "destaques": (
                                    ("Produto crítico", "produto_critico", "texto", "valor_produto_critico", "inteiro"),
                                    ("Maior estoque", "produto_maior_estoque", "texto", "valor_maior_estoque", "inteiro"),
                            ),
                    },
                    "cadastro": {
                            "cards": (
                                    ("REGISTROS", "total_registros", "inteiro"),
                                    ("ÚNICOS", "registros_unicos", "inteiro"),
                                    ("DUPLICADOS", "registros_duplicados", "inteiro"),
                                    ("ATIVOS", "registros_ativos", "inteiro"),
                            ),
                            "destaques": (
                                    ("Maior categoria", "maior_categoria", "texto", "quantidade_categoria_lider", "inteiro"),
                                    ("Qualidade da base", "qualidade.nivel_qualidade", "texto", "qualidade.score_qualidade", "percentual"),
                            ),
                    },
                    "recursos_humanos": {
                            "cards": (
                                    ("COLABORADORES", "total_colaboradores", "inteiro"),
                                    ("SETORES", "total_setores", "inteiro"),
                                    ("ADMISSÕES", "total_admissoes", "inteiro"),
                                    ("DESLIGAMENTOS", "total_desligamentos", "inteiro"),
                            ),
                            "destaques": (
                                    ("Maior setor", "maior_setor", "texto", "quantidade_maior_setor", "inteiro"),
                                    ("Folha salarial", "folha_total", "moeda", None, None),
                            ),
                    },
                    "compras": {
                            "cards": (
                                    ("SOLICITAÇÕES", "total_solicitacoes", "inteiro"),
                                    ("PENDENTES", "solicitacoes_pendentes", "inteiro"),
                                    ("VALOR SOLICITADO", "valor_solicitado", "moeda"),
                                    ("APROVAÇÃO", "taxa_aprovacao", "percentual"),
                            ),
                            "destaques": (
                                    ("Fornecedor mais utilizado", "fornecedor_mais_utilizado", "texto", None, None),
                                    ("Valor pendente", "valor_pendente", "moeda", None, None),
                            ),
                    },
                    "ti": {
                            "cards": (
                                    ("CHAMADOS", "total_chamados", "inteiro"),
                                    ("ABERTOS", "chamados_abertos", "inteiro"),
                                    ("CRÍTICOS", "chamados_criticos", "inteiro"),
                                    ("RESOLUÇÃO", "taxa_resolucao", "percentual"),
                            ),
                            "destaques": (
                                    ("Categoria mais frequente", "categoria_mais_frequente", "texto", None, None),
                                    ("Chamados reincidentes", "chamados_reincidentes", "inteiro", None, None),
                            ),
                    },
                    "marketing": {
                            "cards": (
                                    ("INVESTIMENTO", "investimento_total", "moeda"),
                                    ("RECEITA", "receita_atribuida", "moeda"),
                                    ("ROAS", "roas", "decimal"),
                                    ("CONVERSÃO", "taxa_conversao", "percentual"),
                            ),
                            "destaques": (
                                    ("Melhor canal", "melhor_canal", "texto", None, None),
                                    ("CAC", "cac", "moeda", "cpl", "moeda"),
                            ),
                    },
                    "administrativo": {
                            "cards": (
                                    ("SOLICITAÇÕES", "total_solicitacoes", "inteiro"),
                                    ("PENDENTES", "solicitacoes_pendentes", "inteiro"),
                                    ("VALOR TOTAL", "valor_total", "moeda"),
                                    ("APROVAÇÃO", "taxa_aprovacao", "percentual"),
                            ),
                            "destaques": (
                                    ("Categoria principal", "categoria_principal", "texto", None, None),
                                    ("Valor pendente", "valor_pendente", "moeda", None, None),
                            ),
                    },
                    "juridico": {
                            "cards": (
                                    ("CONTRATOS", "total_contratos", "inteiro"),
                                    ("ATIVOS", "contratos_ativos", "inteiro"),
                                    ("VENCENDO", "contratos_vencendo_30_dias", "inteiro"),
                                    ("VALOR EM RISCO", "valor_em_risco", "moeda"),
                            ),
                            "destaques": (
                                    ("Risco predominante", "risco_predominante", "texto", None, None),
                                    ("Alto risco", "contratos_alto_risco", "inteiro", None, None),
                            ),
                    },
                    "comercial": {
                            "cards": (
                                    ("OPORTUNIDADES", "total_oportunidades", "inteiro"),
                                    ("ABERTAS", "oportunidades_abertas", "inteiro"),
                                    ("PIPELINE", "pipeline_aberto", "moeda"),
                                    ("CONVERSÃO", "taxa_conversao", "percentual"),
                            ),
                            "destaques": (
                                    ("Etapa principal", "etapa_principal", "texto", None, None),
                                    ("Receita ganha", "receita_ganha", "moeda", None, None),
                            ),
                    },
            }
            self.dashboard_config = configuracoes.get(
                    self.categoria_atual,
                    {
                            "cards": (
                                    ("REGISTROS", "universais.total_registros", "inteiro"),
                                    ("COLUNAS", "universais.total_colunas", "inteiro"),
                                    ("AUSENTES", "universais.valores_ausentes", "inteiro"),
                                    ("COMPLETUDE", "universais.completude", "percentual"),
                            ),
                            "destaques": (
                                    ("Categoria", "categoria_motor", "texto", None, None),
                                    ("Qualidade", "qualidade.nivel_qualidade", "texto", "qualidade.score_qualidade", "percentual"),
                            ),
                    },
            )
            for label, titulo in zip(
                    (
                            self.card_faturamento_titulo,
                            self.card_vendas_titulo,
                            self.card_quantidade_titulo,
                            self.card_ticket_titulo,
                    ),
                    (item[0] for item in self.dashboard_config["cards"]),
            ):
                    label.configure(text=titulo)

            destaques = self.dashboard_config["destaques"]
            self.label_produto_titulo.configure(text=destaques[0][0])
            self.label_loja_titulo.configure(text=destaques[1][0])

