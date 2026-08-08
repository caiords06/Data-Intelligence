from pathlib import Path
import pandas as pd

EXTENSOES_PERMITIDAS = {
    '.xlsx',
    '.xls',
    '.csv'
}

def validar_arquivo(caminho):
    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(
            f'Arquivo não encontrado: {caminho}'
        )
    
    if not caminho.is_file():
        raise ValueError(
            'O caminho informado não corresponde a um arquivo.'
        )

    extensao = caminho.suffix.lower()

    if extensao not in EXTENSOES_PERMITIDAS:
        raise ValueError(
            'Formato não suportado.'
            'Utilize XLSX, XLS ou CSV.'
        )

    return True

def carregar_planilha(caminho):
    caminho= Path(caminho)
    validar_arquivo(caminho)
    extensao = caminho.suffix.lower()

    if extensao == '.csv':

        df = pd.read_csv(
            caminho
        )

    elif extensao in {'.xlsx', '.xls'}:

        df = pd.read_excel(
            caminho
        )

    else:
        raise ValueError(
            f'Extensão não suportada: {extensao}'
        )

    return df