"""Navegação canônica da Inteligência Empresarial — V10.4.0.

A área principal é orientada a decisão. O laboratório de arquivos continua
existindo como capacidade secundária e os antigos placeholders de IA/MLOps
não são expostos como funcionalidades prontas.
"""
from __future__ import annotations

from interface.componentes import criar_sidebar

MENU_INTELIGENCIA = (
    ("visao", "▦", "Visão executiva"),
    ("insights", "◇", "Insights"),
    ("conjuntos", "▣", "Explorar dados"),
    ("alertas", "!", "Alertas"),
    ("relatorios", "▤", "Relatórios"),
    ("visualizacoes", "▥", "Visualizações"),
    ("agendamentos", "◷", "Agendamentos"),
)
MENU_LABORATORIO = (
    ("nova", "+", "Análise externa"),
    ("importacoes", "↓", "Importações"),
)
MENU_ADMIN_ANALYTICS = (("regras", "⚙", "Regras analíticas"),)
# Compatibilidade para testes/extensões que importam o nome histórico.
MENU_ANALYTICS = MENU_INTELIGENCIA + MENU_LABORATORIO + MENU_ADMIN_ANALYTICS

def _cmd(navegacao, chave):
    if chave == "nova": return navegacao.get("nova")
    callback = navegacao.get("analytics_secao")
    return (lambda destino=chave, acao=callback: acao(destino)) if callback else None

def _grupo(navegacao, itens):
    return tuple((chave, icone, titulo, _cmd(navegacao, chave)) for chave, icone, titulo in itens)

def grupos_sidebar_analytics(navegacao):
    return (
        ("INTELIGÊNCIA", _grupo(navegacao, MENU_INTELIGENCIA)),
        ("LABORATÓRIO", _grupo(navegacao, MENU_LABORATORIO)),
        ("ADMINISTRAÇÃO", _grupo(navegacao, MENU_ADMIN_ANALYTICS)),
    )

def criar_sidebar_analytics(parent,navegacao,*,ativo,voltar):
    return criar_sidebar(parent,navegacao,ativo=ativo,grupos_customizados=grupos_sidebar_analytics(navegacao),
                         rodape_texto="Voltar aos módulos",rodape_comando=voltar)
