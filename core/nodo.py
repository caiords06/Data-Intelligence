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
import os
from pathlib import Path

from core.caminhos import pasta_dados

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
        if url and not (url.startswith("https://") or url.startswith("http://")):
            raise ValueError("A URL do servidor deve começar com http:// ou https://.")
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
        return ConfigNodo()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        permitidos = set(ConfigNodo.__dataclass_fields__)
        return ConfigNodo(**{k: v for k, v in dados.items() if k in permitidos}).validar()
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ConfigNodo()


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
