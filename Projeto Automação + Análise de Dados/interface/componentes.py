"""Fachada compatível dos componentes reutilizáveis do front-end empresarial.

V9.8: implementação separada por responsabilidade; imports públicos preservados.
"""

from interface.componentes_navegacao import (
    ITENS_NAVEGACAO, GRUPOS_NAVEGACAO, acao_em_preparacao,
    preparar_janela_secundaria, criar_botao_sidebar, criar_sidebar, criar_cabecalho,
)
from interface.componentes_basicos import (
    criar_card, criar_botao, criar_chip, criar_campo_pesquisa,
    criar_estado_vazio, criar_titulo_secao, criar_metrica, criar_card_acao,
)
from interface.componentes_responsivos import AreaRolavel, GradeResponsiva

__all__ = [
    "ITENS_NAVEGACAO", "GRUPOS_NAVEGACAO", "acao_em_preparacao",
    "preparar_janela_secundaria", "criar_botao_sidebar", "criar_sidebar", "criar_cabecalho",
    "criar_card", "criar_botao", "criar_chip", "criar_campo_pesquisa",
    "criar_estado_vazio", "criar_titulo_secao", "criar_metrica", "criar_card_acao",
    "AreaRolavel", "GradeResponsiva",
]
