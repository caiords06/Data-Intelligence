"""Componente central_analytics_dashboard.py V9.8."""
from interface.central_analytics_shared import *

class CentralAnalyticsDashboardMixin:
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
                font=("Inter", 9, "bold"),
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
                font=("Inter", 8, "bold"),
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
            font=("Inter", 11, "bold"),
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
            tk.Label(linha, text=valor, font=("Inter", 8, "bold"), fg=CORES["success"], bg=CORES["card"]).pack(side="right")

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
                font=("Inter", 8, "bold"),
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
