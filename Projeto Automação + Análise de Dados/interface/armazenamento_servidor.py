"""Decisões de armazenamento de saídas geradas pela interface.

Em Central/Cliente, relatórios e exportações gerados pelo sistema são
persistidos diretamente no Servidor Corporativo. O seletor de arquivo local é
reservado ao modo de desenvolvimento standalone explicitamente habilitado.
"""
from __future__ import annotations

from pathlib import Path
import re
from tkinter import filedialog

from core.nodo import usa_servidor_remoto

_NOME_SEGURO = re.compile(r"[^A-Za-z0-9._() -]+")


def nome_seguro(nome: str, *, padrao: str = "resultado.bin") -> str:
    nome = Path(str(nome or padrao)).name.strip() or padrao
    nome = _NOME_SEGURO.sub("_", nome).strip(" .")
    return nome or padrao


def escolher_destino_gerado(
    *,
    parent,
    nome_sugerido: str,
    titulo: str = "Salvar arquivo",
    defaultextension: str = "",
    filetypes=(),
) -> tuple[str | None, bool]:
    """Retorna ``(destino, remoto)``.

    Produção remota nunca abre ``Save As``: o destino ``server://`` é
    interpretado pelo transporte RPC e o arquivo permanece no servidor.
    """
    seguro = nome_seguro(nome_sugerido)
    if usa_servidor_remoto():
        return f"server://{seguro}", True
    destino = filedialog.asksaveasfilename(
        parent=parent,
        title=titulo,
        defaultextension=defaultextension,
        initialfile=seguro,
        filetypes=filetypes,
    )
    return (destino or None), False


def mensagem_arquivo_gerado(resultado, *, remoto: bool, nome: str) -> str:
    if remoto:
        if isinstance(resultado, dict):
            identificador = resultado.get("id")
            nome_final = resultado.get("nome") or nome
            sufixo = f"\nID: {identificador}" if identificador not in (None, "") else ""
            return f"Arquivo armazenado no Servidor Corporativo:\n{nome_final}{sufixo}"
        return f"Arquivo armazenado no Servidor Corporativo:\n{nome}"
    return f"Arquivo salvo em:\n{resultado or nome}"


__all__ = ["escolher_destino_gerado", "mensagem_arquivo_gerado", "nome_seguro"]
