"""Ponto de entrada da aplicação."""

import tkinter as tk

from auth.banco import inicializar_banco, tem_usuarios
from auth.sessao import SESSAO
from interface.app import AplicacaoAutomacao
from interface.login import TelaLogin
from interface.nova_analise import TelaNovaAnalise
from interface.primeiro_acesso import TelaPrimeiroAcesso
from interface.principal import TelaPrincipal
from interface.usuarios import TelaUsuarios


def main() -> None:
    janela = tk.Tk()
    janela.title("Data Analytics Platform")
    janela.geometry("1200x760")
    janela.minsize(1000, 650)
    janela.configure(bg="#0F172A")

    inicializar_banco()

    def abrir_aplicacao(configuracao=None):
        AplicacaoAutomacao(
            janela,
            configuracao_analise=configuracao,
        )

    def abrir_nova_analise():
        TelaNovaAnalise(
            janela,
            executar_analise=abrir_aplicacao,
            voltar=abrir_principal,
        )

    def sair_da_sessao():
        SESSAO.encerrar()
        abrir_login()

    def abrir_usuarios():
        TelaUsuarios(
            janela,
            voltar=abrir_principal,
        )

    def abrir_principal():
        TelaPrincipal(
            janela,
            abrir_analise=abrir_nova_analise,
            sair=sair_da_sessao,
            abrir_usuarios=abrir_usuarios,
        )

    def abrir_login():
        TelaLogin(
            janela,
            abrir_principal,
        )

    if tem_usuarios():
        abrir_login()
    else:
        TelaPrimeiroAcesso(
            janela,
            abrir_principal,
        )

    janela.mainloop()


if __name__ == "__main__":
    main()
