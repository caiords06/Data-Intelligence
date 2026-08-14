"""Contrato das operações RPC que transportam arquivos entre estação e servidor.

O RPC transacional comum transporta apenas dados estruturados. Operações que
recebem um caminho selecionado na estação ou que geram um arquivo no servidor
usam estes contratos para que o arquivo atravesse HTTP sem expor caminhos do
filesystem do servidor ao cliente.
"""
from __future__ import annotations

# Funções em que um parâmetro aponta para arquivo EXISTENTE na estação.
RPC_ARQUIVO_ENTRADA: dict[tuple[str, str], str] = {
    ("enterprise.rh", "registrar_documento"): "caminho_origem",
    ("enterprise.financeiro", "anexar_documento"): "caminho",
    ("enterprise.financeiro", "importar_extrato"): "caminho",
    ("enterprise.compras", "registrar_documento_fornecedor"): "caminho_origem",
    ("enterprise.ferramentas", "registrar_documento"): "caminho_origem",
    ("enterprise.datasets", "importar_conjunto"): "caminho",
    ("enterprise.datasets", "substituir_arquivo_conjunto"): "caminho",
    ("enterprise.core_v11.documentos", "registrar_midia"): "caminho_origem",
    ("enterprise.core_v11.documentos", "registrar_documento"): "caminho_origem",
    ("enterprise.core_v11.documentos", "adicionar_versao_documento"): "caminho_origem",
    ("enterprise.core_v11.funcionarios", "registrar_avatar"): "caminho",
}

# Funções em que um parâmetro representa o DESTINO do artefato. Em
# Central/Cliente a UI usa ``server://nome`` e o resultado é promovido ao
# repositório corporativo sem download. O caminho local permanece apenas para
# desenvolvimento standalone explicitamente habilitado.
RPC_ARQUIVO_SAIDA_PARAM: dict[tuple[str, str], str] = {
    ("enterprise.rh", "gerar_relatorio_rh"): "destino",
    ("enterprise.compras", "gerar_pdf_pedido"): "destino",
    ("enterprise.compras", "gerar_relatorio_compras"): "destino",
    ("enterprise.estoque", "gerar_relatorio_estoque"): "destino",
    ("enterprise.tecnologia", "gerar_relatorio_tecnologia"): "destino",
}

# Funções que geram um artefato administrado pelo servidor e, no modo
# Central/Cliente, devem retornar apenas metadados. Não há download automático.
RPC_ARQUIVO_PERSISTE_SERVIDOR: set[tuple[str, str]] = {
    ("enterprise.rh", "gerar_contracheque"),
    ("enterprise.financeiro", "gerar_relatorio_financeiro"),
    ("enterprise.ferramentas", "gerar_relatorio"),
}

# Operações explicitamente de ABERTURA/USO podem pedir uma cópia transitória;
# a autoridade e o original continuam no servidor e a cópia é limpa no fim da sessão.
RPC_ARQUIVO_RETORNO: set[tuple[str, str]] = {
    ("enterprise.ferramentas", "obter_arquivo_relatorio"),
    ("enterprise.datasets", "obter_conjunto"),
}

MARCADOR_ENTRADA = "__di_rpc_input_file__"
MARCADOR_SAIDA = "__di_rpc_output_file__"


def operacao_arquivo(modulo: str, funcao: str) -> bool:
    chave = (str(modulo), str(funcao))
    return (
        chave in RPC_ARQUIVO_ENTRADA
        or chave in RPC_ARQUIVO_SAIDA_PARAM
        or chave in RPC_ARQUIVO_RETORNO
        or chave in RPC_ARQUIVO_PERSISTE_SERVIDOR
    )


__all__ = [
    "RPC_ARQUIVO_ENTRADA",
    "RPC_ARQUIVO_SAIDA_PARAM",
    "RPC_ARQUIVO_RETORNO",
    "RPC_ARQUIVO_PERSISTE_SERVIDOR",
    "MARCADOR_ENTRADA",
    "MARCADOR_SAIDA",
    "operacao_arquivo",
]
