"""Captura e validação visual das interfaces Tkinter.

O módulo não interfere na execução normal da aplicação. Ele é usado
pelos testes visuais e pelo gerador de evidências em ``scripts/``.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import time
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageStat


def habilitar_dpi_windows() -> None:
    """Alinha as coordenadas do Tk e do ImageGrab em monitores com escala."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, ImportError, OSError):
        # A captura ainda funciona sem DPI awareness; somente pode haver uma
        # pequena diferença de coordenadas em escalas acima de 100%.
        pass


def aguardar_renderizacao(widget, milissegundos: int = 180) -> None:
    """Processa eventos pendentes até a janela estar efetivamente desenhada."""
    widget.update_idletasks()
    widget.update()
    limite = time.monotonic() + max(0, milissegundos) / 1000
    while time.monotonic() < limite:
        widget.update_idletasks()
        widget.update()
        time.sleep(0.015)


def capturar_widget_png(widget, destino: str | Path, *, espera_ms: int = 180) -> Path:
    """Captura a área visível de um widget raiz e salva um PNG.

    A janela precisa estar mapeada em um desktop gráfico real. No Windows a
    captura inclui janelas em camadas e considera todos os monitores.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    aguardar_renderizacao(widget, espera_ms)

    try:
        widget.lift()
        widget.attributes("-topmost", True)
        widget.update()
    except Exception:
        pass

    x = int(widget.winfo_rootx())
    y = int(widget.winfo_rooty())
    largura = int(widget.winfo_width())
    altura = int(widget.winfo_height())
    if largura < 2 or altura < 2:
        raise RuntimeError(
            f"A janela ainda não possui dimensões capturáveis: {largura}x{altura}."
        )

    parametros = {"bbox": (x, y, x + largura, y + altura)}
    if sys.platform.startswith("win"):
        parametros.update(include_layered_windows=True, all_screens=True)
    imagem = ImageGrab.grab(**parametros)
    imagem.save(destino, format="PNG", optimize=True)

    try:
        widget.attributes("-topmost", False)
    except Exception:
        pass
    return destino


def _cor_dominante_amostrada(imagem: Image.Image) -> tuple[tuple[int, int, int], float, int]:
    amostra = imagem.convert("RGB")
    amostra.thumbnail((240, 160))
    cores = amostra.getcolors(maxcolors=amostra.width * amostra.height) or []
    if not cores:
        return (0, 0, 0), 0.0, 0
    quantidade, cor = max(cores, key=lambda item: item[0])
    total = max(1, amostra.width * amostra.height)
    return tuple(cor), quantidade / total, len(cores)


def analisar_png(
    caminho: str | Path,
    *,
    largura_minima: int = 800,
    altura_minima: int = 600,
) -> dict:
    """Retorna métricas e alertas objetivos sobre uma captura visual."""
    caminho = Path(caminho)
    alertas: list[str] = []
    falhas: list[str] = []
    with Image.open(caminho) as original:
        imagem = original.convert("RGB")
        largura, altura = imagem.size
        cinza = imagem.convert("L")
        estatistica = ImageStat.Stat(cinza)
        media = float(estatistica.mean[0])
        desvio = float(estatistica.stddev[0])
        entropia = float(cinza.entropy())
        cor_dominante, proporcao_dominante, cores_amostradas = (
            _cor_dominante_amostrada(imagem)
        )

    if largura < largura_minima or altura < altura_minima:
        falhas.append(
            f"captura menor que o mínimo: {largura}x{altura}; "
            f"esperado ao menos {largura_minima}x{altura_minima}"
        )
    if desvio < 2.0 or proporcao_dominante >= 0.995:
        falhas.append("imagem praticamente uniforme ou vazia")
    elif entropia < 2.0 or proporcao_dominante > 0.94:
        alertas.append("baixa variedade visual; revisar se a tela renderizou por completo")
    if media > 248 and desvio < 8:
        falhas.append("captura quase totalmente branca")
    if media < 2 and desvio < 4:
        falhas.append("captura quase totalmente preta")

    status = "reprovada" if falhas else "alerta" if alertas else "aprovada"
    return {
        "arquivo": caminho.name,
        "caminho": str(caminho),
        "largura": largura,
        "altura": altura,
        "media_luminancia": round(media, 2),
        "desvio_luminancia": round(desvio, 2),
        "entropia": round(entropia, 3),
        "cor_dominante": "#%02X%02X%02X" % cor_dominante,
        "proporcao_cor_dominante": round(proporcao_dominante, 4),
        "cores_amostradas": int(cores_amostradas),
        "status": status,
        "alertas": alertas,
        "falhas": falhas,
    }


def analisar_limites_widgets(root, *, tolerancia: int = 2) -> dict:
    """Localiza controles visíveis posicionados para fora da janela.

    Descendentes de ``Canvas`` são ignorados porque uma área rolável
    intencionalmente mantém conteúdo maior do que seu viewport.
    """
    import tkinter as tk

    root.update_idletasks()
    esquerda = int(root.winfo_rootx())
    topo = int(root.winfo_rooty())
    direita = esquerda + int(root.winfo_width())
    base = topo + int(root.winfo_height())
    excedentes: list[dict] = []
    textos_cortados: list[dict] = []
    colunas_estreitas: list[dict] = []

    def visitar(widget, dentro_canvas=False):
        agora_canvas = dentro_canvas or isinstance(widget, tk.Canvas)
        for filho in widget.winfo_children():
            try:
                mapeado = bool(filho.winfo_ismapped())
            except tk.TclError:
                continue
            if mapeado and not agora_canvas and not isinstance(filho, tk.Toplevel):
                x = int(filho.winfo_rootx())
                y = int(filho.winfo_rooty())
                w = int(filho.winfo_width())
                h = int(filho.winfo_height())
                classe = filho.winfo_class()
                fora = (
                    x < esquerda - tolerancia
                    or y < topo - tolerancia
                    or x + w > direita + tolerancia
                    or y + h > base + tolerancia
                )
                if fora:
                    texto = ""
                    try:
                        texto = str(filho.cget("text"))[:80]
                    except tk.TclError:
                        pass
                    excedentes.append(
                        {
                            "classe": classe,
                            "texto": texto,
                            "geometria": f"{w}x{h}+{x-esquerda}+{y-topo}",
                        }
                    )

                # Heurística sem OCR: detecta texto severamente comprimido em
                # labels/botões pela diferença entre tamanho requisitado e real.
                if classe in {"Label", "TLabel", "Button", "TButton", "Checkbutton", "TCheckbutton"}:
                    try:
                        texto = str(filho.cget("text") or "").strip()
                        reqw = int(filho.winfo_reqwidth())
                        if len(texto) >= 5 and reqw >= 40 and w < reqw * 0.55:
                            textos_cortados.append({
                                "classe": classe, "texto": texto[:80],
                                "largura": w, "largura_requisitada": reqw,
                            })
                    except (tk.TclError, TypeError, ValueError):
                        pass

                if classe == "Treeview":
                    try:
                        for coluna in filho["columns"]:
                            heading = str(filho.heading(coluna, "text") or "").strip()
                            largura_coluna = int(filho.column(coluna, "width"))
                            if heading and largura_coluna < 45:
                                colunas_estreitas.append({
                                    "coluna": str(coluna), "titulo": heading[:80],
                                    "largura": largura_coluna,
                                })
                    except (tk.TclError, TypeError, ValueError):
                        pass
            visitar(filho, agora_canvas)

    visitar(root)
    return {
        "widgets_fora_da_janela": len(excedentes),
        "exemplos": excedentes[:20],
        "textos_possivelmente_cortados": len(textos_cortados),
        "exemplos_texto_cortado": textos_cortados[:20],
        "colunas_treeview_estreitas": len(colunas_estreitas),
        "exemplos_colunas_estreitas": colunas_estreitas[:20],
    }


def salvar_manifesto(resultados: Iterable[dict], destino: str | Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    serializaveis: list[dict] = []
    base = destino.parent.resolve()
    for resultado in resultados:
        item = dict(resultado)
        caminho = item.get("caminho")
        if caminho:
            try:
                item["caminho"] = str(Path(caminho).resolve().relative_to(base))
            except ValueError:
                # Não vaza caminhos absolutos da estação de trabalho no manifesto.
                item["caminho"] = Path(caminho).name
        serializaveis.append(item)
    destino.write_text(
        json.dumps(serializaveis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def gerar_folha_contato(
    resultados: Iterable[dict],
    destino: str | Path,
    *,
    colunas: int = 4,
    miniatura: tuple[int, int] = (360, 203),
) -> Path:
    """Monta um painel único com todas as capturas e seus estados."""
    resultados = list(resultados)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    margem = 14
    legenda = 44
    largura_celula = miniatura[0] + margem * 2
    altura_celula = miniatura[1] + legenda + margem * 2
    linhas = max(1, math.ceil(len(resultados) / max(1, colunas)))
    folha = Image.new(
        "RGB",
        (largura_celula * colunas, altura_celula * linhas),
        "#081524",
    )
    desenho = ImageDraw.Draw(folha)
    fonte = ImageFont.load_default()
    cores_status = {"aprovada": "#22C55E", "alerta": "#F59E0B", "reprovada": "#EF4444"}

    for indice, resultado in enumerate(resultados):
        linha, coluna = divmod(indice, colunas)
        x = coluna * largura_celula + margem
        y = linha * altura_celula + margem
        try:
            with Image.open(resultado["caminho"]) as imagem:
                mini = imagem.convert("RGB")
                mini.thumbnail(miniatura)
                fundo = Image.new("RGB", miniatura, "#0B1B2E")
                posicao = ((miniatura[0] - mini.width) // 2, (miniatura[1] - mini.height) // 2)
                fundo.paste(mini, posicao)
                folha.paste(fundo, (x, y))
        except (FileNotFoundError, OSError):
            desenho.rectangle((x, y, x + miniatura[0], y + miniatura[1]), fill="#2A1015")

        status = resultado.get("status", "reprovada")
        desenho.rectangle(
            (x, y + miniatura[1] + 6, x + 8, y + miniatura[1] + 34),
            fill=cores_status.get(status, "#EF4444"),
        )
        nome = str(resultado.get("tela") or resultado.get("arquivo") or "captura")
        desenho.text((x + 14, y + miniatura[1] + 7), nome[:52], fill="#F8FAFC", font=fonte)
        desenho.text(
            (x + 14, y + miniatura[1] + 22),
            f"{status.upper()} · {resultado.get('largura', 0)}x{resultado.get('altura', 0)}",
            fill="#94A3B8",
            font=fonte,
        )

    folha.save(destino, format="PNG", optimize=True)
    return destino


def gerar_relatorio_markdown(resultados: Iterable[dict], destino: str | Path) -> Path:
    resultados = list(resultados)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    totais = {
        status: sum(item.get("status") == status for item in resultados)
        for status in ("aprovada", "alerta", "reprovada")
    }
    linhas = [
        "# Relatório de validação visual",
        "",
        "Relatório gerado automaticamente a partir das janelas Tkinter renderizadas.",
        "",
        f"- Capturas: **{len(resultados)}**",
        f"- Aprovadas: **{totais['aprovada']}**",
        f"- Alertas: **{totais['alerta']}**",
        f"- Reprovadas: **{totais['reprovada']}**",
        "",
        "![Folha de contato](FOLHA_CONTATO.png)",
        "",
        "| Tela | Grupo | Dimensões | Estado | Diagnóstico |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in resultados:
        mensagens = list(item.get("falhas", [])) + list(item.get("alertas", []))
        limite = item.get("layout", {}).get("widgets_fora_da_janela", 0)
        if limite:
            mensagens.append(f"{limite} controle(s) fora da janela")
        diagnostico = "; ".join(mensagens) or "Sem anomalias automáticas"
        relativo = Path(item["caminho"]).name
        linhas.append(
            f"| [{item.get('tela', relativo)}]({relativo}) | "
            f"{item.get('grupo', '—')} | {item.get('largura', 0)}×{item.get('altura', 0)} | "
            f"{item.get('status', 'reprovada')} | {diagnostico.replace('|', '/')} |"
        )
    linhas.extend(
        [
            "",
            "## Como interpretar",
            "",
            "Uma captura aprovada passou pelas verificações automáticas de dimensão, "
            "contraste e variedade visual. Isso não substitui a revisão humana da folha "
            "de contato, especialmente para alinhamento, legibilidade e hierarquia.",
            "",
        ]
    )
    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino
