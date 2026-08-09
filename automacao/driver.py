"""Criação de WebDrivers Selenium."""

from __future__ import annotations


def criar_driver(navegador, caminho_executavel):
    try:
        from selenium import webdriver
    except ImportError as erro:
        raise RuntimeError(
            "Selenium não está instalado. Execute: pip install -r requirements.txt"
        ) from erro

    navegador = str(navegador).lower()
    caminho = str(caminho_executavel)

    if navegador in {"chrome", "brave", "vivaldi", "opera", "chromium"}:
        opcoes = webdriver.ChromeOptions()
        opcoes.binary_location = caminho
        return webdriver.Chrome(options=opcoes)

    if navegador == "edge":
        opcoes = webdriver.EdgeOptions()
        opcoes.binary_location = caminho
        return webdriver.Edge(options=opcoes)

    if navegador in {"firefox", "librewolf", "waterfox"}:
        opcoes = webdriver.FirefoxOptions()
        opcoes.binary_location = caminho
        return webdriver.Firefox(options=opcoes)

    raise RuntimeError(f"Navegador não suportado: {navegador}")
