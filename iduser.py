from pathlib import Path
import os
import getpass

def identificar_usuario():
    nome_usuario = getpass.getuser()
    pasta_usuario = Path.home()

    pasta_local_appdata = Path(
        os.environ["LOCALAPPDATA"]
    )

    return nome_usuario, pasta_usuario, pasta_local_appdata