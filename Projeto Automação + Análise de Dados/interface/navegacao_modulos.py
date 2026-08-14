"""Navegação departamental canônica da interface V9.5.

Este módulo concentra duas responsabilidades que antes estavam espalhadas entre
``main.py`` e as telas: normalização de rotas legadas e construção da leftbox
contextual. Assim, a Visão geral e as páginas internas de um departamento usam
os mesmos destinos e o mesmo componente lateral.
"""

from __future__ import annotations

from collections.abc import Iterable

from auth.sessao import SESSAO
from services.contexto import tem_permissao
from interface.componentes import criar_sidebar


MODULOS_ESPECIALIZADOS = frozenset({"financeiro", "rh", "estoque", "compras", "ti", "marketing", "comercial", "administrativo", "juridico"})
MODULOS_VISUAIS = frozenset()

# Rotas que existiam no catálogo departamental antigo, mas não correspondem aos
# nomes das seções especializadas atuais. Mantê-las aqui preserva favoritos,
# atalhos e callbacks de versões anteriores sem deixar a UI voltar à Visão geral.
ALIASES_SECOES = {
    "financeiro": {
        "registros": "lancamentos",
    },
    "rh": {
        "registros": "colaboradores",
        "admissoes": "colaboradores", "desligamentos": "colaboradores", "movimentacoes": "colaboradores",
        "ponto": "colaboradores", "ferias": "colaboradores", "beneficios": "colaboradores",
        "folha": "colaboradores", "cargos": "colaboradores", "desempenho": "colaboradores",
        "treinamentos": "colaboradores", "carreira": "colaboradores",
    },
    "estoque": {
        "registros": "itens",
    },
    "compras": {
        "registros": "solicitacoes",
    },
    "comercial": {"registros": "oportunidades", "crm": "clientes"},
    "administrativo": {"registros": "solicitacoes", "salas": "reservas", "veiculos": "recursos"},
    "juridico": {"registros": "contratos"},
}

SECOES_VISUAIS_GENERICAS = {}


def normalizar_secao_modulo(modulo: str, secao: str | None, *, usuario=None) -> str:
    """Converte aliases antigos no destino real usado pelo módulo atual.

    Tecnologia possui uma diferença deliberada: qualquer colaborador pode usar
    o portal de suporte, enquanto o cockpit e a fila técnica exigem permissão de
    TI. Por isso ``visao`` e ``registros`` são resolvidos conforme o usuário.
    """
    modulo = str(modulo or "").strip().lower()
    secao = str(secao or "visao").strip().lower() or "visao"

    if modulo == "marketing" and secao == "registros":
        return "campanhas"

    if modulo == "ti":
        usuario = SESSAO.usuario if usuario is None else usuario
        operador = bool(usuario and tem_permissao(usuario, "ti", "ler"))
        if secao == "visao":
            return "cockpit" if operador else "portal"
        if secao == "registros":
            return "chamados" if operador else "meus_chamados"
        return secao

    return ALIASES_SECOES.get(modulo, {}).get(secao, secao)


def tipo_tela_modulo(modulo: str, secao: str) -> str:
    """Retorna o renderizador canônico de uma rota departamental."""
    modulo = str(modulo or "").strip().lower()
    secao = str(secao or "visao").strip().lower()
    if modulo in MODULOS_ESPECIALIZADOS:
        return modulo
    if modulo in MODULOS_VISUAIS:
        if secao == "visao":
            return "experiencia"
        if secao in SECOES_VISUAIS_GENERICAS.get(modulo, ()):
            return "operacao_visual"
        return "painel"
    return "painel"


def _callback_secao(navegacao: dict, modulo: str, secao: str):
    def navegar():
        callback = navegacao.get("secao_modulo")
        if callable(callback):
            callback(modulo, secao)
    return navegar


def criar_sidebar_modulo(
    parent,
    navegacao: dict,
    *,
    modulo: str,
    titulo: str,
    ativo: str,
    grupos_menu: Iterable | None = None,
    itens_menu: Iterable | None = None,
    grupos_recolhiveis: bool = False,
    incluir_correio: bool = True,
):
    """Cria a leftbox canônica de um departamento.

    ``grupos_menu`` recebe itens no formato ``(grupo, ((chave, ícone, título), ...))``.
    ``itens_menu`` recebe apenas a sequência de itens. Os callbacks são sempre
    encaminhados ao roteador principal, evitando que cada tela invente um caminho
    diferente para a mesma seção.
    """
    if grupos_menu is not None and itens_menu is not None:
        raise ValueError("Informe grupos_menu ou itens_menu, não ambos.")

    grupos_customizados = None
    itens_customizados = None
    if grupos_menu is not None:
        grupos_customizados = []
        for nome_grupo, itens in grupos_menu:
            itens_convertidos = tuple(
                (
                    chave,
                    icone,
                    rotulo,
                    _callback_secao(navegacao, modulo, chave),
                )
                for chave, icone, rotulo in itens
            )
            grupos_customizados.append((nome_grupo, itens_convertidos))
        if incluir_correio and callable(navegacao.get("correio")):
            grupos_customizados.append((
                "COLABORAÇÃO",
                (("correio", "✉", "Correio interno", lambda: navegacao["correio"](modulo)),),
            ))
        grupos_customizados = tuple(grupos_customizados)
    else:
        itens_customizados = tuple(
            (chave, icone, rotulo, _callback_secao(navegacao, modulo, chave))
            for chave, icone, rotulo in (itens_menu or ())
        )
        if incluir_correio and callable(navegacao.get("correio")):
            itens_customizados += ((
                "correio", "✉", "Correio interno", lambda: navegacao["correio"](modulo)
            ),)

    return criar_sidebar(
        parent,
        navegacao,
        ativo=ativo,
        itens_customizados=itens_customizados,
        grupos_customizados=grupos_customizados,
        titulo_customizado=titulo,
        rodape_texto="Voltar aos módulos",
        rodape_comando=navegacao.get("modulos"),
        grupos_recolhiveis=grupos_recolhiveis,
    )
