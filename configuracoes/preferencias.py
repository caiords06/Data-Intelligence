"""Preferências globais persistidas localmente em JSON."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from core.caminhos import pasta_dados
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = pasta_dados()
PREFERENCIAS_PATH = STORAGE_DIR / "preferencias.json"
_LOCK = threading.RLock()

PREFERENCIAS_PADRAO = {
    "atraso_minimo_segundos": 5,
    "categoria_padrao": "automatica",
    "periodo_padrao": "automatico",
    "pasta_padrao": "",
    "url_validacao": os.getenv("AUTOMACAO_URL_VALIDACAO", "https://example.com"),
    "tempo_sessao_minutos": 30,
    "confirmar_exclusao_historico": True,
}

CATEGORIAS_VALIDAS = {
    "automatica",
    "vendas",
    "financeiro",
    "estoque",
    "cadastro",
    "recursos_humanos",
    "compras",
    "ti",
    "marketing",
    "administrativo",
    "juridico",
    "comercial",
}
PERIODOS_VALIDOS = {
    "automatico",
    "mensal",
    "trimestral",
    "semestral",
    "anual",
    "personalizado",
}


def normalizar_preferencias(preferencias: dict | None) -> dict:
    recebidas = dict(preferencias or {})
    resultado = dict(PREFERENCIAS_PADRAO)
    resultado.update(
        {
            chave: valor
            for chave, valor in recebidas.items()
            if chave in PREFERENCIAS_PADRAO
        }
    )
    resultado["atraso_minimo_segundos"] = max(
        0,
        min(15, int(resultado["atraso_minimo_segundos"])),
    )
    resultado["tempo_sessao_minutos"] = max(
        5,
        min(240, int(resultado["tempo_sessao_minutos"])),
    )
    if resultado["categoria_padrao"] not in CATEGORIAS_VALIDAS:
        resultado["categoria_padrao"] = "automatica"
    if resultado["periodo_padrao"] not in PERIODOS_VALIDOS:
        resultado["periodo_padrao"] = "automatico"
    resultado["pasta_padrao"] = str(resultado["pasta_padrao"] or "").strip()
    resultado["url_validacao"] = str(resultado["url_validacao"] or "").strip()
    url = urlparse(resultado["url_validacao"])
    if url.scheme not in {"http", "https"} or not url.netloc:
        resultado["url_validacao"] = "https://example.com"
    resultado["confirmar_exclusao_historico"] = bool(
        resultado["confirmar_exclusao_historico"]
    )
    return resultado


def carregar_preferencias() -> dict:
    with _LOCK:
        if not PREFERENCIAS_PATH.exists():
            return dict(PREFERENCIAS_PADRAO)
        try:
            conteudo = json.loads(PREFERENCIAS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, TypeError):
            return dict(PREFERENCIAS_PADRAO)
        return normalizar_preferencias(conteudo)


def salvar_preferencias(preferencias: dict) -> dict:
    normalizadas = normalizar_preferencias(preferencias)
    with _LOCK:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        temporario = PREFERENCIAS_PATH.with_suffix(".json.tmp")
        temporario.write_text(
            json.dumps(normalizadas, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporario.replace(PREFERENCIAS_PATH)
    return normalizadas


def obter_preferencia(chave: str, padrao=None):
    return carregar_preferencias().get(chave, padrao)
