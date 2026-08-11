"""Converte caminhos absolutos de RH sob o storage para caminhos relativos portáveis."""

from __future__ import annotations

from pathlib import Path
from auth import banco


def _converter(conexao, tabela: str) -> None:
    try:
        linhas = conexao.execute(f"SELECT id,caminho FROM {tabela} WHERE caminho IS NOT NULL AND TRIM(caminho)<>''").fetchall()
    except Exception:
        return
    raiz = banco.STORAGE_DIR.resolve()
    for linha in linhas:
        bruto = str(linha["caminho"])
        caminho = Path(bruto).expanduser()
        if not caminho.is_absolute():
            continue
        try:
            relativo = caminho.resolve().relative_to(raiz).as_posix()
        except (OSError, ValueError):
            # Caminho externo legado é preservado; não inventamos destino.
            continue
        conexao.execute(f"UPDATE {tabela} SET caminho=? WHERE id=?", (relativo, int(linha["id"])))


def upgrade(conexao) -> None:
    _converter(conexao, "rh_documentos")
    _converter(conexao, "rh_contracheques")
