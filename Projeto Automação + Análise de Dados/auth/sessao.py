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
        try:
            from core.nodo import usa_servidor_remoto
            if usa_servidor_remoto():
                from enterprise.servidor_cliente import contexto_memoria
                bootstrap = contexto_memoria()
                empresa = dict(bootstrap.get("empresa") or {})
                if empresa.get("id") is not None:
                    self.empresa_id = int(empresa["id"])
                if bootstrap.get("filial_id") is not None:
                    self.filial_id = int(bootstrap["filial_id"])
        except (RuntimeError, ValueError, TypeError):
            # A sessão permanece em memória; a próxima operação remota falhará
            # explicitamente se a configuração do servidor estiver inválida.
            pass

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

    def validar(self) -> bool:
        """Confirma se a sessão em memória continua válida na autoridade configurada.

        Alterações de senha, perfil ou status incrementam ``sessao_epoch``.
        Quando o epoch diverge, a sessão é encerrada imediatamente para que
        todas as telas usem a mesma regra de revogação.
        """
        if self.usuario is None:
            return False
        try:
            from core.nodo import usa_servidor_remoto
            if usa_servidor_remoto():
                from enterprise.servidor_cliente import validar_sessao_remota
                payload = validar_sessao_remota()
                remoto = dict(payload.get("usuario") or {})
                if not remoto or not bool(remoto.get("ativo", True)):
                    self.encerrar()
                    return False
                # O servidor é a autoridade do epoch/perfil; mantenha a sessão
                # em memória alinhada ao bootstrap mais recente.
                self.usuario.update(remoto)
                empresa = dict(payload.get("empresa") or {})
                if empresa.get("id") is not None:
                    self.empresa_id = int(empresa["id"])
                self.filial_id = (
                    int(payload["filial_id"])
                    if payload.get("filial_id") is not None else None
                )
                return True

            from auth.banco import buscar_usuario_por_id
            registro = buscar_usuario_por_id(int(self.usuario["id"]))
        except PermissionError:
            self.encerrar()
            return False
        except (KeyError, TypeError, ValueError):
            # Indisponibilidade temporária do servidor não cria fallback local.
            # A sessão permanece em memória; qualquer
            # operação remota continuará falhando de forma explícita.
            if self.usuario is not None:
                return True
            self.encerrar()
            return False
        if registro is None or not bool(registro["ativo"]):
            self.encerrar()
            return False
        epoch_banco = int(registro["sessao_epoch"] or 0)
        epoch_sessao = int(self.usuario.get("sessao_epoch", 0) or 0)
        if epoch_banco != epoch_sessao:
            self.encerrar()
            return False
        return True

    def eh_admin(self):
        return bool(self.usuario and self.usuario.get("perfil") == "admin")


SESSAO = Sessao()
