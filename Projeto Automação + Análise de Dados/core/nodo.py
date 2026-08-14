"""Papel do instalável e vínculo opcional com o Servidor Corporativo.

O mesmo código de interface pode operar em três papéis:
- standalone: desenvolvimento/uso local legado;
- central: estação administrativa conectada ao servidor corporativo;
- cliente: estação convencional conectada ao servidor, sem bootstrap/admin local.
O processo headless do servidor usa ``servidor``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse

from core.caminhos import executando_empacotado, pasta_dados

PAPEIS = {"standalone", "central", "cliente", "servidor"}


@dataclass(frozen=True, slots=True)
class ConfigNodo:
    papel: str = "standalone"
    servidor_url: str | None = None
    permitir_http_privado: bool = False
    sincronizar_backups: bool = True
    sincronizar_exportacoes: bool = True
    intervalo_backup_minutos: int = 15

    def validar(self) -> "ConfigNodo":
        papel = str(self.papel or "standalone").strip().lower()
        if papel not in PAPEIS:
            raise ValueError(f"Papel de nó inválido: {papel}")
        url = str(self.servidor_url or "").strip().rstrip("/") or None
        if papel in {"central", "cliente"} and not url:
            raise ValueError("Central/cliente precisam informar a URL do servidor corporativo.")
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("A URL do servidor deve ser HTTP(S) válida.")
            if parsed.username or parsed.password:
                raise ValueError("Não coloque credenciais na URL do servidor.")
            if parsed.scheme == "http":
                host = parsed.hostname.lower()
                local = host in {"localhost", "127.0.0.1", "::1"}
                try:
                    privado = ipaddress.ip_address(host).is_private
                except ValueError:
                    privado = False
                if not local and not (bool(self.permitir_http_privado) and privado):
                    raise ValueError(
                        "HTTP sem TLS só é permitido em localhost ou, quando habilitado explicitamente, "
                        "em um endereço IP privado de laboratório."
                    )
        intervalo = max(5, min(int(self.intervalo_backup_minutos or 15), 24 * 60))
        return ConfigNodo(
            papel=papel,
            servidor_url=url,
            permitir_http_privado=bool(self.permitir_http_privado),
            sincronizar_backups=bool(self.sincronizar_backups),
            sincronizar_exportacoes=bool(self.sincronizar_exportacoes),
            intervalo_backup_minutos=intervalo,
        )


def caminho_config_nodo() -> Path:
    override = str(os.environ.get("DATA_INTELLIGENCE_NODE_CONFIG", "")).strip()
    return Path(override).expanduser().resolve() if override else pasta_dados() / "node.json"


def carregar_config_nodo() -> ConfigNodo:
    papel_env = str(os.environ.get("DATA_INTELLIGENCE_NODE_ROLE", "")).strip().lower()
    url_env = str(os.environ.get("DATA_INTELLIGENCE_SERVER_URL", "")).strip()
    if papel_env or url_env:
        return ConfigNodo(
            papel=papel_env or ("central" if url_env else "standalone"),
            servidor_url=url_env or None,
            permitir_http_privado=str(os.environ.get("DATA_INTELLIGENCE_ALLOW_PRIVATE_HTTP", "")).lower() in {"1","true","yes","sim"},
        ).validar()
    caminho = caminho_config_nodo()
    if not caminho.is_file():
        # Em desenvolvimento o modo standalone continua útil. Um executável
        # distribuído, porém, jamais deve virar autoridade local por acidente:
        # ausência de node.json após uma instalação parcial deve falhar fechado.
        permitir_standalone = str(
            os.environ.get("DATA_INTELLIGENCE_ALLOW_STANDALONE", "")
        ).strip().lower() in {"1", "true", "yes", "sim"}
        if not permitir_standalone:
            raise ValueError(
                f"Configuração do nó ausente em {caminho}. "
                "A estação não pode assumir modo local automaticamente. Configure-a como Central/Cliente "
                "apontando para o Servidor Corporativo. Para desenvolvimento isolado, habilite "
                "DATA_INTELLIGENCE_ALLOW_STANDALONE=1 explicitamente."
            )
        return ConfigNodo()
    try:
        # utf-8-sig aceita tanto UTF-8 puro quanto arquivos gravados com BOM por
        # algumas versões do Windows PowerShell.
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Configuração do nó inválida em {caminho}.") from exc
    if not isinstance(dados, dict):
        raise ValueError(f"Configuração do nó inválida em {caminho}: o JSON deve ser um objeto.")
    permitidos = set(ConfigNodo.__dataclass_fields__)
    try:
        return ConfigNodo(**{k: v for k, v in dados.items() if k in permitidos}).validar()
    except (TypeError, ValueError) as exc:
        # Falhar fechado evita que um cliente configurado para o servidor remoto
        # vire silenciosamente um nó standalone ao encontrar um arquivo inválido.
        raise ValueError(f"Configuração do nó rejeitada em {caminho}: {exc}") from exc


def salvar_config_nodo(config: ConfigNodo) -> Path:
    config = config.validar()
    caminho = caminho_config_nodo()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(caminho)
    return caminho


def usa_servidor_remoto() -> bool:
    cfg = carregar_config_nodo()
    return cfg.papel in {"central", "cliente"} and bool(cfg.servidor_url)


def cliente_convencional() -> bool:
    return carregar_config_nodo().papel == "cliente"


def estacao_central() -> bool:
    return carregar_config_nodo().papel == "central"


__all__ = [
    "ConfigNodo", "carregar_config_nodo", "salvar_config_nodo",
    "usa_servidor_remoto", "cliente_convencional", "estacao_central",
]
