"""Fachada visual especializada de TelaRH, componentizada na V9.7."""

from interface.rh_shared import *  # noqa: F401,F403
from interface.rh_views import TelaRHViewsMixin
from interface.rh_acoes import TelaRHAcoesMixin


class TelaRH(TelaRHViewsMixin, TelaRHAcoesMixin):
        def __init__(self, root, navegacao, secao="visao"):
            self.root = root
            self.navegacao = navegacao
            self.secao = secao if secao in ROTULOS else "visao"
            self.tabela = None
            self.estado_vazio = None
            self.registros = []
            if not tem_permissao(SESSAO.usuario, "rh", "ler"):
                raise PermissionError("Seu perfil não possui acesso aos Recursos Humanos.")
            self.container = tk.Frame(root, bg=CORES["bg"])
            self.container.pack(fill="both", expand=True)
            self._criar_interface()

        def _criar_interface(self):
            configurar_estilos_ttk(self.root)
            criar_sidebar_modulo(
                self.container,
                self.navegacao,
                modulo="rh",
                titulo="RECURSOS HUMANOS",
                ativo=self.secao,
                grupos_menu=GRUPOS_MENU,
                grupos_recolhiveis=True,
            )
            viewport = AreaRolavel(self.container)
            viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
            self.conteudo = viewport.conteudo
            renderizadores = {
                "visao": self._visao,
                "relatorios": self._relatorios,
                "auditoria": self._auditoria,
                "configuracoes": self._configuracoes,
            }
            renderizadores.get(self.secao, self._secao_operacional)()

        def abrir_secao(self, secao):
            callback = self.navegacao.get("secao_modulo")
            if callable(callback):
                callback("rh", secao)
                return
            self.container.destroy()
            TelaRH(self.root, self.navegacao, secao=secao)

