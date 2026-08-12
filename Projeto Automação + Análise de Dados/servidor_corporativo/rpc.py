"""Dispatcher restrito das operações transacionais do Servidor Corporativo."""
from __future__ import annotations

import importlib
import inspect
from typing import Any

from core.rpc_central import RPC_ALLOWLIST, desserializar, serializar


class RPCError(ValueError):
    pass


def executar_rpc(sessao, payload: dict[str, Any]) -> Any:
    modulo = str(payload.get("modulo") or "").strip()
    funcao = str(payload.get("funcao") or "").strip()
    if modulo not in RPC_ALLOWLIST or funcao not in RPC_ALLOWLIST[modulo]:
        raise PermissionError("Operação RPC não autorizada.")
    args = desserializar(payload.get("args") or [])
    kwargs = desserializar(payload.get("kwargs") or {})
    if not isinstance(args, list) or not isinstance(kwargs, dict):
        raise RPCError("Argumentos RPC inválidos.")

    mod = importlib.import_module(modulo)
    alvo = getattr(mod, funcao, None)
    if alvo is None or not callable(alvo):
        raise RPCError("Operação RPC indisponível no servidor.")
    # No servidor, wrappers executam localmente. Para inspeção usamos a função
    # original quando disponível para garantir uma assinatura estável.
    alvo_real = getattr(alvo, "__di_rpc_original__", alvo)
    assinatura = inspect.signature(alvo_real)
    try:
        ligados = assinatura.bind_partial(*args, **kwargs)
    except TypeError as erro:
        raise RPCError(str(erro)) from None
    if "ator" in assinatura.parameters:
        ligados.arguments["ator"] = sessao.ator()
    resultado = alvo_real(*ligados.args, **ligados.kwargs)
    return serializar(resultado)


__all__ = ["RPCError", "executar_rpc"]
