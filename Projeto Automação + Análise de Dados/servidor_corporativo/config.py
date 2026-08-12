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
    ambiente: str = "lan"

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
        if ambiente == "producao" and host in {"0.0.0.0", "::"} and not self.tls:
            raise ValueError(
                "Em produção, escutar em todas as interfaces exige TLS. "
                "Use TLS ou publique o serviço apenas em loopback atrás de um proxy reverso seguro."
            )
        if self.tls:
            if not self.certificado or not Path(self.certificado).is_file():
                raise ValueError("Certificado TLS não encontrado.")
            if not self.chave_privada or not Path(self.chave_privada).is_file():
                raise ValueError("Chave privada TLS não encontrada.")
        return ConfigServidor(
            host=host, porta=porta, tls=bool(self.tls),
            certificado=self.certificado, chave_privada=self.chave_privada,
            max_upload_mb=max_upload, ambiente=ambiente,
        )


def caminho_config() -> Path:
    return pasta_servidor() / "server.json"


def carregar_config() -> ConfigServidor:
    p = caminho_config()
    if not p.is_file():
        return ConfigServidor()
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Configuração do servidor inválida em {p}.") from exc
    if not isinstance(dados, dict):
        raise ValueError(f"Configuração do servidor inválida em {p}: o JSON deve ser um objeto.")
    permitidos = set(ConfigServidor.__dataclass_fields__)
    try:
        return ConfigServidor(**{k: v for k, v in dados.items() if k in permitidos}).validar()
    except (TypeError, ValueError) as exc:
        # Falhar fechado: uma configuração explicitamente gravada como produção
        # nunca pode cair silenciosamente para o padrão LAN sem TLS.
        raise ValueError(f"Configuração do servidor rejeitada em {p}: {exc}") from exc


def salvar_config(config: ConfigServidor) -> Path:
    config = config.validar()
    p = caminho_config()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p
