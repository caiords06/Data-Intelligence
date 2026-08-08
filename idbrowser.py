import os
import winreg
from pathlib import Path
import shlex

def localizar_navegador_padrao():
    caminho_associacao = (r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoiceLatest\ProgId")

#Descobrir o ProgId do navegador padrão
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, 
        caminho_associacao
        ) as chave: 

            prog_id, _ = winreg.QueryValueEx(
                 chave, 
                 "ProgId"
            )

# Localizar o comando associado ao navegador

    caminho_comando = (rf"{prog_id}\shell\open\command")

    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, caminho_comando) as chave:
        comando, _ = winreg.QueryValueEx(chave, None)

# Separar somente o caminho do executável
    partes_comando = shlex.split(comando, posix=False)
    caminho_executavel = partes_comando[0]
    caminho_executavel = caminho_executavel.strip('"')
    caminho_executavel = os.path.normpath(caminho_executavel)
    return prog_id, Path(caminho_executavel)

def identificar_tipo_navegador(prog_id, caminho_executavel):

    identificador = (f"{prog_id} - {caminho_executavel.name}").lower()

    #Navegadores baseados no Chromium
    if "brave" in identificador:
        return "brave"

    if 'vivaldi' in identificador:
        return "vivaldi"

    if 'opera' in identificador:
        return "opera"

    if 'chromium' in identificador or 'chrome' in identificador:
        return "chrome"

    # Derivados do Firefox
    if 'librewolf' in identificador:
        return "libreWolf"
    if 'waterfox' in identificador:
        return "waterfox"

    #Navegadores principais
    if 'firefox' in identificador:
        return "firefox"
    if 'msedge' in identificador:
        return "edge"
    if 'chrome' in identificador:
        return "chrome"

    raise RuntimeError(f"Navegador padrão não foi reconhecido. Identificador encontrado: {prog_id}")