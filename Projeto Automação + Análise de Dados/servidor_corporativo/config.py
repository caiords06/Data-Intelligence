"""Configuração do servidor corporativo instalável."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import ipaddress
import json
import os
from pathlib import Path
from urllib.parse import urlparse


def _loopback(host: str) -> bool:
    texto = str(host or "").strip().strip("[]").lower()
    if texto in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(texto).is_loopback
    except ValueError:
        return False


def pasta_servidor() -> Path:
    override = str(os.environ.get("DATA_INTELLIGENCE_SERVER_DATA_DIR", "")).strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "DataIntelligence" / "Server"
    return Path.home() / ".local" / "state" / "data-intelligence-server"


@dataclass(frozen=True, slots=True)
class ConfigServidor:
    host: str = "127.0.0.1"
    porta: int = 8770
    tls: bool = False
    certificado: str | None = None
    chave_privada: str | None = None
    max_upload_mb: int = 1024
    ambiente: str = "producao"
    db_backend: str = "postgresql"
    postgres_host: str = "127.0.0.1"
    postgres_porta: int = 5432
    postgres_banco: str = "dataintelligence"
    postgres_usuario: str = "dataintelligence"
    postgres_sslmode: str = "prefer"
    postgres_pool_min: int = 2
    postgres_pool_max: int = 12
    postgres_segredo: str | None = None
    # Origens Web autorizadas para CORS. Vazio = somente mesma origem.
    cors_origins: tuple[str, ...] = ()

    def validar(self) -> "ConfigServidor":
        host = str(self.host or "").strip()
        if not host:
            raise ValueError("Host inválido.")
        porta = int(self.porta)
        if not 1024 <= porta <= 65535:
            raise ValueError("A porta deve ficar entre 1024 e 65535.")
        max_upload = max(10, min(int(self.max_upload_mb), 4096))
        ambiente = str(self.ambiente or "lan").strip().lower()
        if ambiente not in {"desenvolvimento", "lan", "producao"}:
            raise ValueError("Ambiente deve ser desenvolvimento, lan ou producao.")
        laboratorio_inseguro = (
            ambiente == "desenvolvimento"
            and os.environ.get("DATA_INTELLIGENCE_ALLOW_INSECURE_LAB") == "1"
        )
        if not _loopback(host) and not self.tls and not laboratorio_inseguro:
            raise ValueError(
                "Em produção ou LAN corporativa, qualquer bind fora de loopback exige TLS. Publique em HTTPS com certificado/chave "
                "ou mantenha o servidor em 127.0.0.1 atrás de um proxy reverso HTTPS. "
                "HTTP externo existe somente em desenvolvimento isolado com autorização explícita de laboratório."
            )
        if self.tls:
            if not self.certificado or not Path(self.certificado).is_file():
                raise ValueError("Certificado TLS não encontrado.")
            if not self.chave_privada or not Path(self.chave_privada).is_file():
                raise ValueError("Chave privada TLS não encontrada.")
        db_backend = str(self.db_backend or "postgresql").strip().lower()
        if db_backend in {"postgres", "pg"}:
            db_backend = "postgresql"
        if db_backend != "postgresql":
            raise ValueError(
                "O Servidor Corporativo V11.1.0 aceita somente PostgreSQL. "
                "SQLite pode ser usado apenas por ferramentas offline de migração/teste, nunca como backend do servidor."
            )
        pg_host = str(self.postgres_host or "127.0.0.1").strip()
        pg_porta = int(self.postgres_porta or 5432)
        pg_banco = str(self.postgres_banco or "dataintelligence").strip()
        pg_usuario = str(self.postgres_usuario or "dataintelligence").strip()
        pg_sslmode = str(self.postgres_sslmode or "prefer").strip().lower()
        pg_pool_min = max(1, min(int(self.postgres_pool_min or 2), 50))
        pg_pool_max = max(pg_pool_min, min(int(self.postgres_pool_max or 12), 100))
        if db_backend == "postgresql":
            if not pg_host or not pg_banco or not pg_usuario:
                raise ValueError("PostgreSQL exige host, banco e usuário.")
            if not 1 <= pg_porta <= 65535:
                raise ValueError("Porta PostgreSQL inválida.")
            if pg_sslmode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
                raise ValueError("sslmode PostgreSQL inválido.")
            if not _loopback(pg_host) and pg_sslmode not in {"require", "verify-ca", "verify-full"} and not laboratorio_inseguro:
                raise ValueError(
                    "PostgreSQL remoto exige sslmode=require, verify-ca ou verify-full."
                )
            if not self.postgres_segredo:
                raise ValueError("A referência do segredo PostgreSQL não foi configurada.")
        cors_origins: list[str] = []
        for origem in self.cors_origins or ():
            origem = str(origem or "").strip().rstrip("/")
            if not origem:
                continue
            if origem == "*":
                if ambiente == "producao":
                    raise ValueError("CORS '*' não é permitido em produção; informe origens explícitas.")
                cors_origins.append(origem)
                continue
            parsed = urlparse(origem)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
                raise ValueError(f"Origem CORS inválida: {origem}")
            normalizada = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
            if normalizada not in cors_origins:
                cors_origins.append(normalizada)
        return ConfigServidor(
            host=host, porta=porta, tls=bool(self.tls),
            certificado=self.certificado, chave_privada=self.chave_privada,
            max_upload_mb=max_upload, ambiente=ambiente,
            db_backend=db_backend, postgres_host=pg_host, postgres_porta=pg_porta,
            postgres_banco=pg_banco, postgres_usuario=pg_usuario, postgres_sslmode=pg_sslmode,
            postgres_pool_min=pg_pool_min, postgres_pool_max=pg_pool_max,
            postgres_segredo=self.postgres_segredo,
            cors_origins=tuple(cors_origins),
        )


def caminho_config() -> Path:
    return pasta_servidor() / "server.json"


def _ler_config_bruta() -> ConfigServidor:
    """Lê server.json sem exigir que o bootstrap PostgreSQL já esteja concluído.

    O Setup V11.1.0 podia deixar um ``server.json`` parcial antes de gravar o
    segredo PostgreSQL. Esse estado é inválido para execução normal, mas precisa
    ser recuperável pelo próprio comando ``configure-db`` para que uma nova
    instalação consiga se autocorrigir sem intervenção manual em ProgramData.
    """
    p = caminho_config()
    if not p.is_file():
        return ConfigServidor()
    try:
        dados = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Configuração do servidor inválida em {p}.") from exc
    if not isinstance(dados, dict):
        raise ValueError(f"Configuração do servidor inválida em {p}: o JSON deve ser um objeto.")
    permitidos = set(ConfigServidor.__dataclass_fields__)
    try:
        return ConfigServidor(**{k: v for k, v in dados.items() if k in permitidos})
    except TypeError as exc:
        raise ValueError(f"Configuração do servidor inválida em {p}: {exc}") from exc


def carregar_config_parcial() -> ConfigServidor:
    """Configuração não validada, exclusiva para bootstrap/recuperação do Setup."""
    return _ler_config_bruta()


def carregar_config() -> ConfigServidor:
    config = _ler_config_bruta()
    if not caminho_config().is_file():
        return config
    try:
        return config.validar()
    except ValueError as exc:
        # Falhar fechado: uma configuração explicitamente gravada como produção
        # nunca pode cair silenciosamente para o padrão LAN sem TLS.
        raise ValueError(f"Configuração do servidor rejeitada em {caminho_config()}: {exc}") from exc


def salvar_config(config: ConfigServidor) -> Path:
    config = config.validar()
    p = caminho_config()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def caminho_segredo_postgresql() -> Path:
    return pasta_servidor() / "secrets" / "postgres.dpapi"


def aplicar_ambiente_banco(config: ConfigServidor) -> None:
    """Publica a configuração do backend apenas dentro do processo servidor."""
    import os
    os.environ["DATA_INTELLIGENCE_DB_BACKEND"] = config.db_backend
    if config.db_backend != "postgresql":
        return
    referencia = str(config.postgres_segredo or "").strip()
    if referencia.startswith("env:"):
        nome_var = referencia.split(":", 1)[1] or "DATA_INTELLIGENCE_PG_PASSWORD"
        senha = str(os.environ.get(nome_var, ""))
        if not senha:
            raise FileNotFoundError(f"Variável de segredo PostgreSQL não definida: {nome_var}")
    else:
        from core.segredos import carregar_segredo_maquina
        segredo = Path(referencia or caminho_segredo_postgresql())
        senha = carregar_segredo_maquina(segredo, variavel_ambiente="DATA_INTELLIGENCE_PG_PASSWORD")
    os.environ["DATA_INTELLIGENCE_PG_HOST"] = config.postgres_host
    os.environ["DATA_INTELLIGENCE_PG_PORT"] = str(config.postgres_porta)
    os.environ["DATA_INTELLIGENCE_PG_DATABASE"] = config.postgres_banco
    os.environ["DATA_INTELLIGENCE_PG_USER"] = config.postgres_usuario
    os.environ["DATA_INTELLIGENCE_PG_SSLMODE"] = config.postgres_sslmode
    os.environ["DATA_INTELLIGENCE_PG_POOL_MIN"] = str(config.postgres_pool_min)
    os.environ["DATA_INTELLIGENCE_PG_POOL_MAX"] = str(config.postgres_pool_max)
    os.environ["DATA_INTELLIGENCE_PG_PASSWORD"] = senha
