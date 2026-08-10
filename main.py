"""Ponto de entrada e roteador central da plataforma empresarial V7."""

import tkinter as tk
from tkinter import messagebox

from auth.banco import inicializar_banco, tem_usuarios
from auth.sessao import SESSAO
from configuracoes.preferencias import carregar_preferencias
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
from interface.historico import TelaHistorico
from interface.login import TelaLogin
from interface.modulo_empresarial import TelaModuloEmpresarial
from interface.nova_analise import TelaNovaAnalise
from interface.notificacoes import TelaNotificacoes
from interface.organizacao import TelaOrganizacao
from interface.painel_modulo import TelaPainelModulo
from interface.perfis_analise import TelaPerfisAnalise
from interface.primeiro_acesso import TelaPrimeiroAcesso
from interface.principal import TelaPrincipal
from interface.tema import CORES, configurar_estilos_ttk
from interface.usuarios import TelaUsuarios


def main() -> None:
    janela = tk.Tk()
    janela.title("Data Intelligence · Enterprise Platform · V7")
    janela.geometry("1440x900")
    janela.minsize(1180, 740)
    janela.configure(bg=CORES["bg"])

    inicializar_banco()
    inicializar_historico()
    inicializar_enterprise()
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
            "nova": abrir_nova_analise,
            "historico": abrir_historico,
            "aprovacoes": abrir_aprovacoes,
            "notificacoes": abrir_notificacoes,
            "configuracoes": abrir_configuracoes,
            "organizacao": abrir_organizacao,
            "perfis": abrir_perfis,
            "usuarios": abrir_usuarios,
            "busca": abrir_busca,
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
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui acesso a este módulo.",
                parent=janela,
            )
            abrir_modulos()
            return
        preparar_tela()
        TelaPainelModulo(janela, mapa_navegacao(), modulo)

    def abrir_secao_modulo(modulo, secao="visao"):
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui acesso a este módulo.",
                parent=janela,
            )
            abrir_modulos()
            return
        preparar_tela()
        TelaPainelModulo(janela, mapa_navegacao(), modulo, secao=secao)

    def abrir_registros_modulo(modulo):
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            messagebox.showerror(
                "Acesso negado",
                "Seu perfil não possui acesso a este módulo.",
                parent=janela,
            )
            abrir_modulos()
            return
        preparar_tela()
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

    def abrir_login(mensagem=None):
        limpar_janela()
        TelaLogin(janela, abrir_principal, mensagem_inicial=mensagem)

    def sair_da_sessao():
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

    if tem_usuarios():
        abrir_login()
    else:
        limpar_janela()
        TelaPrimeiroAcesso(janela, abrir_principal)

    janela.mainloop()


if __name__ == "__main__":
    main()
