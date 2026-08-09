"""Estado da sessão autenticada em memória."""


class Sessao:
    def __init__(self):
        self.usuario = None

    def iniciar(self, usuario):
        self.usuario = usuario

    def encerrar(self):
        self.usuario = None

    def autenticado(self):
        return self.usuario is not None

    def eh_admin(self):
        return bool(self.usuario and self.usuario.get("perfil") == "admin")


SESSAO = Sessao()
