import platform

def verificar_sistema_operacional():
    sistema = platform.system()
    if sistema != "Windows":
        raise OSError("Este script só pode ser executado em sistemas Windows.")
    return sistema