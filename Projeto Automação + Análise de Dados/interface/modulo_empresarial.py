"""Fachada do cadastro operacional empresarial V9.8."""
from interface.modulo_empresarial_shared import *
from interface.modulo_empresarial_tabela import ModuloEmpresarialTabelaMixin
from interface.modulo_empresarial_formularios import ModuloEmpresarialFormulariosMixin

class TelaModuloEmpresarial(ModuloEmpresarialTabelaMixin, ModuloEmpresarialFormulariosMixin):
    def __init__(self, root, navegacao, modulo):
        self.root = root
        self.navegacao = navegacao
        self.modulo = modulo
        self.configuracao = obter_modulo(modulo)
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            raise PermissionError("Seu perfil não possui acesso a este módulo.")
        self.registros = []
        self.pagina = 1
        self.paginas = 1
        self.total = 0
        self.ordenar_por = "id"
        self.direcao = "DESC"
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()
        self.carregar()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        itens_modulo = tuple(
            (
                chave,
                icone,
                titulo,
                (
                    None
                    if chave == "registros"
                    else lambda destino=chave: self.navegacao["secao_modulo"](
                        self.modulo, destino
                    )
                ),
            )
            for chave, icone, titulo in PAINEIS_MODULOS[self.modulo]["menu"]
        )
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="registros",
            itens_customizados=itens_modulo,
            titulo_customizado=self.configuracao["nome"].upper(),
            rodape_texto="Voltar ao painel do módulo",
            rodape_comando=lambda: self.navegacao["modulo"](self.modulo),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(26, 22),
        )
        conteudo = viewport.conteudo
        self._cabecalho(conteudo)
        self.area_cards = tk.Frame(conteudo, bg=CORES["bg"])
        self.area_cards.pack(fill="x", pady=(0, 16))
        self._tabela(conteudo)
