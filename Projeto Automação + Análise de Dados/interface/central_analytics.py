"""Central Analytics — Inteligência Empresarial V10.4.x."""
from interface.central_analytics_shared import *
from interface.central_analytics_inteligencia import CentralAnalyticsInteligenciaMixin
from interface.central_analytics_datasets import CentralAnalyticsDatasetsMixin
from interface.central_analytics_recursos import CentralAnalyticsRecursosMixin


class TelaCentralAnalytics(CentralAnalyticsInteligenciaMixin, CentralAnalyticsDatasetsMixin, CentralAnalyticsRecursosMixin):
    _ALIASES_LEGADOS = {
        "dashboard": "visao", "modelos": "regras", "assistente": "insights", "perfis": "conjuntos",
    }

    def __init__(self, root, navegacao, secao="visao"):
        self.root=root; self.navegacao=navegacao
        self.secao=self._ALIASES_LEGADOS.get(str(secao or "visao"), str(secao or "visao"))
        self._ativa=True
        self.container=tk.Frame(root,bg=CORES["bg"]); self.container.pack(fill="both",expand=True)
        self.container.bind("<Destroy>",self._ao_destruir,add="+"); self.criar_interface()

    def _ao_destruir(self,evento):
        if evento.widget is self.container: self._ativa=False

    def criar_interface(self):
        criar_sidebar_analytics(self.container,self.navegacao,ativo=self.secao,voltar=self.navegacao.get("modulos"))
        viewport=AreaRolavel(self.container); viewport.pack(side="left",fill="both",expand=True,padx=LAYOUT["conteudo_padx"],pady=(24,22))
        conteudo=viewport.conteudo
        if self.secao == "visao": self._visao_executiva(conteudo)
        elif self.secao == "insights": self._insights_empresariais(conteudo)
        elif self.secao == "alertas": self._insights_empresariais(conteudo, somente_alertas=True)
        elif self.secao == "regras": self._regras_analiticas(conteudo)
        elif self.secao in {"importacoes","conjuntos"}: self._biblioteca_dados(conteudo)
        else: self._recurso_analytics(conteudo)

    def abrir_secao(self,secao):
        secao=self._ALIASES_LEGADOS.get(str(secao),str(secao))
        if secao == "nova": self.navegacao["nova"](); return
        self.container.destroy(); TelaCentralAnalytics(self.root,self.navegacao,secao=secao)
