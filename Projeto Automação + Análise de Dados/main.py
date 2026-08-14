"""Ponto de entrada e roteador central da plataforma empresarial V11.1.0."""

import sys
import threading
import traceback
import tkinter as tk
from tkinter import messagebox

from auth.banco import inicializar_banco, tem_usuarios
from auth.sessao import SESSAO
from configuracoes.preferencias import carregar_preferencias
from core.nodo import carregar_config_nodo, cliente_convencional, usa_servidor_remoto
from core.caminhos import pasta_logs_desktop
from core.observabilidade import configurar_logger_rotativo
from core.versao import VERSAO_INTERFACE
from dados.fontes import limpar_temporarios_antigos
from enterprise import inicializar_enterprise
from enterprise.contexto import garantir_contexto_sessao, tem_permissao
from enterprise.catalogo import MODULOS
from enterprise.modulos import exportar_dataframe_modulo
from historico.repositorio import inicializar_historico
from interface.app import AplicacaoAutomacao
from interface.aprovacoes import TelaAprovacoes
from interface.busca_universal import JanelaBuscaUniversal
from interface.catalogo_modulos import TelaCatalogoModulos
from interface.central_analytics import TelaCentralAnalytics
from interface.configuracoes_app import TelaConfiguracoesApp
from interface.compliance import TelaCompliance
from interface.ferramentas import TelaFerramentaCorporativa
from interface.financeiro import TelaFinanceiro
from interface.compras import TelaCompras
from interface.correio import TelaCorreio
from interface.estoque import TelaEstoque
from interface.experiencias_departamentais import TelaExperienciaDepartamental
from interface.rh import TelaRH
from interface.tecnologia import TelaTecnologia
from interface.historico import TelaHistorico
from interface.login import TelaLogin
from interface.marketing import TelaMarketing
from interface.comercial import TelaComercial
from interface.administrativo import TelaAdministrativo
from interface.juridico import TelaJuridico
from interface.nova_analise import TelaNovaAnalise
from interface.navegacao_modulos import normalizar_secao_modulo, tipo_tela_modulo
from interface.notificacoes import TelaNotificacoes
from interface.organizacao import TelaOrganizacao
from interface.operacoes_visuais import TelaOperacaoVisual
from interface.painel_modulo import TelaPainelModulo
from interface.perfis_analise import TelaPerfisAnalise
from interface.primeiro_acesso import TelaPrimeiroAcesso
from interface.principal import TelaPrincipal
from interface.gerenciador_tema import aplicar_tema_inicial
from interface.tema import CORES, configurar_estilos_ttk
from interface.usuarios import TelaUsuarios
from servidor_ti import iniciar_servidor_embutido


_LOGGER_DESKTOP = configurar_logger_rotativo(
    "data_intelligence.desktop",
    pasta_logs_desktop() / "desktop.jsonl",
)


def main() -> None:
    janela = tk.Tk()
    janela.title(f"Data Intelligence · Enterprise Platform · {VERSAO_INTERFACE}")
    largura_tela = janela.winfo_screenwidth()
    altura_tela = janela.winfo_screenheight()
    # Full HD é a resolução de design; a janela continua responsiva em telas
    # menores. No Windows preferimos a área útil maximizada (sem cobrir a
    # barra de tarefas) em vez de impor 1920x1080 cegamente.
    largura = min(1920, max(1024, int(largura_tela * 0.96)))
    altura = min(1080, max(680, int(altura_tela * 0.94)))
    posicao_x = max(0, (largura_tela - largura) // 2)
    posicao_y = max(0, (altura_tela - altura) // 2)
    janela.geometry(f"{largura}x{altura}+{posicao_x}+{posicao_y}")
    janela.minsize(1024, 680)
    if sys.platform.startswith("win"):
        try:
            janela.state("zoomed")
        except tk.TclError:
            pass
    janela.configure(bg=CORES["bg"])

    try:
        config_nodo = carregar_config_nodo()
    except ValueError as erro:
        messagebox.showerror(
            "Configuração da estação",
            f"{erro}\n\nA aplicação foi interrompida para evitar operar no banco local por engano.",
            parent=janela,
        )
        janela.destroy()
        return

    remoto = config_nodo.papel in {"central", "cliente"} and bool(config_nodo.servidor_url)
    limpar_temporarios_antigos()
    if not remoto:
        # O servidor/standalone explícito inicializa o backend configurado.
        # Central e Cliente nunca criam banco, schema ou cache persistente local.
        inicializar_banco()
        inicializar_historico()
        inicializar_enterprise()
    # Em modo conectado, o receptor de agentes vive no Servidor Corporativo.
    # A estação Central não abre uma segunda autoridade/banco local na porta 8765.
    if config_nodo.papel == "standalone":
        iniciar_servidor_embutido()
    aplicar_tema_inicial(janela)

    def limpar_janela():
        janela.protocol("WM_DELETE_WINDOW", janela.destroy)
        # Remove atalhos específicos da tela anterior (principalmente <Return>
        # do login) antes de destruir seus widgets. Isso evita callbacks órfãos
        # apontando para Entry/Canvas já removidos após a autenticação.
        try:
            janela.unbind("<Return>")
        except tk.TclError:
            pass
        for componente in janela.winfo_children():
            try:
                componente.destroy()
            except tk.TclError:
                pass

    def _registrar_erro_interface(tipo, valor, tb):
        detalhe = "".join(traceback.format_exception(tipo, valor, tb))
        _LOGGER_DESKTOP.error(
            "Falha não tratada na interface",
            exc_info=(tipo, valor, tb),
            extra={"evento": "desktop_callback_exception", "componente": "desktop"},
        )
        try:
            messagebox.showerror(
                "Data Intelligence",
                f"Não foi possível concluir esta operação.\n\n{valor}\n\n"
                f"O diagnóstico foi registrado em:\n"
                f"{getattr(_LOGGER_DESKTOP, 'arquivo_log', None) or 'saída de diagnóstico do aplicativo'}",
                parent=janela,
            )
        except tk.TclError:
            return

        # Se a exceção ocorreu durante uma troca de tela e o conteúdo já havia
        # sido destruído, nunca deixe o usuário diante de uma janela vazia.
        try:
            if janela.winfo_exists() and not janela.winfo_children():
                fallback = tk.Frame(janela, bg=CORES["bg"])
                fallback.pack(fill="both", expand=True)
                centro = tk.Frame(fallback, bg=CORES["card"], padx=34, pady=30)
                centro.place(relx=0.5, rely=0.5, anchor="center")
                tk.Label(
                    centro, text="Não foi possível carregar esta tela",
                    font=("Inter", 18, "bold"), fg=CORES["text"], bg=CORES["card"],
                ).pack(pady=(0, 10))
                tk.Label(
                    centro,
                    text=str(valor) or "Ocorreu uma falha operacional inesperada.",
                    font=("Inter", 10), fg=CORES["text_sec"], bg=CORES["card"],
                    wraplength=620, justify="center",
                ).pack(pady=(0, 20))
                botoes = tk.Frame(centro, bg=CORES["card"])
                botoes.pack()
                tk.Button(
                    botoes, text="TENTAR NOVAMENTE", command=abrir_principal,
                    bg=CORES["primary"], fg="#FFFFFF", bd=0, padx=18, pady=9,
                ).pack(side="left", padx=6)
                tk.Button(
                    botoes, text="SAIR DA SESSÃO", command=sair_da_sessao,
                    bg=CORES["input"], fg=CORES["text"], bd=0, padx=18, pady=9,
                ).pack(side="left", padx=6)
        except Exception:
            _LOGGER_DESKTOP.error(
                "Falha ao renderizar tela de recuperação",
                exc_info=True,
                extra={"evento": "desktop_recovery_failed", "componente": "desktop"},
            )

    janela.report_callback_exception = _registrar_erro_interface

    def mapa_navegacao():
        return {
            "inicio": abrir_principal,
            "modulos": abrir_modulos,
            "modulo": abrir_modulo,
            "registros_modulo": abrir_registros_modulo,
            "secao_modulo": abrir_secao_modulo,
            "analisar_modulo": analisar_modulo,
            "analytics": abrir_analytics,
            "analytics_secao": abrir_secao_analytics,
            "nova": abrir_nova_analise,
            "historico": abrir_historico,
            "aprovacoes": abrir_aprovacoes,
            "notificacoes": abrir_notificacoes,
            "correio": abrir_correio,
            "configuracoes": abrir_configuracoes,
            "compliance": abrir_compliance,
            "organizacao": abrir_organizacao,
            "perfis": abrir_perfis,
            "usuarios": abrir_usuarios,
            "busca": abrir_busca,
            "ferramenta": abrir_ferramenta,
            "sair": sair_da_sessao,
        }

    def preparar_tela():
        # Valide antes de destruir a tela atual. Se servidor/contexto falhar,
        # o login ou a tela anterior permanece visível e recuperável.
        garantir_contexto_sessao()
        limpar_janela()
        janela.title(f"Data Intelligence · Enterprise Platform · {VERSAO_INTERFACE}")

    def abrir_principal():
        preparar_tela()
        TelaPrincipal(janela, mapa_navegacao())

    def abrir_modulos():
        preparar_tela()
        TelaCatalogoModulos(janela, mapa_navegacao())

    def _pode_abrir_modulo(modulo):
        # Tecnologia oferece suporte básico a qualquer usuário autenticado;
        # as seções administrativas continuam protegidas dentro do módulo.
        return modulo == "ti" or tem_permissao(SESSAO.usuario, modulo, "ler")

    def _renderizar_modulo(modulo, secao="visao"):
        modulo = str(modulo or "").strip().lower()
        if modulo not in MODULOS or modulo == "analytics":
            messagebox.showerror(
                "Módulo inválido",
                "O destino solicitado não corresponde a um módulo operacional.",
                parent=janela,
            )
            abrir_modulos()
            return
        if not _pode_abrir_modulo(modulo):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui acesso a este módulo.",
                parent=janela,
            )
            abrir_modulos()
            return

        secao = normalizar_secao_modulo(modulo, secao, usuario=SESSAO.usuario)
        preparar_tela()
        navegacao = mapa_navegacao()
        tipo = tipo_tela_modulo(modulo, secao)

        if tipo == "financeiro":
            TelaFinanceiro(janela, navegacao, secao=secao)
        elif tipo == "compras":
            TelaCompras(janela, navegacao, secao=secao)
        elif tipo == "rh":
            TelaRH(janela, navegacao, secao=secao)
        elif tipo == "estoque":
            TelaEstoque(janela, navegacao, secao=secao)
        elif tipo == "ti":
            TelaTecnologia(janela, navegacao, secao=secao)
        elif tipo == "marketing":
            TelaMarketing(janela, navegacao, secao=secao)
        elif tipo == "comercial":
            TelaComercial(janela, navegacao, secao=secao)
        elif tipo == "administrativo":
            TelaAdministrativo(janela, navegacao, secao=secao)
        elif tipo == "juridico":
            TelaJuridico(janela, navegacao, secao=secao)
        elif tipo == "experiencia":
            TelaExperienciaDepartamental(janela, navegacao, modulo)
        elif tipo == "operacao_visual":
            TelaOperacaoVisual(janela, navegacao, modulo, secao=secao)
        else:
            TelaPainelModulo(janela, navegacao, modulo, secao=secao)

    def abrir_modulo(modulo):
        _renderizar_modulo(modulo, "visao")

    def abrir_secao_modulo(modulo, secao="visao"):
        _renderizar_modulo(modulo, secao)

    def abrir_registros_modulo(modulo):
        _renderizar_modulo(modulo, "registros")

    def analisar_modulo(modulo):
        if not tem_permissao(SESSAO.usuario, "analytics", "escrever"):
            messagebox.showerror(
                "Analytics empresarial",
                "Seu perfil não possui permissão para executar análises.",
                parent=janela,
            )
            abrir_modulos()
            return
        try:
            dataframe = exportar_dataframe_modulo(modulo, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Analytics empresarial", str(erro), parent=janela)
            return
        categorias = {
            "rh": "recursos_humanos",
            "financeiro": "financeiro",
            "estoque": "estoque",
            "compras": "compras",
            "ti": "ti",
            "marketing": "marketing",
            "administrativo": "administrativo",
            "juridico": "juridico",
            "comercial": "comercial",
        }
        configuracao = {
            "fonte": "sistema",
            "categoria": categorias.get(modulo, "cadastro"),
            "periodo": "automatico",
            "modulos": {
                "tratamento": True,
                "estrutural": True,
                "indicadores": True,
                "temporal": True,
                "qualidade": True,
            },
            "atraso_minimo_segundos": carregar_preferencias().get(
                "atraso_minimo_segundos", 5
            ),
        }
        preparar_tela()
        AplicacaoAutomacao(
            janela,
            configuracao_analise=configuracao,
            navegacao=mapa_navegacao(),
            dataframe_inicial=dataframe,
            nome_fonte_empresarial=f'Módulo · {MODULOS[modulo]["nome"]}',
        )

    def abrir_analytics():
        if not tem_permissao(SESSAO.usuario, "analytics", "ler"):
            messagebox.showerror("Acesso negado", "Analytics não autorizado.")
            abrir_modulos()
            return
        preparar_tela()
        TelaCentralAnalytics(janela, mapa_navegacao())

    def abrir_secao_analytics(secao):
        if not tem_permissao(SESSAO.usuario, "analytics", "ler"):
            messagebox.showerror("Acesso negado", "Analytics não autorizado.")
            abrir_modulos()
            return
        preparar_tela()
        TelaCentralAnalytics(
            janela,
            mapa_navegacao(),
            secao=secao,
        )

    def abrir_nova_analise(configuracao_inicial=None):
        if not tem_permissao(SESSAO.usuario, "analytics", "escrever"):
            messagebox.showerror("Acesso negado", "Execução analítica não autorizada.")
            abrir_modulos()
            return
        preparar_tela()
        TelaNovaAnalise(
            janela,
            executar_analise=abrir_aplicacao,
            voltar=abrir_analytics,
            navegacao=mapa_navegacao(),
            configuracao_inicial=configuracao_inicial,
        )

    def abrir_aplicacao(configuracao=None):
        if not tem_permissao(SESSAO.usuario, "analytics", "escrever"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui permissão para executar análises.",
            )
            abrir_modulos()
            return
        preparar_tela()
        AplicacaoAutomacao(
            janela,
            configuracao_analise=configuracao,
            navegacao=mapa_navegacao(),
        )

    def abrir_historico():
        if not tem_permissao(SESSAO.usuario, "analytics", "ler"):
            messagebox.showerror("Acesso negado", "Histórico analítico não autorizado.")
            abrir_principal()
            return
        preparar_tela()
        TelaHistorico(janela, mapa_navegacao())

    def abrir_aprovacoes():
        preparar_tela()
        TelaAprovacoes(janela, mapa_navegacao())

    def abrir_notificacoes():
        preparar_tela()
        TelaNotificacoes(janela, mapa_navegacao())

    def abrir_correio(modulo_origem=None):
        preparar_tela()
        TelaCorreio(janela, mapa_navegacao(), modulo_origem=modulo_origem)

    def abrir_configuracoes():
        preparar_tela()
        TelaConfiguracoesApp(janela, mapa_navegacao())

    def abrir_compliance():
        preparar_tela()
        try:
            TelaCompliance(janela, mapa_navegacao())
        except PermissionError as erro:
            messagebox.showerror("Acesso negado", str(erro), parent=janela)
            abrir_principal()

    def abrir_organizacao():
        if not SESSAO.eh_admin():
            messagebox.showerror("Acesso negado", "Somente administradores.")
            abrir_configuracoes()
            return
        preparar_tela()
        TelaOrganizacao(janela, mapa_navegacao())

    def abrir_perfis():
        if not tem_permissao(SESSAO.usuario, "analytics", "escrever"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui permissão para configurar análises.",
            )
            abrir_modulos()
            return
        preparar_tela()
        TelaPerfisAnalise(janela, mapa_navegacao())

    def abrir_usuarios():
        if cliente_convencional():
            messagebox.showerror(
                "Acesso negado",
                "Esta estação é um cliente convencional. Usuários são criados somente pela estação Central/Administrador.",
                parent=janela,
            )
            abrir_principal()
            return
        if not SESSAO.eh_admin():
            messagebox.showerror(
                "Acesso negado",
                "Somente administradores podem gerenciar usuários.",
            )
            abrir_principal()
            return
        preparar_tela()
        TelaUsuarios(janela, navegacao=mapa_navegacao())

    def abrir_busca(_evento=None):
        if not SESSAO.autenticado():
            return
        JanelaBuscaUniversal(janela, mapa_navegacao())

    def abrir_ferramenta(ferramenta):
        preparar_tela()
        try:
            TelaFerramentaCorporativa(
                janela,
                mapa_navegacao(),
                ferramenta,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror(
                "Ferramenta corporativa",
                str(erro),
                parent=janela,
            )
            abrir_principal()

    def concluir_autenticacao():
        # O login já sincronizou a escolha visual atual. Apenas reaplicamos os
        # estilos sem sobrescrever o modo claro na primeira navegação.
        configurar_estilos_ttk(janela)
        abrir_principal()

    def abrir_login(mensagem=None):
        aplicar_tema_inicial(janela)
        limpar_janela()
        TelaLogin(janela, concluir_autenticacao, mensagem_inicial=mensagem)

    def sair_da_sessao():
        if usa_servidor_remoto():
            try:
                from enterprise.servidor_cliente import encerrar_sessao_remota
                encerrar_sessao_remota()
            except Exception as erro:
                _LOGGER_DESKTOP.warning(
                    "Falha ao encerrar a sessão remota",
                    extra={"evento": "remote_logout_failed", "erro_operacional": str(erro)},
                )
        SESSAO.encerrar()
        abrir_login("Sessão encerrada com segurança.")

    def registrar_atividade(_evento=None):
        SESSAO.registrar_atividade()

    estado_watchdog = {"relogin_em_andamento": False, "aviso_preferencia_emitido": False}

    def verificar_expiracao_sessao():
        # A indisponibilidade temporária do Servidor Corporativo não deve parar
        # silenciosamente o watchdog de sessão nem desmontar a tela atual.
        minutos = 30
        try:
            # No login não existe preferência corporativa a atualizar. Além de
            # poupar RPCs, isso impede o mesmo aviso a cada 30 segundos depois
            # de uma revogação/expiração remota.
            if not SESSAO.autenticado():
                return
            try:
                minutos = carregar_preferencias()["tempo_sessao_minutos"]
            except (ValueError, PermissionError, RuntimeError, OSError) as erro:
                mensagem = str(erro)
                sessao_remota_invalida = usa_servidor_remoto() and (
                    isinstance(erro, PermissionError)
                    or "entre novamente" in mensagem.lower()
                    or "sessão" in mensagem.lower() and "inválid" in mensagem.lower()
                )
                if sessao_remota_invalida and not estado_watchdog["relogin_em_andamento"]:
                    estado_watchdog["relogin_em_andamento"] = True
                    _LOGGER_DESKTOP.info(
                        "Sessão remota indisponível; retornando ao login",
                        extra={"evento": "remote_session_reauthentication_required", "componente": "desktop"},
                    )
                    SESSAO.encerrar()
                    abrir_login("A sessão do servidor terminou. Entre novamente para continuar.")
                    return
                if not estado_watchdog["aviso_preferencia_emitido"]:
                    estado_watchdog["aviso_preferencia_emitido"] = True
                    _LOGGER_DESKTOP.warning(
                        "Não foi possível atualizar preferência de sessão; usando 30 minutos",
                        extra={
                            "evento": "session_preferences_unavailable",
                            "componente": "desktop",
                            "erro_operacional": mensagem,
                        },
                    )
            else:
                estado_watchdog["aviso_preferencia_emitido"] = False
                estado_watchdog["relogin_em_andamento"] = False
            if SESSAO.autenticado() and not SESSAO.validar():
                abrir_login(
                    "Sua sessão foi revogada porque credenciais, perfil ou status foram alterados. Entre novamente."
                )
            elif SESSAO.expirada(minutos):
                SESSAO.encerrar()
                abrir_login(
                    "Sua sessão expirou por inatividade. Entre novamente."
                )
        except tk.TclError:
            return
        finally:
            try:
                if janela.winfo_exists():
                    janela.after(30_000, verificar_expiracao_sessao)
            except tk.TclError:
                pass

    janela.bind_all("<KeyPress>", registrar_atividade, add="+")
    janela.bind_all("<Button>", registrar_atividade, add="+")
    janela.bind_all("<Control-k>", abrir_busca, add="+")
    janela.bind_all("<Control-K>", abrir_busca, add="+")
    janela.after(30_000, verificar_expiracao_sessao)

    # Em modo Server First, a Central apenas solicita o backup ao Servidor
    # Corporativo. A estação não mantém banco empresarial local.
    backup_em_execucao = {"valor": False}

    def sincronizar_backup_servidor():
        try:
            cfg = carregar_config_nodo()
            intervalo_ms = max(5, cfg.intervalo_backup_minutos) * 60_000
        except (ValueError, RuntimeError, OSError) as erro:
            _LOGGER_DESKTOP.warning(
                "Configuração do backup corporativo indisponível",
                extra={
                    "evento": "backup_config_unavailable",
                    "componente": "desktop",
                    "erro_operacional": str(erro),
                },
            )
            intervalo_ms = 5 * 60_000
            cfg = None
        if cfg is not None and cfg.papel == "central" and cfg.sincronizar_backups and SESSAO.autenticado() and SESSAO.eh_admin() and not backup_em_execucao["valor"]:
            backup_em_execucao["valor"] = True
            ator = dict(SESSAO.usuario)
            ator["_empresa_id"] = SESSAO.empresa_id
            ator["_filial_id"] = SESSAO.filial_id
            def trabalho():
                try:
                    from enterprise.backups import criar_backup
                    criar_backup(ator)
                except Exception as erro:
                    # Backup agendado é best-effort. Em modo remoto ele é criado
                    # diretamente no Servidor Corporativo; nunca há fallback para
                    # qualquer backup persistente na estação.
                    _LOGGER_DESKTOP.exception(
                        "Backup corporativo agendado falhou",
                        extra={"evento": "scheduled_backup_failed", "erro_operacional": str(erro)},
                    )
                finally:
                    backup_em_execucao["valor"] = False
            threading.Thread(target=trabalho, name="Corporate-Backup-Sync", daemon=True).start()
        try:
            janela.after(intervalo_ms, sincronizar_backup_servidor)
        except tk.TclError:
            pass

    janela.after(60_000, sincronizar_backup_servidor)

    if usa_servidor_remoto():
        abrir_login("Conecte-se com a conta corporativa criada pelo administrador.")
    elif tem_usuarios():
        abrir_login()
    else:
        limpar_janela()
        TelaPrimeiroAcesso(janela, concluir_autenticacao)

    janela.mainloop()


if __name__ == "__main__":
    main()
