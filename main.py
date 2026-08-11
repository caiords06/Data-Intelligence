"""Ponto de entrada e roteador central da plataforma empresarial V9.1."""

import sys
import threading
import tkinter as tk
from tkinter import messagebox

from auth.banco import inicializar_banco, tem_usuarios
from auth.sessao import SESSAO
from configuracoes.preferencias import carregar_preferencias
from core.nodo import carregar_config_nodo, cliente_convencional, usa_servidor_remoto
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
from interface.modulo_empresarial import TelaModuloEmpresarial
from interface.nova_analise import TelaNovaAnalise
from interface.notificacoes import TelaNotificacoes
from interface.organizacao import TelaOrganizacao
from interface.operacoes_visuais import TelaOperacaoVisual
from interface.painel_modulo import TelaPainelModulo
from interface.perfis_analise import TelaPerfisAnalise
from interface.primeiro_acesso import TelaPrimeiroAcesso
from interface.principal import TelaPrincipal
from interface.tema import CORES, configurar_estilos_ttk
from interface.usuarios import TelaUsuarios
from servidor_ti import iniciar_servidor_embutido


def main() -> None:
    janela = tk.Tk()
    janela.title("Data Intelligence · Enterprise Platform · V9.1")
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

    inicializar_banco()
    limpar_temporarios_antigos()
    inicializar_historico()
    inicializar_enterprise()
    config_nodo = carregar_config_nodo()
    # Em modo conectado, o receptor de agentes vive no Servidor Corporativo.
    # A estação Central não abre uma segunda autoridade/banco local na porta 8765.
    if config_nodo.papel == "standalone":
        iniciar_servidor_embutido()
    configurar_estilos_ttk(janela)

    def limpar_janela():
        janela.protocol("WM_DELETE_WINDOW", janela.destroy)
        for componente in janela.winfo_children():
            try:
                componente.destroy()
            except tk.TclError:
                pass

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
            "organizacao": abrir_organizacao,
            "perfis": abrir_perfis,
            "usuarios": abrir_usuarios,
            "busca": abrir_busca,
            "ferramenta": abrir_ferramenta,
            "sair": sair_da_sessao,
        }

    def preparar_tela():
        garantir_contexto_sessao()
        limpar_janela()

    def abrir_principal():
        preparar_tela()
        TelaPrincipal(janela, mapa_navegacao())

    def abrir_modulos():
        preparar_tela()
        TelaCatalogoModulos(janela, mapa_navegacao())

    def abrir_modulo(modulo):
        # Tecnologia expõe um portal público de suporte a qualquer usuário
        # autenticado. A própria TelaTecnologia restringe as áreas operacionais
        # quando o perfil não possui permissão técnica.
        if modulo != "ti" and not tem_permissao(SESSAO.usuario, modulo, "ler"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui acesso a este módulo.",
                parent=janela,
            )
            abrir_modulos()
            return
        preparar_tela()
        if modulo == "ti":
            TelaTecnologia(janela, mapa_navegacao())
        else:
            TelaExperienciaDepartamental(janela, mapa_navegacao(), modulo)

    def abrir_secao_modulo(modulo, secao="visao"):
        if modulo != "ti" and not tem_permissao(SESSAO.usuario, modulo, "ler"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui acesso a este módulo.",
                parent=janela,
            )
            abrir_modulos()
            return
        preparar_tela()
        if secao == "visao" and modulo != "ti":
            TelaExperienciaDepartamental(janela, mapa_navegacao(), modulo)
        elif modulo == "financeiro":
            TelaFinanceiro(janela, mapa_navegacao(), secao=secao)
        elif modulo == "compras":
            TelaCompras(janela, mapa_navegacao(), secao=secao)
        elif modulo == "rh":
            TelaRH(janela, mapa_navegacao(), secao=secao)
        elif modulo == "estoque":
            TelaEstoque(janela, mapa_navegacao(), secao=secao)
        elif modulo == "ti":
            TelaTecnologia(janela, mapa_navegacao(), secao=secao)
        elif modulo in {"marketing", "administrativo", "juridico", "comercial"} and secao in {
            "registros", "calendario", "automacao", "conteudo",
            "facilities", "viagens", "reembolsos", "veiculos", "salas",
            "processos", "prazos", "audiencias", "riscos",
            "crm", "pipeline", "propostas", "metas",
        }:
            TelaOperacaoVisual(janela, mapa_navegacao(), modulo, secao=secao)
        else:
            # Grade tabular somente nas áreas em que comparação por linhas/colunas
            # é parte natural do trabalho (leads, clientes, documentos, relatórios etc.).
            TelaPainelModulo(janela, mapa_navegacao(), modulo, secao=secao)

    def abrir_registros_modulo(modulo):
        if modulo != "ti" and not tem_permissao(SESSAO.usuario, modulo, "ler"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui acesso a este módulo.",
                parent=janela,
            )
            abrir_modulos()
            return
        preparar_tela()
        if modulo == "financeiro":
            TelaFinanceiro(janela, mapa_navegacao(), secao="lancamentos")
        elif modulo == "compras":
            TelaCompras(janela, mapa_navegacao(), secao="solicitacoes")
        elif modulo == "rh":
            TelaRH(janela, mapa_navegacao(), secao="colaboradores")
        elif modulo == "estoque":
            TelaEstoque(janela, mapa_navegacao(), secao="itens")
        elif modulo == "ti":
            secao_ti = "chamados" if tem_permissao(SESSAO.usuario, "ti", "ler") else "meus_chamados"
            TelaTecnologia(janela, mapa_navegacao(), secao=secao_ti)
        elif modulo in {"marketing", "administrativo", "juridico", "comercial"}:
            TelaOperacaoVisual(janela, mapa_navegacao(), modulo, secao="registros")
        else:
            TelaModuloEmpresarial(janela, mapa_navegacao(), modulo)

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

    def abrir_login(mensagem=None):
        limpar_janela()
        TelaLogin(janela, abrir_principal, mensagem_inicial=mensagem)

    def sair_da_sessao():
        if usa_servidor_remoto():
            try:
                from enterprise.servidor_cliente import encerrar_sessao_remota
                encerrar_sessao_remota()
            except Exception:
                pass
        SESSAO.encerrar()
        abrir_login("Sessão encerrada com segurança.")

    def registrar_atividade(_evento=None):
        SESSAO.registrar_atividade()

    def verificar_expiracao_sessao():
        try:
            minutos = carregar_preferencias()["tempo_sessao_minutos"]
            if SESSAO.expirada(minutos):
                SESSAO.encerrar()
                abrir_login(
                    "Sua sessão expirou por inatividade. Entre novamente."
                )
            janela.after(30_000, verificar_expiracao_sessao)
        except tk.TclError:
            return

    janela.bind_all("<KeyPress>", registrar_atividade, add="+")
    janela.bind_all("<Button>", registrar_atividade, add="+")
    janela.bind_all("<Control-k>", abrir_busca, add="+")
    janela.bind_all("<Control-K>", abrir_busca, add="+")
    janela.after(30_000, verificar_expiracao_sessao)

    # Sincronização de segurança: a estação Central mantém cópia local e envia
    # backups completos ao Servidor Corporativo sem bloquear a interface.
    backup_em_execucao = {"valor": False}

    def sincronizar_backup_servidor():
        cfg = carregar_config_nodo()
        intervalo_ms = max(5, cfg.intervalo_backup_minutos) * 60_000
        if cfg.papel == "central" and cfg.sincronizar_backups and SESSAO.autenticado() and SESSAO.eh_admin() and not backup_em_execucao["valor"]:
            backup_em_execucao["valor"] = True
            ator = dict(SESSAO.usuario)
            ator["_empresa_id"] = SESSAO.empresa_id
            ator["_filial_id"] = SESSAO.filial_id
            def trabalho():
                try:
                    from enterprise.backups import criar_backup
                    from enterprise.servidor_cliente import enviar_backup
                    resultado = criar_backup(ator, sincronizar_servidor=False)
                    enviar_backup(resultado["arquivo"])
                except Exception:
                    # Sincronização é resiliente: a cópia local continua válida e
                    # nova tentativa será feita no próximo ciclo.
                    pass
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
        TelaPrimeiroAcesso(janela, abrir_principal)

    janela.mainloop()


if __name__ == "__main__":
    main()
