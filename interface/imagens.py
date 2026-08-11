"""Carregamento centralizado dos ativos visuais da interface.

O módulo mantém a resolução de caminhos fora das telas e oferece um
fallback seguro quando o Pillow não está instalado. As telas devem manter a
referência retornada enquanto o widget estiver visível para que o Tkinter não
descarte a imagem.
"""

from __future__ import annotations

from pathlib import Path

from core.caminhos import raiz_recursos

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:  # A aplicação continua funcional sem o pacote opcional.
    Image = None
    ImageOps = None
    ImageTk = None


PASTA_PROJETO = raiz_recursos()
PASTA_ASSETS = PASTA_PROJETO / "assets"


def caminho_asset(caminho_relativo: str | Path) -> Path:
    """Retorna um caminho validado dentro da pasta ``assets``."""
    caminho = (PASTA_ASSETS / Path(caminho_relativo)).resolve()
    try:
        caminho.relative_to(PASTA_ASSETS.resolve())
    except ValueError as erro:
        raise ValueError("O ativo precisa estar dentro da pasta assets.") from erro
    return caminho


def carregar_imagem(
    caminho_relativo: str | Path,
    *,
    tamanho: tuple[int, int] | None = None,
    preencher: bool = False,
    master=None,
):
    """Carrega um PNG/JPG para o Tkinter preservando a proporção.

    Retorna ``None`` quando o Pillow ou o arquivo não estão disponíveis. Isso
    permite que a tela apresente sua representação vetorial de contingência.
    """
    imagem = abrir_imagem(caminho_relativo)
    if imagem is None:
        return None

    return criar_photoimage(
        imagem,
        tamanho=tamanho,
        preencher=preencher,
        master=master,
    )


def abrir_imagem(caminho_relativo: str | Path):
    """Abre um ativo como imagem Pillow independente do interpretador Tk."""
    if Image is None:
        return None

    caminho = caminho_asset(caminho_relativo)
    if not caminho.is_file():
        return None

    try:
        with Image.open(caminho) as arquivo:
            modo = "RGBA" if "A" in arquivo.getbands() else "RGB"
            return arquivo.convert(modo).copy()
    except (OSError, ValueError):
        return None


def criar_photoimage(
    imagem,
    *,
    tamanho: tuple[int, int] | None = None,
    preencher: bool = False,
    master=None,
):
    """Converte uma imagem Pillow para Tk, com ajuste proporcional opcional."""
    if Image is None or ImageOps is None or ImageTk is None or imagem is None:
        return None

    preparada = imagem.copy()
    if tamanho is not None:
        largura = max(1, int(tamanho[0]))
        altura = max(1, int(tamanho[1]))
        tamanho_seguro = (largura, altura)
        if preencher:
            preparada = ImageOps.fit(
                preparada,
                tamanho_seguro,
                method=Image.Resampling.LANCZOS,
            )
        else:
            preparada.thumbnail(tamanho_seguro, Image.Resampling.LANCZOS)

    return ImageTk.PhotoImage(preparada, master=master)
