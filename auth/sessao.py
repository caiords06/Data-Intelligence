"""Estado e tempo de atividade da sessão autenticada em memória."""

from datetime import datetime, timedelta, timezone


class Sessao:
    def __init__(self):
        self.usuario = None
        self.iniciada_em = None
        self.ultima_atividade = None
        self.empresa_id = None
        self.filial_id = None
        self.empresas_criadas_sessao = set()

    def iniciar(self, usuario):
        agora = datetime.now(timezone.utc)
        self.usuario = usuario
        self.iniciada_em = agora
        self.ultima_atividade = agora
        self.empresa_id = None
        self.filial_id = None
        self.empresas_criadas_sessao = set()

    def definir_contexto_empresarial(self, empresa_id, filial_id=None):
        self.empresa_id = int(empresa_id) if empresa_id is not None else None
        self.filial_id = int(filial_id) if filial_id is not None else None

    def registrar_empresa_criada(self, empresa_id):
        if self.usuario is not None and empresa_id is not None:
            self.empresas_criadas_sessao.add(int(empresa_id))

    def empresa_criada_na_sessao(self, empresa_id) -> bool:
        try:
            return int(empresa_id) in self.empresas_criadas_sessao
        except (TypeError, ValueError):
            return False

    def descartar_empresa_criada(self, empresa_id):
        try:
            self.empresas_criadas_sessao.discard(int(empresa_id))
        except (TypeError, ValueError):
            return

    def registrar_atividade(self):
        if self.usuario is not None:
            self.ultima_atividade = datetime.now(timezone.utc)

    def expirada(self, minutos: int = 30) -> bool:
        if self.usuario is None or self.ultima_atividade is None:
            return False
        limite = datetime.now(timezone.utc) - timedelta(minutes=max(1, minutos))
        return self.ultima_atividade < limite

    def encerrar(self):
        self.usuario = None
        self.iniciada_em = None
        self.ultima_atividade = None
        self.empresa_id = None
        self.filial_id = None
        self.empresas_criadas_sessao = set()

    def autenticado(self):
        return self.usuario is not None

    def eh_admin(self):
        return bool(self.usuario and self.usuario.get("perfil") == "admin")


SESSAO = Sessao()
