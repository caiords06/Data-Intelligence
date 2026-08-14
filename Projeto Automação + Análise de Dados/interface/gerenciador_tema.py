"""Orquestra troca de tema e preferência visual da sessão V10.2.0."""

from __future__ import annotations

import json
import os

from auth.sessao import SESSAO
from core.caminhos import pasta_estado_usuario
from interface.tema import (
    TEMA_PADRAO,
    aplicar_paleta,
    configurar_estilos_ttk,
    normalizar_tema,
    tema_atual,
)


def aplicar_tema(nome: str | None, root=None) -> str:
    nome = aplicar_paleta(nome)
    configurar_estilos_ttk(root)
    return nome


def _arquivo_preferencia_visual():
    return pasta_estado_usuario() / "preferencia_visual.json"


def carregar_tema_local() -> str:
    """Lê somente a preferência visual não sensível deste usuário do sistema."""
    try:
        payload = json.loads(_arquivo_preferencia_visual().read_text(encoding="utf-8"))
        return normalizar_tema(payload.get("tema"))
    except (OSError, TypeError, ValueError):
        return TEMA_PADRAO


def salvar_tema_local(nome: str | None) -> str:
    nome = normalizar_tema(nome)
    destino = _arquivo_preferencia_visual()
    temporario = destino.with_name(destino.name + ".tmp")
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario.write_text(
            json.dumps({"tema": nome}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temporario, destino)
    except OSError:
        temporario.unlink(missing_ok=True)
    return nome


def aplicar_tema_inicial(root=None) -> str:
    return aplicar_tema(carregar_tema_local(), root)


def alternar_tema(root=None) -> str:
    destino = "claro" if tema_atual() == "escuro" else "escuro"
    salvar_tema_local(destino)
    return aplicar_tema(destino, root)


def persistir_tema_autenticado() -> bool:
    """Sincroniza o tema do login sem apagar as demais preferências da conta."""
    if not SESSAO.autenticado():
        return False
    escolhido = salvar_tema_local(tema_atual())
    try:
        from configuracoes.preferencias import carregar_preferencias, salvar_preferencias
        preferencias = carregar_preferencias()
        preferencias["tema_interface"] = escolhido
        salvar_preferencias(preferencias)
        return True
    except (ConnectionError, OSError, PermissionError, RuntimeError, TypeError, ValueError):
        return False


def aplicar_tema_da_sessao(root=None) -> str:
    """Aplica a preferência corporativa do usuário autenticado.

    Falhas temporárias do servidor não impedem a abertura da interface: nesse
    caso preservamos o tema já ativo e a navegação segue normalmente.
    """
    if not SESSAO.autenticado():
        return aplicar_tema_inicial(root)
    try:
        from configuracoes.preferencias import carregar_preferencias
        preferencia = carregar_preferencias().get("tema_interface", TEMA_PADRAO)
    except (ConnectionError, OSError, PermissionError, RuntimeError, TypeError, ValueError):
        preferencia = tema_atual()
    return aplicar_tema(normalizar_tema(preferencia), root)


__all__ = (
    "aplicar_tema", "aplicar_tema_inicial", "aplicar_tema_da_sessao",
    "alternar_tema", "carregar_tema_local", "salvar_tema_local",
    "persistir_tema_autenticado",
)
