"""Consultas de leitura do Estoque. V9.5."""
from __future__ import annotations

from enterprise.domains.estoque.base import (
    _texto, conectar, exigir_permissao, obter_escopo_ator, tem_permissao_estoque,
)
from .catalogos import garantir_catalogos

def listar_itens(ator: dict, *, pesquisa="", status="Todos", pagina=1, por_pagina=50) -> dict:
    exigir_permissao(ator, "estoque", "ler")
    garantir_catalogos(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtros, parametros = ["i.empresa_id=?"], [empresa_id]
    if pesquisa:
        filtros.append("(i.nome LIKE ? OR i.codigo LIKE ? OR i.sku LIKE ? OR i.codigo_barras LIKE ?)")
        termo = f"%{_texto(pesquisa, 120)}%"; parametros.extend([termo] * 4)
    if status != "Todos":
        filtros.append("i.status=?"); parametros.append(status)
    onde = " AND ".join(filtros)
    limite, deslocamento = max(1, min(200, int(por_pagina))), max(0, (int(pagina) - 1) * int(por_pagina))
    custos = tem_permissao_estoque(ator, "consultar_custos")
    with conectar() as conexao:
        total = int(conexao.execute(f"SELECT COUNT(*) AS n FROM est_itens i WHERE {onde}", parametros).fetchone()["n"])
        registros = [dict(x) for x in conexao.execute(
            f"""SELECT i.*, c.nome AS categoria_nome, u.codigo AS unidade,
                COALESCE(SUM(CASE WHEN s.filial_id IS ? THEN s.quantidade_fisica ELSE 0 END),0) AS fisico,
                COALESCE(SUM(CASE WHEN s.filial_id IS ? THEN s.quantidade_reservada ELSE 0 END),0) AS reservado,
                COALESCE(SUM(CASE WHEN s.filial_id IS ? THEN s.quantidade_bloqueada ELSE 0 END),0) AS bloqueado
            FROM est_itens i
            LEFT JOIN est_categorias c ON c.id=i.categoria_id
            LEFT JOIN est_unidades_medida u ON u.id=i.unidade_id
            LEFT JOIN est_saldos s ON s.item_id=i.id
            WHERE {onde}
            GROUP BY i.id, c.nome, u.codigo ORDER BY i.nome LIMIT ? OFFSET ?""",
            (filial_id, filial_id, filial_id, *parametros, limite, deslocamento),
        ).fetchall()]
    for item in registros:
        item["disponivel"] = float(item["fisico"] or 0) - float(item["reservado"] or 0) - float(item["bloqueado"] or 0)
        if not custos:
            item["custo_medio_centavos"] = None; item["ultimo_custo_centavos"] = None; item["preco_referencia_centavos"] = None
    return {"registros": registros, "total": total, "pagina": int(pagina), "por_pagina": limite}


def listar_movimentacoes(ator: dict, *, item_id=None, deposito_id=None, limite=1000) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtros, parametros = ["m.empresa_id=?", "m.filial_id IS ?"], [empresa_id, filial_id]
    if item_id: filtros.append("m.item_id=?"); parametros.append(int(item_id))
    if deposito_id: filtros.append("m.deposito_id=?"); parametros.append(int(deposito_id))
    with conectar() as conexao:
        registros = [dict(x) for x in conexao.execute(
            f"""SELECT m.*, i.codigo, i.nome AS item_nome, d.nome AS deposito_nome,
                l.codigo AS localizacao_codigo, lo.numero AS lote_numero, u.nome AS usuario_nome
                FROM est_movimentacoes m JOIN est_itens i ON i.id=m.item_id
                JOIN est_depositos d ON d.id=m.deposito_id
                LEFT JOIN est_localizacoes l ON l.id=m.localizacao_id
                LEFT JOIN est_lotes lo ON lo.id=m.lote_id
                LEFT JOIN usuarios u ON u.id=m.criado_por
                WHERE {' AND '.join(filtros)} ORDER BY m.id DESC LIMIT ?""",
            (*parametros, int(limite)),
        ).fetchall()]
    if not tem_permissao_estoque(ator, "consultar_custos"):
        for item in registros: item["custo_unitario_centavos"] = None
    return registros


def listar_inventarios(ator: dict) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT i.*, d.nome AS deposito_nome, COUNT(ii.id) AS itens,
                SUM(CASE WHEN ABS(ii.divergencia)>0.000001 THEN 1 ELSE 0 END) AS divergencias
                FROM est_inventarios i JOIN est_depositos d ON d.id=i.deposito_id
                LEFT JOIN est_inventario_itens ii ON ii.inventario_id=i.id
                WHERE i.empresa_id=? AND i.filial_id IS ? GROUP BY i.id, d.nome ORDER BY i.criado_em DESC""",
            (empresa_id, filial_id),
        ).fetchall()]
