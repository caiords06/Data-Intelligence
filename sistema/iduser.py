"""Informações básicas do usuário do sistema operacional."""

import getpass
import os
from pathlib import Path


def identificar_usuario():
    nome_usuario = getpass.getuser()
    pasta_usuario = Path.home()
    local_appdata = os.environ.get("LOCALAPPDATA")
    pasta_local_appdata = Path(local_appdata) if local_appdata else pasta_usuario
    return nome_usuario, pasta_usuario, pasta_local_appdata
