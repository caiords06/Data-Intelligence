import queue
import threading
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

from automacao.driver import criar_driver
from configuracoes.settings import (
    LINK,
    TEMPO_ABERTURA_NAVEGADOR,
    TEMPO_CARREGAMENTO_PAGINA,
)
from core.orquestrador import OrquestradorAnalise, normalizar_configuracao
from sistema.idbrowser import identificar_tipo_navegador, localizar_navegador_padrao
from sistema.iduser import identificar_usuario
from sistema.opsystemcheck import verificar_sistema_operacional


class AplicacaoAutomacao:

        def __init__(self, root, arquivos_iniciais=None, configuracao_analise=None):
                self.root = root
                self.configuracao_analise = normalizar_configuracao(configuracao_analise)
                self.modulos_analise = self.configuracao_analise["modulos"]
                self.categoria_solicitada = self.configuracao_analise["categoria"]
                self.periodo_solicitado = self.configuracao_analise["periodo"]
                self.ia_habilitada = self.configuracao_analise["ia"]

                self.fila_log = queue.Queue()
                self.fila_ui = queue.Queue()
                self.arquivo_selecionado = None
                self.arquivos_selecionados = []
                self.resultados_arquivos = []
                self.df_consolidado = None
                self.classificacao_atual = None
                self.indicadores_atuais = None
                self.resultado_analise = None
                self.analise_estrutural = None
                self.analise_qualidade = None
                self.analise_temporal = None
                self.driver_selenium = None
                self.processando = False

                self.root.title("Automação de Análise de Dados")
                self.root.geometry("1100x700")
                self.root.minsize(950, 600)

                self.criar_interface()
                self.processar_logs()

                arquivos_configurados = self.configuracao_analise.get("arquivos", [])
                caminhos_iniciais = arquivos_configurados or list(arquivos_iniciais or [])
                if caminhos_iniciais:
                        self.adicionar_log(
                                f"[OK] Configuração recebida com "
                                f"{len(caminhos_iniciais)} arquivo(s)."
                        )
                        self.root.after(
                                300,
                                lambda: self.carregar_arquivos_configurados(caminhos_iniciais),
                        )

        def criar_interface(self):


                # ==========================================================
                # TEMA / CORES
                # ==========================================================

                self.cores = {
                        "bg": "#0F172A",
                        "sidebar": "#111827",
                        "card": "#1E293B",
                        "card_hover": "#263449",
                        "border": "#334155",
                        "text": "#F8FAFC",
                        "text_sec": "#94A3B8",
                        "primary": "#38BDF8",
                        "success": "#22C55E",
                        "warning": "#F59E0B",
                        "danger": "#EF4444",
                        "terminal": "#0B1120"
                }

                self.root.configure(
                        bg=self.cores["bg"]
                )

                self.root.title(
                        "Data Analytics Automation"
                )

                self.root.geometry(
                        "1200x760"
                )

                self.root.minsize(
                        1050,
                        680
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
                        font=("Segoe UI", 10, "bold"),
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
                # SIDEBAR
                # ==========================================================

                sidebar = tk.Frame(
                        container,
                        bg=self.cores["sidebar"],
                        width=230
                )

                sidebar.pack(
                        side="left",
                        fill="y"
                )

                sidebar.pack_propagate(
                        False
                )

                # ----------------------------------------------------------
                # LOGO / NOME
                # ----------------------------------------------------------

                logo_area = tk.Frame(
                        sidebar,
                        bg=self.cores["sidebar"]
                )

                logo_area.pack(
                        fill="x",
                        padx=20,
                        pady=(25, 30)
                )

                tk.Label(
                        logo_area,
                        text="◈",
                        font=("Segoe UI", 26, "bold"),
                        fg=self.cores["primary"],
                        bg=self.cores["sidebar"]
                ).pack(
                        side="left"
                )

                logo_texto = tk.Frame(
                        logo_area,
                        bg=self.cores["sidebar"]
                )

                logo_texto.pack(
                        side="left",
                        padx=(10, 0)
                )

                tk.Label(
                        logo_texto,
                        text="DATA",
                        font=("Segoe UI", 12, "bold"),
                        fg=self.cores["text"],
                        bg=self.cores["sidebar"]
                ).pack(
                        anchor="w"
                )

                tk.Label(
                        logo_texto,
                        text="AUTOMATION",
                        font=("Segoe UI", 8),
                        fg=self.cores["text_sec"],
                        bg=self.cores["sidebar"]
                ).pack(
                        anchor="w"
                )

                # ----------------------------------------------------------
                # MENU
                # ----------------------------------------------------------

                self.criar_menu_item(
                        sidebar,
                        "⌂",
                        "Dashboard"
                )

                self.criar_menu_item(
                        sidebar,
                        "▣",
                        "Arquivos"
                )

                self.criar_menu_item(
                        sidebar,
                        "◉",
                        "Análise"
                )

                self.criar_menu_item(
                        sidebar,
                        "⚙",
                        "Configurações"
                )

                # ----------------------------------------------------------
                # ESPAÇAMENTO
                # ----------------------------------------------------------

                tk.Frame(
                        sidebar,
                        bg=self.cores["sidebar"]
                ).pack(
                        fill="both",
                        expand=True
                )

                # ----------------------------------------------------------
                # BOTÃO EXECUTAR
                # ----------------------------------------------------------

                botao_executar = tk.Button(
                        sidebar,
                        text="▶  VALIDAR AUTOMAÇÃO WEB",
                        command=self.iniciar_automacao,
                        font=("Segoe UI", 9, "bold"),
                        bg=self.cores["primary"],
                        fg="#FFFFFF",
                        activebackground="#0EA5E9",
                        activeforeground="#FFFFFF",
                        relief="flat",
                        bd=0,
                        cursor="hand2",
                        padx=10,
                        pady=12
                )

                botao_executar.pack(
                        fill="x",
                        padx=15,
                        pady=(10, 8)
                )

                self.botao_iniciar = botao_executar

                # ----------------------------------------------------------
                # STATUS SIDEBAR
                # ----------------------------------------------------------

                status_sidebar = tk.Frame(
                        sidebar,
                        bg=self.cores["sidebar"]
                )

                status_sidebar.pack(
                        fill="x",
                        padx=20,
                        pady=(5, 20)
                )

                tk.Label(
                        status_sidebar,
                        text="●",
                        font=("Segoe UI", 9),
                        fg=self.cores["success"],
                        bg=self.cores["sidebar"]
                ).pack(
                        side="left"
                )

                tk.Label(
                        status_sidebar,
                        text=" Sistema pronto",
                        font=("Segoe UI", 8),
                        fg=self.cores["text_sec"],
                        bg=self.cores["sidebar"]
                ).pack(
                        side="left"
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
                        text="Dashboard",
                        font=("Segoe UI", 23, "bold"),
                        fg=self.cores["text"],
                        bg=self.cores["bg"]
                ).pack(
                        anchor="w"
                )

                tk.Label(
                        titulo_area,
                        text="Visão geral da automação e análise de dados",
                        font=("Segoe UI", 10),
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

                tk.Label(
                        status_area,
                        text="●",
                        font=("Segoe UI", 10),
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
                        font=("Segoe UI", 9, "bold"),
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
                        font=("Segoe UI", 9),
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
                        font=("Segoe UI", 9),
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
                        font=("Segoe UI", 9, "bold"),
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
                        font=("Segoe UI", 12, "bold"),
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
                        font=("Segoe UI", 11, "bold"),
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
                        font=("Segoe UI", 12, "bold"),
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
                        font=("Segoe UI", 11, "bold"),
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

        def criar_menu_item(self, parent, icone, texto):

                frame = tk.Frame(
                        parent,
                        bg=self.cores["sidebar"],
                        cursor="hand2"
                )

                frame.pack(
                        fill="x",
                        padx=10,
                        pady=2
                )

                tk.Label(
                        frame,
                        text=icone,
                        font=("Segoe UI", 13),
                        fg=self.cores["text_sec"],
                        bg=self.cores["sidebar"]
                ).pack(
                        side="left",
                        padx=(12, 10),
                        pady=10
                )

                tk.Label(
                        frame,
                        text=texto,
                        font=("Segoe UI", 10),
                        fg=self.cores["text_sec"],
                        bg=self.cores["sidebar"]
                ).pack(
                        side="left",
                        pady=10
                )

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
                        font=("Segoe UI", 14),
                        fg=self.cores["primary"],
                        bg=self.cores["card"]
                ).pack(
                        side="left"
                )

                titulo_label = tk.Label(
                        topo,
                        text=titulo,
                        font=("Segoe UI", 8, "bold"),
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
                        font=("Segoe UI", 17, "bold"),
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
                        font=("Segoe UI", 10, "bold"),
                        fg=self.cores["text"],
                        bg=self.cores["card"]
                )

                titulo_label.pack(
                        anchor="w",
                        padx=15,
                        pady=(12, 8)
                )

                return painel

        def adicionar_log(self, mensagem):
                horario = datetime.now().strftime("%H:%M:%S")
                self.fila_log.put(f"[{horario}] {mensagem}\n")

        def processar_logs(self):
                try:
                        while True:
                                mensagem = self.fila_log.get_nowait()
                                self.log.configure(state="normal")
                                self.log.insert("end", mensagem)
                                self.log.see("end")
                                self.log.configure(state="disabled")
                except queue.Empty:
                        pass

                try:
                        while True:
                                callback, args = self.fila_ui.get_nowait()
                                callback(*args)
                except queue.Empty:
                        pass
                except tk.TclError:
                        return

                self.root.after(50, self.processar_logs)

        def executar_na_ui(self, callback, *args):
                self.fila_ui.put((callback, args))

        def limpar_log(self):
                self.log.configure(state="normal")
                self.log.delete("1.0", "end")
                self.log.configure(state="disabled")

        # ==========================================================
        # AUTOMAÇÃO WEB / SELENIUM
        # ==========================================================

        def iniciar_automacao(self):
                self.botao_iniciar.configure(state="disabled")
                self.progresso["value"] = 0
                self.status.set("Executando verificações da automação web...")
                self.adicionar_log("=" * 40)
                self.adicionar_log("INÍCIO DA AUTOMAÇÃO WEB")
                self.adicionar_log("=" * 40)

                thread = threading.Thread(
                        target=self.executar_processo,
                        daemon=True,
                )
                thread.start()

        def executar_processo(self):
                try:
                        try:
                                from selenium.common.exceptions import (
                                        TimeoutException,
                                        WebDriverException,
                                )
                                from selenium.webdriver.support.ui import WebDriverWait
                        except ImportError as erro:
                                raise RuntimeError(
                                        "Selenium não está instalado. Execute: "
                                        "pip install -r requirements.txt"
                                ) from erro

                        self.adicionar_log("CONFIGURAÇÃO DA AUTOMAÇÃO")
                        self.adicionar_log("=" * 40)
                        self.adicionar_log(
                                f"Categoria solicitada: {self.categoria_solicitada}"
                        )
                        self.adicionar_log(
                                f"Período solicitado: {self.periodo_solicitado}"
                        )
                        self.adicionar_log(
                                f"IA habilitada: {'Sim' if self.ia_habilitada else 'Não'}"
                        )
                        self.adicionar_log("Módulos:")
                        for modulo, ativo in self.modulos_analise.items():
                                self.adicionar_log(
                                        f"- {modulo}: {'Ativo' if ativo else 'Desativado'}"
                                )

                        self.atualizar_status("Verificando sistema operacional...")
                        self.atualizar_progresso(10)
                        sistema = verificar_sistema_operacional()
                        self.adicionar_log(f"[OK] Sistema Operacional: {sistema}")

                        self.atualizar_status("Identificando usuário...")
                        self.atualizar_progresso(20)
                        usuario, pasta_usuario, local_appdata = identificar_usuario()
                        self.adicionar_log(f"[OK] Usuário identificado: {usuario}")
                        self.adicionar_log(f"[OK] Pasta do usuário: {pasta_usuario}")
                        self.adicionar_log(f"[OK] Local do AppData: {local_appdata}")

                        self.atualizar_status("Localizando navegador padrão...")
                        self.atualizar_progresso(30)
                        prog_id, caminho_executavel = localizar_navegador_padrao()
                        self.adicionar_log(f"[OK] Identificador do navegador: {prog_id}")
                        self.adicionar_log(f"[OK] Executável: {caminho_executavel}")

                        self.atualizar_status("Verificando executável do navegador...")
                        self.atualizar_progresso(40)
                        if not caminho_executavel.exists():
                                raise FileNotFoundError(
                                        "Executável do navegador não encontrado: "
                                        f"{caminho_executavel}"
                                )
                        self.adicionar_log("[OK] Executável do navegador encontrado.")

                        self.atualizar_status("Identificando tipo do navegador...")
                        self.atualizar_progresso(50)
                        navegador = identificar_tipo_navegador(
                                prog_id,
                                caminho_executavel,
                        )
                        self.adicionar_log(
                                f"[OK] Navegador identificado: {navegador.upper()}"
                        )

                        self.atualizar_status(f"Abrindo {navegador.upper()}...")
                        self.atualizar_progresso(60)
                        self.adicionar_log("[AGUARDE] Abrindo navegador com Selenium...")
                        driver = criar_driver(navegador, caminho_executavel)
                        WebDriverWait(driver, TEMPO_ABERTURA_NAVEGADOR).until(
                                lambda navegador_aberto: len(
                                        navegador_aberto.window_handles
                                ) > 0
                        )
                        driver.maximize_window()
                        self.driver_selenium = driver
                        self.adicionar_log("[OK] Navegador aberto com sucesso.")

                        self.atualizar_status("Acessando página configurada...")
                        self.atualizar_progresso(75)
                        self.adicionar_log(f"[AGUARDE] Acessando: {LINK}")
                        driver.get(LINK)

                        self.atualizar_status("Aguardando carregamento da página...")
                        self.atualizar_progresso(85)
                        WebDriverWait(driver, TEMPO_CARREGAMENTO_PAGINA).until(
                                lambda navegador_aberto: navegador_aberto.execute_script(
                                        "return document.readyState"
                                ) == "complete"
                        )

                        self.atualizar_progresso(100)
                        self.atualizar_status("Automação web validada com sucesso.")
                        self.adicionar_log("=" * 40)
                        self.adicionar_log("[OK] INFRAESTRUTURA WEB VALIDADA")
                        self.adicionar_log("[OK] Navegador aberto e página carregada.")
                        self.adicionar_log("=" * 40)

                except Exception as erro:
                        # Os tipos específicos do Selenium podem não existir quando
                        # a dependência não está instalada; por isso o tratamento é
                        # centralizado e o traceback completo continua disponível.
                        self.adicionar_log(f"[ERRO NA AUTOMAÇÃO WEB] {erro}")
                        self.adicionar_log(traceback.format_exc())
                        self.atualizar_status("Falha na automação web. Verifique o log.")
                finally:
                        self.habilitar_botao()

        # ==========================================================
        # ATUALIZAÇÃO DO DASHBOARD
        # ==========================================================

        @staticmethod
        def _moeda_br(valor):
                return (
                        f"R$ {float(valor):,.2f}"
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                )

        @staticmethod
        def _numero_br(valor):
                return f"{int(float(valor)):,}".replace(",", ".")

        def configurar_dashboard_categoria(self, categoria):
                configuracoes = {
                        "vendas": (
                                ("FATURAMENTO", "VENDAS", "ITENS VENDIDOS", "TICKET MÉDIO"),
                                ("Produto líder", "Loja líder"),
                        ),
                        "financeiro": (
                                ("RECEITA", "DESPESA", "SALDO", "MÉDIA"),
                                ("Maior receita", "Maior despesa"),
                        ),
                        "estoque": (
                                ("ESTOQUE", "PRODUTOS", "BAIXO ESTOQUE", "GIRO"),
                                ("Produto crítico", "Maior estoque"),
                        ),
                        "cadastro": (
                                ("REGISTROS", "DUPLICADOS", "AUSENTES", "ATIVOS"),
                                ("Maior categoria", "Qualidade"),
                        ),
                        "recursos_humanos": (
                                ("COLABORADORES", "SETORES", "ADMISSÕES", "DESLIGAMENTOS"),
                                ("Maior setor", "Situação"),
                        ),
                }
                titulos_cards, titulos_destaques = configuracoes.get(
                        categoria,
                        (("INDICADOR 1", "INDICADOR 2", "INDICADOR 3", "INDICADOR 4"),
                         ("Destaque 1", "Destaque 2")),
                )
                for label, titulo in zip(
                        (
                                self.card_faturamento_titulo,
                                self.card_vendas_titulo,
                                self.card_quantidade_titulo,
                                self.card_ticket_titulo,
                        ),
                        titulos_cards,
                ):
                        label.configure(text=titulo)

                self.label_produto_titulo.configure(text=titulos_destaques[0])
                self.label_loja_titulo.configure(text=titulos_destaques[1])

        def atualizar_cards_indicadores(self):
                indicadores = self.indicadores_atuais or {}
                if not indicadores:
                        return

                configuracoes = (
                        (self.card_faturamento, "faturamento_total", self._moeda_br),
                        (self.card_vendas, "total_vendas", self._numero_br),
                        (self.card_quantidade, "quantidade_total", self._numero_br),
                        (self.card_ticket, "ticket_medio", self._moeda_br),
                )
                for label, chave, formatador in configuracoes:
                        if chave in indicadores:
                                label.configure(
                                        text=formatador(indicadores[chave]),
                                        fg=self.cores["text"],
                                )
                        else:
                                label.configure(text="—", fg=self.cores["text_sec"])

        def atualizar_cards_desativados(self):
                for label in (
                        self.card_faturamento,
                        self.card_vendas,
                        self.card_quantidade,
                        self.card_ticket,
                ):
                        label.configure(text="—", fg=self.cores["text_sec"])

                self.label_produto.configure(
                        text="Indicadores desativados",
                        fg=self.cores["warning"],
                )
                self.label_loja.configure(
                        text="Indicadores desativados",
                        fg=self.cores["warning"],
                )

        def atualizar_cards_indisponiveis(self):
                for label in (
                        self.card_faturamento,
                        self.card_vendas,
                        self.card_quantidade,
                        self.card_ticket,
                ):
                        label.configure(text="—", fg=self.cores["text_sec"])

                self.label_produto.configure(
                        text="Sem indicador específico",
                        fg=self.cores["text_sec"],
                )
                self.label_loja.configure(
                        text="Sem indicador específico",
                        fg=self.cores["text_sec"],
                )

        def atualizar_destaques_analise(self):
                indicadores = self.indicadores_atuais or {}
                produto = indicadores.get("produto_maior_faturamento")
                loja = indicadores.get("loja_maior_faturamento")

                if produto:
                        self.label_produto.configure(
                                text=(
                                        f"{produto}\n"
                                        f"{self._moeda_br(indicadores.get('valor_produto_lider', 0))}"
                                ),
                                fg=self.cores["text"],
                        )
                else:
                        self.label_produto.configure(
                                text="Não disponível",
                                fg=self.cores["text_sec"],
                        )

                if loja:
                        self.label_loja.configure(
                                text=(
                                        f"{loja}\n"
                                        f"{self._moeda_br(indicadores.get('valor_loja_lider', 0))}"
                                ),
                                fg=self.cores["text"],
                        )
                else:
                        self.label_loja.configure(
                                text="Não disponível",
                                fg=self.cores["text_sec"],
                        )

        def atualizar_status(self, mensagem):
                self.executar_na_ui(self.status.set, mensagem)

        def _definir_progresso_ui(self, valor):
                self.progresso.configure(value=valor)

        def atualizar_progresso(self, valor):
                self.executar_na_ui(self._definir_progresso_ui, valor)

        def atualizar_status_e_progresso(self, valor, mensagem):
                self.atualizar_progresso(valor)
                self.atualizar_status(mensagem)

        def _habilitar_botao_ui(self):
                self.botao_iniciar.configure(state="normal")

        def habilitar_botao(self):
                self.executar_na_ui(self._habilitar_botao_ui)

        # ==========================================================
        # PIPELINE DE ANÁLISE
        # ==========================================================

        def carregar_arquivos_configurados(self, caminhos):
                if not caminhos:
                        self.adicionar_log(
                                "[INFO] Nenhum arquivo recebido da tela de preparação."
                        )
                        return

                self.adicionar_log("=" * 40)
                self.adicionar_log("INICIANDO PROCESSAMENTO CONFIGURADO")
                self.adicionar_log("=" * 40)
                self.adicionar_log(f"[OK] Arquivos recebidos: {len(caminhos)}")
                self._iniciar_processamento(caminhos, substituir=True)

        def selecionar_arquivos(self, caminhos=None):
                recebido_externamente = caminhos is not None

                if isinstance(caminhos, dict):
                        caminhos = caminhos.get("arquivos", [])

                if caminhos is None:
                        caminhos = filedialog.askopenfilenames(
                                title="Selecionar planilhas",
                                filetypes=[
                                        ("Planilhas", "*.xlsx *.xls *.csv"),
                                        ("Excel", "*.xlsx *.xls"),
                                        ("CSV", "*.csv"),
                                        ("Todos os arquivos", "*.*"),
                                ],
                        )

                caminhos = list(caminhos or [])
                if not caminhos:
                        return

                if recebido_externamente:
                        finais = caminhos
                else:
                        finais = list(
                                dict.fromkeys(
                                        [*self.arquivos_selecionados, *caminhos]
                                )
                        )

                self._iniciar_processamento(finais, substituir=True)

        def _iniciar_processamento(self, caminhos, substituir=True):
                if self.processando:
                        self.adicionar_log(
                                "[INFO] Já existe uma análise em processamento. Aguarde a conclusão."
                        )
                        return

                caminhos = list(dict.fromkeys(str(caminho) for caminho in caminhos if caminho))
                if not caminhos:
                        return

                if substituir:
                        self.arquivos_selecionados = caminhos
                else:
                        self.arquivos_selecionados = list(
                                dict.fromkeys([*self.arquivos_selecionados, *caminhos])
                        )

                self.configuracao_analise["arquivos"] = list(
                        self.arquivos_selecionados
                )
                self._atualizar_lista_arquivos()
                self.processando = True
                self.progresso.configure(value=0)
                self.status.set("Preparando análise...")

                thread = threading.Thread(
                        target=self._processar_analise_thread,
                        args=(list(self.arquivos_selecionados),),
                        daemon=True,
                )
                thread.start()

        def _processar_analise_thread(self, caminhos):
                try:
                        orquestrador = OrquestradorAnalise(
                                logger=self.adicionar_log,
                                progresso=self.atualizar_status_e_progresso,
                        )
                        resultado = orquestrador.processar(
                                caminhos,
                                self.configuracao_analise,
                        )
                        self.executar_na_ui(
                                self._processamento_concluido,
                                resultado,
                        )
                except Exception as erro:
                        mensagem = str(erro)
                        traceback_completo = traceback.format_exc()
                        self.executar_na_ui(
                                self._processamento_falhou,
                                mensagem,
                                traceback_completo,
                        )

        def _processamento_concluido(self, resultado):
                self.resultado_analise = resultado
                self.resultados_arquivos = resultado.get("resultados_arquivos", [])
                self.df_consolidado = resultado.get("dataframe")
                self.classificacao_atual = resultado.get("classificacao")
                self.indicadores_atuais = resultado.get("indicadores")
                self.analise_estrutural = resultado.get("estrutural")
                self.analise_qualidade = resultado.get("qualidade")
                self.analise_temporal = resultado.get("temporal")

                self.configurar_dashboard_categoria(resultado.get("categoria"))

                if not self.modulos_analise.get("indicadores", True):
                        self.atualizar_cards_desativados()
                elif self.indicadores_atuais:
                        self.atualizar_cards_indicadores()
                        self.atualizar_destaques_analise()
                else:
                        self.atualizar_cards_indisponiveis()

                quantidade = len(self.arquivos_selecionados)
                self.label_arquivo.configure(
                        text=f"{quantidade} arquivo(s) selecionado(s)"
                )
                self.status.set("Análise concluída com sucesso.")
                self.progresso.configure(value=100)
                self.processando = False

        def _processamento_falhou(self, mensagem, traceback_completo):
                self.processando = False
                self.adicionar_log("[ERRO AO PROCESSAR ARQUIVOS]")
                self.adicionar_log(mensagem)
                self.adicionar_log(traceback_completo)
                self.status.set("Erro ao processar arquivos.")

        def _atualizar_lista_arquivos(self):
                self.lista_arquivos.delete(0, tk.END)
                for caminho in self.arquivos_selecionados:
                        self.lista_arquivos.insert(tk.END, Path(caminho).name)


# ==============================================================
# EXECUÇÃO
# ==============================================================

if __name__ == "__main__":

        janela = tk.Tk()

        app = AplicacaoAutomacao(janela)

        janela.mainloop()


