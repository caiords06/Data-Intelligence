"""Catálogos e sincronização de legado do Estoque. V9.5."""
from __future__ import annotations

from enterprise.domains.estoque.base import (
    _numero, conectar, exigir_permissao, obter_escopo_ator,
)

def _sincronizar_legado(conexao, empresa_id: int, filial_id: int | None, ator: dict) -> None:
    deposito = conexao.execute(
        "SELECT id FROM est_depositos WHERE empresa_id=? AND filial_id IS ? ORDER BY id LIMIT 1",
        (empresa_id, filial_id),
    ).fetchone()
    if deposito is None:
        cursor = conexao.execute(
            """INSERT INTO est_depositos (empresa_id, filial_id, codigo, nome, tipo)
               VALUES (?, ?, 'PADRAO', 'Depósito principal', 'Depósito')""",
            (empresa_id, filial_id),
        )
        deposito_id = int(cursor.lastrowid)
    else:
        deposito_id = int(deposito["id"])
    local = conexao.execute(
        "SELECT id FROM est_localizacoes WHERE deposito_id=? ORDER BY id LIMIT 1", (deposito_id,)
    ).fetchone()
    if local is None:
        local_id = int(conexao.execute(
            "INSERT INTO est_localizacoes (deposito_id, codigo) VALUES (?, 'GERAL')", (deposito_id,)
        ).lastrowid)
    else:
        local_id = int(local["id"])
    unidade = conexao.execute(
        "SELECT id FROM est_unidades_medida WHERE empresa_id=? AND codigo='UN'", (empresa_id,)
    ).fetchone()
    if unidade is None:
        unidade_id = int(conexao.execute(
            "INSERT INTO est_unidades_medida (empresa_id, codigo, nome) VALUES (?, 'UN', 'Unidade')", (empresa_id,)
        ).lastrowid)
    else:
        unidade_id = int(unidade["id"])

    legados = conexao.execute(
        """SELECT * FROM itens_estoque WHERE empresa_id=? AND filial_id IS ?
           AND NOT EXISTS (SELECT 1 FROM est_itens e WHERE e.origem_legado_id=itens_estoque.id)""",
        (empresa_id, filial_id),
    ).fetchall()
    for legado in legados:
        item_id = int(conexao.execute(
            """INSERT INTO est_itens (
                empresa_id, codigo, sku, nome, descricao, unidade_id,
                estoque_minimo, custo_medio_centavos, ultimo_custo_centavos,
                status, origem_legado_id, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                empresa_id, legado["codigo"], legado["codigo"], legado["descricao"],
                legado["descricao"], unidade_id, float(legado["estoque_minimo"] or 0),
                int(legado["custo_centavos"] or round(float(legado["custo"] or 0) * 100)),
                int(legado["custo_centavos"] or round(float(legado["custo"] or 0) * 100)),
                legado["status"], int(legado["id"]), int(ator["id"]),
            ),
        ).lastrowid)
        quantidade = float(legado["quantidade"] or 0)
        if quantidade:
            saldo_id = int(conexao.execute(
                """INSERT INTO est_saldos (
                    empresa_id, filial_id, item_id, deposito_id, localizacao_id, quantidade_fisica
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (empresa_id, filial_id, item_id, deposito_id, local_id, quantidade),
            ).lastrowid)
            conexao.execute(
                """INSERT INTO est_movimentacoes (
                    empresa_id, filial_id, numero, item_id, deposito_id, localizacao_id,
                    tipo, quantidade, custo_unitario_centavos, saldo_anterior, saldo_posterior,
                    motivo, criado_por
                ) VALUES (?, ?, ?, ?, ?, ?, 'Migração', ?, ?, 0, ?, 'Saldo inicial legado', ?)""",
                (empresa_id, filial_id, _numero("MOV"), item_id, deposito_id, local_id,
                 quantidade, int(legado["custo_centavos"] or 0), quantidade, int(ator["id"])),
            )


def garantir_catalogos(ator: dict) -> None:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        for codigo, nome, casas in (("UN", "Unidade", 0), ("CX", "Caixa", 0), ("KG", "Quilograma", 3), ("LT", "Litro", 3), ("MT", "Metro", 2)):
            conexao.execute(
                "INSERT OR IGNORE INTO est_unidades_medida (empresa_id, codigo, nome, casas_decimais) VALUES (?, ?, ?, ?)",
                (empresa_id, codigo, nome, casas),
            )
        for codigo, nome in (("GERAL", "Geral"), ("TI", "Tecnologia"), ("ESCR", "Escritório"), ("INSUM", "Insumos"), ("PATR", "Patrimônio")):
            conexao.execute(
                "INSERT OR IGNORE INTO est_categorias (empresa_id, codigo, nome) VALUES (?, ?, ?)",
                (empresa_id, codigo, nome),
            )
        _sincronizar_legado(conexao, empresa_id, filial_id, ator)


def listar_catalogos(ator: dict) -> dict:
    garantir_catalogos(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        def linhas(sql, params):
            return [dict(x) for x in conexao.execute(sql, params).fetchall()]
        return {
            "unidades": linhas("SELECT * FROM est_unidades_medida WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)),
            "categorias": linhas("SELECT * FROM est_categorias WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)),
            "fornecedores": linhas("SELECT * FROM est_fornecedores WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)),
            "depositos": linhas("SELECT * FROM est_depositos WHERE empresa_id=? AND filial_id IS ? AND ativo=1 ORDER BY nome", (empresa_id, filial_id)),
            "localizacoes": linhas("""SELECT l.*, d.nome AS deposito_nome FROM est_localizacoes l JOIN est_depositos d ON d.id=l.deposito_id WHERE d.empresa_id=? AND d.filial_id IS ? AND l.ativo=1 ORDER BY d.nome, l.codigo""", (empresa_id, filial_id)),
            "departamentos": linhas("SELECT id, nome FROM departamentos WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)),
            "centros_custo": linhas("SELECT id, nome FROM centros_custo WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)),
        }
