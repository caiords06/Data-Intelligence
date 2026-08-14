"""Preferências persistidas na autoridade transacional (PostgreSQL no servidor)."""

from __future__ import annotations

import json
import os
from urllib.parse import urlparse

from auth.banco import conectar
from auth.sessao import SESSAO

PREFERENCIAS_PADRAO = {
    "atraso_minimo_segundos": 5,
    "categoria_padrao": "automatica",
    "periodo_padrao": "automatico",
    "pasta_padrao": "",
    "url_validacao": os.getenv("AUTOMACAO_URL_VALIDACAO", "https://example.com"),
    "tempo_sessao_minutos": 30,
    "confirmar_exclusao_historico": True,
    "tema_interface": "escuro",
}

CATEGORIAS_VALIDAS = {
    "automatica", "vendas", "financeiro", "estoque", "cadastro",
    "recursos_humanos", "compras", "ti", "marketing",
    "administrativo", "juridico", "comercial",
}
PERIODOS_VALIDOS = {
    "automatico", "mensal", "trimestral", "semestral", "anual", "personalizado",
}
TEMAS_VALIDOS = {"escuro", "claro"}


def normalizar_preferencias(preferencias: dict | None) -> dict:
    recebidas = dict(preferencias or {})
    resultado = dict(PREFERENCIAS_PADRAO)
    resultado.update({
        chave: valor for chave, valor in recebidas.items()
        if chave in PREFERENCIAS_PADRAO
    })
    resultado["atraso_minimo_segundos"] = max(0, min(15, int(resultado["atraso_minimo_segundos"])))
    resultado["tempo_sessao_minutos"] = max(5, min(240, int(resultado["tempo_sessao_minutos"])))
    if resultado["categoria_padrao"] not in CATEGORIAS_VALIDAS:
        resultado["categoria_padrao"] = "automatica"
    if resultado["periodo_padrao"] not in PERIODOS_VALIDOS:
        resultado["periodo_padrao"] = "automatico"
    resultado["tema_interface"] = str(resultado.get("tema_interface") or "escuro").strip().lower()
    if resultado["tema_interface"] not in TEMAS_VALIDOS:
        resultado["tema_interface"] = "escuro"
    resultado["pasta_padrao"] = str(resultado["pasta_padrao"] or "").strip()
    resultado["url_validacao"] = str(resultado["url_validacao"] or "").strip()
    url = urlparse(resultado["url_validacao"])
    if url.scheme not in {"http", "https"} or not url.netloc:
        resultado["url_validacao"] = "https://example.com"
    resultado["confirmar_exclusao_historico"] = bool(resultado["confirmar_exclusao_historico"])
    return resultado


def _usuario_id(ator: dict | None = None) -> int | None:
    origem = ator or SESSAO.usuario
    try:
        return int(origem["id"]) if origem and origem.get("id") is not None else None
    except (KeyError, TypeError, ValueError):
        return None


def _garantir_schema(conexao) -> None:
    # Idempotente também no SQLite legado usado exclusivamente por migração/testes.
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS preferencias_usuarios (
            usuario_id INTEGER PRIMARY KEY,
            preferencias_json TEXT NOT NULL,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def carregar_preferencias(ator: dict | None = None) -> dict:
    usuario_id = _usuario_id(ator)
    if usuario_id is None:
        return dict(PREFERENCIAS_PADRAO)
    with conectar() as conexao:
        _garantir_schema(conexao)
        registro = conexao.execute(
            "SELECT preferencias_json FROM preferencias_usuarios WHERE usuario_id=?",
            (usuario_id,),
        ).fetchone()
    if registro is None:
        return dict(PREFERENCIAS_PADRAO)
    try:
        conteudo = json.loads(registro["preferencias_json"])
    except (json.JSONDecodeError, TypeError, ValueError):
        return dict(PREFERENCIAS_PADRAO)
    return normalizar_preferencias(conteudo)


def salvar_preferencias(preferencias: dict, ator: dict | None = None) -> dict:
    usuario_id = _usuario_id(ator)
    if usuario_id is None:
        raise PermissionError("É necessário estar autenticado para salvar preferências.")
    normalizadas = normalizar_preferencias(preferencias)
    conteudo = json.dumps(normalizadas, ensure_ascii=False, separators=(",", ":"))
    with conectar() as conexao:
        _garantir_schema(conexao)
        conexao.execute(
            """
            INSERT INTO preferencias_usuarios (usuario_id, preferencias_json, atualizado_em)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(usuario_id) DO UPDATE SET
                preferencias_json=excluded.preferencias_json,
                atualizado_em=CURRENT_TIMESTAMP
            """,
            (usuario_id, conteudo),
        )
    return normalizadas


def obter_preferencia(chave: str, padrao=None, ator: dict | None = None):
    return carregar_preferencias(ator).get(chave, padrao)


# Central/Cliente executam preferências no servidor; nenhum JSON é gravado localmente.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
