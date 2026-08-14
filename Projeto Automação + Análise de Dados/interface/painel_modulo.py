"""Fachada do painel departamental V9.8."""
from interface.painel_modulo_shared import *
from interface.painel_modulo_visao import PainelModuloVisaoMixin
from interface.painel_modulo_operacoes import PainelModuloOperacoesMixin

class TelaPainelModulo(PainelModuloVisaoMixin, PainelModuloOperacoesMixin):
    def __init__(self, root, navegacao, modulo, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.modulo = modulo
        self.secao = secao
        self.modulo_config = obter_modulo(modulo)
        self.ui = PAINEIS_MODULOS[modulo]
        self.cor = self.modulo_config["cor"]
        self.pagina = 1
        self.paginas = 1
        self.registros: list[dict] = []
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            raise PermissionError("Seu perfil não possui acesso a este módulo.")
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_modulo(
            self.container,
            self.navegacao,
            modulo=self.modulo,
            titulo=self.modulo_config["nome"].upper(),
            ativo=self.secao,
            itens_menu=self.ui["menu"],
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(22, 20),
        )
        conteudo = viewport.conteudo
        if self.secao == "visao":
            self._visao_geral(conteudo)
        else:
            self._secao_operacional(conteudo)

    def abrir_secao(self, secao):
        callback = self.navegacao.get("secao_modulo")
        if callable(callback):
            callback(self.modulo, secao)
            return
        self.container.destroy()
        TelaPainelModulo(self.root, self.navegacao, self.modulo, secao)
