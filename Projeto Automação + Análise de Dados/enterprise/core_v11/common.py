"""Primitivas de contexto, eventos, histórico e validação do CORE V11."""
from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from enterprise.contexto import exigir_permissao, obter_escopo_ator

_CODIGO = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,79}$")
_MAX_JSON = 512 * 1024
MODULOS_PERMISSAO = {"crm": "comercial", "automacao": "analytics", "documentos": "administrativo"}


def texto(valor: Any, *, minimo: int = 0, maximo: int = 240, campo: str = "Texto") -> str:
    resultado = str(valor or "").strip()
    if len(resultado) < minimo or len(resultado) > maximo:
        raise ValueError(f"{campo} deve possuir entre {minimo} e {maximo} caracteres.")
    return resultado


def codigo(valor: Any, *, campo: str = "Código") -> str:
    resultado = str(valor or "").strip().lower()
    if not _CODIGO.fullmatch(resultado):
        raise ValueError(f"{campo} deve usar letras minúsculas, números, ponto, hífen ou sublinhado.")
    return resultado


def json_objeto(valor: Any, *, campo: str = "Dados", limite: int = _MAX_JSON) -> dict:
    if valor in (None, ""):
        return {}
    if not isinstance(valor, dict):
        raise ValueError(f"{campo} deve ser um objeto.")
    serializado = json.dumps(valor, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(serializado.encode("utf-8")) > limite:
        raise ValueError(f"{campo} excede o limite permitido.")
    return valor


def json_lista(valor: Any, *, campo: str = "Lista", limite: int = _MAX_JSON) -> list:
    if valor in (None, ""):
        return []
    if not isinstance(valor, list):
        raise ValueError(f"{campo} deve ser uma lista.")
    serializado = json.dumps(valor, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(serializado.encode("utf-8")) > limite:
        raise ValueError(f"{campo} excede o limite permitido.")
    return valor


def dump(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":"), default=str)


def load(valor: Any, padrao):
    try:
        resultado = json.loads(str(valor or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return padrao
    return resultado if isinstance(resultado, type(padrao)) else padrao


def exigir_admin(ator: dict) -> None:
    if not ator or str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Esta configuração exige administrador.")


def escopo(ator: dict, modulo: str | None = None, acao: str = "ler") -> tuple[int, int | None]:
    if modulo:
        exigir_permissao(ator, MODULOS_PERMISSAO.get(modulo, modulo), acao)
    return obter_escopo_ator(ator)


def registrar_historico(
    con,
    *,
    empresa_id: int,
    filial_id: int | None,
    modulo: str,
    recurso_tipo: str,
    recurso_id: int,
    acao: str,
    ator: dict,
    antes: dict | None = None,
    depois: dict | None = None,
    request_id: str | None = None,
) -> None:
    con.execute(
        """INSERT INTO core_historico
           (empresa_id,filial_id,modulo,recurso_tipo,recurso_id,acao,antes_json,depois_json,usuario_id,request_id)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            int(empresa_id), filial_id, str(modulo), str(recurso_tipo), int(recurso_id), str(acao),
            dump(antes) if antes is not None else None, dump(depois) if depois is not None else None,
            int(ator["id"]) if ator.get("id") is not None else None, str(request_id or "")[:80] or None,
        ),
    )


def registrar_evento(
    con,
    *,
    empresa_id: int,
    filial_id: int | None,
    modulo: str,
    tipo: str,
    ator: dict,
    recurso_tipo: str | None = None,
    recurso_id: int | None = None,
    payload: dict | None = None,
    correlacao_id: str | None = None,
    causacao_id: str | None = None,
) -> str:
    evento_uuid = uuid4().hex
    con.execute(
        """INSERT INTO core_eventos_corporativos
           (evento_uuid,empresa_id,filial_id,modulo,tipo,recurso_tipo,recurso_id,payload_json,
            correlacao_id,causacao_id,criado_por)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            evento_uuid, int(empresa_id), filial_id, str(modulo), str(tipo), recurso_tipo,
            int(recurso_id) if recurso_id is not None else None, dump(payload or {}),
            correlacao_id, causacao_id, int(ator["id"]) if ator.get("id") is not None else None,
        ),
    )
    return evento_uuid


def indexar_recurso(
    con,
    *,
    empresa_id: int,
    recurso_tipo: str,
    recurso_id: int,
    modulo: str,
    titulo: str,
    subtitulo: str = "",
    termos: str = "",
    classificacao: str = "Interno",
) -> None:
    con.execute(
        """INSERT INTO core_busca_indice
           (empresa_id,recurso_tipo,recurso_id,modulo,titulo,subtitulo,termos,classificacao)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(empresa_id,recurso_tipo,recurso_id) DO UPDATE SET
           modulo=excluded.modulo,titulo=excluded.titulo,subtitulo=excluded.subtitulo,
           termos=excluded.termos,classificacao=excluded.classificacao,atualizado_em=CURRENT_TIMESTAMP""",
        (
            int(empresa_id), str(recurso_tipo), int(recurso_id), str(modulo), str(titulo)[:240],
            str(subtitulo)[:500], str(termos)[:8000], str(classificacao),
        ),
    )


def deserializar_linha(linha: Any, *campos_json: str) -> dict:
    item = dict(linha)
    for campo in campos_json:
        if campo in item:
            padrao = [] if campo.endswith("_lista_json") else {}
            item[campo.removesuffix("_json")] = load(item.pop(campo), padrao)
    return item


__all__ = (
    "MODULOS_PERMISSAO", "codigo", "deserializar_linha", "dump", "escopo", "exigir_admin", "indexar_recurso",
    "json_lista", "json_objeto", "load", "registrar_evento", "registrar_historico", "texto",
)
