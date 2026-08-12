"""Definição única da navegação contextual do Analytics.

Todas as telas do contexto analítico usam exatamente o mesmo menu. Isso evita
que a sidebar mude ao sair do dashboard para Explorar dados, Relatórios,
Visualizações ou qualquer outra seção do Analytics.
"""

from __future__ import annotations

from auth.sessao import SESSAO
from interface.componentes import criar_sidebar


MENU_ANALYTICS = (
    ("visao", "⌂", "Dashboard analítico"),
    ("nova", "+", "Nova análise"),
    ("importacoes", "↓", "Importações"),
    ("conjuntos", "▣", "Explorar dados"),
    ("relatorios", "▤", "Relatórios"),
    ("visualizacoes", "▥", "Visualizações"),
    ("agendamentos", "◷", "Agendamentos"),
    ("alertas", "!", "Alertas analíticos"),
    ("modelos", "◈", "Modelos"),
    ("perfis", "◎", "Perfis de análise"),
    ("assistente", "✦", "IA Assistente"),
)


MENU_GERAL_ANALYTICS = (
    ("inicio", "⌂", "Início"),
    ("modulos", "▦", "Módulos"),
    ("historico", "◷", "Histórico"),
    ("aprovacoes", "✓", "Aprovações"),
    ("configuracoes", "⚙", "Configurações"),
)


def _itens_contextuais(navegacao):
    itens = []
    for chave, icone, titulo in MENU_ANALYTICS:
        if chave == "nova":
            comando = navegacao.get("nova")
        elif chave == "perfis":
            comando = navegacao.get("perfis")
        else:
            callback = navegacao.get("analytics_secao")
            comando = (
                (lambda destino=chave, acao=callback: acao(destino))
                if callback is not None
                else None
            )
        itens.append((chave, icone, titulo, comando))
    return tuple(itens)


def _itens_gerais(navegacao):
    itens = [
        (chave, icone, titulo, navegacao.get(chave))
        for chave, icone, titulo in MENU_GERAL_ANALYTICS
    ]
    if SESSAO.eh_admin():
        itens.append(("usuarios", "◎", "Usuários", navegacao.get("usuarios")))
    return tuple(itens)


def grupos_sidebar_analytics(navegacao):
    """Retorna os grupos canônicos usados por todas as páginas analíticas."""
    return (
        ("ANALYTICS", _itens_contextuais(navegacao)),
        ("GERAL", _itens_gerais(navegacao)),
    )


def criar_sidebar_analytics(parent, navegacao, *, ativo, voltar):
    """Cria a sidebar única do contexto analítico."""
    return criar_sidebar(
        parent,
        navegacao,
        ativo=ativo,
        grupos_customizados=grupos_sidebar_analytics(navegacao),
        rodape_texto="Voltar aos módulos",
        rodape_comando=voltar,
    )
