"""Dispatcher restrito das operações transacionais do Servidor Corporativo."""
from __future__ import annotations

import importlib
import inspect
from typing import Any

from core.rpc_central import RPC_ALLOWLIST, desserializar, serializar


class RPCError(ValueError):
    pass


def executar_alvo_autenticado(sessao, modulo: str, funcao: str, args, kwargs):
    """Executa uma função de domínio substituindo sempre o ator pelo bearer.

    O chamador é responsável por validar a allowlist adequada antes desta
    função. Centralizar o bind aqui impede que os fluxos de arquivo tenham uma
    regra de identidade diferente do RPC transacional normal.
    """
    mod = importlib.import_module(modulo)
    alvo = getattr(mod, funcao, None)
    if alvo is None or not callable(alvo):
        raise RPCError("Operação RPC indisponível no servidor.")
    alvo_real = getattr(alvo, "__di_rpc_original__", alvo)
    assinatura = inspect.signature(alvo_real)
    try:
        ligados = assinatura.bind_partial(*args, **kwargs)
    except TypeError as erro:
        raise RPCError(str(erro)) from None
    if "ator" in assinatura.parameters:
        ligados.arguments["ator"] = sessao.ator()
    return alvo_real(*ligados.args, **ligados.kwargs)


def executar_rpc(sessao, payload: dict[str, Any]) -> Any:
    modulo = str(payload.get("modulo") or "").strip()
    funcao = str(payload.get("funcao") or "").strip()
    if modulo not in RPC_ALLOWLIST or funcao not in RPC_ALLOWLIST[modulo]:
        raise PermissionError("Operação RPC não autorizada.")
    args = desserializar(payload.get("args") or [])
    kwargs = desserializar(payload.get("kwargs") or {})
    if not isinstance(args, list) or not isinstance(kwargs, dict):
        raise RPCError("Argumentos RPC inválidos.")
    return serializar(executar_alvo_autenticado(sessao, modulo, funcao, args, kwargs))


def validar_rpc_runtime() -> dict[str, list[str]]:
    """Valida toda a superfície RPC antes de o servidor ficar disponível.

    O servidor empacotado usa importação dinâmica. Uma dependência esquecida no
    PyInstaller só seria descoberta quando um usuário abrisse a tela afetada.
    Este preflight importa todos os módulos/targets da allowlist no startup e
    falha imediatamente com uma lista completa de ausências.
    """
    erros: list[str] = []
    validados: dict[str, list[str]] = {}
    for modulo, funcoes in sorted(RPC_ALLOWLIST.items()):
        try:
            mod = importlib.import_module(modulo)
        except Exception as erro:
            erros.append(f"{modulo}: {type(erro).__name__}: {erro}")
            continue
        disponiveis: list[str] = []
        for funcao in sorted(funcoes):
            alvo = getattr(mod, funcao, None)
            if not callable(alvo):
                erros.append(f"{modulo}.{funcao}: função ausente ou não chamável")
            else:
                disponiveis.append(funcao)
        validados[modulo] = disponiveis
    if erros:
        raise RuntimeError(
            "Superfície RPC incompleta no Servidor Corporativo:\n- " + "\n- ".join(erros)
        )
    return validados


__all__ = ["RPCError", "executar_rpc", "executar_alvo_autenticado", "validar_rpc_runtime"]
