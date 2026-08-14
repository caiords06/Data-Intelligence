"""Fachada visual especializada de TelaEstoque, componentizada na V9.7."""

from interface.estoque_shared import *  # noqa: F401,F403
from interface.estoque_views import TelaEstoqueViewsMixin
from interface.estoque_acoes import TelaEstoqueAcoesMixin


class TelaEstoque(TelaEstoqueViewsMixin, TelaEstoqueAcoesMixin):
        def __init__(self, root, navegacao, secao="visao"):
            self.root = root
            self.navegacao = navegacao
            self.secao = secao if secao in ROTULOS else "visao"
            self.tabela = None
            self.registros = []
            if not tem_permissao(SESSAO.usuario, "estoque", "ler"):
                raise PermissionError("Seu perfil não possui acesso ao Estoque.")
            self.container = tk.Frame(root, bg=CORES["bg"])
            self.container.pack(fill="both", expand=True)
            self._criar_interface()

        def _criar_interface(self):
            configurar_estilos_ttk(self.root)
            criar_sidebar_modulo(
                self.container,
                self.navegacao,
                modulo="estoque",
                titulo="ESTOQUE",
                ativo=self.secao,
                grupos_menu=GRUPOS_MENU,
                grupos_recolhiveis=True,
            )
            viewport = AreaRolavel(self.container)
            viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
            self.conteudo = viewport.conteudo
            renderizadores = {
                "visao": self._visao, "relatorios": self._relatorios,
                "auditoria": self._auditoria, "configuracoes": self._configuracoes,
            }
            renderizadores.get(self.secao, self._secao_operacional)()

        def abrir_secao(self, secao):
            callback = self.navegacao.get("secao_modulo")
            if callable(callback):
                callback("estoque", secao)
                return
            self.container.destroy()
            TelaEstoque(self.root, self.navegacao, secao=secao)

