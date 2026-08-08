import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter .scrolledtext import ScrolledText
from datetime import datetime
import threading
import traceback
from Assertions.opsystemcheck import verificar_sistema_operacional
from Assertions.iduser import identificar_usuario
import queue
from dados.leitor import carregar_planilha

from Assertions.idbrowser import(
        localizar_navegador_padrao,
        identificar_tipo_navegador
)

from driver import criar_driver

from Settings import (
        LINK,
        TEMPO_ABERTURA_NAVEGADOR,
        TEMPO_CARREGAMENTO_PAGINA
)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
        TimeoutException,
        WebDriverException
)

class AplicacaoAutomacao:

        def __init__(self, root):
                self.root = root

                self.fila_log = queue.Queue()

                self.root.title(
                        'Automação de Análise de Dados'
                )

                self.root.geometry('1100x700')
                self.root.minsize(950, 600)

                self.criar_interface()

                self.processar_logs()

                # ============================================
                # INTERFACE
                # ============================================

        def criar_interface(self):

                # -----------------------------------------
                # CABEÇALHO
                # -----------------------------------------

                cabecalho = ttk.Frame(
                        self.root,
                        padding=(20, 15)
                )

                cabecalho.pack(
                        fill='x'
                )

                titulo = ttk.Label(
                        cabecalho,
                        text='AUTOMAÇÃO DE ANÁLISE DE DADOS',
                        font=('Segoe UI', 20, 'bold')
                )

                titulo.pack(
                        anchor='w'
                )

                subtitulo = ttk.Label(
                        cabecalho,
                        text='Sistema de tratamento, análise e envio automático de relatórios'
                )

                subtitulo.pack(
                        anchor='w',
                        pady=(4,0)
                )

                # ------------------------------------------------
                # ÁREA PRINCIPAL
                # ------------------------------------------------

                area_principal = ttk.Frame(
                        self.root,
                        padding=(20, 5)
                )

                area_principal.pack(
                        fill='both',
                        expand=True
                )

                # ================================================
                # CONFIGURAÇÕES
                # ================================================

                configuracoes = ttk.LabelFrame(
                        area_principal,
                        text="Configuração da automação",
                        padding=15
                )

                configuracoes.pack(
                        side='left',
                        fill="y",
                        padx=(0, 10)
                )

                # --------------------------------------------------
                # ORIGEM DOS DADOS
                # --------------------------------------------------

                ttk.Label(
                        configuracoes,
                        text='Origem da planilha:',
                        font=('Segoe UI', 10, "bold")
                ).pack(
                        anchor='w'
                )

                self.origem = tk.StringVar(
                        value="Arquivo Local"
                )

                self.combo_origem = ttk.Combobox(
                        configuracoes,
                        textvariable=self.origem,
                        state='readonly',
                        values=[
                                "Arquivo Local",
                                "Google Drive",
                                'Link / URL'
                        ],
                        width=30
                )
                self.combo_origem.pack(
                        fill='x',
                        pady=(5, 20)
                )

                # ------------------------------------------
                # TIPO DE DADOS
                # ------------------------------------------

                ttk.Label(
                        configuracoes,
                        text='Tipo de dados:',
                        font=('Segoe UI', 10, 'bold')
                ).pack(
                        anchor='w'
                )
                self.tipo_dados = tk.StringVar(
                        value='Detecção automática'
                )
                self.combo_tipo = ttk.Combobox(
                        configuracoes,
                        textvariable=self.tipo_dados,
                        state='readonly',
                        values=[
                                'Detecção automática',
                                'Vendas',
                                'Financeiro',
                                'Cadastro',
                                'Estoque',
                                'Clientes',
                                'Produtos',
                                'Personalizado'
                        ],
                        width=30
                )

                self.combo_tipo.pack(
                        fill='x',
                        pady=(5,20)
                )

                # ---------------------------------------------------
                # SERVIÇO DE E-MAIL
                # ---------------------------------------------------

                ttk.Label(
                        configuracoes,
                        text='Serviço de e-mail:',
                        font=('Segoe UI', 10, 'bold')
                ).pack(
                        anchor='w'
                )
                self.email_servico = tk.StringVar(
                        value='Gmail'
                )
                self.combo_email = ttk.Combobox(
                        configuracoes,
                        textvariable=self.email_servico,
                        state='readonly',
                        values=[
                                'Gmail',
                                'Outlook'
                        ],
                        width=30
                )
                self.combo_email.pack(
                        fill='x',
                        pady=(5, 20)
                )

                # ------------------------------------------------------
                # BOTÃO INICIAR
                # ------------------------------------------------------

                self.botao_iniciar = ttk.Button(
                            configuracoes,
                            text="▶  INICIAR AUTOMAÇÃO",
                            command= self.iniciar_automacao
                        )

                self.botao_iniciar.pack(
                            fill="x",
                            pady=(15, 5)
                        )

                # ------------------------------------------------------
                # BOTÃO LIMPAR LOG
                # ------------------------------------------------------

                ttk.Button(
                    configuracoes,
                    text="Limpar log",
                    command=self.limpar_log
                        ).pack(
                    fill="x",
                    pady=5
                    )

            # ======================================================
            # PAINEL DIREITO
            # ======================================================

                painel_direito = ttk.Frame(
                area_principal
                )

                painel_direito.pack(
                side="right",
                fill="both",
                expand=True
                )

            # ------------------------------------------------------
            # STATUS
            # ------------------------------------------------------

                status_frame = ttk.LabelFrame(
                painel_direito,
                text="Status da execução",
                padding=15
                )

                status_frame.pack(
                fill="x",
                pady=(0, 10)
                )

                self.status = tk.StringVar(
                value="Aguardando execução..."
            )

                ttk.Label(
                status_frame,
                textvariable=self.status,
                font=("Segoe UI", 11, "bold")
                ).pack(
                anchor="w"
                )

            # ------------------------------------------------------
            # PROGRESSO
            # ------------------------------------------------------

                self.progresso = ttk.Progressbar(
                status_frame,
                mode="determinate",
                maximum=100
            )

                self.progresso.pack(
                fill="x",
                pady=(10, 0)
            )

            # ------------------------------------------------------
            # LOG
            # ------------------------------------------------------

                log_frame = ttk.LabelFrame(
                painel_direito,
                text="Informações do projeto",
                padding=10
            )

                log_frame.pack(
                fill="both",
                expand=True
            )

                self.log = ScrolledText(
                log_frame,
                height=25,
                font=("Consolas", 10),
                state="disabled"
                )

                self.log.pack(
                fill="both",
                expand=True
                )

            # ------------------------------------------------------
            # RODAPÉ
            # ------------------------------------------------------

                self.adicionar_log(
                "Sistema inicializado."
                )

                self.adicionar_log(
                "Aguardando configuração da automação."
                )

            # ==========================================================
            # LOG
            # ==========================================================

        def adicionar_log(
                self,
                mensagem
                ):

                    horario = datetime.now().strftime(
                "%H:%M:%S"
                )
                    texto = (
                f"[{horario}] {mensagem}\n"
                )
                    self.fila_log.put(texto)

                    def escrever():
                            self.log.configure(
                        state="normal"
                )
                            self.log.insert(
                                    "end",
                                    texto   
                                    )
                            self.log.see(
                                    "end"
                                    )
                            self.log.configure(
                                state="disabled"
                                )
                            self.root.after(
                                0,
                                escrever
                        )

                # ====================================================
                # Processar os logs realizados e escrever na interface
                # ====================================================

        def processar_logs(self):

                try:
                        while True:
                                mensagem = self.fila_log.get_nowait()

                                self.log.configure(
                                        state='normal'
                                )

                                self.log.insert(
                                        'end',
                                        mensagem +'\n'
                                )

                                self.log.see(
                                        'end'
                                )

                                self.log.configure(
                                        state='disabled'
                                )

                except queue.Empty:
                        pass

                self.root.after(
                        100,
                        self.processar_logs
                )


            # ==========================================================
            # LIMPAR LOG
            # ==========================================================

        def limpar_log(self):

                    self.log.configure(
                    state="normal"
            )

                    self.log.delete(
                    "1.0",
                    "end"
            )

                    self.log.configure(
                    state="disabled"
            )

            # ==========================================================
            # INICIAR AUTOMAÇÃO
            # ==========================================================

        def iniciar_automacao(self):

                    self.botao_iniciar.configure(
                    state="disabled"
                )

                    self.progresso["value"] = 0

                    self.status.set(
                    "Executando verificações do sistema..."
                )

                    self.adicionar_log(
                    "====================================="
                )

                    self.adicionar_log(
                    "INÍCIO DA AUTOMAÇÃO"
                )

                    self.adicionar_log(
                    "====================================="
                )

                    thread = threading.Thread(
                            target=self.executar_processo,
                            daemon=True
                    )

                    thread.start()

        def executar_processo(self):

                driver_selenium = None

                try:

                        # ======================================================
                        # 1. VERIFICAR SISTEMA OPERACIONAL
                        # ======================================================
                        self.atualizar_status(
                                'Verificando sistema operacional...'
                        )

                        self.atualizar_progresso(10)

                        sistema = verificar_sistema_operacional()

                        self.adicionar_log(
                                f'[OK] Sistema Operacional: {sistema}'
                        )

                        # ======================================================
                        # 2. IDENTIFICAR USUARIO
                        # ======================================================

                        self.atualizar_status(
                                'Identificando usuário...'
                        )
                        self.atualizar_progresso(20)

                        (
                                usuario,
                                pasta_usuario,
                                local_appdata
                        ) = identificar_usuario()

                        self.adicionar_log(
                                f'[OK] Usuário identificado: {usuario}'
                        )

                        self.adicionar_log(
                                f'[OK] Pasta do usuário: {pasta_usuario}'
                        )

                        self.adicionar_log(
                                f'[OK] Local do AppData: {local_appdata}'
                        )

                        # ======================================================
                        # 3. LOCALIZAR NAVEGADOR
                        # ======================================================


                        self.atualizar_status(
                        "Localizando navegador padrão..."
                        )

                        self.atualizar_progresso(30)

                        (
                        prog_id,
                        caminho_executavel
                        ) = localizar_navegador_padrao()

                        self.adicionar_log(
                        f"[OK] Identificador do navegador: {prog_id}"
                        )

                        self.adicionar_log(
                        f"[OK] Executável: {caminho_executavel}"
                        )

                        # ======================================================
                        # 4. VERIFICAR EXECUTÁVEL
                        # ======================================================

                        self.atualizar_status(
                        "Verificando executável do navegador..."
                        )

                        self.atualizar_progresso(40)

                        if not caminho_executavel.exists():

                                raise FileNotFoundError(
                                "Executável do navegador não encontrado: "
                                f"{caminho_executavel}"
                        )

                        self.adicionar_log(
                        "[OK] Executável do navegador encontrado."
                        )


                        # ======================================================
                        # 5. IDENTIFICAR TIPO
                        # ======================================================

                        self.atualizar_status(
                        "Identificando tipo do navegador..."
                        )

                        self.atualizar_progresso(50)

                        navegador = identificar_tipo_navegador(
                        prog_id,
                        caminho_executavel
                        )

                        self.adicionar_log(
                        f"[OK] Navegador identificado: "
                        f"{navegador.upper()}"
                        )


                        # ======================================================
                        # 6. ABRIR NAVEGADOR
                        # ======================================================

                        self.atualizar_status(
                        f"Abrindo {navegador.upper()}..."
                        )

                        self.atualizar_progresso(60)

                        self.adicionar_log(
                        "[AGUARDE] Abrindo navegador com Selenium..."
                        )

                        driver_selenium = criar_driver(
                        navegador,
                        caminho_executavel
                        )

                        WebDriverWait(
                        driver_selenium,
                        TEMPO_ABERTURA_NAVEGADOR
                        ).until(
                                lambda navegador_aberto:
                                len(
                                navegador_aberto.window_handles
                                ) > 0
                        )

                        driver_selenium.maximize_window()

                        self.adicionar_log(
                        "[OK] Navegador aberto com sucesso."
                        )


                        # ======================================================
                        # 7. ACESSAR LINK
                        # ======================================================

                        self.atualizar_status(
                        "Acessando página configurada..."
                        )

                        self.atualizar_progresso(75)

                        self.adicionar_log(
                                f"[AGUARDE] Acessando: {LINK}"
                        )

                        driver_selenium.get(
                        LINK
                        )


                        # ======================================================
                        # 8. AGUARDAR CARREGAMENTO
                        # ======================================================

                        self.atualizar_status(
                        "Aguardando carregamento da página..."
                        )

                        self.atualizar_progresso(85)

                        WebDriverWait(
                        driver_selenium,
                        TEMPO_CARREGAMENTO_PAGINA
                        ).until(
                                lambda navegador_aberto:
                                navegador_aberto.execute_script(
                                "return document.readyState"
                                ) == "complete"
                        )

                        self.adicionar_log(
                        "[OK] Página carregada com sucesso."
                        )


                        # ======================================================
                        # 9. FINALIZAÇÃO DA ETAPA 2
                        # ======================================================

                        self.atualizar_progresso(100)

                        self.atualizar_status(
                        "Verificação concluída com sucesso."
                        )

                        self.adicionar_log(
                        "========================================"
                        )

                        self.adicionar_log(
                        "[OK] INFRAESTRUTURA VALIDADA"
                        )

                        self.adicionar_log(
                        "O navegador foi aberto e a página foi carregada."
                        )

                        self.adicionar_log(
                        "Pronto para iniciar o processamento da planilha."
                        )

                        self.adicionar_log(
                        "========================================"
                        )

                        self.habilitar_botao()


                except TimeoutException:

                        self.adicionar_log(
                        "[ERRO] Tempo de espera excedido."
                        )

                        self.atualizar_status(
                        "Tempo de espera excedido."
                        )

                        self.habilitar_botao()


                except WebDriverException as erro:

                        self.adicionar_log(
                        f"[ERRO] WebDriver: {erro}"
                        )

                        self.atualizar_status(
                        "Erro no WebDriver."
                        )

                        self.habilitar_botao()


                except (
                        FileNotFoundError,
                        OSError,
                        RuntimeError
                ) as erro:

                        self.adicionar_log(
                        f"[ERRO] {erro}"
                        )

                        self.atualizar_status(
                        "Erro durante a verificação."
                        )

                        self.habilitar_botao()


                except Exception as erro:

                        traceback_completo = traceback.format_exc()

                        # Mostra obrigatoriamente no terminal

                        print("\n" + "=" * 70)
                        print("ERRO INESPERADO NA AUTOMAÇÃO")
                        print("=" * 70)
                        print(traceback_completo)
                        print("=" * 70 + "\n")

                        try:
                                self.adicionar_log(
                                f"[ERRO INESPERADO] {erro}"
                                )

                                self.adicionar_log(
                                traceback.format_exc()
                                )

                                self.atualizar_status(
                                "Erro inesperado."
                                )
                        except Exception as erro_log:

                                print(f'Não foi possível escrever o erro na interface: {erro_log}')

                        self.atualizar_status(
                                'Erro inesperado. Verifique o LOG gerado.'
                        )

                        self.habilitar_botao()

        def atualizar_status(self, mensagem):

                self.root.after(
                        0,
                        lambda: self.status.set(mensagem)
                )

        def atualizar_progresso(self, valor):

                self.root.after(
                        0,
                        lambda: self.progresso.configure(
                        value=valor
                        )
                )

        def habilitar_botao(self):

                self.root.after(
                0,
                lambda: self.botao_iniciar.configure(
                state="normal"
                        )
                )


# ==============================================================
# EXECUÇÃO
# ==============================================================

if __name__ == "__main__":

        janela = tk.Tk()

        app = AplicacaoAutomacao(janela)

        janela.mainloop()

                