from selenium import webdriver

def criar_driver(
        navegador,
        caminho_executavel
):
    caminho = str(caminho_executavel)

    navegadores_chromium = ["chrome", "brave", "vivaldi", "opera", "chromium"]

    navegadores_firefox = ["firefox", "libreWolf", "waterfox"]

    if navegador in navegadores_chromium:
        opcoes = webdriver.ChromeOptions()

        opcoes.binary_location = caminho

        return webdriver.Chrome(options=opcoes)

    if navegador == "edge":
        opcoes = webdriver.EdgeOptions()

        opcoes.binary_location = caminho

        return webdriver.Edge(options=opcoes)

    if navegador in navegadores_firefox:
        opcoes = webdriver.FirefoxOptions()

        opcoes.binary_location = caminho

        return webdriver.Firefox(options=opcoes)

    raise RuntimeError(f"Navegador não suportado: {navegador}")