"""Configuração do servidor corporativo instalável."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path


def pasta_servidor() -> Path:
    override = str(os.environ.get("DATA_INTELLIGENCE_SERVER_DATA_DIR", "")).strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "DataIntelligence" / "Server"
    return Path.home() / ".local" / "state" / "data-intelligence-server"


@dataclass(frozen=True, slots=True)
class ConfigServidor:
    host: str = "0.0.0.0"
    porta: int = 8770
    tls: bool = False
    certificado: str | None = None
    chave_privada: str | None = None
    max_upload_mb: int = 1024

    def validar(self) -> "ConfigServidor":
        host = str(self.host or "").strip()
        if not host:
            raise ValueError("Host inválido.")
        porta = int(self.porta)
        if not 1024 <= porta <= 65535:
            raise ValueError("A porta deve ficar entre 1024 e 65535.")
        max_upload = max(10, min(int(self.max_upload_mb), 4096))
        if self.tls:
            if not self.certificado or not Path(self.certificado).is_file():
                raise ValueError("Certificado TLS não encontrado.")
            if not self.chave_privada or not Path(self.chave_privada).is_file():
                raise ValueError("Chave privada TLS não encontrada.")
        return ConfigServidor(host, porta, bool(self.tls), self.certificado, self.chave_privada, max_upload)


def caminho_config() -> Path:
    return pasta_servidor() / "server.json"


def carregar_config() -> ConfigServidor:
    p = caminho_config()
    if not p.is_file():
        return ConfigServidor()
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
        permitidos = set(ConfigServidor.__dataclass_fields__)
        return ConfigServidor(**{k: v for k, v in dados.items() if k in permitidos}).validar()
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ConfigServidor()


def salvar_config(config: ConfigServidor) -> Path:
    config = config.validar()
    p = caminho_config()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p
