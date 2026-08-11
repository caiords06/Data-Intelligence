"""Configuração persistente do receptor de agentes TI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import socket

from auth import banco

ARQUIVO_CONFIG = "ti_server.json"


@dataclass(frozen=True, slots=True)
class ServidorTIConfig:
    habilitado: bool = True
    host: str = "0.0.0.0"
    porta: int = 8765
    tls: bool = False
    certificado: str | None = None
    chave_privada: str | None = None

    def validar(self) -> "ServidorTIConfig":
        if not str(self.host or "").strip():
            raise ValueError("Host do servidor TI inválido.")
        if not 1024 <= int(self.porta) <= 65535:
            raise ValueError("A porta do servidor TI deve ficar entre 1024 e 65535.")
        if self.tls:
            if not self.certificado or not Path(self.certificado).is_file():
                raise ValueError("Certificado TLS do servidor TI não encontrado.")
            if not self.chave_privada or not Path(self.chave_privada).is_file():
                raise ValueError("Chave privada TLS do servidor TI não encontrada.")
        return self


def caminho_config() -> Path:
    return banco.STORAGE_DIR / ARQUIVO_CONFIG


def carregar_config() -> ServidorTIConfig:
    origem = caminho_config()
    if not origem.is_file():
        return ServidorTIConfig()
    try:
        dados = json.loads(origem.read_text(encoding="utf-8"))
        permitidos = {"habilitado", "host", "porta", "tls", "certificado", "chave_privada"}
        dados = {k: v for k, v in dados.items() if k in permitidos}
        return ServidorTIConfig(**dados).validar()
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ServidorTIConfig()


def salvar_config(config: ServidorTIConfig) -> Path:
    config.validar()
    destino = caminho_config()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temp = destino.with_suffix(".tmp")
    temp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(destino)
    return destino


def ip_lan_sugerido() -> str:
    """Tenta descobrir o IPv4 usado para sair da máquina sem enviar tráfego."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        sock.close()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return "127.0.0.1"


def url_lan_sugerida(config: ServidorTIConfig | None = None) -> str:
    config = (config or carregar_config()).validar()
    host = config.host
    if host in {"0.0.0.0", "::", "localhost", "127.0.0.1"}:
        host = ip_lan_sugerido()
    esquema = "https" if config.tls else "http"
    return f"{esquema}://{host}:{config.porta}"
