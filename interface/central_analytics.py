"""Central visual e funcional do motor analítico V8."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import threading
from pathlib import Path

from auth.sessao import SESSAO
from historico.repositorio import listar_historico
from enterprise.recursos import (
    alterar_estado_recurso,
    criar_recurso,
    listar_recursos,
)
from enterprise.datasets import (
    atualizar_metadados_conjunto,
    excluir_conjunto,
    importar_conjunto,
    listar_conjuntos,
    obter_conjunto,
    substituir_arquivo_conjunto,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_card_acao,
    criar_chip,
    criar_estado_vazio,
    preparar_janela_secundaria,
    criar_sidebar,
    criar_titulo_secao,
)
from interface.tema import CORES, FONTES, LAYOUT
from interface.tema import adicionar_divisorias_treeview, configurar_estilos_ttk
from interface.navegacao_analytics import MENU_ANALYTICS, criar_sidebar_analytics


ESQUEMAS_ANALYTICS = {
    "relatorios": (
        ("titulo", "Relatório", "texto"),
        ("conjunto", "Conjunto de dados", "texto"),
        ("periodo", "Período", "texto"),
        ("formato", "Formato", "opcoes", ("PDF", "Excel", "CSV", "HTML")),
        ("responsavel", "Responsável", "texto"),
        ("status", "Situação", "opcoes", ("Rascunho", "Configurado", "Gerado")),
    ),
    "visualizacoes": (
        ("nome", "Visualização", "texto"),
        ("conjunto", "Conjunto de dados", "texto"),
        ("grafico", "Tipo de gráfico", "opcoes", ("Barras", "Linha", "Pizza", "Dispersão", "Tabela")),
        ("eixo", "Dimensão / eixo", "texto"),
        ("metrica", "Métrica", "texto"),
        ("status", "Situação", "opcoes", ("Rascunho", "Publicada", "Arquivada")),
    ),
    "agendamentos": (
        ("nome", "Agendamento", "texto"),
        ("rotina", "Rotina", "opcoes", ("Análise", "Relatório", "Importação", "E-mail")),
        ("frequencia", "Frequência", "opcoes", ("Diária", "Semanal", "Mensal", "Uma vez")),
        ("horario", "Horário", "texto"),
        ("responsavel", "Responsável", "texto"),
        ("status", "Situação", "opcoes", ("Ativo", "Pausado", "Concluído")),
    ),
    "alertas": (
        ("nome", "Alerta", "texto"),
        ("metrica", "Indicador monitorado", "texto"),
        ("condicao", "Condição", "opcoes", ("Maior que", "Menor que", "Igual a", "Variação %")),
        ("limite", "Limite", "numero"),
        ("severidade", "Severidade", "opcoes", ("Informativa", "Atenção", "Crítica")),
        ("status", "Situação", "opcoes", ("Ativo", "Pausado", "Disparado")),
    ),
    "modelos": (
        ("nome", "Modelo", "texto"),
        ("categoria", "Categoria", "texto"),
        ("objetivo", "Objetivo", "texto"),
        ("versao", "Versão", "texto"),
        ("responsavel", "Responsável", "texto"),
        ("status", "Situação", "opcoes", ("Rascunho", "Validado", "Produção", "Desativado")),
    ),
    "assistente": (
        ("titulo", "Conversa", "texto"),
        ("contexto", "Contexto autorizado", "texto"),
        ("pergunta", "Pergunta inicial", "texto"),
        ("escopo", "Escopo", "opcoes", ("Resumo", "Indicadores", "Qualidade", "Anomalias")),
        ("responsavel", "Solicitante", "texto"),
        ("status", "Situação", "opcoes", ("Aberta", "Respondida", "Arquivada")),
    ),
}

CONFIGURACOES_SECOES_ANALYTICS = {
    "relatorios": {
        "subtitulo": (
            "Configure conjunto, período e formato antes da geração. "
            "A configuração permanece auditada para futura prévia e exportação."
        ),
        "acao": "+  CONFIGURAR RELATÓRIO",
        "vazio": "Configure o primeiro relatório analítico.",
    },
    "visualizacoes": {
        "subtitulo": (
            "Defina conjunto, dimensão, métrica e tipo de gráfico para compor "
            "dashboards e relatórios."
        ),
        "acao": "+  NOVA VISUALIZAÇÃO",
        "vazio": "Crie a primeira visualização vinculada aos seus dados.",
    },
    "agendamentos": {
        "subtitulo": (
            "Planeje análises, importações, relatórios e entregas recorrentes "
            "com frequência e horário explícitos."
        ),
        "acao": "+  NOVO AGENDAMENTO",
        "vazio": "Cadastre a primeira rotina programada.",
    },
    "alertas": {
        "subtitulo": (
            "Monitore indicadores do Analytics sem misturar estes eventos com a "
            "Central global de notificações."
        ),
        "acao": "+  NOVO ALERTA",
        "vazio": "Defina uma métrica e um limite para iniciar o monitoramento.",
    },
    "modelos": {
        "subtitulo": (
            "Catalogue versões, objetivos, responsáveis e estados de validação "
            "dos modelos analíticos."
        ),
        "acao": "+  NOVO MODELO",
        "vazio": "Registre o primeiro modelo analítico.",
    },
    "assistente": {
        "subtitulo": (
            "Organize conversas por contexto autorizado, pergunta e escopo. "
            "Respostas por IA exigem uma integração homologada."
        ),
        "acao": "+  NOVA CONVERSA",
        "vazio": "Inicie uma conversa contextual sobre indicadores e qualidade.",
    },
}


class TelaCentralAnalytics:
    def __init__(self, root, navegacao, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.secao = secao
        self._ativa = True
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.container.bind("<Destroy>", self._ao_destruir, add="+")
        self.criar_interface()

    def _ao_destruir(self, evento):
        if evento.widget is self.container:
            self._ativa = False

    def criar_interface(self):
        criar_sidebar_analytics(
            self.container,
            self.navegacao,
            ativo=self.secao,
            voltar=self.navegacao.get("modulos"),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(24, 22),
        )
        conteudo = viewport.conteudo
        if self.secao == "visao":
            self._dashboard(conteudo)
        elif self.secao in {"importacoes", "conjuntos"}:
            self._biblioteca_dados(conteudo)
        else:
            self._recurso_analytics(conteudo)

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
        criar_cabecalho(
            parent,
            "Dashboard analítico",
            "Importe dados, execute o motor analítico e transforme resultados em decisões.",
            acao=lambda area: criar_botao(
                area,
                "+  NOVA ANÁLISE",
                lambda: self.navegacao["nova"](),
            ),
            breadcrumb="MÓDULOS  /  ANALYTICS  /  DASHBOARD ANALÍTICO",
            etiqueta="MOTOR DISPONÍVEL",
        )
        grade = GradeResponsiva(parent, max_colunas=4, largura_minima=235, bg=CORES["bg"])
        grade.pack(fill="x")
        atalhos = (
            ("+", "Nova análise", "Configure fonte, categoria, período e módulos do processamento.", lambda: self.navegacao["nova"](), CORES["primary"], None),
            ("↓", "Importar dados", "Prepare arquivos e conexões para novos conjuntos de dados.", lambda: self.abrir_secao("importacoes"), CORES["teal"], None),
            ("◷", "Histórico", "Consulte análises concluídas e seus resumos persistidos.", self.navegacao.get("historico"), CORES["purple"], None),
            ("▤", "Relatórios", "Monte relatórios executivos e exportações persistidas.", lambda: self.abrir_secao("relatorios"), CORES["success"], None),
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
            grade.adicionar(card)

        corpo = tk.Frame(parent, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, pady=(14, 0))
        esquerda = tk.Frame(corpo, bg=CORES["bg"])
        direita = tk.Frame(corpo, bg=CORES["bg"])
        self._recentes(esquerda)
        self._motor(direita)
        self._pipeline(direita)

        def reorganizar(evento=None):
            largura = evento.width if evento else corpo.winfo_width()
            esquerda.grid_forget()
            direita.grid_forget()
            corpo.grid_columnconfigure(0, weight=1)
            corpo.grid_columnconfigure(1, weight=0)
            if largura >= 900:
                corpo.grid_columnconfigure(1, minsize=315)
                esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
                direita.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            else:
                esquerda.grid(row=0, column=0, columnspan=2, sticky="nsew")
                direita.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        corpo.bind("<Configure>", reorganizar, add="+")
        corpo.after_idle(reorganizar)

    def _recentes(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True)
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=18, pady=16)
        criar_titulo_secao(
            interior,
            "Análises recentes",
            "Execuções armazenadas sem preservar as planilhas originais.",
            acao=lambda area: criar_botao(
                area,
                "VER HISTÓRICO  →",
                self.navegacao.get("historico"),
                tipo="fantasma",
                compacto=True,
            ),
        )
        cab = tk.Frame(interior, bg=CORES["card_secundario"])
        cab.pack(fill="x", pady=(4, 2))
        for texto, largura in (("ANÁLISE", 36), ("DATA", 15), ("REGISTROS", 12), ("STATUS", 12)):
            tk.Label(
                cab,
                text=texto,
                font=("Segoe UI", 9, "bold"),
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

    def _recurso_analytics(self, parent):
        titulo = next(
            (rotulo for chave, _icone, rotulo in MENU_ANALYTICS if chave == self.secao),
            self.secao.title(),
        )
        configurar_estilos_ttk(self.root)
        self.analytics_esquema = ESQUEMAS_ANALYTICS.get(
            self.secao,
            (("nome", "Nome", "texto"), ("descricao", "Descrição", "texto"),
             ("responsavel", "Responsável", "texto"),
             ("status", "Situação", "opcoes", ("Ativo", "Inativo"))),
        )
        configuracao_secao = CONFIGURACOES_SECOES_ANALYTICS.get(
            self.secao,
            {
                "subtitulo": "Configurações persistidas e auditadas do motor analítico.",
                "acao": "+  NOVO",
                "vazio": "Registre a primeira configuração.",
            },
        )

        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            criar_botao(
                bloco,
                "?  AJUDA",
                lambda: messagebox.showinfo(
                    titulo,
                    configuracao_secao["subtitulo"],
                    parent=self.root,
                ),
                tipo="secundario",
                compacto=True,
            ).pack(side="right")
            criar_botao(
                bloco,
                configuracao_secao["acao"],
                lambda: self._novo_recurso_analytics(titulo),
                compacto=True,
            ).pack(side="right", padx=(0, 8))
            return bloco

        criar_cabecalho(
            parent,
            titulo,
            configuracao_secao["subtitulo"],
            acao=acoes,
            breadcrumb=f"MÓDULOS  /  ANALYTICS  /  {titulo.upper()}",
            etiqueta="OPERACIONAL V9.0",
        )
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=16, pady=(14, 10))
        self.analytics_total = tk.Label(
            topo,
            text="0 registro(s)",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.analytics_total.pack(side="right")
        tk.Label(
            topo,
            text="CONFIGURAÇÕES DO CONTEXTO ATUAL",
            font=("Segoe UI", 9, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(side="left")
        area = tk.Frame(painel, bg=CORES["card"])
        area.pack(fill="both", expand=True, padx=16)
        colunas = tuple(campo[0] for campo in self.analytics_esquema) + (
            "atualizacao",
        )
        self.analytics_tabela = ttk.Treeview(
            area,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        definicoes = tuple(
            (campo[0], campo[1].upper(), 130 if campo[2] != "texto" else 200)
            for campo in self.analytics_esquema
        ) + (("atualizacao", "ATUALIZAÇÃO", 150),)
        for chave, rotulo, largura in definicoes:
            self.analytics_tabela.heading(chave, text=rotulo)
            self.analytics_tabela.column(
                chave,
                width=largura,
                anchor="w",
                stretch=chave == self.analytics_esquema[0][0],
            )
        barra = ttk.Scrollbar(
            area,
            orient="vertical",
            command=self.analytics_tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            area,
            orient="horizontal",
            command=self.analytics_tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.analytics_tabela.configure(
            yscrollcommand=barra.set,
            xscrollcommand=barra_horizontal.set,
        )
        self.analytics_tabela.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        area.grid_rowconfigure(0, weight=1)
        area.grid_columnconfigure(0, weight=1)
        self.analytics_vazio = criar_estado_vazio(
            area,
            "◇",
            f"Nenhuma configuração em {titulo}",
            configuracao_secao["vazio"],
        )
        adicionar_divisorias_treeview(
            self.analytics_tabela,
            sobreposicao=self.analytics_vazio,
        )
        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=16, pady=14)
        criar_botao(
            rodape,
            "ARQUIVAR SELECIONADO",
            self._arquivar_recurso_analytics,
            tipo="secundario",
            compacto=True,
        ).pack(side="left")
        self._carregar_recursos_analytics()

    def _biblioteca_dados(self, parent):
        titulo = "Importações" if self.secao == "importacoes" else "Explorar dados"
        subtitulo = (
            "Importe, valide e armazene fontes para reutilização em novas análises."
            if self.secao == "importacoes"
            else (
                "Consulte os conjuntos de dados administrados e escolha quais serão usados "
                "pelo motor analítico."
            )
        )

        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            criar_botao(
                bloco,
                "?  AJUDA",
                lambda: messagebox.showinfo(
                    titulo,
                    "A biblioteca preserva uma cópia administrada do arquivo, "
                    "valida sua integridade e registra metadados para reutilização.",
                    parent=self.root,
                ),
                tipo="secundario",
                compacto=True,
            ).pack(side="right")
            criar_botao(
                bloco,
                "+  IMPORTAR ARQUIVO",
                self._importar_dataset,
                compacto=True,
            ).pack(side="right", padx=(0, 8))
            return bloco

        criar_cabecalho(
            parent,
            titulo,
            subtitulo,
            acao=acoes,
            breadcrumb=f"MÓDULOS  /  ANALYTICS  /  {titulo.upper()}",
            etiqueta="BIBLIOTECA V9.0",
        )
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=16, pady=(14, 10))
        self.dataset_status = tk.Label(
            topo,
            text="Carregando biblioteca...",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.dataset_status.pack(side="right")
        tk.Label(
            topo,
            text="FONTES ADMINISTRADAS",
            font=("Segoe UI", 9, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(side="left")

        area = tk.Frame(painel, bg=CORES["card"])
        area.pack(fill="both", expand=True, padx=16)
        colunas = (
            "nome", "arquivo", "tipo", "tamanho", "registros", "colunas",
            "categoria", "status", "responsavel", "atualizacao",
        )
        self.dataset_tabela = ttk.Treeview(
            area, columns=colunas, show="headings", style="Dark.Treeview"
        )
        definicoes = (
            ("nome", "CONJUNTO", 210),
            ("arquivo", "ARQUIVO", 210),
            ("tipo", "TIPO", 65),
            ("tamanho", "TAMANHO", 90),
            ("registros", "REGISTROS", 95),
            ("colunas", "COLUNAS", 80),
            ("categoria", "CATEGORIA", 125),
            ("status", "STATUS", 90),
            ("responsavel", "RESPONSÁVEL", 150),
            ("atualizacao", "ATUALIZAÇÃO", 145),
        )
        for chave, rotulo, largura in definicoes:
            self.dataset_tabela.heading(chave, text=rotulo)
            self.dataset_tabela.column(
                chave,
                width=largura,
                minwidth=min(80, largura),
                stretch=chave in {"nome", "arquivo"},
                anchor="w",
            )
        vertical = ttk.Scrollbar(
            area,
            orient="vertical",
            command=self.dataset_tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        horizontal = ttk.Scrollbar(
            area,
            orient="horizontal",
            command=self.dataset_tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.dataset_tabela.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )
        self.dataset_tabela.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        area.grid_rowconfigure(0, weight=1, minsize=280)
        area.grid_columnconfigure(0, weight=1)
        self.dataset_vazio = criar_estado_vazio(
            area,
            "◇",
            "Nenhum conjunto de dados importado",
            "Use Importar arquivo para iniciar a biblioteca.",
        )
        adicionar_divisorias_treeview(
            self.dataset_tabela, sobreposicao=self.dataset_vazio
        )

        rodape = GradeResponsiva(
            painel,
            max_colunas=5,
            largura_minima=160,
            gap=8,
            bg=CORES["card"],
        )
        rodape.pack(fill="x", padx=16, pady=14)
        for texto, comando, tipo in (
            ("VISUALIZAR", self._visualizar_dataset, "secundario"),
            ("USAR EM NOVA ANÁLISE", self._usar_dataset, "primario"),
            ("EDITAR METADADOS", self._editar_dataset, "secundario"),
            ("SUBSTITUIR ARQUIVO", self._substituir_dataset, "secundario"),
            ("EXCLUIR", self._excluir_dataset, "perigo"),
        ):
            botao = criar_botao(
                rodape, texto, comando, tipo=tipo, compacto=True
            )
            botao.configure(anchor="center")
            rodape.adicionar(botao)
        self._carregar_datasets()

    @staticmethod
    def _tamanho_dataset(total):
        valor = float(total or 0)
        for unidade in ("B", "KB", "MB", "GB"):
            if valor < 1024 or unidade == "GB":
                return f"{valor:.1f} {unidade}" if unidade != "B" else f"{int(valor)} B"
            valor /= 1024

    def _carregar_datasets(self):
        self.datasets = listar_conjuntos(SESSAO.usuario)
        for item in self.dataset_tabela.get_children():
            self.dataset_tabela.delete(item)
        for registro in self.datasets:
            self.dataset_tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(
                    registro["nome"],
                    registro["nome_original"],
                    registro["extensao"].lstrip(".").upper(),
                    self._tamanho_dataset(registro["tamanho_bytes"]),
                    f"{int(registro['total_registros']):,}".replace(",", "."),
                    registro["total_colunas"],
                    str(registro["categoria"]).replace("_", " ").title(),
                    registro["status"],
                    registro.get("responsavel_nome") or "—",
                    str(registro["atualizado_em"])[:19],
                ),
            )
        if self.datasets:
            self.dataset_vazio.place_forget()
        else:
            self.dataset_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.dataset_vazio.lift()
        self.dataset_status.configure(text=f"{len(self.datasets)} conjunto(s)")

    def _dataset_selecionado(self):
        selecao = self.dataset_tabela.selection()
        if not selecao:
            messagebox.showinfo(
                "Biblioteca de dados",
                "Selecione um conjunto de dados para continuar.",
                parent=self.root,
            )
            return None
        return int(selecao[0])

    def _importar_dataset(self):
        caminho = filedialog.askopenfilename(
            parent=self.root,
            title="Importar conjunto de dados",
            filetypes=[
                ("Dados suportados", "*.xlsx *.xls *.csv *.json *.parquet *.txt"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return
        nome = simpledialog.askstring(
            "Nome do conjunto",
            "Informe um nome para a biblioteca:",
            initialvalue=Path(caminho).stem,
            parent=self.root,
        )
        if nome is None:
            return
        self.dataset_status.configure(text="Validando e importando...", fg=CORES["warning"])
        ator = self._ator_congelado()

        def worker():
            try:
                importar_conjunto(caminho, nome=nome, ator=ator)
                erro = None
            except Exception as excecao:
                erro = str(excecao)
            try:
                self.root.after(0, self._importacao_concluida, erro)
            except tk.TclError:
                pass
        threading.Thread(target=worker, daemon=True, name="importacao-dataset").start()

    def _importacao_concluida(self, erro=None):
        if not self._ativa:
            return
        if erro:
            self.dataset_status.configure(text="Falha na importação", fg=CORES["danger"])
            messagebox.showerror("Importação", erro, parent=self.root)
            return
        self.dataset_status.configure(text="Importação concluída", fg=CORES["success"])
        self._carregar_datasets()

    @staticmethod
    def _ator_congelado():
        ator = dict(SESSAO.usuario or {})
        ator["_empresa_id"] = SESSAO.empresa_id
        ator["_filial_id"] = SESSAO.filial_id
        return ator

    def _editar_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        atual = next(item for item in self.datasets if item["id"] == conjunto_id)
        nome = simpledialog.askstring(
            "Metadados do conjunto",
            "Nome do conjunto:",
            initialvalue=atual["nome"],
            parent=self.root,
        )
        if nome is None:
            return
        descricao = simpledialog.askstring(
            "Metadados do conjunto",
            "Descrição:",
            initialvalue=atual.get("descricao") or "",
            parent=self.root,
        )
        if descricao is None:
            return
        tags = simpledialog.askstring(
            "Metadados do conjunto",
            "Tags separadas por vírgula:",
            initialvalue=atual.get("tags") or "",
            parent=self.root,
        )
        if tags is None:
            return
        try:
            atualizar_metadados_conjunto(
                conjunto_id,
                nome=nome,
                descricao=descricao,
                tags=tags,
                ator=SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Conjunto de dados", str(erro), parent=self.root)
            return
        self.dataset_status.configure(
            text="Metadados atualizados", fg=CORES["success"]
        )
        self._carregar_datasets()

    def _substituir_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        caminho = filedialog.askopenfilename(
            parent=self.root,
            title="Substituir arquivo do conjunto",
            filetypes=[
                ("Dados suportados", "*.xlsx *.xls *.csv *.json *.parquet *.txt"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return
        if not messagebox.askyesno(
            "Substituir arquivo",
            "O novo arquivo criará uma nova versão deste conjunto. Continuar?",
            parent=self.root,
        ):
            return
        self.dataset_status.configure(
            text="Validando nova versão...", fg=CORES["warning"]
        )
        ator = self._ator_congelado()

        def worker():
            try:
                substituir_arquivo_conjunto(conjunto_id, caminho, ator)
                erro = None
            except Exception as excecao:
                erro = str(excecao)
            try:
                self.root.after(0, self._substituicao_concluida, erro)
            except tk.TclError:
                pass

        threading.Thread(
            target=worker,
            daemon=True,
            name="substituicao-dataset",
        ).start()

    def _substituicao_concluida(self, erro=None):
        if not self._ativa:
            return
        if erro:
            self.dataset_status.configure(
                text="Falha na substituição", fg=CORES["danger"]
            )
            messagebox.showerror("Substituir conjunto", erro, parent=self.root)
            return
        self.dataset_status.configure(
            text="Nova versão importada", fg=CORES["success"]
        )
        self._carregar_datasets()

    def _visualizar_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        registro = obter_conjunto(conjunto_id, SESSAO.usuario)
        messagebox.showinfo(
            registro["nome"],
            f"Arquivo: {registro['nome_original']}\n"
            f"Categoria: {registro['categoria']}\n"
            f"Registros: {registro['total_registros']}\n"
            f"Colunas: {registro['total_colunas']}\n"
            f"Versão: {registro['versao']}\n"
            f"Status: {registro['status']}",
            parent=self.root,
        )

    def _usar_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        registro = obter_conjunto(conjunto_id, SESSAO.usuario)
        self.navegacao["nova"](
            {
                "fonte": "computador",
                "arquivos": [registro["caminho"]],
                "categoria": registro["categoria"] or "automatica",
            }
        )

    def _excluir_dataset(self):
        conjunto_id = self._dataset_selecionado()
        if conjunto_id is None:
            return
        if not messagebox.askyesno(
            "Excluir conjunto",
            "Mover o conjunto selecionado para a lixeira? O histórico será preservado.",
            parent=self.root,
        ):
            return
        excluir_conjunto(conjunto_id, SESSAO.usuario)
        self._carregar_datasets()

    def _carregar_recursos_analytics(self):
        resultado = listar_recursos(
            "analytics",
            self.secao,
            SESSAO.usuario,
            tamanho=200,
        )
        self.analytics_registros = resultado["registros"]
        for item in self.analytics_tabela.get_children():
            self.analytics_tabela.delete(item)
        for registro in self.analytics_registros:
            extras = registro.get("dados") or {}
            valores = []
            for chave, _rotulo, _tipo, *_configuracao in self.analytics_esquema:
                valor = extras.get(chave)
                if valor in (None, ""):
                    if chave in {"nome", "titulo"}:
                        valor = registro.get("identificacao", "")
                    elif chave == "descricao":
                        valor = registro.get("descricao", "")
                    elif chave == "responsavel":
                        valor = registro.get("responsavel", "")
                    elif chave == "status":
                        valor = registro.get("status", "")
                valores.append("" if valor is None else str(valor))
            self.analytics_tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(*valores, str(registro.get("atualizado_em") or "")[:19]),
            )
        if self.analytics_registros:
            self.analytics_vazio.place_forget()
        else:
            self.analytics_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.analytics_vazio.lift()
        self.analytics_total.configure(text=f"{resultado['total']} registro(s)")

    def _novo_recurso_analytics(self, titulo):
        janela = tk.Toplevel(self.root)
        janela.title(f"Novo · {titulo}")
        preparar_janela_secundaria(
            janela, self.root, 720, 520, minimo=(620, 470)
        )
        janela.configure(bg=CORES["bg"])
        variaveis = {}
        tk.Label(
            janela,
            text=f"Novo · {titulo}",
            font=FONTES["titulo_grande"],
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=26, pady=(22, 10))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=26)
        card = criar_card(viewport.conteudo)
        card.pack(fill="both", expand=True)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        for indice, campo_def in enumerate(self.analytics_esquema):
            chave, rotulo, tipo, *configuracao = campo_def
            grupo = tk.Frame(card, bg=CORES["card"])
            grupo.grid(
                row=indice // 2,
                column=indice % 2,
                sticky="ew",
                padx=(17, 8) if indice % 2 == 0 else (8, 17),
                pady=(12, 0),
            )
            tk.Label(
                grupo,
                text=rotulo.upper(),
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(anchor="w", pady=(0, 4))
            padrao = SESSAO.usuario.get("nome", "") if chave == "responsavel" else ""
            variavel = tk.StringVar(value=padrao)
            variaveis[chave] = variavel
            if tipo == "opcoes":
                opcoes = configuracao[0] if configuracao else ()
                campo = ttk.Combobox(
                    grupo, textvariable=variavel, values=opcoes,
                    state="readonly", style="Dark.TCombobox",
                )
                if opcoes:
                    variavel.set(opcoes[0])
            else:
                campo = tk.Entry(
                    grupo,
                    textvariable=variavel,
                    font=FONTES["texto"],
                    bg=CORES["input"],
                    fg=CORES["text"],
                    insertbackground=CORES["primary"],
                    relief="flat",
                    bd=0,
                )
            campo.pack(fill="x", ipady=7)
        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=26, pady=17)
        status = tk.Label(rodape, text="", fg=CORES["danger"], bg=CORES["bg"])
        status.pack(side="left")

        def salvar():
            extras = {chave: valor.get().strip() for chave, valor in variaveis.items()}
            primeira_chave, primeiro_rotulo, *_ = self.analytics_esquema[0]
            identificacao = extras.get(primeira_chave, "")
            if len(identificacao) < 2:
                status.configure(text=f"Preencha {primeiro_rotulo}.")
                return
            try:
                criar_recurso(
                    "analytics",
                    self.secao,
                    {
                        "identificacao": identificacao,
                        "descricao": extras.get("descricao") or extras.get("pergunta") or titulo,
                        "responsavel": extras.get("responsavel", ""),
                        "status": extras.get("status", "Ativo"),
                        "prioridade": "Média",
                        "dados": extras,
                    },
                    SESSAO.usuario,
                )
            except (PermissionError, ValueError) as erro:
                status.configure(text=str(erro))
                return
            janela.destroy()
            self._carregar_recursos_analytics()

        criar_botao(rodape, "SALVAR", salvar).pack(side="right")
        criar_botao(
            rodape,
            "CANCELAR",
            janela.destroy,
            tipo="secundario",
        ).pack(side="right", padx=(0, 8))
        janela.bind("<Escape>", lambda _evento: janela.destroy())

    def _arquivar_recurso_analytics(self):
        selecao = self.analytics_tabela.selection()
        if not selecao:
            return
        try:
            alterar_estado_recurso(
                "analytics",
                self.secao,
                int(selecao[0]),
                "Arquivado",
                SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Arquivar", str(erro), parent=self.root)
            return
        self._carregar_recursos_analytics()
