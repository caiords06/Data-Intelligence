"""Serviços transacionais do Estoque 2.0.

O módulo trabalha com um razão imutável. Saldos, custo médio,
disponibilidade, alertas e indicadores são efeitos das operações confirmadas,
nunca campos alterados diretamente pela interface.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

import pandas as pd

from auth.banco import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator, tem_permissao


ACOES_ESTOQUE = {
    "consultar_custos", "cadastrar_item", "editar_item", "gerenciar_catalogos",
    "registrar_entrada", "registrar_saida", "confirmar_operacao",
    "aprovar_ajuste", "aprovar_transferencia", "receber_transferencia",
    "reservar", "inventariar", "aprovar_inventario", "registrar_avaria",
    "gerar_reposicao", "gerar_relatorio", "consultar_auditoria",
}

PERFIS_ACOES = {
    "estoque_operador": {
        "cadastrar_item", "registrar_entrada", "registrar_saida",
        "confirmar_operacao", "reservar", "inventariar", "registrar_avaria",
    },
    "estoque_analista": ACOES_ESTOQUE - {
        "aprovar_ajuste", "aprovar_transferencia", "aprovar_inventario",
    },
    "estoque_gestor": ACOES_ESTOQUE,
    "estoque_auditor": {"consultar_custos", "gerar_relatorio", "consultar_auditoria"},
    "estoque": ACOES_ESTOQUE - {"aprovar_ajuste", "aprovar_transferencia"},
    "estoque_plus": ACOES_ESTOQUE - {"aprovar_ajuste", "aprovar_transferencia"},
}

TIPOS_OPERACAO = {
    "Entrada", "Recebimento de compra", "Saída", "Consumo interno",
    "Transferência", "Ajuste", "Devolução ao estoque",
    "Devolução ao fornecedor", "Perda", "Avaria", "Vencimento",
}


def _texto(valor, limite=500) -> str:
    return str(valor or "").strip()[:limite]


def _quantidade(valor, *, permite_zero=False) -> float:
    texto = str(valor if valor is not None else "").strip().replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = float(texto)
    except (TypeError, ValueError) as erro:
        raise ValueError("Informe uma quantidade numérica válida.") from erro
    if not math.isfinite(numero) or numero < 0 or (numero == 0 and not permite_zero):
        raise ValueError("A quantidade deve ser maior que zero.")
    return numero


def _centavos(valor) -> int:
    texto = str(valor if valor is not None else "0").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as erro:
        raise ValueError("Informe um valor monetário válido.") from erro
    if not numero.is_finite() or numero < 0:
        raise ValueError("O valor monetário não pode ser negativo.")
    return int(numero * 100)


def _data(valor, *, obrigatoria=False) -> str | None:
    texto = _texto(valor, 20)
    if not texto and not obrigatoria:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Data inválida. Utilize DD/MM/AAAA ou AAAA-MM-DD.")


def _numero(prefixo: str) -> str:
    return f"{prefixo}-{datetime.now():%Y%m%d%H%M%S}-{uuid4().hex[:5].upper()}"


def tem_permissao_estoque(ator: dict | None, acao: str) -> bool:
    if acao not in ACOES_ESTOQUE or not tem_permissao(ator, "estoque", "ler"):
        return False
    if ator and ator.get("perfil") == "admin":
        return True
    try:
        empresa_id, _ = obter_escopo_ator(ator)
    except (PermissionError, RuntimeError):
        return False
    with conectar() as conexao:
        personalizado = conexao.execute(
            "SELECT permitido FROM est_permissoes_acoes WHERE usuario_id=? AND empresa_id=? AND acao=?",
            (int(ator["id"]), empresa_id, acao),
        ).fetchone()
    if personalizado is not None:
        return bool(personalizado["permitido"])
    perfil = _texto(ator.get("perfil_acesso"), 40).lower()
    if perfil in PERFIS_ACOES:
        return acao in PERFIS_ACOES[perfil]
    if acao in {"consultar_custos", "gerar_relatorio", "consultar_auditoria"}:
        return tem_permissao(ator, "estoque", "ler")
    if acao.startswith("aprovar_"):
        return tem_permissao(ator, "estoque", "aprovar")
    return tem_permissao(ator, "estoque", "escrever")


def exigir_acao(ator: dict | None, acao: str) -> None:
    if not tem_permissao_estoque(ator, acao):
        raise PermissionError(
            f"Seu perfil não possui permissão de Estoque para {acao.replace('_', ' ')}."
        )


def salvar_permissao_acao(usuario_id: int, acao: str, permitido: bool, ator: dict) -> None:
    if ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem configurar ações de Estoque.")
    if acao not in ACOES_ESTOQUE:
        raise ValueError("Ação de Estoque inválida.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            """INSERT INTO est_permissoes_acoes
               (usuario_id, empresa_id, acao, permitido, atualizado_por)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(usuario_id, empresa_id, acao) DO UPDATE SET
                 permitido=excluded.permitido, atualizado_por=excluded.atualizado_por,
                 atualizado_em=CURRENT_TIMESTAMP""",
            (int(usuario_id), empresa_id, acao, int(bool(permitido)), int(ator["id"])),
        )


def _evento(conexao, ator, acao, entidade, entidade_id, antes=None, depois=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """INSERT INTO historico_alteracoes (
            operacao_id, empresa_id, filial_id, usuario_id, modulo,
            entidade, entidade_id, acao, dados_antes, dados_depois
        ) VALUES (?, ?, ?, ?, 'estoque', ?, ?, ?, ?, ?)""",
        (
            str(uuid4()), empresa_id, filial_id, int(ator["id"]), entidade,
            int(entidade_id), acao,
            json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
            json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None,
        ),
    )
    conexao.execute(
        """INSERT INTO atividades (
            usuario_id, empresa_id, filial_id, modulo, acao, descricao, recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, 'estoque', ?, ?, ?, ?)""",
        (int(ator["id"]), empresa_id, filial_id, acao, f"Estoque: {entidade} #{entidade_id}", entidade, int(entidade_id)),
    )


def _notificar(conexao, ator, titulo, mensagem, nivel="aviso", recurso=None, recurso_id=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """INSERT INTO notificacoes (
            empresa_id, filial_id, modulo, titulo, mensagem, nivel, recurso_tipo, recurso_id
        ) VALUES (?, ?, 'estoque', ?, ?, ?, ?, ?)""",
        (empresa_id, filial_id, titulo, mensagem, nivel, recurso, recurso_id),
    )


def _criar_tarefa(conexao, ator, modulo, titulo, descricao, recurso, recurso_id, prioridade="Média") -> int:
    empresa_id, filial_id = obter_escopo_ator(ator)
    cursor = conexao.execute(
        """INSERT INTO tarefas (
            empresa_id, filial_id, modulo, titulo, descricao, prioridade,
            status, recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, ?, ?, ?, 'Pendente', ?, ?)""",
        (empresa_id, filial_id, modulo, titulo, descricao, prioridade, recurso, int(recurso_id)),
    )
    return int(cursor.lastrowid)


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


def criar_categoria(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_catalogos")
    empresa_id, _ = obter_escopo_ator(ator)
    codigo, nome = _texto(dados.get("codigo"), 30).upper(), _texto(dados.get("nome"), 120)
    if not codigo or not nome:
        raise ValueError("Código e nome da categoria são obrigatórios.")
    with conectar() as conexao:
        identificador = int(conexao.execute(
            "INSERT INTO est_categorias (empresa_id, codigo, nome, descricao) VALUES (?, ?, ?, ?)",
            (empresa_id, codigo, nome, _texto(dados.get("descricao"), 500)),
        ).lastrowid)
        _evento(conexao, ator, "categoria_criada", "est_categorias", identificador, depois=dados)
    return identificador


def criar_fornecedor(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_catalogos")
    empresa_id, _ = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 160)
    if not nome:
        raise ValueError("O nome do fornecedor é obrigatório.")
    with conectar() as conexao:
        identificador = int(conexao.execute(
            """INSERT INTO est_fornecedores
               (empresa_id, nome, documento, email, telefone, prazo_medio_dias, avaliacao)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, nome, _texto(dados.get("documento"), 30) or None,
             _texto(dados.get("email"), 150), _texto(dados.get("telefone"), 40),
             int(_quantidade(dados.get("prazo_medio_dias", 0), permite_zero=True)),
             min(10, _quantidade(dados.get("avaliacao", 0), permite_zero=True))),
        ).lastrowid)
        _evento(conexao, ator, "fornecedor_criado", "est_fornecedores", identificador, depois=dados)
    return identificador


def criar_deposito(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_catalogos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    codigo, nome = _texto(dados.get("codigo"), 30).upper(), _texto(dados.get("nome"), 120)
    if not codigo or not nome:
        raise ValueError("Código e nome do depósito são obrigatórios.")
    with conectar() as conexao:
        deposito_id = int(conexao.execute(
            """INSERT INTO est_depositos
               (empresa_id, filial_id, codigo, nome, tipo, endereco, capacidade, responsavel_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, codigo, nome, _texto(dados.get("tipo"), 60) or "Depósito",
             _texto(dados.get("endereco"), 300), _quantidade(dados.get("capacidade", 0), permite_zero=True),
             int(dados["responsavel_id"]) if dados.get("responsavel_id") else None),
        ).lastrowid)
        conexao.execute("INSERT INTO est_localizacoes (deposito_id, codigo) VALUES (?, 'GERAL')", (deposito_id,))
        _evento(conexao, ator, "deposito_criado", "est_depositos", deposito_id, depois=dados)
    return deposito_id


def criar_localizacao(deposito_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_catalogos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    codigo = _texto(dados.get("codigo"), 80).upper()
    if not codigo:
        raise ValueError("O código da localização é obrigatório.")
    with conectar() as conexao:
        deposito = conexao.execute("SELECT id FROM est_depositos WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(deposito_id), empresa_id, filial_id)).fetchone()
        if deposito is None:
            raise ValueError("Depósito fora do contexto atual.")
        identificador = int(conexao.execute(
            """INSERT INTO est_localizacoes
               (deposito_id, codigo, corredor, prateleira, nivel, posicao, capacidade)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (int(deposito_id), codigo, _texto(dados.get("corredor"), 30),
             _texto(dados.get("prateleira"), 30), _texto(dados.get("nivel"), 30),
             _texto(dados.get("posicao"), 30), _quantidade(dados.get("capacidade", 0), permite_zero=True)),
        ).lastrowid)
        _evento(conexao, ator, "localizacao_criada", "est_localizacoes", identificador, depois=dados)
    return identificador


def criar_item(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "cadastrar_item")
    garantir_catalogos(ator)
    empresa_id, _ = obter_escopo_ator(ator)
    codigo = _texto(dados.get("codigo"), 60).upper()
    nome = _texto(dados.get("nome") or dados.get("descricao"), 180)
    if not codigo or not nome:
        raise ValueError("Código e nome do item são obrigatórios.")
    minimo = _quantidade(dados.get("estoque_minimo", 0), permite_zero=True)
    maximo = _quantidade(dados.get("estoque_maximo", 0), permite_zero=True)
    if maximo and maximo < minimo:
        raise ValueError("O estoque máximo não pode ser menor que o mínimo.")
    campos = {
        "empresa_id": empresa_id, "codigo": codigo,
        "sku": _texto(dados.get("sku"), 80) or codigo,
        "codigo_barras": _texto(dados.get("codigo_barras"), 100) or None,
        "qr_code": _texto(dados.get("qr_code"), 160) or None,
        "nome": nome, "descricao": _texto(dados.get("descricao"), 1000),
        "categoria_id": int(dados["categoria_id"]) if dados.get("categoria_id") else None,
        "subcategoria": _texto(dados.get("subcategoria"), 120),
        "marca": _texto(dados.get("marca"), 100), "fabricante": _texto(dados.get("fabricante"), 120),
        "modelo": _texto(dados.get("modelo"), 120),
        "unidade_id": int(dados["unidade_id"]) if dados.get("unidade_id") else None,
        "peso": _quantidade(dados.get("peso", 0), permite_zero=True),
        "dimensoes": _texto(dados.get("dimensoes"), 100), "foto_caminho": _texto(dados.get("foto_caminho"), 500),
        "fornecedor_principal_id": int(dados["fornecedor_principal_id"]) if dados.get("fornecedor_principal_id") else None,
        "estoque_minimo": minimo, "estoque_maximo": maximo,
        "ponto_reposicao": _quantidade(dados.get("ponto_reposicao", minimo), permite_zero=True),
        "estoque_seguranca": _quantidade(dados.get("estoque_seguranca", 0), permite_zero=True),
        "consumo_medio_dia": _quantidade(dados.get("consumo_medio_dia", 0), permite_zero=True),
        "lead_time_dias": int(_quantidade(dados.get("lead_time_dias", 0), permite_zero=True)),
        "custo_medio_centavos": _centavos(dados.get("custo", 0)),
        "ultimo_custo_centavos": _centavos(dados.get("custo", 0)),
        "preco_referencia_centavos": _centavos(dados.get("preco_referencia", 0)),
        "metodo_custeio": _texto(dados.get("metodo_custeio"), 40) or "Custo médio",
        "controla_lote": int(bool(dados.get("controla_lote"))),
        "controla_validade": int(bool(dados.get("controla_validade"))),
        "controla_serie": int(bool(dados.get("controla_serie"))),
        "eh_patrimonio": int(bool(dados.get("eh_patrimonio"))),
        "status": _texto(dados.get("status"), 30) or "Ativo", "criado_por": int(ator["id"]),
    }
    colunas = list(campos)
    try:
        with conectar() as conexao:
            identificador = int(conexao.execute(
                f"INSERT INTO est_itens ({', '.join(colunas)}) VALUES ({', '.join('?' for _ in colunas)})",
                tuple(campos[x] for x in colunas),
            ).lastrowid)
            _evento(conexao, ator, "item_criado", "est_itens", identificador, depois=campos)
    except Exception as erro:
        if "UNIQUE" in str(erro).upper():
            raise ValueError("Código, SKU, código de barras ou QR já cadastrado.") from erro
        raise
    return identificador


def atualizar_item(item_id: int, dados: dict, ator: dict) -> None:
    exigir_acao(ator, "editar_item")
    empresa_id, _ = obter_escopo_ator(ator)
    permitidos = {
        "nome": lambda v: _texto(v, 180), "descricao": lambda v: _texto(v, 1000),
        "categoria_id": lambda v: int(v) if v else None, "marca": lambda v: _texto(v, 100),
        "modelo": lambda v: _texto(v, 120), "estoque_minimo": lambda v: _quantidade(v, permite_zero=True),
        "estoque_maximo": lambda v: _quantidade(v, permite_zero=True),
        "ponto_reposicao": lambda v: _quantidade(v, permite_zero=True),
        "estoque_seguranca": lambda v: _quantidade(v, permite_zero=True),
        "consumo_medio_dia": lambda v: _quantidade(v, permite_zero=True),
        "lead_time_dias": lambda v: int(_quantidade(v, permite_zero=True)),
        "status": lambda v: _texto(v, 30), "foto_caminho": lambda v: _texto(v, 500),
    }
    alteracoes = {k: permitidos[k](v) for k, v in dados.items() if k in permitidos}
    if not alteracoes:
        raise ValueError("Nenhuma alteração válida foi informada.")
    with conectar() as conexao:
        antes = conexao.execute("SELECT * FROM est_itens WHERE id=? AND empresa_id=?", (int(item_id), empresa_id)).fetchone()
        if antes is None:
            raise ValueError("Item não encontrado.")
        alteracoes.update({"atualizado_por": int(ator["id"])})
        atribuicoes = ", ".join(f"{k}=?" for k in alteracoes)
        conexao.execute(f"UPDATE est_itens SET {atribuicoes}, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (*alteracoes.values(), int(item_id)))
        _evento(conexao, ator, "item_atualizado", "est_itens", item_id, antes=dict(antes), depois=alteracoes)


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
            GROUP BY i.id ORDER BY i.nome LIMIT ? OFFSET ?""",
            (filial_id, filial_id, filial_id, *parametros, limite, deslocamento),
        ).fetchall()]
    for item in registros:
        item["disponivel"] = float(item["fisico"] or 0) - float(item["reservado"] or 0) - float(item["bloqueado"] or 0)
        if not custos:
            item["custo_medio_centavos"] = None; item["ultimo_custo_centavos"] = None; item["preco_referencia_centavos"] = None
    return {"registros": registros, "total": total, "pagina": int(pagina), "por_pagina": limite}


def obter_item(item_id: int, ator: dict) -> dict:
    pagina = listar_itens(ator, por_pagina=200)
    item = next((x for x in pagina["registros"] if int(x["id"]) == int(item_id)), None)
    if item is None:
        empresa_id, filial_id = obter_escopo_ator(ator)
        with conectar() as conexao:
            linha = conexao.execute("SELECT * FROM est_itens WHERE id=? AND empresa_id=?", (int(item_id), empresa_id)).fetchone()
            if linha is None:
                raise ValueError("Item não encontrado.")
            item = dict(linha)
            saldos = conexao.execute("SELECT COALESCE(SUM(quantidade_fisica),0) fisico, COALESCE(SUM(quantidade_reservada),0) reservado, COALESCE(SUM(quantidade_bloqueada),0) bloqueado FROM est_saldos WHERE item_id=? AND filial_id IS ?", (int(item_id), filial_id)).fetchone()
            item.update(dict(saldos)); item["disponivel"] = item["fisico"] - item["reservado"] - item["bloqueado"]
    return item


def _validar_deposito(conexao, deposito_id, empresa_id, filial_id):
    if not deposito_id:
        return None
    registro = conexao.execute(
        "SELECT * FROM est_depositos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
        (int(deposito_id), empresa_id, filial_id),
    ).fetchone()
    if registro is None:
        raise ValueError("Depósito não pertence ao contexto atual ou está inativo.")
    return registro


def _validar_localizacao(conexao, localizacao_id, deposito_id):
    if not localizacao_id:
        linha = conexao.execute(
            "SELECT id FROM est_localizacoes WHERE deposito_id=? AND ativo=1 ORDER BY id LIMIT 1",
            (int(deposito_id),),
        ).fetchone()
        return int(linha["id"]) if linha else None
    linha = conexao.execute(
        "SELECT id FROM est_localizacoes WHERE id=? AND deposito_id=? AND ativo=1 AND bloqueada=0",
        (int(localizacao_id), int(deposito_id)),
    ).fetchone()
    if linha is None:
        raise ValueError("Localização inválida, bloqueada ou fora do depósito selecionado.")
    return int(linha["id"])


def _obter_saldo(conexao, item_id, deposito_id, localizacao_id=None, lote_id=None):
    if localizacao_id is not None or lote_id is not None:
        return conexao.execute(
            """SELECT * FROM est_saldos WHERE item_id=? AND deposito_id=?
               AND localizacao_id IS ? AND lote_id IS ? ORDER BY id LIMIT 1""",
            (int(item_id), int(deposito_id), localizacao_id, lote_id),
        ).fetchone()
    return conexao.execute(
        """SELECT NULL AS id, COALESCE(SUM(quantidade_fisica),0) quantidade_fisica,
                  COALESCE(SUM(quantidade_reservada),0) quantidade_reservada,
                  COALESCE(SUM(quantidade_bloqueada),0) quantidade_bloqueada
           FROM est_saldos WHERE item_id=? AND deposito_id=?""",
        (int(item_id), int(deposito_id)),
    ).fetchone()


def _alterar_saldo(
    conexao, ator, *, item_id, deposito_id, localizacao_id, lote_id,
    quantidade, tipo, operacao_id=None, custo_centavos=0, motivo="", documento="",
    centro_custo_id=None, departamento_id=None,
):
    empresa_id, filial_id = obter_escopo_ator(ator)
    saldo = _obter_saldo(conexao, item_id, deposito_id, localizacao_id, lote_id)
    anterior = float(saldo["quantidade_fisica"] or 0) if saldo else 0.0
    posterior = anterior + float(quantidade)
    deposito = conexao.execute("SELECT permite_negativo FROM est_depositos WHERE id=?", (int(deposito_id),)).fetchone()
    if posterior < -1e-9 and not (deposito and bool(deposito["permite_negativo"])):
        raise ValueError("Saldo insuficiente. O Estoque 2.0 não permite quantidade negativa neste depósito.")
    if saldo and saldo["id"] is not None:
        conexao.execute(
            "UPDATE est_saldos SET quantidade_fisica=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (posterior, int(saldo["id"])),
        )
    else:
        conexao.execute(
            """INSERT INTO est_saldos (
                empresa_id, filial_id, item_id, deposito_id, localizacao_id, lote_id, quantidade_fisica
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, int(item_id), int(deposito_id), localizacao_id, lote_id, posterior),
        )
    conexao.execute(
        """INSERT INTO est_movimentacoes (
            empresa_id, filial_id, numero, operacao_id, item_id, deposito_id,
            localizacao_id, lote_id, tipo, quantidade, custo_unitario_centavos,
            saldo_anterior, saldo_posterior, centro_custo_id, departamento_id,
            motivo, documento, criado_por
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (empresa_id, filial_id, _numero("MOV"), operacao_id, int(item_id), int(deposito_id),
         localizacao_id, lote_id, tipo, float(quantidade), int(custo_centavos or 0),
         anterior, posterior, centro_custo_id, departamento_id, motivo, documento, int(ator["id"])),
    )
    return posterior


def _resolver_lote_entrada(conexao, item, linha, empresa_id):
    if not bool(item["controla_lote"]):
        return None
    numero = _texto(linha.get("lote_numero"), 100)
    if not numero:
        raise ValueError(f"O item {item['nome']} exige número de lote.")
    validade = _data(linha.get("validade"))
    if bool(item["controla_validade"]) and not validade:
        raise ValueError(f"O item {item['nome']} exige data de validade.")
    lote = conexao.execute(
        "SELECT id FROM est_lotes WHERE empresa_id=? AND item_id=? AND numero=?",
        (empresa_id, int(item["id"]), numero),
    ).fetchone()
    if lote:
        return int(lote["id"])
    return int(conexao.execute(
        """INSERT INTO est_lotes (
            empresa_id, item_id, numero, fabricante, fabricacao, validade, quantidade_original
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (empresa_id, int(item["id"]), numero, _texto(linha.get("fabricante"), 120),
         _data(linha.get("fabricacao")), validade, _quantidade(linha.get("quantidade"))),
    ).lastrowid)


def _resolver_lote_saida(conexao, item_id, deposito_id, quantidade, solicitado=None):
    if solicitado:
        saldo = conexao.execute(
            "SELECT lote_id, quantidade_fisica FROM est_saldos WHERE item_id=? AND deposito_id=? AND lote_id=? AND quantidade_fisica>0 ORDER BY id LIMIT 1",
            (int(item_id), int(deposito_id), int(solicitado)),
        ).fetchone()
        if saldo is None or float(saldo["quantidade_fisica"]) < quantidade:
            raise ValueError("O lote selecionado não possui saldo suficiente.")
        return int(solicitado)
    candidato = conexao.execute(
        """SELECT s.lote_id, s.quantidade_fisica FROM est_saldos s
           JOIN est_lotes l ON l.id=s.lote_id
           WHERE s.item_id=? AND s.deposito_id=? AND s.quantidade_fisica>=?
             AND l.status='Disponível' AND (l.validade IS NULL OR l.validade>=date('now'))
           ORDER BY CASE WHEN l.validade IS NULL THEN 1 ELSE 0 END, l.validade, l.id LIMIT 1""",
        (int(item_id), int(deposito_id), float(quantidade)),
    ).fetchone()
    if candidato is None:
        raise ValueError("Nenhum lote FEFO possui saldo suficiente para a saída.")
    return int(candidato["lote_id"])


def _validar_seriais(conexao, item, linha, *, entrada, empresa_id, deposito_id=None, localizacao_id=None, lote_id=None):
    if not bool(item["controla_serie"]):
        return
    seriais = linha.get("seriais") or linha.get("seriais_json") or []
    if isinstance(seriais, str):
        try:
            seriais = json.loads(seriais)
        except json.JSONDecodeError:
            seriais = [x.strip() for x in seriais.replace(";", ",").split(",") if x.strip()]
    seriais = [str(x).strip() for x in seriais if str(x).strip()]
    quantidade = _quantidade(linha.get("quantidade"))
    if not quantidade.is_integer() or len(seriais) != int(quantidade):
        raise ValueError(f"Informe um número de série para cada unidade de {item['nome']}.")
    if len(set(seriais)) != len(seriais):
        raise ValueError("Números de série duplicados na operação.")
    for serial in seriais:
        existente = conexao.execute("SELECT * FROM est_seriais WHERE empresa_id=? AND numero_serie=?", (empresa_id, serial)).fetchone()
        if entrada:
            if existente:
                raise ValueError(f"O número de série {serial} já existe.")
            conexao.execute(
                """INSERT INTO est_seriais (
                    empresa_id, item_id, lote_id, numero_serie, patrimonio, deposito_id,
                    localizacao_id, garantia_ate, data_compra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (empresa_id, int(item["id"]), lote_id, serial,
                 f"PAT-{serial}" if bool(item["eh_patrimonio"]) else None,
                 int(deposito_id), localizacao_id, _data(linha.get("garantia_ate")), date.today().isoformat()),
            )
        else:
            if not existente or existente["status"] != "Disponível" or int(existente["deposito_id"] or 0) != int(deposito_id):
                raise ValueError(f"O serial {serial} não está disponível no depósito de origem.")
            conexao.execute(
                "UPDATE est_seriais SET status='Baixado', deposito_id=NULL, localizacao_id=NULL WHERE id=?",
                (int(existente["id"]),),
            )


def criar_operacao(dados: dict, itens: list[dict], ator: dict) -> int:
    tipo = _texto(dados.get("tipo"), 60)
    if tipo not in TIPOS_OPERACAO:
        raise ValueError("Tipo de operação de estoque inválido.")
    acao = "registrar_entrada" if tipo in {"Entrada", "Recebimento de compra", "Devolução ao estoque"} else "registrar_saida"
    if tipo == "Transferência":
        acao = "aprovar_transferencia" if dados.get("aprovar_imediatamente") else "registrar_saida"
    exigir_acao(ator, acao)
    if not itens:
        raise ValueError("Inclua pelo menos um item na operação.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        origem = _validar_deposito(conexao, dados.get("deposito_origem_id"), empresa_id, filial_id)
        destino = _validar_deposito(conexao, dados.get("deposito_destino_id"), empresa_id, filial_id)
        entrada = tipo in {"Entrada", "Recebimento de compra", "Devolução ao estoque"}
        if entrada and destino is None:
            raise ValueError("A operação de entrada exige um depósito de destino.")
        if not entrada and tipo != "Ajuste" and origem is None:
            raise ValueError("A operação exige um depósito de origem.")
        if tipo == "Transferência" and (destino is None or origem is None or int(origem["id"]) == int(destino["id"])):
            raise ValueError("A transferência exige depósitos de origem e destino diferentes.")
        local_origem = _validar_localizacao(conexao, dados.get("localizacao_origem_id"), origem["id"]) if origem else None
        local_destino = _validar_localizacao(conexao, dados.get("localizacao_destino_id"), destino["id"]) if destino else None
        numero = _numero("TRF" if tipo == "Transferência" else "EST")
        status = "Aguardando aprovação" if tipo in {"Transferência", "Ajuste", "Perda", "Avaria", "Vencimento"} else "Rascunho"
        etapa = "Recebimento" if entrada else ("Solicitada" if tipo == "Transferência" else "Separação")
        operacao_id = int(conexao.execute(
            """INSERT INTO est_operacoes (
                empresa_id, filial_id, numero, tipo, etapa, status,
                deposito_origem_id, deposito_destino_id, localizacao_origem_id,
                localizacao_destino_id, fornecedor_id, departamento_id, centro_custo_id,
                solicitante_id, responsavel_id, documento_numero, motivo, observacao,
                origem_modulo, origem_recurso_tipo, origem_recurso_id, prevista_em, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, numero, tipo, etapa, status,
             int(origem["id"]) if origem else None, int(destino["id"]) if destino else None,
             local_origem, local_destino, int(dados["fornecedor_id"]) if dados.get("fornecedor_id") else None,
             int(dados["departamento_id"]) if dados.get("departamento_id") else None,
             int(dados["centro_custo_id"]) if dados.get("centro_custo_id") else None,
             int(dados["solicitante_id"]) if dados.get("solicitante_id") else int(ator["id"]),
             int(dados["responsavel_id"]) if dados.get("responsavel_id") else int(ator["id"]),
             _texto(dados.get("documento_numero"), 100), _texto(dados.get("motivo"), 500),
             _texto(dados.get("observacao"), 1000), _texto(dados.get("origem_modulo"), 60),
             _texto(dados.get("origem_recurso_tipo"), 80),
             int(dados["origem_recurso_id"]) if dados.get("origem_recurso_id") else None,
             _data(dados.get("prevista_em")), int(ator["id"])),
        ).lastrowid)
        total = 0
        for linha in itens:
            item = conexao.execute("SELECT * FROM est_itens WHERE id=? AND empresa_id=? AND status='Ativo'", (int(linha.get("item_id", 0)), empresa_id)).fetchone()
            if item is None:
                raise ValueError("Um dos itens não existe ou está inativo.")
            quantidade = _quantidade(linha.get("quantidade"))
            custo = _centavos(linha.get("custo_unitario", int(item["custo_medio_centavos"] or 0) / 100))
            lote_numero = _texto(linha.get("lote_numero"), 100)
            total += round(quantidade * custo)
            conexao.execute(
                """INSERT INTO est_operacao_itens (
                    operacao_id, item_id, quantidade_solicitada, custo_unitario_centavos,
                    lote_id, lote_numero, fabricacao, validade, seriais_json,
                    divergencia_motivo, observacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (operacao_id, int(item["id"]), quantidade, custo,
                 int(linha["lote_id"]) if linha.get("lote_id") else None, lote_numero,
                 _data(linha.get("fabricacao")), _data(linha.get("validade")),
                 json.dumps(linha.get("seriais") or [], ensure_ascii=False),
                 _texto(linha.get("divergencia_motivo"), 500), _texto(linha.get("observacao"), 500)),
            )
        conexao.execute("UPDATE est_operacoes SET valor_total_centavos=? WHERE id=?", (total, operacao_id))
        if status == "Aguardando aprovação":
            aprovacao_id = int(conexao.execute(
                """INSERT INTO aprovacoes (
                    empresa_id, filial_id, solicitante_id, modulo, recurso_tipo,
                    recurso_id, titulo, valor, status
                ) VALUES (?, ?, ?, 'estoque', 'est_operacoes', ?, ?, ?, 'Pendente')""",
                (empresa_id, filial_id, int(ator["id"]), operacao_id,
                 f"{tipo} {numero}", total / 100),
            ).lastrowid)
            conexao.execute("UPDATE est_operacoes SET aprovacao_id=? WHERE id=?", (aprovacao_id, operacao_id))
            _notificar(conexao, ator, f"{tipo} aguardando aprovação", numero, "aviso", "est_operacoes", operacao_id)
        _evento(conexao, ator, "operacao_criada", "est_operacoes", operacao_id, depois={"numero": numero, "tipo": tipo, "status": status})
    return operacao_id


def aprovar_operacao(operacao_id: int, aprovar: bool, observacao: str, ator: dict) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        operacao = conexao.execute("SELECT * FROM est_operacoes WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(operacao_id), empresa_id, filial_id)).fetchone()
        if operacao is None:
            raise ValueError("Operação não encontrada.")
        acao = "aprovar_transferencia" if operacao["tipo"] == "Transferência" else "aprovar_ajuste"
        exigir_acao(ator, acao)
        if operacao["status"] != "Aguardando aprovação":
            raise ValueError("A operação não está aguardando aprovação.")
        novo = "Aprovada" if aprovar else "Rejeitada"
        conexao.execute("UPDATE est_operacoes SET status=?, etapa=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (novo, "Separação" if aprovar else "Encerrada", int(operacao_id)))
        if operacao["aprovacao_id"]:
            conexao.execute("UPDATE aprovacoes SET status=?, observacao=?, responsavel_id=?, decidido_em=CURRENT_TIMESTAMP WHERE id=?", ("Aprovado" if aprovar else "Rejeitado", _texto(observacao, 1000), int(ator["id"]), int(operacao["aprovacao_id"])))
        _evento(conexao, ator, "operacao_aprovada" if aprovar else "operacao_rejeitada", "est_operacoes", operacao_id, antes={"status": operacao["status"]}, depois={"status": novo, "observacao": observacao})


def conferir_operacao(operacao_id: int, quantidades: dict[int, float], ator: dict) -> None:
    exigir_acao(ator, "confirmar_operacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        operacao = conexao.execute("SELECT * FROM est_operacoes WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(operacao_id), empresa_id, filial_id)).fetchone()
        if operacao is None or operacao["status"] not in {"Rascunho", "Aprovada", "Em conferência"}:
            raise ValueError("Operação indisponível para conferência.")
        for linha_id, quantidade in quantidades.items():
            conexao.execute("UPDATE est_operacao_itens SET quantidade_conferida=? WHERE id=? AND operacao_id=?", (_quantidade(quantidade, permite_zero=True), int(linha_id), int(operacao_id)))
        conexao.execute("UPDATE est_operacoes SET status='Em conferência', etapa='Conferência', atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(operacao_id),))
        _evento(conexao, ator, "operacao_conferida", "est_operacoes", operacao_id, depois=quantidades)


def confirmar_operacao(operacao_id: int, ator: dict) -> None:
    exigir_acao(ator, "confirmar_operacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        operacao = conexao.execute("SELECT * FROM est_operacoes WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(operacao_id), empresa_id, filial_id)).fetchone()
        if operacao is None:
            raise ValueError("Operação não encontrada.")
        permitidos = {"Rascunho", "Aprovada", "Em conferência"}
        if operacao["status"] not in permitidos:
            raise ValueError("Esta operação não pode ser confirmada no estado atual.")
        if operacao["tipo"] in {"Transferência", "Ajuste", "Perda", "Avaria", "Vencimento"} and operacao["status"] != "Aprovada":
            raise ValueError("A operação precisa ser aprovada antes da confirmação.")
        linhas = conexao.execute("SELECT * FROM est_operacao_itens WHERE operacao_id=? ORDER BY id", (int(operacao_id),)).fetchall()
        entrada = operacao["tipo"] in {"Entrada", "Recebimento de compra", "Devolução ao estoque"}
        for registro in linhas:
            linha = dict(registro)
            linha["quantidade"] = float(linha["quantidade_conferida"] or linha["quantidade_solicitada"])
            item = conexao.execute("SELECT * FROM est_itens WHERE id=?", (int(linha["item_id"]),)).fetchone()
            if entrada:
                lote_id = _resolver_lote_entrada(conexao, item, linha, empresa_id)
                _validar_seriais(conexao, item, linha, entrada=True, empresa_id=empresa_id, deposito_id=operacao["deposito_destino_id"], localizacao_id=operacao["localizacao_destino_id"], lote_id=lote_id)
                saldo_antes = conexao.execute("SELECT COALESCE(SUM(quantidade_fisica),0) AS q FROM est_saldos WHERE item_id=?", (int(item["id"]),)).fetchone()["q"]
                custo_antigo = int(item["custo_medio_centavos"] or 0)
                novo_custo = int(round((float(saldo_antes) * custo_antigo + linha["quantidade"] * int(linha["custo_unitario_centavos"])) / (float(saldo_antes) + linha["quantidade"]))) if float(saldo_antes) + linha["quantidade"] > 0 else int(linha["custo_unitario_centavos"])
                _alterar_saldo(conexao, ator, item_id=item["id"], deposito_id=operacao["deposito_destino_id"], localizacao_id=operacao["localizacao_destino_id"], lote_id=lote_id, quantidade=linha["quantidade"], tipo=operacao["tipo"], operacao_id=operacao_id, custo_centavos=linha["custo_unitario_centavos"], motivo=operacao["motivo"], documento=operacao["documento_numero"], centro_custo_id=operacao["centro_custo_id"], departamento_id=operacao["departamento_id"])
                conexao.execute("UPDATE est_itens SET custo_medio_centavos=?, ultimo_custo_centavos=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (novo_custo, int(linha["custo_unitario_centavos"]), int(item["id"])))
                conexao.execute("INSERT INTO est_custos_historico (empresa_id, item_id, operacao_id, custo_anterior_centavos, custo_novo_centavos, quantidade_entrada) VALUES (?, ?, ?, ?, ?, ?)", (empresa_id, int(item["id"]), operacao_id, custo_antigo, novo_custo, linha["quantidade"]))
            elif operacao["tipo"] == "Ajuste":
                alvo = float(linha["quantidade"])
                atual = float(_obter_saldo(conexao, item["id"], operacao["deposito_origem_id"], operacao["localizacao_origem_id"], linha.get("lote_id"))["quantidade_fisica"] or 0)
                diferenca = alvo - atual
                if diferenca:
                    _alterar_saldo(conexao, ator, item_id=item["id"], deposito_id=operacao["deposito_origem_id"], localizacao_id=operacao["localizacao_origem_id"], lote_id=linha.get("lote_id"), quantidade=diferenca, tipo="Ajuste", operacao_id=operacao_id, custo_centavos=item["custo_medio_centavos"], motivo=operacao["motivo"], documento=operacao["documento_numero"])
            else:
                lote_id = linha.get("lote_id")
                if bool(item["controla_lote"]):
                    lote_id = _resolver_lote_saida(conexao, item["id"], operacao["deposito_origem_id"], linha["quantidade"], lote_id)
                _validar_seriais(conexao, item, linha, entrada=False, empresa_id=empresa_id, deposito_id=operacao["deposito_origem_id"], localizacao_id=operacao["localizacao_origem_id"], lote_id=lote_id)
                if operacao["tipo"] == "Transferência" and bool(item["controla_serie"]):
                    seriais = json.loads(linha.get("seriais_json") or "[]")
                    if seriais:
                        marcadores = ",".join("?" for _ in seriais)
                        conexao.execute(
                            f"""UPDATE est_seriais
                                SET status='Em trânsito', deposito_id=NULL,
                                    localizacao_id=NULL
                                WHERE empresa_id=? AND numero_serie IN ({marcadores})""",
                            (empresa_id, *seriais),
                        )
                _alterar_saldo(conexao, ator, item_id=item["id"], deposito_id=operacao["deposito_origem_id"], localizacao_id=operacao["localizacao_origem_id"], lote_id=lote_id, quantidade=-linha["quantidade"], tipo="Transferência - saída" if operacao["tipo"] == "Transferência" else operacao["tipo"], operacao_id=operacao_id, custo_centavos=item["custo_medio_centavos"], motivo=operacao["motivo"], documento=operacao["documento_numero"], centro_custo_id=operacao["centro_custo_id"], departamento_id=operacao["departamento_id"])
        if operacao["tipo"] == "Transferência":
            conexao.execute("UPDATE est_operacoes SET status='Em trânsito', etapa='Em trânsito', confirmada_em=CURRENT_TIMESTAMP, confirmado_por=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(ator["id"]), int(operacao_id)))
        else:
            conexao.execute("UPDATE est_operacoes SET status='Concluída', etapa=?, confirmada_em=CURRENT_TIMESTAMP, confirmado_por=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", ("Armazenagem" if entrada else "Expedição", int(ator["id"]), int(operacao_id)))
        if operacao["tipo"] == "Recebimento de compra":
            _criar_tarefa(conexao, ator, "financeiro", f"Conferir documento do recebimento {operacao['numero']}", "O pedido foi recebido pelo Estoque e pode originar conta a pagar.", "est_operacoes", operacao_id, "Alta")
        _evento(conexao, ator, "operacao_confirmada", "est_operacoes", operacao_id, antes={"status": operacao["status"]}, depois={"status": "Em trânsito" if operacao["tipo"] == "Transferência" else "Concluída"})
    gerar_alertas_estoque(ator)


def receber_transferencia(operacao_id: int, ator: dict) -> None:
    exigir_acao(ator, "receber_transferencia")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        operacao = conexao.execute("SELECT * FROM est_operacoes WHERE id=? AND empresa_id=? AND filial_id IS ? AND tipo='Transferência'", (int(operacao_id), empresa_id, filial_id)).fetchone()
        if operacao is None or operacao["status"] != "Em trânsito":
            raise ValueError("A transferência não está aguardando recebimento.")
        linhas = conexao.execute("SELECT * FROM est_operacao_itens WHERE operacao_id=?", (int(operacao_id),)).fetchall()
        for linha in linhas:
            quantidade = float(linha["quantidade_conferida"] or linha["quantidade_solicitada"])
            item = conexao.execute("SELECT * FROM est_itens WHERE id=?", (int(linha["item_id"]),)).fetchone()
            _alterar_saldo(conexao, ator, item_id=item["id"], deposito_id=operacao["deposito_destino_id"], localizacao_id=operacao["localizacao_destino_id"], lote_id=linha["lote_id"], quantidade=quantidade, tipo="Transferência - entrada", operacao_id=operacao_id, custo_centavos=item["custo_medio_centavos"], motivo=operacao["motivo"], documento=operacao["documento_numero"])
            if bool(item["controla_serie"]):
                seriais = json.loads(linha["seriais_json"] or "[]")
                if seriais:
                    marcadores = ",".join("?" for _ in seriais)
                    conexao.execute(
                        f"""UPDATE est_seriais
                            SET status='Disponível', deposito_id=?, localizacao_id=?
                            WHERE empresa_id=? AND status='Em trânsito'
                              AND numero_serie IN ({marcadores})""",
                        (
                            int(operacao["deposito_destino_id"]),
                            operacao["localizacao_destino_id"],
                            empresa_id,
                            *seriais,
                        ),
                    )
        conexao.execute("UPDATE est_operacoes SET status='Concluída', etapa='Recebida', recebida_em=CURRENT_TIMESTAMP, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(operacao_id),))
        _evento(conexao, ator, "transferencia_recebida", "est_operacoes", operacao_id, depois={"status": "Concluída"})


def cancelar_operacao(operacao_id: int, motivo: str, ator: dict) -> None:
    exigir_acao(ator, "confirmar_operacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        operacao = conexao.execute("SELECT * FROM est_operacoes WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(operacao_id), empresa_id, filial_id)).fetchone()
        if operacao is None or operacao["status"] in {"Concluída", "Em trânsito"}:
            raise ValueError("Operação concluída ou em trânsito não pode ser apagada; use uma operação de estorno.")
        conexao.execute("UPDATE est_operacoes SET status='Cancelada', etapa='Encerrada', motivo=?, cancelada_em=CURRENT_TIMESTAMP WHERE id=?", (_texto(motivo, 500), int(operacao_id)))
        _evento(conexao, ator, "operacao_cancelada", "est_operacoes", operacao_id, antes={"status": operacao["status"]}, depois={"status": "Cancelada", "motivo": motivo})


def listar_operacoes(ator: dict, *, tipo="Todos", status="Todos", pesquisa="", limite=500) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtros, parametros = ["o.empresa_id=?", "o.filial_id IS ?"], [empresa_id, filial_id]
    if tipo != "Todos": filtros.append("o.tipo=?"); parametros.append(tipo)
    if status != "Todos": filtros.append("o.status=?"); parametros.append(status)
    if pesquisa:
        filtros.append("(o.numero LIKE ? OR o.documento_numero LIKE ? OR o.motivo LIKE ?)")
        termo = f"%{_texto(pesquisa, 100)}%"; parametros.extend([termo] * 3)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            f"""SELECT o.*, do.nome AS deposito_origem, dd.nome AS deposito_destino,
                COUNT(oi.id) AS itens, COALESCE(SUM(oi.quantidade_solicitada),0) AS unidades
                FROM est_operacoes o
                LEFT JOIN est_depositos do ON do.id=o.deposito_origem_id
                LEFT JOIN est_depositos dd ON dd.id=o.deposito_destino_id
                LEFT JOIN est_operacao_itens oi ON oi.operacao_id=o.id
                WHERE {' AND '.join(filtros)} GROUP BY o.id ORDER BY o.criado_em DESC LIMIT ?""",
            (*parametros, int(limite)),
        ).fetchall()]


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


def criar_reserva(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "reservar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    item_id, deposito_id = int(dados.get("item_id", 0)), int(dados.get("deposito_id", 0))
    quantidade = _quantidade(dados.get("quantidade"))
    with conectar() as conexao:
        item = conexao.execute("SELECT id, nome FROM est_itens WHERE id=? AND empresa_id=? AND status='Ativo'", (item_id, empresa_id)).fetchone()
        deposito = _validar_deposito(conexao, deposito_id, empresa_id, filial_id)
        if item is None or deposito is None:
            raise ValueError("Item ou depósito inválido.")
        saldo = _obter_saldo(conexao, item_id, deposito_id)
        disponivel = float(saldo["quantidade_fisica"] or 0) - float(saldo["quantidade_reservada"] or 0) - float(saldo["quantidade_bloqueada"] or 0)
        if quantidade > disponivel + 1e-9:
            raise ValueError(f"Saldo disponível insuficiente. Disponível: {disponivel:g}.")
        numero = _numero("RES")
        reserva_id = int(conexao.execute(
            """INSERT INTO est_reservas (
                empresa_id, filial_id, numero, item_id, deposito_id, localizacao_id,
                lote_id, quantidade, solicitante_id, departamento_id, centro_custo_id,
                finalidade, origem_modulo, origem_recurso_id, expira_em, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, numero, item_id, deposito_id,
             int(dados["localizacao_id"]) if dados.get("localizacao_id") else None,
             int(dados["lote_id"]) if dados.get("lote_id") else None, quantidade,
             int(dados["solicitante_id"]) if dados.get("solicitante_id") else int(ator["id"]),
             int(dados["departamento_id"]) if dados.get("departamento_id") else None,
             int(dados["centro_custo_id"]) if dados.get("centro_custo_id") else None,
             _texto(dados.get("finalidade"), 500) or "Reserva operacional",
             _texto(dados.get("origem_modulo"), 60),
             int(dados["origem_recurso_id"]) if dados.get("origem_recurso_id") else None,
             _data(dados.get("expira_em")), int(ator["id"])),
        ).lastrowid)
        # Reserva é agregada nas linhas de saldo existentes, começando pela mais antiga.
        restante = quantidade
        for linha in conexao.execute("SELECT id, quantidade_fisica, quantidade_reservada, quantidade_bloqueada FROM est_saldos WHERE item_id=? AND deposito_id=? ORDER BY id", (item_id, deposito_id)).fetchall():
            livre = max(0, float(linha["quantidade_fisica"]) - float(linha["quantidade_reservada"]) - float(linha["quantidade_bloqueada"]))
            parcela = min(livre, restante)
            if parcela:
                conexao.execute("UPDATE est_saldos SET quantidade_reservada=quantidade_reservada+?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (parcela, int(linha["id"])))
                restante -= parcela
            if restante <= 1e-9: break
        _evento(conexao, ator, "reserva_criada", "est_reservas", reserva_id, depois={"numero": numero, "item_id": item_id, "quantidade": quantidade})
    return reserva_id


def liberar_reserva(reserva_id: int, ator: dict, *, atender=False) -> None:
    exigir_acao(ator, "reservar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        reserva = conexao.execute("SELECT * FROM est_reservas WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(reserva_id), empresa_id, filial_id)).fetchone()
        if reserva is None or reserva["status"] != "Ativa":
            raise ValueError("Reserva não encontrada ou já encerrada.")
        restante = float(reserva["quantidade"] or 0) - float(reserva["quantidade_atendida"] or 0)
        for linha in conexao.execute("SELECT id, quantidade_reservada FROM est_saldos WHERE item_id=? AND deposito_id=? ORDER BY id", (int(reserva["item_id"]), int(reserva["deposito_id"]))).fetchall():
            parcela = min(restante, float(linha["quantidade_reservada"] or 0))
            if parcela:
                conexao.execute("UPDATE est_saldos SET quantidade_reservada=MAX(0, quantidade_reservada-?), atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (parcela, int(linha["id"])))
                restante -= parcela
            if restante <= 1e-9: break
        novo = "Atendida" if atender else "Liberada"
        conexao.execute("UPDATE est_reservas SET status=?, quantidade_atendida=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (novo, reserva["quantidade"] if atender else reserva["quantidade_atendida"], int(reserva_id)))
        _evento(conexao, ator, "reserva_encerrada", "est_reservas", reserva_id, antes={"status": "Ativa"}, depois={"status": novo})


def listar_reservas(ator: dict, *, status="Todos") -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    complemento, params = ("", []) if status == "Todos" else (" AND r.status=?", [status])
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            f"""SELECT r.*, i.codigo, i.nome AS item_nome, d.nome AS deposito_nome,
                u.nome AS solicitante_nome FROM est_reservas r
                JOIN est_itens i ON i.id=r.item_id JOIN est_depositos d ON d.id=r.deposito_id
                LEFT JOIN usuarios u ON u.id=r.solicitante_id
                WHERE r.empresa_id=? AND r.filial_id IS ? {complemento}
                ORDER BY r.criado_em DESC""", (empresa_id, filial_id, *params)).fetchall()]


def criar_solicitacao(dados: dict, ator: dict) -> int:
    exigir_permissao(ator, "estoque", "escrever")
    empresa_id, filial_id = obter_escopo_ator(ator)
    item_id, quantidade = int(dados.get("item_id", 0)), _quantidade(dados.get("quantidade"))
    justificativa = _texto(dados.get("justificativa"), 800)
    if not justificativa:
        raise ValueError("A justificativa da solicitação é obrigatória.")
    with conectar() as conexao:
        if conexao.execute("SELECT 1 FROM est_itens WHERE id=? AND empresa_id=?", (item_id, empresa_id)).fetchone() is None:
            raise ValueError("Item não encontrado.")
        numero = _numero("SOL")
        solicitacao_id = int(conexao.execute(
            """INSERT INTO est_solicitacoes (
                empresa_id, filial_id, numero, solicitante_id, departamento_id,
                centro_custo_id, item_id, quantidade, justificativa, prioridade
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, numero, int(ator["id"]),
             int(dados["departamento_id"]) if dados.get("departamento_id") else None,
             int(dados["centro_custo_id"]) if dados.get("centro_custo_id") else None,
             item_id, quantidade, justificativa, _texto(dados.get("prioridade"), 30) or "Normal"),
        ).lastrowid)
        aprovacao_id = int(conexao.execute(
            """INSERT INTO aprovacoes (
                empresa_id, filial_id, solicitante_id, modulo, recurso_tipo,
                recurso_id, titulo, status
            ) VALUES (?, ?, ?, 'estoque', 'est_solicitacoes', ?, ?, 'Pendente')""",
            (empresa_id, filial_id, int(ator["id"]), solicitacao_id, f"Solicitação {numero}"),
        ).lastrowid)
        conexao.execute("UPDATE est_solicitacoes SET aprovacao_id=? WHERE id=?", (aprovacao_id, solicitacao_id))
        _evento(conexao, ator, "solicitacao_criada", "est_solicitacoes", solicitacao_id, depois={"numero": numero, "item_id": item_id, "quantidade": quantidade})
    return solicitacao_id


def decidir_solicitacao(solicitacao_id: int, aprovar: bool, ator: dict) -> None:
    exigir_acao(ator, "aprovar_ajuste")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        solicitacao = conexao.execute("SELECT * FROM est_solicitacoes WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(solicitacao_id), empresa_id, filial_id)).fetchone()
        if solicitacao is None or solicitacao["status"] != "Solicitada":
            raise ValueError("Solicitação indisponível para decisão.")
        novo = "Aprovada" if aprovar else "Rejeitada"
        conexao.execute("UPDATE est_solicitacoes SET status=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (novo, int(solicitacao_id)))
        if solicitacao["aprovacao_id"]:
            conexao.execute("UPDATE aprovacoes SET status=?, responsavel_id=?, decidido_em=CURRENT_TIMESTAMP WHERE id=?", ("Aprovado" if aprovar else "Rejeitado", int(ator["id"]), int(solicitacao["aprovacao_id"])))
        _evento(conexao, ator, "solicitacao_aprovada" if aprovar else "solicitacao_rejeitada", "est_solicitacoes", solicitacao_id, depois={"status": novo})


def listar_solicitacoes(ator: dict) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT s.*, i.codigo, i.nome AS item_nome, u.nome AS solicitante_nome
               FROM est_solicitacoes s JOIN est_itens i ON i.id=s.item_id
               LEFT JOIN usuarios u ON u.id=s.solicitante_id
               WHERE s.empresa_id=? AND s.filial_id IS ? ORDER BY s.criado_em DESC""",
            (empresa_id, filial_id),
        ).fetchall()]


def iniciar_inventario(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "inventariar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    deposito_id = int(dados.get("deposito_id", 0))
    with conectar() as conexao:
        _validar_deposito(conexao, deposito_id, empresa_id, filial_id)
        numero = _numero("INV")
        inventario_id = int(conexao.execute(
            """INSERT INTO est_inventarios (
                empresa_id, filial_id, numero, deposito_id, tipo, descricao,
                categoria_id, contagem_cega, status, etapa, responsavel_id,
                previsto_inicio, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Em andamento', 'Contagem', ?, ?, ?)""",
            (empresa_id, filial_id, numero, deposito_id,
             _texto(dados.get("tipo"), 60) or "Geral", _texto(dados.get("descricao"), 500),
             int(dados["categoria_id"]) if dados.get("categoria_id") else None,
             int(bool(dados.get("contagem_cega", True))),
             int(dados["responsavel_id"]) if dados.get("responsavel_id") else int(ator["id"]),
             _data(dados.get("previsto_inicio")) or date.today().isoformat(), int(ator["id"])),
        ).lastrowid)
        categoria = " AND i.categoria_id=?" if dados.get("categoria_id") else ""
        params = [deposito_id]
        if dados.get("categoria_id"): params.append(int(dados["categoria_id"]))
        saldos = conexao.execute(
            f"""SELECT s.item_id, s.localizacao_id, s.lote_id, SUM(s.quantidade_fisica) AS quantidade
                FROM est_saldos s JOIN est_itens i ON i.id=s.item_id
                WHERE s.deposito_id=? {categoria} GROUP BY s.item_id, s.localizacao_id, s.lote_id""",
            params,
        ).fetchall()
        for saldo in saldos:
            conexao.execute(
                """INSERT INTO est_inventario_itens (
                    inventario_id, item_id, localizacao_id, lote_id, quantidade_sistema
                ) VALUES (?, ?, ?, ?, ?)""",
                (inventario_id, saldo["item_id"], saldo["localizacao_id"], saldo["lote_id"], saldo["quantidade"]),
            )
        _evento(conexao, ator, "inventario_iniciado", "est_inventarios", inventario_id, depois={"numero": numero, "deposito_id": deposito_id, "itens": len(saldos)})
    return inventario_id


def registrar_contagem(inventario_id: int, item_inventario_id: int, quantidade, ator: dict) -> None:
    exigir_acao(ator, "inventariar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    valor = _quantidade(quantidade, permite_zero=True)
    with conectar() as conexao:
        inventario = conexao.execute("SELECT * FROM est_inventarios WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(inventario_id), empresa_id, filial_id)).fetchone()
        if inventario is None or inventario["status"] != "Em andamento":
            raise ValueError("Inventário não está em contagem.")
        linha = conexao.execute("SELECT * FROM est_inventario_itens WHERE id=? AND inventario_id=?", (int(item_inventario_id), int(inventario_id))).fetchone()
        if linha is None:
            raise ValueError("Item do inventário não encontrado.")
        if linha["primeira_contagem"] is None:
            conexao.execute("UPDATE est_inventario_itens SET primeira_contagem=?, quantidade_final=?, divergencia=?-quantidade_sistema, contado_por=?, contado_em=CURRENT_TIMESTAMP WHERE id=?", (valor, valor, valor, int(ator["id"]), int(item_inventario_id)))
        else:
            conexao.execute("UPDATE est_inventario_itens SET segunda_contagem=?, quantidade_final=?, divergencia=?-quantidade_sistema, recontado_por=?, recontado_em=CURRENT_TIMESTAMP WHERE id=?", (valor, valor, valor, int(ator["id"]), int(item_inventario_id)))
        _evento(conexao, ator, "contagem_registrada", "est_inventario_itens", item_inventario_id, depois={"quantidade": valor})


def finalizar_inventario(inventario_id: int, ator: dict, *, aprovar_ajustes=False) -> None:
    exigir_acao(ator, "inventariar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        inventario = conexao.execute("SELECT * FROM est_inventarios WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(inventario_id), empresa_id, filial_id)).fetchone()
        if inventario is None or inventario["status"] != "Em andamento":
            raise ValueError("Inventário não está em andamento.")
        pendentes = conexao.execute("SELECT COUNT(*) AS n FROM est_inventario_itens WHERE inventario_id=? AND primeira_contagem IS NULL", (int(inventario_id),)).fetchone()["n"]
        if pendentes:
            raise ValueError(f"Ainda existem {pendentes} item(ns) sem contagem.")
        divergencias = conexao.execute("SELECT * FROM est_inventario_itens WHERE inventario_id=? AND ABS(divergencia)>0.000001", (int(inventario_id),)).fetchall()
        if divergencias and not (aprovar_ajustes and tem_permissao_estoque(ator, "aprovar_inventario")):
            aprovacao_id = int(conexao.execute(
                """INSERT INTO aprovacoes (
                    empresa_id, filial_id, solicitante_id, modulo, recurso_tipo, recurso_id,
                    titulo, status
                ) VALUES (?, ?, ?, 'estoque', 'est_inventarios', ?, ?, 'Pendente')""",
                (empresa_id, filial_id, int(ator["id"]), int(inventario_id), f"Ajustes do inventário {inventario['numero']}"),
            ).lastrowid)
            conexao.execute("UPDATE est_inventarios SET status='Aguardando aprovação', etapa='Aprovação', aprovacao_id=? WHERE id=?", (aprovacao_id, int(inventario_id)))
            _evento(conexao, ator, "inventario_aguardando_aprovacao", "est_inventarios", inventario_id, depois={"divergencias": len(divergencias)})
            return
        for linha in divergencias:
            _alterar_saldo(conexao, ator, item_id=linha["item_id"], deposito_id=inventario["deposito_id"], localizacao_id=linha["localizacao_id"], lote_id=linha["lote_id"], quantidade=float(linha["divergencia"]), tipo="Inventário", motivo=f"Ajuste do inventário {inventario['numero']}")
        conexao.execute("UPDATE est_inventarios SET status='Finalizado', etapa='Finalizado', finalizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(inventario_id),))
        _evento(conexao, ator, "inventario_finalizado", "est_inventarios", inventario_id, depois={"divergencias": len(divergencias)})


def aprovar_inventario(inventario_id: int, ator: dict) -> None:
    exigir_acao(ator, "aprovar_inventario")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        inventario = conexao.execute("SELECT * FROM est_inventarios WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(inventario_id), empresa_id, filial_id)).fetchone()
        if inventario is None or inventario["status"] != "Aguardando aprovação":
            raise ValueError("Inventário não aguarda aprovação.")
        conexao.execute("UPDATE est_inventarios SET status='Em andamento', etapa='Ajuste' WHERE id=?", (int(inventario_id),))
        if inventario["aprovacao_id"]:
            conexao.execute("UPDATE aprovacoes SET status='Aprovado', responsavel_id=?, decidido_em=CURRENT_TIMESTAMP WHERE id=?", (int(ator["id"]), int(inventario["aprovacao_id"])))
    finalizar_inventario(inventario_id, ator, aprovar_ajustes=True)


def listar_inventarios(ator: dict) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT i.*, d.nome AS deposito_nome, COUNT(ii.id) AS itens,
                SUM(CASE WHEN ABS(ii.divergencia)>0.000001 THEN 1 ELSE 0 END) AS divergencias
                FROM est_inventarios i JOIN est_depositos d ON d.id=i.deposito_id
                LEFT JOIN est_inventario_itens ii ON ii.inventario_id=i.id
                WHERE i.empresa_id=? AND i.filial_id IS ? GROUP BY i.id ORDER BY i.criado_em DESC""",
            (empresa_id, filial_id),
        ).fetchall()]


def itens_inventario(inventario_id: int, ator: dict) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        inventario = conexao.execute("SELECT contagem_cega FROM est_inventarios WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(inventario_id), empresa_id, filial_id)).fetchone()
        if inventario is None: raise ValueError("Inventário não encontrado.")
        registros = [dict(x) for x in conexao.execute(
            """SELECT ii.*, i.codigo, i.nome AS item_nome, l.codigo AS localizacao_codigo,
                lo.numero AS lote_numero FROM est_inventario_itens ii
                JOIN est_itens i ON i.id=ii.item_id
                LEFT JOIN est_localizacoes l ON l.id=ii.localizacao_id
                LEFT JOIN est_lotes lo ON lo.id=ii.lote_id
                WHERE ii.inventario_id=? ORDER BY i.nome""", (int(inventario_id),)).fetchall()]
    if bool(inventario["contagem_cega"]) and not tem_permissao_estoque(ator, "aprovar_inventario"):
        for item in registros: item["quantidade_sistema"] = None; item["divergencia"] = None
    return registros


def registrar_ocorrencia(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "registrar_avaria")
    empresa_id, filial_id = obter_escopo_ator(ator)
    tipo = _texto(dados.get("tipo"), 40) or "Avaria"
    quantidade = _quantidade(dados.get("quantidade"))
    motivo = _texto(dados.get("motivo"), 800)
    if not motivo: raise ValueError("Informe o motivo da ocorrência.")
    with conectar() as conexao:
        _validar_deposito(conexao, dados.get("deposito_id"), empresa_id, filial_id)
        numero = _numero("OCR")
        identificador = int(conexao.execute(
            """INSERT INTO est_ocorrencias (
                empresa_id, filial_id, numero, tipo, item_id, deposito_id,
                lote_id, serial_id, quantidade, motivo, destino, foto_caminho, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, numero, tipo, int(dados["item_id"]), int(dados["deposito_id"]),
             int(dados["lote_id"]) if dados.get("lote_id") else None,
             int(dados["serial_id"]) if dados.get("serial_id") else None,
             quantidade, motivo, _texto(dados.get("destino"), 60),
             _texto(dados.get("foto_caminho"), 500), int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "ocorrencia_registrada", "est_ocorrencias", identificador, depois={"numero": numero, "tipo": tipo, "quantidade": quantidade})
    return identificador


def listar_secao(secao: str, ator: dict, *, limite=500) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    consultas = {
        "depositos": ("SELECT d.*, u.nome responsavel_nome FROM est_depositos d LEFT JOIN usuarios u ON u.id=d.responsavel_id WHERE d.empresa_id=? AND d.filial_id IS ? ORDER BY d.nome", (empresa_id, filial_id)),
        "localizacoes": ("SELECT l.*, d.nome deposito_nome FROM est_localizacoes l JOIN est_depositos d ON d.id=l.deposito_id WHERE d.empresa_id=? AND d.filial_id IS ? ORDER BY d.nome,l.codigo", (empresa_id, filial_id)),
        "lotes": ("SELECT l.*, i.codigo, i.nome item_nome, COALESCE(SUM(s.quantidade_fisica),0) quantidade_restante FROM est_lotes l JOIN est_itens i ON i.id=l.item_id LEFT JOIN est_saldos s ON s.lote_id=l.id WHERE l.empresa_id=? GROUP BY l.id ORDER BY l.validade,l.id DESC", (empresa_id,)),
        "patrimonio": ("SELECT s.*, i.codigo, i.nome item_nome, d.nome deposito_nome, c.nome_completo colaborador_nome FROM est_seriais s JOIN est_itens i ON i.id=s.item_id LEFT JOIN est_depositos d ON d.id=s.deposito_id LEFT JOIN rh_colaboradores c ON c.id=s.colaborador_id WHERE s.empresa_id=? ORDER BY s.id DESC", (empresa_id,)),
        "avarias": ("SELECT o.*, i.nome item_nome, d.nome deposito_nome FROM est_ocorrencias o JOIN est_itens i ON i.id=o.item_id JOIN est_depositos d ON d.id=o.deposito_id WHERE o.empresa_id=? AND o.filial_id IS ? ORDER BY o.criado_em DESC", (empresa_id, filial_id)),
        "alertas": ("SELECT a.*, i.nome item_nome, d.nome deposito_nome FROM est_alertas a LEFT JOIN est_itens i ON i.id=a.item_id LEFT JOIN est_depositos d ON d.id=a.deposito_id WHERE a.empresa_id=? AND a.filial_id IS ? ORDER BY CASE a.severidade WHEN 'Crítico' THEN 0 ELSE 1 END,a.criado_em DESC", (empresa_id, filial_id)),
        "reposicao": ("SELECT r.*, i.codigo, i.nome item_nome, d.nome deposito_nome FROM est_reposicoes r JOIN est_itens i ON i.id=r.item_id JOIN est_depositos d ON d.id=r.deposito_id WHERE r.empresa_id=? AND r.filial_id IS ? ORDER BY r.criado_em DESC", (empresa_id, filial_id)),
        "solicitacoes": ("SELECT s.*, i.codigo, i.nome item_nome, u.nome solicitante_nome FROM est_solicitacoes s JOIN est_itens i ON i.id=s.item_id LEFT JOIN usuarios u ON u.id=s.solicitante_id WHERE s.empresa_id=? AND s.filial_id IS ? ORDER BY s.criado_em DESC", (empresa_id, filial_id)),
    }
    if secao not in consultas: return []
    sql, params = consultas[secao]
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(f"{sql} LIMIT ?", (*params, int(limite))).fetchall()]


def calcular_reposicao(ator: dict, *, criar_sugestoes=True) -> list[dict]:
    exigir_acao(ator, "gerar_reposicao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registros = conexao.execute(
            """SELECT i.id item_id, i.codigo, i.nome, i.estoque_minimo, i.estoque_maximo,
                i.ponto_reposicao, i.estoque_seguranca, i.consumo_medio_dia, i.lead_time_dias,
                d.id deposito_id, d.nome deposito_nome,
                COALESCE(SUM(s.quantidade_fisica-s.quantidade_reservada-s.quantidade_bloqueada),0) disponivel
                FROM est_itens i CROSS JOIN est_depositos d
                LEFT JOIN est_saldos s ON s.item_id=i.id AND s.deposito_id=d.id
                WHERE i.empresa_id=? AND i.status='Ativo' AND d.empresa_id=? AND d.filial_id IS ? AND d.ativo=1
                GROUP BY i.id,d.id""", (empresa_id, empresa_id, filial_id)).fetchall()
        sugestoes = []
        for linha in registros:
            disponivel = float(linha["disponivel"] or 0)
            consumo = float(linha["consumo_medio_dia"] or 0)
            ponto = max(float(linha["ponto_reposicao"] or 0), consumo * int(linha["lead_time_dias"] or 0) + float(linha["estoque_seguranca"] or 0), float(linha["estoque_minimo"] or 0))
            if disponivel > ponto:
                continue
            alvo = float(linha["estoque_maximo"] or 0) or max(ponto * 2, float(linha["estoque_minimo"] or 0))
            quantidade = max(0, alvo - disponivel)
            if quantidade <= 0: continue
            cobertura = disponivel / consumo if consumo > 0 else None
            item = {**dict(linha), "quantidade_sugerida": quantidade, "cobertura_dias": cobertura, "ponto_calculado": ponto}
            sugestoes.append(item)
            if criar_sugestoes:
                existente = conexao.execute("SELECT id FROM est_reposicoes WHERE item_id=? AND deposito_id=? AND status IN ('Sugerida','Encaminhada') ORDER BY id DESC LIMIT 1", (linha["item_id"], linha["deposito_id"])).fetchone()
                if existente is None:
                    conexao.execute(
                        """INSERT INTO est_reposicoes (
                            empresa_id, filial_id, item_id, deposito_id, saldo_disponivel,
                            consumo_medio_dia, cobertura_dias, quantidade_sugerida, justificativa
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (empresa_id, filial_id, linha["item_id"], linha["deposito_id"], disponivel,
                         consumo, cobertura, quantidade, f"Saldo {disponivel:g} abaixo do ponto de reposição {ponto:g}."),
                    )
        return sugestoes


def encaminhar_reposicao_compras(reposicao_id: int, ator: dict) -> int:
    exigir_acao(ator, "gerar_reposicao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        reposicao = conexao.execute("SELECT r.*, i.nome item_nome FROM est_reposicoes r JOIN est_itens i ON i.id=r.item_id WHERE r.id=? AND r.empresa_id=? AND r.filial_id IS ?", (int(reposicao_id), empresa_id, filial_id)).fetchone()
        if reposicao is None or reposicao["status"] != "Sugerida":
            raise ValueError("Sugestão de reposição indisponível.")
        compra_id = int(conexao.execute(
            """INSERT INTO solicitacoes_compra (
                empresa_id, filial_id, item, quantidade, fornecedor, valor_estimado,
                status, criado_por
            ) VALUES (?, ?, ?, ?, '', 0, 'Pendente', ?)""",
            (empresa_id, filial_id, reposicao["item_nome"], reposicao["quantidade_sugerida"], int(ator["id"])),
        ).lastrowid)
        tarefa_id = _criar_tarefa(conexao, ator, "compras", f"Cotizar reposição de {reposicao['item_nome']}", reposicao["justificativa"], "est_reposicoes", reposicao_id, "Alta")
        conexao.execute("UPDATE est_reposicoes SET status='Encaminhada', solicitacao_compra_id=?, tarefa_id=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (compra_id, tarefa_id, int(reposicao_id)))
        _evento(conexao, ator, "reposicao_encaminhada", "est_reposicoes", reposicao_id, depois={"solicitacao_compra_id": compra_id})
    return compra_id


def gerar_alertas_estoque(ator: dict) -> list[str]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    mensagens = []
    with conectar() as conexao:
        # Alertas recalculáveis são resolvidos e reabertos somente quando a condição persiste.
        conexao.execute("UPDATE est_alertas SET status='Resolvido', resolvido_em=CURRENT_TIMESTAMP WHERE empresa_id=? AND filial_id IS ? AND status='Aberto' AND tipo IN ('Crítico','Zerado','Acima do máximo','Validade','Vencido','Sem localização')", (empresa_id, filial_id))
        itens = conexao.execute(
            """SELECT i.*, d.id deposito_id, d.nome deposito_nome,
                COALESCE(SUM(s.quantidade_fisica-s.quantidade_reservada-s.quantidade_bloqueada),0) disponivel,
                MAX(s.localizacao_id) localizacao_id
                FROM est_itens i CROSS JOIN est_depositos d
                LEFT JOIN est_saldos s ON s.item_id=i.id AND s.deposito_id=d.id
                WHERE i.empresa_id=? AND i.status='Ativo' AND d.empresa_id=? AND d.filial_id IS ? AND d.ativo=1
                GROUP BY i.id,d.id""", (empresa_id, empresa_id, filial_id)).fetchall()
        for item in itens:
            disponivel = float(item["disponivel"] or 0)
            alertas = []
            if disponivel <= 0:
                alertas.append(("Zerado", "Crítico", f"{item['nome']} está sem saldo disponível."))
            elif disponivel < float(item["estoque_minimo"] or 0):
                alertas.append(("Crítico", "Crítico", f"{item['nome']}: {disponivel:g} disponível; mínimo {float(item['estoque_minimo'] or 0):g}."))
            if float(item["estoque_maximo"] or 0) > 0 and disponivel > float(item["estoque_maximo"]):
                alertas.append(("Acima do máximo", "Aviso", f"{item['nome']} está acima do estoque máximo."))
            if item["localizacao_id"] is None and disponivel > 0:
                alertas.append(("Sem localização", "Aviso", f"{item['nome']} possui saldo sem endereçamento definido."))
            for tipo, severidade, mensagem in alertas:
                mensagens.append(mensagem)
                existente = conexao.execute(
                    """SELECT id FROM est_alertas WHERE empresa_id=? AND tipo=?
                       AND item_id IS ? AND deposito_id IS ? AND lote_id IS NULL""",
                    (empresa_id, tipo, item["id"], item["deposito_id"]),
                ).fetchone()
                if existente:
                    conexao.execute(
                        """UPDATE est_alertas SET filial_id=?, severidade=?, titulo=?,
                           mensagem=?, status='Aberto', resolvido_por=NULL, resolvido_em=NULL
                           WHERE id=?""",
                        (filial_id, severidade, tipo, mensagem, existente["id"]),
                    )
                else:
                    conexao.execute(
                        """INSERT INTO est_alertas (
                            empresa_id, filial_id, tipo, severidade, titulo, mensagem,
                            item_id, deposito_id, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Aberto')""",
                        (empresa_id, filial_id, tipo, severidade, tipo, mensagem, item["id"], item["deposito_id"]),
                    )
        lotes = conexao.execute(
            """SELECT l.*, i.nome item_nome, s.deposito_id, SUM(s.quantidade_fisica) quantidade
               FROM est_lotes l JOIN est_itens i ON i.id=l.item_id JOIN est_saldos s ON s.lote_id=l.id
               WHERE l.empresa_id=? AND s.filial_id IS ? AND s.quantidade_fisica>0 AND l.validade IS NOT NULL
               GROUP BY l.id,s.deposito_id""", (empresa_id, filial_id)).fetchall()
        limite = (date.today() + timedelta(days=30)).isoformat()
        for lote in lotes:
            if lote["validade"] < date.today().isoformat():
                tipo, severidade, mensagem = "Vencido", "Crítico", f"Lote {lote['numero']} de {lote['item_nome']} está vencido."
                conexao.execute("UPDATE est_lotes SET status='Vencido' WHERE id=?", (lote["id"],))
            elif lote["validade"] <= limite:
                tipo, severidade, mensagem = "Validade", "Aviso", f"Lote {lote['numero']} de {lote['item_nome']} vence em {lote['validade']}."
            else:
                continue
            mensagens.append(mensagem)
            existente = conexao.execute(
                """SELECT id FROM est_alertas WHERE empresa_id=? AND tipo=?
                   AND item_id IS ? AND deposito_id IS ? AND lote_id IS ?""",
                (empresa_id, tipo, lote["item_id"], lote["deposito_id"], lote["id"]),
            ).fetchone()
            if existente:
                conexao.execute(
                    """UPDATE est_alertas SET filial_id=?, severidade=?, titulo=?, mensagem=?,
                       status='Aberto', resolvido_por=NULL, resolvido_em=NULL WHERE id=?""",
                    (filial_id, severidade, tipo, mensagem, existente["id"]),
                )
            else:
                conexao.execute(
                    """INSERT INTO est_alertas (
                        empresa_id, filial_id, tipo, severidade, titulo, mensagem,
                        item_id, deposito_id, lote_id, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Aberto')""",
                    (empresa_id, filial_id, tipo, severidade, tipo, mensagem, lote["item_id"], lote["deposito_id"], lote["id"]),
                )
    return mensagens


def resolver_alerta(alerta_id: int, ator: dict) -> None:
    exigir_acao(ator, "confirmar_operacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute("UPDATE est_alertas SET status='Resolvido', resolvido_por=?, resolvido_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(ator["id"]), int(alerta_id), empresa_id, filial_id))
        if cursor.rowcount == 0: raise ValueError("Alerta não encontrado.")
        _evento(conexao, ator, "alerta_resolvido", "est_alertas", alerta_id)


def resumo_estoque(ator: dict) -> dict:
    exigir_permissao(ator, "estoque", "ler")
    garantir_catalogos(ator)
    gerar_alertas_estoque(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        itens = conexao.execute(
            """SELECT i.id, i.estoque_minimo, i.estoque_maximo, i.custo_medio_centavos,
                COALESCE(SUM(s.quantidade_fisica),0) fisico,
                COALESCE(SUM(s.quantidade_reservada),0) reservado,
                COALESCE(SUM(s.quantidade_bloqueada),0) bloqueado
                FROM est_itens i LEFT JOIN est_saldos s ON s.item_id=i.id AND s.filial_id IS ?
                WHERE i.empresa_id=? AND i.status='Ativo' GROUP BY i.id""", (filial_id, empresa_id)).fetchall()
        disponiveis = [float(x["fisico"])-float(x["reservado"])-float(x["bloqueado"]) for x in itens]
        valor = sum(round(float(x["fisico"]) * int(x["custo_medio_centavos"] or 0)) for x in itens)
        hoje = date.today().isoformat()
        primeiro_mes = date.today().replace(day=1).isoformat()
        tipos = conexao.execute("SELECT tipo, COUNT(*) n FROM est_movimentacoes WHERE empresa_id=? AND filial_id IS ? AND criado_em>=? GROUP BY tipo", (empresa_id, filial_id, primeiro_mes)).fetchall()
        contagens = {x["tipo"]: int(x["n"]) for x in tipos}
        return {
            "itens": len(itens), "unidades": sum(float(x["fisico"]) for x in itens),
            "disponiveis": sum(disponiveis), "reservadas": sum(float(x["reservado"]) for x in itens),
            "valor_centavos": valor if tem_permissao_estoque(ator, "consultar_custos") else None,
            "criticos": sum(1 for x, d in zip(itens, disponiveis) if d > 0 and d < float(x["estoque_minimo"] or 0)),
            "zerados": sum(1 for d in disponiveis if d <= 0),
            "excedentes": sum(1 for x, d in zip(itens, disponiveis) if float(x["estoque_maximo"] or 0)>0 and d>float(x["estoque_maximo"])),
            "alertas": int(conexao.execute("SELECT COUNT(*) n FROM est_alertas WHERE empresa_id=? AND filial_id IS ? AND status='Aberto'", (empresa_id, filial_id)).fetchone()["n"]),
            "vencendo": int(conexao.execute("SELECT COUNT(*) n FROM est_lotes l JOIN est_saldos s ON s.lote_id=l.id WHERE l.empresa_id=? AND s.filial_id IS ? AND s.quantidade_fisica>0 AND l.validade BETWEEN ? AND date(?, '+30 day')", (empresa_id, filial_id, hoje, hoje)).fetchone()["n"]),
            "inventarios": int(conexao.execute("SELECT COUNT(*) n FROM est_inventarios WHERE empresa_id=? AND filial_id IS ? AND status!='Finalizado'", (empresa_id, filial_id)).fetchone()["n"]),
            "transferencias": int(conexao.execute("SELECT COUNT(*) n FROM est_operacoes WHERE empresa_id=? AND filial_id IS ? AND tipo='Transferência' AND status NOT IN ('Concluída','Cancelada','Rejeitada')", (empresa_id, filial_id)).fetchone()["n"]),
            "recebimentos": int(conexao.execute("SELECT COUNT(*) n FROM est_operacoes WHERE empresa_id=? AND filial_id IS ? AND tipo IN ('Entrada','Recebimento de compra') AND status NOT IN ('Concluída','Cancelada')", (empresa_id, filial_id)).fetchone()["n"]),
            "entradas_mes": sum(v for k,v in contagens.items() if "Entrada" in k or "Recebimento" in k),
            "saidas_mes": sum(v for k,v in contagens.items() if "Saída" in k or k in {"Consumo interno","Perda","Avaria","Vencimento"}),
        }


def analisar_estoque(ator: dict) -> dict:
    resumo = resumo_estoque(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        parados = [dict(x) for x in conexao.execute(
            """SELECT i.codigo, i.nome, COALESCE(MAX(m.criado_em), i.criado_em) ultima_movimentacao,
                COALESCE(SUM(s.quantidade_fisica),0) saldo, i.custo_medio_centavos
                FROM est_itens i LEFT JOIN est_movimentacoes m ON m.item_id=i.id
                LEFT JOIN est_saldos s ON s.item_id=i.id AND s.filial_id IS ?
                WHERE i.empresa_id=? GROUP BY i.id
                HAVING saldo>0 AND date(ultima_movimentacao)<date('now','-90 day')
                ORDER BY saldo*i.custo_medio_centavos DESC LIMIT 10""", (filial_id, empresa_id)).fetchall()]
        perdas = conexao.execute("SELECT COALESCE(SUM(ABS(quantidade)*custo_unitario_centavos),0) valor FROM est_movimentacoes WHERE empresa_id=? AND filial_id IS ? AND tipo IN ('Perda','Avaria','Vencimento') AND criado_em>=date('now','start of month')", (empresa_id, filial_id)).fetchone()["valor"]
        top = [dict(x) for x in conexao.execute(
            """SELECT i.codigo, i.nome, SUM(ABS(m.quantidade)) movimentado
               FROM est_movimentacoes m JOIN est_itens i ON i.id=m.item_id
               WHERE m.empresa_id=? AND m.filial_id IS ? AND m.criado_em>=date('now','-90 day')
               GROUP BY i.id ORDER BY movimentado DESC LIMIT 10""", (empresa_id, filial_id)).fetchall()]
    pontos = []
    if resumo["zerados"]: pontos.append(f"{resumo['zerados']} item(ns) estão sem estoque disponível.")
    if resumo["criticos"]: pontos.append(f"{resumo['criticos']} item(ns) estão abaixo do estoque mínimo.")
    if resumo["vencendo"]: pontos.append(f"{resumo['vencendo']} lote(s) vencem nos próximos 30 dias.")
    if parados: pontos.append(f"{len(parados)} item(ns) com saldo não se movimentam há pelo menos 90 dias.")
    if perdas: pontos.append(f"Perdas do mês representam R$ {int(perdas)/100:,.2f}.")
    return {"resumo": resumo, "pontos_atencao": pontos or ["Nenhuma anomalia relevante foi detectada."], "itens_parados": parados, "mais_movimentados": top, "perdas_centavos": int(perdas or 0)}


def exportar_dataframe_estoque(ator: dict) -> pd.DataFrame:
    registros = listar_itens(ator, por_pagina=200)["registros"]
    # Analytics nunca fica silenciosamente limitado à página visual.
    total = listar_itens(ator, por_pagina=1)["total"]
    todas = []
    for pagina in range(1, math.ceil(total / 200) + 1):
        todas.extend(listar_itens(ator, pagina=pagina, por_pagina=200)["registros"])
    colunas = ["codigo", "sku", "nome", "categoria_nome", "unidade", "fisico", "reservado", "bloqueado", "disponivel", "estoque_minimo", "estoque_maximo", "ponto_reposicao", "status"]
    if tem_permissao_estoque(ator, "consultar_custos"):
        colunas.extend(["custo_medio_centavos", "ultimo_custo_centavos"])
    return pd.DataFrame([{k: x.get(k) for k in colunas} for x in todas])


def _dataframe_relatorio(tipo: str, ator: dict) -> pd.DataFrame:
    normal = _texto(tipo, 80).lower()
    if normal in {"posição atual", "posicao atual", "estoque", "itens"}:
        return exportar_dataframe_estoque(ator)
    if normal in {"movimentações", "movimentacoes", "razão", "razao"}:
        return pd.DataFrame(listar_movimentacoes(ator, limite=100000))
    if normal in {"inventários", "inventarios"}:
        return pd.DataFrame(listar_inventarios(ator))
    if normal in {"lotes", "validade"}:
        return pd.DataFrame(listar_secao("lotes", ator, limite=100000))
    if normal in {"alertas", "críticos", "criticos"}:
        return pd.DataFrame(listar_secao("alertas", ator, limite=100000))
    if normal in {"rastreabilidade", "patrimônio", "patrimonio"}:
        return pd.DataFrame(listar_secao("patrimonio", ator, limite=100000))
    raise ValueError("Tipo de relatório de estoque não reconhecido.")


def gerar_relatorio_estoque(tipo: str, formato: str, destino: str | Path, ator: dict) -> str:
    exigir_acao(ator, "gerar_relatorio")
    dataframe = _dataframe_relatorio(tipo, ator)
    destino = Path(destino); destino.parent.mkdir(parents=True, exist_ok=True)
    formato = _texto(formato, 10).upper()
    if formato == "XLSX":
        dataframe.to_excel(destino, index=False)
    elif formato == "CSV":
        dataframe.to_csv(destino, index=False, encoding="utf-8-sig")
    elif formato == "PDF":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        documento = SimpleDocTemplate(str(destino), pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        estilos = getSampleStyleSheet(); elementos = [Paragraph(f"Estoque 2.0 · {tipo}", estilos["Title"]), Spacer(1, 8)]
        if dataframe.empty:
            elementos.append(Paragraph("Nenhum registro encontrado para os filtros selecionados.", estilos["BodyText"]))
        else:
            quadro = dataframe.fillna("").astype(str)
            limite_pdf = 5000
            if len(quadro) > limite_pdf:
                elementos.append(Paragraph(
                    f"ATENÇÃO: o PDF contém {limite_pdf:,} de {len(quadro):,} registros. Use XLSX/CSV para o conjunto integral.",
                    estilos["BodyText"],
                ))
                elementos.append(Spacer(1, 6))
            dados = [list(quadro.columns)] + quadro.head(limite_pdf).values.tolist()
            tabela = Table(dados, repeatRows=1, colWidths=[max(0.8*cm, 25*cm/max(1,len(dados[0])))]*len(dados[0]))
            tabela.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#142B48")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#94A3B8")), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 6), ("VALIGN", (0,0), (-1,-1), "TOP")]))
            elementos.append(tabela)
        documento.build(elementos)
    else:
        raise ValueError("Formato suportado: PDF, XLSX ou CSV.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        _evento(conexao, ator, "relatorio_gerado", "est_relatorios_agendados", 0, depois={"tipo": tipo, "formato": formato, "destino": str(destino)})
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="estoque", categoria="relatorio")
    except Exception:
        pass
    return str(destino)


def agendar_relatorio(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerar_relatorio")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        identificador = int(conexao.execute(
            """INSERT INTO est_relatorios_agendados (
                empresa_id, filial_id, tipo, formato, filtros_json, frequencia,
                horario, destinatarios, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, _texto(dados.get("tipo"), 80) or "Posição atual",
             _texto(dados.get("formato"), 10).upper() or "PDF",
             json.dumps(dados.get("filtros") or {}, ensure_ascii=False),
             _texto(dados.get("frequencia"), 40) or "Mensal",
             _texto(dados.get("horario"), 10) or "08:00",
             _texto(dados.get("destinatarios"), 1000), int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "relatorio_agendado", "est_relatorios_agendados", identificador, depois=dados)
    return identificador


def listar_auditoria_estoque(ator: dict, *, limite=500) -> list[dict]:
    exigir_acao(ator, "consultar_auditoria")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT h.*, u.nome usuario_nome FROM historico_alteracoes h
               LEFT JOIN usuarios u ON u.id=h.usuario_id
               WHERE h.empresa_id=? AND h.filial_id IS ? AND h.modulo='estoque'
               ORDER BY h.id DESC LIMIT ?""", (empresa_id, filial_id, int(limite))).fetchall()]

def obter_primeiro_item_operacao(operacao_id: int, ator: dict) -> int:
    """Retorna a primeira linha da operação respeitando empresa/filial.

    Existe para impedir que a interface faça SQL direto no banco-cache quando
    estiver conectada ao Servidor Corporativo.
    """
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT oi.id FROM est_operacao_itens oi
               JOIN est_operacoes o ON o.id=oi.operacao_id
               WHERE oi.operacao_id=? AND o.empresa_id=? AND o.filial_id IS ?
               ORDER BY oi.id LIMIT 1""",
            (int(operacao_id), empresa_id, filial_id),
        ).fetchone()
    if linha is None:
        raise ValueError("Operação sem itens.")
    return int(linha["id"])


# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
