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


from interface.app_layout import AppLayoutMixin

class AplicacaoAutomacao(AppLayoutMixin):

        def __init__(
                self,
                root,
                arquivos_iniciais=None,
                configuracao_analise=None,
                navegacao=None,
                dataframe_inicial=None,
                nome_fonte_empresarial="Módulo empresarial",
        ):
                self.root = root
                self.navegacao = navegacao or {}
                self.configuracao_analise = normalizar_configuracao(configuracao_analise)
                self.modulos_analise = self.configuracao_analise["modulos"]
                self.categoria_solicitada = self.configuracao_analise["categoria"]
                self.periodo_solicitado = self.configuracao_analise["periodo"]
                self.ia_habilitada = self.configuracao_analise["ia"]

                self.fila_log = queue.Queue()
                self.fila_ui = queue.Queue()
                self.arquivo_selecionado = None
                self.arquivos_selecionados = []
                self.arquivos_temporarios = set(
                        self.configuracao_analise.get("arquivos_temporarios") or ()
                )
                self.resultados_arquivos = []
                self.df_consolidado = None
                self.classificacao_atual = None
                self.indicadores_atuais = None
                self.resultado_analise = None
                self.analise_estrutural = None
                self.analise_qualidade = None
                self.analise_temporal = None
                self.relatorio_tratamento = None
                self.driver_selenium = None
                self.processando = False
                self.after_logs_id = None
                self.categoria_atual = "desconhecida"
                self.dashboard_config = {}
                self.job_id = None
                self.cancel_event = threading.Event()
                self.worker_thread = None
                self.ator_execucao = dict(SESSAO.usuario or {})
                self.ator_execucao["_empresa_id"] = SESSAO.empresa_id
                self.ator_execucao["_filial_id"] = SESSAO.filial_id
                self.dataframe_inicial = dataframe_inicial
                self.nome_fonte_empresarial = nome_fonte_empresarial

                self.root.title(f"Data Intelligence · Dashboard analítico · {VERSAO_INTERFACE}")

                self.criar_interface()
                self.processar_logs()
                self.root.protocol("WM_DELETE_WINDOW", self.encerrar_aplicacao)

                if self.dataframe_inicial is not None:
                        self.root.after(
                                300,
                                lambda: self.carregar_dataframe_empresarial(
                                        self.dataframe_inicial,
                                        self.nome_fonte_empresarial,
                                ),
                        )
                        return

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
                except tk.TclError:
                        return

                try:
                        while True:
                                callback, args = self.fila_ui.get_nowait()
                                callback(*args)
                except queue.Empty:
                        pass
                except tk.TclError:
                        return

                if self.container.winfo_exists():
                        self.after_logs_id = self.root.after(50, self.processar_logs)

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

                self.worker_thread = threading.Thread(
                        target=self.executar_processo,
                        daemon=True,
                )
                self.worker_thread.start()

        def executar_processo(self):
                driver = None
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
                        self._encerrar_driver_selenium()
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
                        link_validacao = obter_link_validacao()
                        self.adicionar_log(f"[AGUARDE] Acessando: {link_validacao}")
                        driver.get(link_validacao)

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
                        if driver is not None:
                                self._encerrar_driver_selenium(driver)
                finally:
                        self.habilitar_botao()

        def _encerrar_driver_selenium(self, driver=None):
                driver_alvo = driver or self.driver_selenium
                if driver_alvo is None:
                        return
                try:
                        driver_alvo.quit()
                except Exception as erro:
                        self.adicionar_log(
                                f"[AVISO] Não foi possível encerrar o navegador: {erro}"
                        )
                finally:
                        if self.driver_selenium is driver_alvo:
                                self.driver_selenium = None

        def encerrar_aplicacao(self):
                self.cancel_event.set()
                if self.processando:
                        self._cancelar_job_analise("Aplicação encerrada pelo usuário.")
                if self.after_logs_id is not None:
                        try:
                                self.root.after_cancel(self.after_logs_id)
                        except tk.TclError:
                                pass
                self._encerrar_driver_selenium()
                worker = self.worker_thread
                if (
                        worker is not None
                        and worker.is_alive()
                        and worker is not threading.current_thread()
                ):
                        worker.join(timeout=1.5)
                self.root.destroy()

        def _navegar(self, destino):
                if self.processando:
                        self.adicionar_log(
                                "[INFO] Aguarde o processamento terminar antes de mudar de tela."
                        )
                        return
                callback = self.navegacao.get(destino)
                if callback is None:
                        return
                if self.after_logs_id is not None:
                        try:
                                self.root.after_cancel(self.after_logs_id)
                        except tk.TclError:
                                pass
                        self.after_logs_id = None
                self._encerrar_driver_selenium()
                if self.container.winfo_exists():
                        self.container.destroy()
                callback()

        def _navegar_secao_analytics(self, secao):
                if self.processando:
                        self.adicionar_log(
                                "[INFO] Aguarde o processamento terminar antes de mudar de tela."
                        )
                        return
                callback = self.navegacao.get("analytics_secao")
                if callback is None:
                        return
                self._finalizar_tela_para_navegacao()
                callback(secao)

        def _navegar_ferramenta(self, ferramenta):
                if self.processando:
                        self.adicionar_log(
                                "[INFO] Aguarde o processamento terminar antes de mudar de tela."
                        )
                        return
                callback = self.navegacao.get("ferramenta")
                if callback is None:
                        return
                self._finalizar_tela_para_navegacao()
                callback(ferramenta)

        def _finalizar_tela_para_navegacao(self):
                if self.after_logs_id is not None:
                        try:
                                self.root.after_cancel(self.after_logs_id)
                        except tk.TclError:
                                pass
                        self.after_logs_id = None
                self._encerrar_driver_selenium()
                if self.container.winfo_exists():
                        self.container.destroy()

        # ==========================================================
        # ATUALIZAÇÃO DO DASHBOARD
        # ==========================================================

        @staticmethod
        def _numero_seguro(valor):
                try:
                        return float(valor or 0)
                except (TypeError, ValueError):
                        return 0.0

        @classmethod
        def _moeda_br(cls, valor):
                return (
                        f"R$ {cls._numero_seguro(valor):,.2f}"
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                )

        @classmethod
        def _numero_br(cls, valor):
                return f"{int(cls._numero_seguro(valor)):,}".replace(",", ".")

        @classmethod
        def _decimal_br(cls, valor):
                return f"{cls._numero_seguro(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        @classmethod
        def _percentual_br(cls, valor):
                return f"{cls._numero_seguro(valor):.1f}%".replace(".", ",")


        def _obter_valor_dashboard(self, caminho):
                if not caminho:
                        return None
                if caminho.startswith("qualidade."):
                        fonte = self.analise_qualidade or {}
                        caminho = caminho.split(".", 1)[1]
                elif caminho.startswith("universais."):
                        fonte = (self.indicadores_atuais or {}).get("universais") or {}
                        caminho = caminho.split(".", 1)[1]
                else:
                        fonte = self.indicadores_atuais or {}
                return fonte.get(caminho)

        def _formatar_dashboard(self, valor, formato):
                if valor is None:
                        return "—"
                if formato == "moeda":
                        return self._moeda_br(valor)
                if formato == "inteiro":
                        return self._numero_br(valor)
                if formato == "decimal":
                        return self._decimal_br(valor)
                if formato == "percentual":
                        return self._percentual_br(valor)
                return str(valor)

        def atualizar_cards_indicadores(self):
                if not self.indicadores_atuais:
                        return
                labels = (
                        self.card_faturamento,
                        self.card_vendas,
                        self.card_quantidade,
                        self.card_ticket,
                )
                for label, (_, chave, formato) in zip(
                        labels,
                        self.dashboard_config.get("cards", ()),
                ):
                        valor = self._obter_valor_dashboard(chave)
                        label.configure(
                                text=self._formatar_dashboard(valor, formato),
                                fg=self.cores["text"] if valor is not None else self.cores["text_sec"],
                        )

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
                labels = (self.label_produto, self.label_loja)
                for label, especificacao in zip(
                        labels,
                        self.dashboard_config.get("destaques", ()),
                ):
                        _, chave, formato, detalhe_chave, detalhe_formato = especificacao
                        valor = self._obter_valor_dashboard(chave)
                        if valor is None:
                                label.configure(
                                        text="Não disponível",
                                        fg=self.cores["text_sec"],
                                )
                                continue
                        texto = self._formatar_dashboard(valor, formato)
                        detalhe = self._obter_valor_dashboard(detalhe_chave)
                        if detalhe is not None:
                                texto += "\n" + self._formatar_dashboard(
                                        detalhe,
                                        detalhe_formato,
                                )
                        label.configure(text=texto, fg=self.cores["text"])

        def atualizar_status(self, mensagem):
                self.executar_na_ui(self.status.set, mensagem)

        def _definir_progresso_ui(self, valor):
                self.progresso.configure(value=valor)

        def atualizar_progresso(self, valor):
                self.executar_na_ui(self._definir_progresso_ui, valor)

        def atualizar_status_e_progresso(self, valor, mensagem):
                self.atualizar_progresso(valor)
                self.atualizar_status(mensagem)

        def atualizar_progresso_motor(self, valor, mensagem):
                # Reserva os 10% finais para uma transição visual progressiva.
                valor_visual = min(90, int(float(valor) * 0.90))
                if self.job_id is not None and self.ator_execucao.get("id"):
                        try:
                                atualizar_job(
                                        self.job_id,
                                        valor_visual,
                                        mensagem,
                                        self.ator_execucao,
                                )
                        except (RuntimeError, ValueError):
                                pass
                self.atualizar_status_e_progresso(valor_visual, mensagem)

        def _habilitar_botao_ui(self):
                self.botao_iniciar.configure(state="normal")

        def habilitar_botao(self):
                self.executar_na_ui(self._habilitar_botao_ui)

        # ==========================================================
        # PIPELINE DE ANÁLISE
        # ==========================================================

        def _criar_job_analise(self, titulo):
                if not self.ator_execucao.get("id"):
                        self.job_id = None
                        return
                try:
                        job = criar_job("analise", titulo, self.ator_execucao)
                        self.job_id = job["id"]
                        iniciar_job(self.job_id, self.ator_execucao)
                        self.adicionar_log(f"[JOB] {job['codigo']}")
                except (RuntimeError, ValueError):
                        self.job_id = None

        def _concluir_job_analise(self, resultado):
                if self.job_id is None or not self.ator_execucao.get("id"):
                        return
                universais = (resultado.get("indicadores") or {}).get("universais") or {}
                concluir_job(
                        self.job_id,
                        self.ator_execucao,
                        {
                                "categoria": resultado.get("categoria"),
                                "total_registros": universais.get("total_registros"),
                                "qualidade": (resultado.get("qualidade") or {}).get(
                                        "score_qualidade"
                                ),
                        },
                )

        def _falhar_job_analise(self, erro):
                if self.job_id is None or not self.ator_execucao.get("id"):
                        return
                try:
                        falhar_job(self.job_id, self.ator_execucao, str(erro))
                except (RuntimeError, ValueError):
                        pass

        def _cancelar_job_analise(self, mensagem="Cancelado pelo usuário."):
                if self.job_id is None or not self.ator_execucao.get("id"):
                        return
                try:
                        cancelar_job(
                                self.job_id,
                                self.ator_execucao,
                                mensagem,
                        )
                except (RuntimeError, ValueError):
                        pass

        def _cancelamento_requisitado(self):
                if self.cancel_event.is_set():
                        return True
                if self.job_id is None or not self.ator_execucao.get("id"):
                        return False
                try:
                        return cancelamento_solicitado(
                                self.job_id,
                                self.ator_execucao,
                        )
                except (RuntimeError, ValueError):
                        return False

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
                                        (
                                                "Dados suportados",
                                                "*.xlsx *.xls *.csv *.json *.parquet *.txt",
                                        ),
                                        ("Excel", "*.xlsx *.xls"),
                                        ("CSV", "*.csv"),
                                        ("JSON", "*.json"),
                                        ("Parquet", "*.parquet"),
                                        ("Texto delimitado", "*.txt"),
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

        def carregar_dataframe_empresarial(self, dataframe, nome_fonte):
                if self.processando:
                        return
                self.arquivos_selecionados = [str(nome_fonte)]
                self.configuracao_analise["arquivos"] = [str(nome_fonte)]
                self.configuracao_analise["fonte"] = "sistema"
                self._atualizar_lista_arquivos()
                self.processando = True
                self._criar_job_analise(f"Análise · {nome_fonte}")
                self.progresso.configure(value=0)
                self.status.set("Preparando dados do módulo...")
                self.cancel_event.clear()
                self.worker_thread = threading.Thread(
                        target=self._processar_dataframe_thread,
                        args=(dataframe.copy(deep=True), str(nome_fonte)),
                        daemon=True,
                )
                self.worker_thread.start()

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
                self._criar_job_analise(
                        f"Análise de {len(self.arquivos_selecionados)} arquivo(s)"
                )
                self.progresso.configure(value=0)
                self.status.set("Preparando análise...")

                self.cancel_event.clear()
                self.worker_thread = threading.Thread(
                        target=self._processar_analise_thread,
                        args=(list(self.arquivos_selecionados),),
                        daemon=True,
                )
                self.worker_thread.start()

        def _processar_analise_thread(self, caminhos):
                try:
                        inicio = time.monotonic()
                        orquestrador = OrquestradorAnalise(
                                logger=self.adicionar_log,
                                progresso=self.atualizar_progresso_motor,
                                cancelar=self._cancelamento_requisitado,
                        )
                        resultado = orquestrador.processar(
                                caminhos,
                                self.configuracao_analise,
                        )
                        atraso_minimo = max(
                                0.0,
                                float(
                                        self.configuracao_analise.get(
                                                "atraso_minimo_segundos",
                                                5,
                                        )
                                ),
                        )
                        restante = max(0.0, atraso_minimo - (time.monotonic() - inicio))
                        if restante:
                                self.adicionar_log(
                                        "[INFO] Finalizando a apresentação dos resultados..."
                                )
                                passos = 9
                                for indice in range(passos):
                                        if self._cancelamento_requisitado():
                                                raise ProcessamentoCancelado(
                                                        "Processamento cancelado com segurança."
                                                )
                                        time.sleep(restante / passos)
                                        self.atualizar_status_e_progresso(
                                                91 + indice,
                                                "Organizando o dashboard...",
                                        )
                        self._concluir_job_analise(resultado)
                        self.executar_na_ui(
                                self._processamento_concluido,
                                resultado,
                        )
                except ProcessamentoCancelado as erro:
                        self._cancelar_job_analise(str(erro))
                        self.executar_na_ui(self._processamento_cancelado)
                except Exception as erro:
                        self._falhar_job_analise(erro)
                        mensagem = str(erro)
                        traceback_completo = traceback.format_exc()
                        self.executar_na_ui(
                                self._processamento_falhou,
                                mensagem,
                                traceback_completo,
                        )
                finally:
                        for caminho in tuple(self.arquivos_temporarios):
                                limpar_arquivo_temporario(caminho)
                        self.arquivos_temporarios.clear()

        def _processar_dataframe_thread(self, dataframe, nome_fonte):
                try:
                        inicio = time.monotonic()
                        orquestrador = OrquestradorAnalise(
                                logger=self.adicionar_log,
                                progresso=self.atualizar_progresso_motor,
                                cancelar=self._cancelamento_requisitado,
                        )
                        resultado = orquestrador.processar_dataframe(
                                dataframe,
                                self.configuracao_analise,
                                nome_fonte=nome_fonte,
                        )
                        atraso_minimo = max(
                                0.0,
                                float(
                                        self.configuracao_analise.get(
                                                "atraso_minimo_segundos",
                                                5,
                                        )
                                ),
                        )
                        restante = max(0.0, atraso_minimo - (time.monotonic() - inicio))
                        if restante:
                                for indice in range(9):
                                        if self._cancelamento_requisitado():
                                                raise ProcessamentoCancelado(
                                                        "Processamento cancelado com segurança."
                                                )
                                        time.sleep(restante / 9)
                                        self.atualizar_status_e_progresso(
                                                91 + indice,
                                                "Organizando o dashboard empresarial...",
                                        )
                        self._concluir_job_analise(resultado)
                        self.executar_na_ui(self._processamento_concluido, resultado)
                except ProcessamentoCancelado as erro:
                        self._cancelar_job_analise(str(erro))
                        self.executar_na_ui(self._processamento_cancelado)
                except Exception as erro:
                        self._falhar_job_analise(erro)
                        self.executar_na_ui(
                                self._processamento_falhou,
                                str(erro),
                                traceback.format_exc(),
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
                self.relatorio_tratamento = resultado.get("tratamento")

                if self.ator_execucao.get("id"):
                        try:
                                historico_id = registrar_analise(
                                        resultado,
                                        self.ator_execucao["id"],
                                        empresa_id=self.ator_execucao.get("_empresa_id"),
                                        filial_id=self.ator_execucao.get("_filial_id"),
                                )
                                self.adicionar_log(
                                        f"[OK] Análise registrada no histórico #{historico_id}."
                                )
                                registrar_atividade_analytics(
                                        historico_id,
                                        resultado.get("categoria") or "desconhecida",
                                        self.ator_execucao,
                                )
                        except Exception as erro:
                                self.adicionar_log(
                                        f"[AVISO] Não foi possível salvar o histórico: {erro}"
                                )

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
                qualidade = self.analise_qualidade or {}
                nivel = qualidade.get("nivel_qualidade")
                score = qualidade.get("score_qualidade")
                if nivel is not None and score is not None:
                        self.status.set(
                                f"Análise concluída · Qualidade {nivel} ({score:.1f})"
                        )
                else:
                        self.status.set("Análise concluída com sucesso.")
                self.progresso.configure(value=100)
                self.processando = False
                self.job_id = None

        def _processamento_cancelado(self):
                self.processando = False
                self.job_id = None
                self.progresso.configure(value=0)
                self.status.set("Processamento cancelado com segurança.")
                self.adicionar_log("[CANCELADO] A operação foi interrompida.")

        def _processamento_falhou(self, mensagem, traceback_completo):
                self.processando = False
                self.job_id = None
                self.adicionar_log("[ERRO AO PROCESSAR ARQUIVOS]")
                self.adicionar_log(mensagem)
                self.adicionar_log(traceback_completo)
                self.status.set("Erro ao processar arquivos.")

        def _atualizar_lista_arquivos(self):
                self.lista_arquivos.delete(0, tk.END)
                for caminho in self.arquivos_selecionados:
                        self.lista_arquivos.insert(tk.END, Path(caminho).name)
                quantidade = len(self.arquivos_selecionados)
                if quantidade:
                        self.label_arquivo.configure(
                                text=(
                                        f"{quantidade} arquivo selecionado"
                                        if quantidade == 1
                                        else f"{quantidade} arquivos selecionados"
                                )
                        )
                else:
                        self.label_arquivo.configure(text="Nenhum arquivo selecionado")


# ==============================================================
# EXECUÇÃO
# ==============================================================

if __name__ == "__main__":

        janela = tk.Tk()

        app = AplicacaoAutomacao(janela)

        janela.mainloop()
