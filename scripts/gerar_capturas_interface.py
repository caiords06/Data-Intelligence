"""Gera PNGs, folha de contato e relatório de todas as interfaces.

Uso recomendado no Windows, com a área de trabalho desbloqueada:

    python scripts/gerar_capturas_interface.py --escopo completo
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
import tempfile
import tkinter as tk
import traceback
import unicodedata
from unittest.mock import patch


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from auth import banco
from auth.autenticacao import criar_admin_inicial
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from historico.repositorio import inicializar_historico
from interface.captura_visual import (
    analisar_limites_widgets,
    analisar_png,
    capturar_widget_png,
    gerar_folha_contato,
    gerar_relatorio_markdown,
    habilitar_dpi_windows,
    salvar_manifesto,
)
from interface.tema import CORES, configurar_estilos_ttk


@dataclass(frozen=True)
class CasoVisual:
    nome: str
    grupo: str
    fabrica: object


def _slug(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    normalizado = re.sub(r"[^a-zA-Z0-9]+", "_", normalizado).strip("_").lower()
    return normalizado or "interface"


def _navegacao_inerte() -> dict:
    chaves = (
        "inicio", "modulos", "modulo", "registros_modulo", "secao_modulo",
        "analisar_modulo", "analytics", "analytics_secao", "nova", "historico",
        "aprovacoes", "notificacoes", "configuracoes", "organizacao", "perfis",
        "usuarios", "correio", "busca", "ferramenta", "sair", "voltar",
    )
    return {chave: (lambda *args, **kwargs: None) for chave in chaves}


def construir_catalogo(escopo: str = "completo") -> list[CasoVisual]:
    """Descobre as telas a partir das configurações reais da aplicação."""
    from interface.aprovacoes import TelaAprovacoes
    from interface.app import AplicacaoAutomacao
    from interface.catalogo_modulos import TelaCatalogoModulos
    from interface.central_analytics import TelaCentralAnalytics
    from interface.compras import GRUPOS_MENU as MENU_COMPRAS, TelaCompras
    from interface.configuracao_modulos_ui import PAINEIS_MODULOS
    from interface.configuracoes_app import TelaConfiguracoesApp
    from interface.correio import TelaCorreio
    from interface.experiencias_departamentais import TelaExperienciaDepartamental
    from interface.operacoes_visuais import TelaOperacaoVisual
    from interface.estoque import GRUPOS_MENU as MENU_ESTOQUE, TelaEstoque
    from interface.ferramentas import TelaFerramentaCorporativa
    from interface.financeiro import GRUPOS_MENU as MENU_FINANCEIRO, TelaFinanceiro
    from interface.historico import TelaHistorico
    from interface.login import TelaLogin
    from interface.modulo_empresarial import TelaModuloEmpresarial
    from interface.navegacao_analytics import MENU_ANALYTICS
    from interface.notificacoes import TelaNotificacoes
    from interface.nova_analise import TelaNovaAnalise
    from interface.organizacao import TelaOrganizacao
    from interface.painel_modulo import TelaPainelModulo
    from interface.perfis_analise import TelaPerfisAnalise
    from interface.primeiro_acesso import TelaPrimeiroAcesso
    from interface.principal import TelaPrincipal
    from interface.rh import GRUPOS_MENU as MENU_RH, TelaRH
    from interface.tecnologia import GRUPOS_MENU as MENU_TI, TelaTecnologia
    from interface.usuarios import TelaUsuarios

    navegacao = _navegacao_inerte()
    casos = [
        CasoVisual("Login", "Acesso", lambda r: TelaLogin(r, lambda: None)),
        CasoVisual("Primeiro acesso", "Acesso", lambda r: TelaPrimeiroAcesso(r, lambda: None)),
        CasoVisual("Central da aplicação", "Global", lambda r: TelaPrincipal(r, navegacao)),
        CasoVisual("Catálogo de módulos", "Global", lambda r: TelaCatalogoModulos(r, navegacao)),
        CasoVisual("Histórico analítico", "Global", lambda r: TelaHistorico(r, navegacao)),
        CasoVisual("Aprovações", "Global", lambda r: TelaAprovacoes(r, navegacao)),
        CasoVisual("Central de notificações", "Global", lambda r: TelaNotificacoes(r, navegacao)),
        CasoVisual("Configurações", "Global", lambda r: TelaConfiguracoesApp(r, navegacao)),
        CasoVisual("Organização", "Global", lambda r: TelaOrganizacao(r, navegacao)),
        CasoVisual("Perfis de análise", "Analytics", lambda r: TelaPerfisAnalise(r, navegacao)),
        CasoVisual("Usuários e acessos", "Global", lambda r: TelaUsuarios(r, navegacao=navegacao)),
        CasoVisual("Correio corporativo", "Global", lambda r: TelaCorreio(r, navegacao)),
        CasoVisual(
            "Nova análise",
            "Analytics",
            lambda r: TelaNovaAnalise(r, lambda _config: None, navegacao=navegacao),
        ),
        CasoVisual("Dashboard analítico", "Analytics", lambda r: AplicacaoAutomacao(r, navegacao=navegacao)),
    ]

    secoes_analytics = [chave for chave, _icone, _titulo in MENU_ANALYTICS]
    for secao in secoes_analytics:
        if secao in {"nova", "perfis"}:
            continue
        casos.append(
            CasoVisual(
                f"Analytics · {secao}",
                "Analytics",
                lambda r, s=secao: TelaCentralAnalytics(r, navegacao, secao=s),
            )
        )

    especializados = (
        ("Financeiro", MENU_FINANCEIRO, TelaFinanceiro, "visao"),
        ("Recursos Humanos", MENU_RH, TelaRH, "visao"),
        ("Estoque", MENU_ESTOQUE, TelaEstoque, "visao"),
        ("Compras", MENU_COMPRAS, TelaCompras, "visao"),
        ("Tecnologia", MENU_TI, TelaTecnologia, "portal"),
    )
    for grupo, menu, classe, secao_inicial in especializados:
        secoes = [chave for _titulo_grupo, itens in menu for chave, _icone, _titulo in itens]
        if escopo == "essencial":
            secoes = [secao_inicial]
        for secao in secoes:
            if secao == "visao" and grupo != "Tecnologia":
                mapa_modulo = {"Financeiro":"financeiro", "Recursos Humanos":"rh", "Estoque":"estoque", "Compras":"compras"}
                fabrica = lambda r, m=mapa_modulo[grupo]: TelaExperienciaDepartamental(r, navegacao, m)
            else:
                fabrica = lambda r, c=classe, sec=secao: c(r, navegacao, secao=sec)
            casos.append(CasoVisual(f"{grupo} · {secao}", grupo, fabrica))

    genericos = ("marketing", "administrativo", "juridico", "comercial")
    visuais = {
        "marketing": {"registros", "calendario", "automacao", "conteudo"},
        "administrativo": {"registros", "facilities", "viagens", "reembolsos", "veiculos", "salas"},
        "juridico": {"registros", "processos", "prazos", "audiencias", "riscos"},
        "comercial": {"registros", "crm", "pipeline", "propostas", "metas"},
    }
    for modulo in genericos:
        configuracao = PAINEIS_MODULOS[modulo]
        secoes = [chave for chave, _icone, _titulo in configuracao["menu"]]
        if escopo == "essencial":
            secoes = ["visao"]
        for secao in secoes:
            if secao == "visao":
                fabrica = lambda r, m=modulo: TelaExperienciaDepartamental(r, navegacao, m)
            elif secao in visuais[modulo]:
                fabrica = lambda r, m=modulo, sec=secao: TelaOperacaoVisual(r, navegacao, m, secao=sec)
            else:
                fabrica = lambda r, m=modulo, sec=secao: TelaPainelModulo(r, navegacao, m, secao=sec)
            casos.append(CasoVisual(f"{configuracao['titulo']} · {secao}", modulo.title(), fabrica))

    for ferramenta in (
        "tarefas", "documentos", "workflows", "integracoes", "relatorios", "auditoria",
    ):
        casos.append(
            CasoVisual(
                f"Ferramenta · {ferramenta}",
                "Ferramentas",
                lambda r, f=ferramenta: TelaFerramentaCorporativa(r, navegacao, f),
            )
        )
    return casos


@contextmanager
def banco_visual_temporario():
    """Isola os testes para nunca escrever no banco real do usuário."""
    with tempfile.TemporaryDirectory(prefix="data_intelligence_visual_") as pasta_texto:
        pasta = Path(pasta_texto)
        with (
            patch.object(banco, "DB_PATH", pasta / "interface_visual.db"),
            patch.object(banco, "STORAGE_DIR", pasta),
        ):
            banco.inicializar_banco()
            admin = criar_admin_inicial(
                "Administrador Visual", "admin_visual", "TesteVisual#123"
            )
            SESSAO.iniciar(admin)
            inicializar_historico()
            inicializar_enterprise()
            obter_contexto()
            try:
                yield
            finally:
                SESSAO.encerrar()


def _encerrar_root(root) -> None:
    try:
        agendamentos = root.tk.call("after", "info")
    except tk.TclError:
        agendamentos = ()
    for identificador in agendamentos:
        try:
            root.after_cancel(identificador)
        except tk.TclError:
            pass
    try:
        root.destroy()
    except tk.TclError:
        pass


def executar_capturas(
    destino: str | Path,
    *,
    escopo: str = "completo",
    largura: int = 1600,
    altura: int = 900,
    espera_ms: int = 180,
    falhar_em_erro: bool = False,
) -> list[dict]:
    habilitar_dpi_windows()
    destino = Path(destino).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    resultados: list[dict] = []

    with banco_visual_temporario():
        casos = construir_catalogo(escopo)
        total = len(casos)
        for indice, caso in enumerate(casos, 1):
            print(f"[{indice:03d}/{total:03d}] {caso.nome}", flush=True)
            root = None
            caminho = destino / f"{indice:03d}_{_slug(caso.grupo)}_{_slug(caso.nome)}.png"
            try:
                root = tk.Tk()
                tela_largura = int(root.winfo_screenwidth())
                tela_altura = int(root.winfo_screenheight())
                largura_disponivel = max(800, tela_largura - 40)
                altura_disponivel = max(600, tela_altura - 80)
                largura_real = min(max(800, largura), largura_disponivel)
                altura_real = min(max(600, altura), altura_disponivel)
                root.geometry(f"{largura_real}x{altura_real}+10+10")
                root.minsize(min(900, largura_real), min(640, altura_real))
                root.configure(bg=CORES["bg"])
                configurar_estilos_ttk(root)
                caso.fabrica(root)
                root.update_idletasks()
                root.update()
                layout = analisar_limites_widgets(root)
                capturar_widget_png(root, caminho, espera_ms=espera_ms)
                resultado = analisar_png(
                    caminho,
                    largura_minima=min(800, largura_real),
                    altura_minima=min(600, altura_real),
                )
                resultado.update(tela=caso.nome, grupo=caso.grupo, layout=layout)
                if layout["widgets_fora_da_janela"]:
                    resultado["status"] = "reprovada"
                    resultado["falhas"].append(
                        f"{layout['widgets_fora_da_janela']} controle(s) visível(is) fora da janela"
                    )
                if layout.get("textos_possivelmente_cortados"):
                    if resultado["status"] == "aprovada":
                        resultado["status"] = "alerta"
                    resultado["alertas"].append(
                        f"{layout['textos_possivelmente_cortados']} texto(s) severamente comprimido(s)"
                    )
                if layout.get("colunas_treeview_estreitas"):
                    if resultado["status"] == "aprovada":
                        resultado["status"] = "alerta"
                    resultado["alertas"].append(
                        f"{layout['colunas_treeview_estreitas']} coluna(s) tabular(es) abaixo de 45 px"
                    )
            except Exception as erro:
                resultado = {
                    "tela": caso.nome,
                    "grupo": caso.grupo,
                    "arquivo": caminho.name,
                    "caminho": str(caminho),
                    "largura": 0,
                    "altura": 0,
                    "status": "reprovada",
                    "alertas": [],
                    "falhas": [f"{type(erro).__name__}: {erro}"],
                    "traceback": traceback.format_exc(),
                    "layout": {"widgets_fora_da_janela": 0, "exemplos": []},
                }
            finally:
                if root is not None:
                    _encerrar_root(root)
            resultados.append(resultado)

    salvar_manifesto(resultados, destino / "MANIFESTO_VISUAL.json")
    gerar_folha_contato(resultados, destino / "FOLHA_CONTATO.png")
    gerar_relatorio_markdown(resultados, destino / "RELATORIO_VISUAL.md")
    reprovadas = [item for item in resultados if item["status"] == "reprovada"]
    print(
        f"\nCapturas: {len(resultados)} | "
        f"Aprovadas: {sum(i['status'] == 'aprovada' for i in resultados)} | "
        f"Alertas: {sum(i['status'] == 'alerta' for i in resultados)} | "
        f"Reprovadas: {len(reprovadas)}"
    )
    print(f"Relatório: {destino / 'RELATORIO_VISUAL.md'}")
    if falhar_em_erro and reprovadas:
        raise RuntimeError(f"{len(reprovadas)} interface(s) reprovada(s) na validação visual.")
    return resultados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destino",
        default=str(RAIZ_PROJETO / "artifacts" / "interface_png"),
        help="Pasta que receberá PNGs, manifesto, folha de contato e relatório.",
    )
    parser.add_argument("--escopo", choices=("essencial", "completo"), default="completo")
    parser.add_argument("--largura", type=int, default=1600)
    parser.add_argument("--altura", type=int, default=900)
    parser.add_argument("--espera-ms", type=int, default=180)
    parser.add_argument("--falhar-em-erro", action="store_true")
    argumentos = parser.parse_args()

    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        parser.error(
            "Nenhum display gráfico foi detectado. Execute no Windows ou use "
            "Xvfb em um ambiente Linux com Tk instalado."
        )
    executar_capturas(
        argumentos.destino,
        escopo=argumentos.escopo,
        largura=argumentos.largura,
        altura=argumentos.altura,
        espera_ms=argumentos.espera_ms,
        falhar_em_erro=argumentos.falhar_em_erro,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
