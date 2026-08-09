"""Classificação semântica de bases tabulares."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalizar_texto(texto: object) -> str:
    texto = str(texto).lower().strip().replace("_", " ")
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


MAPEAMENTO_CAMPOS = {'id_venda': ['codigo venda',
              'código venda',
              'codigo_venda',
              'id venda',
              'id_venda',
              'numero venda',
              'número venda',
              'numero pedido',
              'número pedido',
              'id pedido',
              'id_pedido'],
 'data': ['data',
          'date',
          'data venda',
          'data_venda',
          'data da venda',
          'data cadastro',
          'data_cadastro',
          'data pedido',
          'data_pedido'],
 'cliente': ['cliente',
             'nome cliente',
             'nome_cliente',
             'customer',
             'cliente id',
             'id cliente',
             'id_cliente'],
 'produto': ['produto',
             'nome produto',
             'nome_produto',
             'item',
             'mercadoria',
             'sku',
             'codigo produto',
             'código produto',
             'codigo_produto',
             'código_produto'],
 'vendedor': ['vendedor', 'nome vendedor', 'nome_vendedor', 'representante', 'consultor', 'seller'],
 'loja': ['loja',
          'id loja',
          'id_loja',
          'codigo loja',
          'código loja',
          'codigo_loja',
          'código_loja',
          'filial',
          'unidade'],
 'regiao': ['regiao', 'região', 'regional', 'estado', 'uf', 'cidade', 'municipio', 'município'],
 'quantidade': ['quantidade',
                'qtd',
                'qtde',
                'quant',
                'unidades',
                'volume',
                'quantidade vendida',
                'quantidade_vendida'],
 'valor_unitario': ['valor unitario',
                    'valor unitário',
                    'valor_unitario',
                    'preco unitario',
                    'preço unitário',
                    'preco_unitario',
                    'preço_unitario',
                    'preco',
                    'preço'],
 'valor': ['valor',
           'valor venda',
           'valor_venda',
           'valor total',
           'valor_total',
           'valor final',
           'valor_final',
           'faturamento',
           'receita',
           'total venda',
           'total_venda'],
 'categoria': ['categoria', 'tipo', 'grupo', 'departamento', 'segmento'],
 'custo': ['custo',
           'custo total',
           'custo_total',
           'custo unitario',
           'custo_unitario',
           'custo médio',
           'custo medio'],
 'meta': ['meta', 'objetivo', 'target'],
 'estoque': ['estoque',
             'saldo estoque',
             'saldo_estoque',
             'estoque atual',
             'estoque_atual',
             'saldo'],
 'colaborador': ['colaborador',
                 'funcionario',
                 'funcionário',
                 'empregado',
                 'employee',
                 'nome colaborador',
                 'nome funcionario',
                 'nome funcionário',
                 'matricula',
                 'matrícula'],
 'setor': ['setor',
           'area',
           'área',
           'departamento rh',
           'departamento_rh',
           'centro custo',
           'centro de custo'],
 'admissao': ['admissao',
              'admissão',
              'data admissao',
              'data admissão',
              'data_admissao',
              'data_admissão'],
 'desligamento': ['desligamento',
                  'demissao',
                  'demissão',
                  'data desligamento',
                  'data_desligamento',
                  'data demissao',
                  'data demissão'],
 'salario': ['salario', 'salário', 'remuneracao', 'remuneração', 'vencimento', 'folha'],
 'status': ['status', 'situacao', 'situação', 'ativo', 'inativo']}

INDICADORES_POR_CATEGORIA = {'vendas': ['Faturamento total',
            'Quantidade vendida',
            'Ticket médio',
            'Preço médio por unidade',
            'Venda média',
            'Ranking de produtos',
            'Ranking de lojas',
            'Ranking de vendedores',
            'Ranking de regiões',
            'Evolução temporal',
            'Crescimento percentual',
            'Participação por produto',
            'Participação por loja'],
 'financeiro': ['Receita total',
                'Despesa total',
                'Saldo',
                'Média de receitas',
                'Média de despesas',
                'Variação financeira',
                'Evolução temporal'],
 'estoque': ['Estoque total',
             'Quantidade de produtos',
             'Produtos com baixo estoque',
             'Produtos sem movimentação',
             'Ranking de produtos',
             'Giro de estoque'],
 'cadastro': ['Quantidade de registros',
              'Registros duplicados',
              'Dados ausentes',
              'Distribuição por categoria',
              'Registros ativos',
              'Registros inativos'],
 'recursos_humanos': ['Total de colaboradores',
                      'Distribuição por setor',
                      'Admissões',
                      'Desligamentos',
                      'Colaboradores ativos e inativos',
                      'Custo/remuneração',
                      'Evolução temporal']}

_MAPEAMENTO_NORMALIZADO = {
    campo: {normalizar_texto(nome) for nome in nomes}
    for campo, nomes in MAPEAMENTO_CAMPOS.items()
}

_PESOS_CATEGORIA = {
    "vendas": {
        "id_venda": 5, "data": 3, "produto": 4, "quantidade": 3,
        "valor_unitario": 4, "valor": 6, "cliente": 2, "vendedor": 3,
        "loja": 3, "regiao": 1, "meta": 1,
    },
    "estoque": {
        "produto": 5, "quantidade": 4, "estoque": 7,
        "categoria": 2, "loja": 2, "data": 1,
    },
    "financeiro": {
        "data": 3, "valor": 5, "custo": 5, "categoria": 2,
    },
    "cadastro": {
        "cliente": 5, "categoria": 3, "data": 1, "status": 2,
    },
    "recursos_humanos": {
        "colaborador": 7, "setor": 4, "admissao": 4, "desligamento": 3,
        "salario": 4, "status": 2,
    },
}


def identificar_campo(coluna: object) -> str | None:
    coluna_normalizada = normalizar_texto(coluna)
    for campo, nomes_normalizados in _MAPEAMENTO_NORMALIZADO.items():
        if coluna_normalizada in nomes_normalizados:
            return campo
    return None


def identificar_tipo_coluna(
    df: pd.DataFrame,
    coluna: object,
    campo: str | None = None,
) -> str:
    serie = df[coluna]
    if campo in {"data", "admissao", "desligamento"}:
        return "temporal"
    if pd.api.types.is_datetime64_any_dtype(serie):
        return "temporal"
    if pd.api.types.is_numeric_dtype(serie):
        return "numerica"
    return "textual"


def identificar_campos(df: pd.DataFrame) -> dict:
    resultado = {}
    for coluna in df.columns:
        campo = identificar_campo(coluna)
        resultado[coluna] = {
            "campo": campo,
            "tipo": identificar_tipo_coluna(df, coluna, campo),
        }
    return resultado


def criar_mapa_campos(campos_identificados: dict) -> dict[str, object]:
    """Inverte o mapeamento para campo semântico -> coluna original."""
    mapa: dict[str, object] = {}
    for coluna, informacao in campos_identificados.items():
        campo = informacao.get("campo")
        if campo and campo not in mapa:
            mapa[campo] = coluna
    return mapa


def calcular_pontuacao_categoria(categoria: str, campos: list[str]) -> int:
    pesos = _PESOS_CATEGORIA.get(categoria, {})
    return sum(pesos.get(campo, 0) for campo in campos)


def calcular_confianca(pontuacao: int, pontuacoes: dict[str, int]) -> float:
    if not pontuacoes:
        return 0.0
    valores = sorted(pontuacoes.values(), reverse=True)
    maior = valores[0]
    if maior == 0:
        return 0.0
    segundo = valores[1] if len(valores) > 1 else 0
    diferenca = maior - segundo
    confianca = 50 + (diferenca / maior) * 50
    return round(min(max(confianca, 0.0), 100.0), 1)


def classificar_categoria(campos_identificados: dict) -> dict:
    campos = [
        info["campo"]
        for info in campos_identificados.values()
        if info.get("campo") is not None
    ]
    pontuacoes = {
        categoria: calcular_pontuacao_categoria(categoria, campos)
        for categoria in _PESOS_CATEGORIA
    }
    categoria_vencedora = max(pontuacoes, key=pontuacoes.get)
    maior_pontuacao = pontuacoes[categoria_vencedora]
    if maior_pontuacao == 0:
        return {"categoria": "desconhecida", "confianca": 0.0, "pontuacao": pontuacoes}
    return {
        "categoria": categoria_vencedora,
        "confianca": calcular_confianca(maior_pontuacao, pontuacoes),
        "pontuacao": pontuacoes,
    }


def obter_indicadores_sugeridos(categoria: str) -> list[str]:
    return list(INDICADORES_POR_CATEGORIA.get(categoria, []))


def classificar_dataframe(df: pd.DataFrame) -> dict:
    if df is None:
        raise ValueError("DataFrame não informado para classificação.")
    campos = identificar_campos(df)
    categoria = classificar_categoria(campos)
    return {
        "categoria": categoria["categoria"],
        "confianca": categoria["confianca"],
        "pontuacao": categoria["pontuacao"],
        "campos": campos,
        "indicadores_sugeridos": obter_indicadores_sugeridos(categoria["categoria"]),
    }
