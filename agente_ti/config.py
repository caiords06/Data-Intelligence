"""Configuração validada do agente de Tecnologia.

O arquivo não guarda o token de autenticação. No Windows, a credencial é
protegida separadamente pelo DPAPI; em desenvolvimento ela pode ser fornecida
pela variável ``DATA_TI_AGENT_TOKEN``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4


NOME_ARQUIVO_CONFIG = "agent.json"
NOME_ARQUIVO_SEGREDO = "agent_secret.bin"


def diretorio_padrao() -> Path:
    """Retorna o diretório operacional sem depender do usuário conectado."""
    if os.name == "nt":
        base = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
        return base / "DataIntelligence" / "TIAgent"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "data-intelligence-ti-agent"


def caminho_config_padrao() -> Path:
    return diretorio_padrao() / NOME_ARQUIVO_CONFIG


def caminho_segredo_padrao(config_path: str | Path | None = None) -> Path:
    base = Path(config_path).resolve().parent if config_path else diretorio_padrao()
    return base / NOME_ARQUIVO_SEGREDO


def _validar_url(url: str, *, permitir_http_privado: bool = False) -> str:
    texto = str(url or "").strip().rstrip("/")
    parsed = urlparse(texto)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Informe uma URL HTTP(S) válida para o servidor.")
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    privado = False
    try:
        privado = ipaddress.ip_address(parsed.hostname).is_private
    except ValueError:
        privado = False
    if parsed.scheme != "https" and not local and not (permitir_http_privado and privado):
        raise ValueError(
            "O agente exige HTTPS fora do computador local. Para laboratório em LAN privada, "
            "habilite explicitamente permitir_http_privado."
        )
    if parsed.username or parsed.password:
        raise ValueError("Não coloque credenciais na URL do servidor.")
    return texto


@dataclass(frozen=True, slots=True)
class AgentConfig:
    servidor_url: str
    patrimonio: str
    agent_id: str
    intervalo_segundos: int = 60
    timeout_segundos: int = 15
    verificar_tls: bool = True
    ca_bundle: str | None = None
    provedor_remoto: str | None = None
    executavel_remoto: str | None = None
    permitir_http_privado: bool = False

    def validar(self) -> "AgentConfig":
        url = _validar_url(self.servidor_url, permitir_http_privado=bool(self.permitir_http_privado))
        hostname = urlparse(url).hostname
        if not self.verificar_tls and hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("A verificação TLS só pode ser desativada em desenvolvimento local.")
        if not str(self.patrimonio or "").strip():
            raise ValueError("O patrimônio do equipamento é obrigatório.")
        if not str(self.agent_id or "").strip():
            raise ValueError("O identificador do agente é obrigatório.")
        if not 30 <= int(self.intervalo_segundos) <= 3600:
            raise ValueError("O intervalo deve ficar entre 30 e 3600 segundos.")
        if not 3 <= int(self.timeout_segundos) <= 120:
            raise ValueError("O timeout deve ficar entre 3 e 120 segundos.")
        if self.provedor_remoto not in {None, "", "AnyDesk", "TeamViewer", "RustDesk"}:
            raise ValueError("Provedor remoto não suportado.")
        if self.ca_bundle and not Path(self.ca_bundle).is_file():
            raise ValueError("O arquivo de autoridade certificadora não foi encontrado.")
        return self

    @property
    def endpoint_heartbeat(self) -> str:
        return f"{self.servidor_url.rstrip('/')}/api/v1/ti/agentes/heartbeat"


def criar_configuracao(
    servidor_url: str,
    patrimonio: str,
    *,
    intervalo_segundos: int = 60,
    timeout_segundos: int = 15,
    verificar_tls: bool = True,
    ca_bundle: str | None = None,
    provedor_remoto: str | None = None,
    executavel_remoto: str | None = None,
    agent_id: str | None = None,
    permitir_http_privado: bool = False,
) -> AgentConfig:
    return AgentConfig(
        servidor_url=_validar_url(servidor_url, permitir_http_privado=permitir_http_privado),
        patrimonio=str(patrimonio or "").strip(),
        agent_id=agent_id or str(uuid4()),
        intervalo_segundos=int(intervalo_segundos),
        timeout_segundos=int(timeout_segundos),
        verificar_tls=bool(verificar_tls),
        ca_bundle=str(ca_bundle).strip() if ca_bundle else None,
        provedor_remoto=str(provedor_remoto).strip() if provedor_remoto else None,
        executavel_remoto=str(executavel_remoto).strip() if executavel_remoto else None,
        permitir_http_privado=bool(permitir_http_privado),
    ).validar()


def salvar_configuracao(config: AgentConfig, caminho: str | Path | None = None) -> Path:
    config.validar()
    destino = Path(caminho) if caminho else caminho_config_padrao()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    temporario.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporario, destino)
    return destino


def carregar_configuracao(caminho: str | Path | None = None) -> AgentConfig:
    origem = Path(caminho) if caminho else caminho_config_padrao()
    if not origem.is_file():
        raise FileNotFoundError(f"Configuração do agente não encontrada: {origem}")
    dados = json.loads(origem.read_text(encoding="utf-8"))
    campos = {
        "servidor_url", "patrimonio", "agent_id", "intervalo_segundos",
        "timeout_segundos", "verificar_tls", "ca_bundle", "provedor_remoto",
        "executavel_remoto", "permitir_http_privado",
    }
    desconhecidos = set(dados) - campos
    if desconhecidos:
        raise ValueError(f"Campos desconhecidos na configuração: {', '.join(sorted(desconhecidos))}")
    return AgentConfig(**dados).validar()
