"""Constantes técnicas e acesso às configurações persistidas."""

from configuracoes.preferencias import obter_preferencia

TEMPO_ABERTURA_NAVEGADOR = 15
TEMPO_CARREGAMENTO_PAGINA = 30


def obter_link_validacao() -> str:
    return str(obter_preferencia("url_validacao", "https://example.com"))
