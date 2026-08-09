"""Identificação do navegador padrão no Windows."""

from __future__ import annotations

import os
import shlex
from pathlib import Path


def localizar_navegador_padrao() -> tuple[str, Path]:
    if os.name != "nt":
        raise RuntimeError(
            "A detecção automática do navegador padrão está disponível apenas no Windows."
        )

    import winreg  # Import tardio: permite usar o restante do projeto em outros SOs.

    caminhos_user_choice = (
        r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice",
        r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
        r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoiceLatest",
    )

    prog_id = None
    ultimo_erro: OSError | None = None
    for caminho_associacao in caminhos_user_choice:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, caminho_associacao) as chave:
                prog_id, _ = winreg.QueryValueEx(chave, "ProgId")
                break
        except OSError as erro:
            ultimo_erro = erro

    if not prog_id:
        raise RuntimeError(
            "Não foi possível identificar o navegador padrão do Windows."
        ) from ultimo_erro

    caminho_comando = rf"{prog_id}\shell\open\command"
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, caminho_comando) as chave:
            comando, _ = winreg.QueryValueEx(chave, None)
    except OSError as erro:
        raise RuntimeError(
            f"Não foi possível localizar o executável associado a {prog_id}."
        ) from erro

    partes_comando = shlex.split(comando, posix=False)
    if not partes_comando:
        raise RuntimeError("Comando do navegador padrão está vazio.")

    caminho_executavel = os.path.normpath(partes_comando[0].strip('"'))
    return str(prog_id), Path(caminho_executavel)


def identificar_tipo_navegador(prog_id: str, caminho_executavel: Path) -> str:
    identificador = f"{prog_id} - {caminho_executavel.name}".lower()

    verificacoes = (
        ("brave", "brave"),
        ("vivaldi", "vivaldi"),
        ("opera", "opera"),
        ("librewolf", "librewolf"),
        ("waterfox", "waterfox"),
        ("firefox", "firefox"),
        ("msedge", "edge"),
        ("edge", "edge"),
        ("chromium", "chrome"),
        ("chrome", "chrome"),
    )
    for termo, navegador in verificacoes:
        if termo in identificador:
            return navegador

    raise RuntimeError(
        "Navegador padrão não foi reconhecido. "
        f"Identificador encontrado: {prog_id}"
    )
