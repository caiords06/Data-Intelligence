"""Serviços do departamento Financeiro.

O módulo concentra o ciclo completo:
registrar -> classificar -> aprovar -> liquidar -> conciliar -> contabilizar
-> analisar -> auditar. Valores monetários são sempre persistidos em centavos.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import math
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

import pandas as pd

from auth import banco as banco_auth
from enterprise.repositories import conectar
from enterprise.contexto import (
    obter_escopo_ator,
    tem_permissao,
)

from enterprise.domains.financeiro.base import (
    ACOES_FINANCEIRAS,
    NATUREZAS,
    STATUS_ABERTOS,
    STATUS_TERMINAIS,
    GRUPOS_DRE,
    _centavos,
    _moeda,
    _data_iso,
    _somar_meses,
    _proxima_periodicidade,
    _normalizar_texto,
    tem_permissao_financeira,
    exigir_acao,
    salvar_permissao_acao,
    _registrar_evento,
    _notificar,
    _sincronizar_legado,
    _validar_referencia,
)


def criar_conta(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _normalizar_texto(dados.get("nome"), 120)
    if len(nome) < 2:
        raise ValueError("Informe um nome para a conta.")
    saldo = _centavos(dados.get("saldo_inicial", 0), permite_negativo=True)
    tipo = dados.get("tipo") or "Conta corrente"
    if tipo not in {"Conta corrente", "Poupança", "Investimento", "Caixa físico", "Carteira digital"}:
        raise ValueError("Tipo de conta inválido.")
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO fin_contas (
                empresa_id,filial_id,nome,banco,agencia,numero,tipo,
                saldo_inicial_centavos,data_saldo_inicial,responsavel_id,
                criado_por,atualizado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id, filial_id, nome, _normalizar_texto(dados.get("banco"), 100),
                _normalizar_texto(dados.get("agencia"), 30),
                _normalizar_texto(dados.get("numero"), 40), tipo, saldo,
                _data_iso(dados.get("data_saldo_inicial")) or date.today().isoformat(),
                int(dados["responsavel_id"]) if dados.get("responsavel_id") else None,
                int(ator["id"]), int(ator["id"]),
            ),
        )
        conta_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "conta_criada", "fin_contas", conta_id, depois=dados)
    return conta_id


def criar_parte(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _normalizar_texto(dados.get("nome"), 160)
    if len(nome) < 2:
        raise ValueError("Informe o nome do cliente ou fornecedor.")
    tipo = dados.get("tipo") or "Ambos"
    if tipo not in {"Cliente", "Fornecedor", "Ambos"}:
        raise ValueError("Tipo de parte inválido.")
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO fin_partes (
                empresa_id,filial_id,tipo,nome,documento,email,telefone,
                banco,chave_pix,criado_por,atualizado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id, filial_id, tipo, nome,
                _normalizar_texto(dados.get("documento"), 30) or None,
                _normalizar_texto(dados.get("email"), 160),
                _normalizar_texto(dados.get("telefone"), 40),
                _normalizar_texto(dados.get("banco"), 100),
                _normalizar_texto(dados.get("chave_pix"), 160),
                int(ator["id"]), int(ator["id"]),
            ),
        )
        parte_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "parte_criada", "fin_partes", parte_id, depois=dados)
    return parte_id


def criar_categoria(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar")
    empresa_id, _ = obter_escopo_ator(ator)
    nome = _normalizar_texto(dados.get("nome"), 120)
    natureza = dados.get("natureza") or "Ambos"
    if not nome or natureza not in {"Receita", "Despesa", "Ambos"}:
        raise ValueError("Categoria ou natureza inválida.")
    with conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO fin_categorias (empresa_id,nome,natureza,plano_conta_id) VALUES (?,?,?,?)",
            (empresa_id, nome, natureza, int(dados["plano_conta_id"]) if dados.get("plano_conta_id") else None),
        )
        categoria_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "categoria_criada", "fin_categorias", categoria_id, depois=dados)
    return categoria_id


def _status_inicial(natureza: str, solicitado: str | None) -> str:
    if solicitado:
        return str(solicitado)
    if natureza in {"Conta a pagar", "Reembolso"}:
        return "Aguardando aprovação"
    if natureza == "Conta a receber":
        return "Previsto"
    if natureza == "Transferência":
        return "Liquidado"
    return "Rascunho"


def criar_lancamento(dados: dict, ator: dict) -> list[int]:
    exigir_acao(ator, "criar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    natureza = str(dados.get("natureza") or "").strip()
    if natureza not in NATUREZAS:
        raise ValueError("Selecione uma natureza financeira válida.")
    descricao = _normalizar_texto(dados.get("descricao"), 240)
    if len(descricao) < 2:
        raise ValueError("Informe uma descrição para o lançamento.")
    valor_total = _centavos(dados.get("valor"))
    if valor_total <= 0:
        raise ValueError("O valor precisa ser maior que zero.")
    competencia = _data_iso(dados.get("competencia"), obrigatoria=True)
    vencimento = _data_iso(dados.get("vencimento"))
    parcelas = max(1, min(int(dados.get("parcelas") or 1), 360))
    if natureza == "Transferência" and parcelas != 1:
        raise ValueError("Transferências não podem ser parceladas.")
    grupo = str(uuid4()) if parcelas > 1 else None
    base = valor_total // parcelas
    resto = valor_total % parcelas
    status = _status_inicial(natureza, dados.get("status"))
    if status not in STATUS_ABERTOS | STATUS_TERMINAIS:
        raise ValueError("Status financeiro inválido.")
    ids: list[int] = []
    with conectar() as conexao:
        referencias = {
            "departamento_id": _validar_referencia(conexao, "departamentos", dados.get("departamento_id"), empresa_id),
            "centro_custo_id": _validar_referencia(conexao, "centros_custo", dados.get("centro_custo_id"), empresa_id),
            "projeto_id": _validar_referencia(conexao, "fin_projetos", dados.get("projeto_id"), empresa_id, filial_id=filial_id),
            "conta_id": _validar_referencia(conexao, "fin_contas", dados.get("conta_id"), empresa_id, filial_id=filial_id),
            "conta_destino_id": _validar_referencia(conexao, "fin_contas", dados.get("conta_destino_id"), empresa_id, filial_id=filial_id),
            "plano_conta_id": _validar_referencia(conexao, "fin_plano_contas", dados.get("plano_conta_id"), empresa_id),
            "categoria_id": _validar_referencia(conexao, "fin_categorias", dados.get("categoria_id"), empresa_id),
            "parte_id": _validar_referencia(conexao, "fin_partes", dados.get("parte_id"), empresa_id, filial_id=filial_id),
        }
        natureza_classificacao = (
            "Receita" if natureza in {"Receita", "Conta a receber"}
            else "Despesa" if natureza in {"Despesa", "Conta a pagar", "Reembolso"}
            else "Neutra" if natureza == "Transferência" else None
        )
        if referencias["plano_conta_id"] and natureza_classificacao:
            plano = conexao.execute(
                "SELECT natureza,aceita_lancamento FROM fin_plano_contas WHERE id=?",
                (referencias["plano_conta_id"],),
            ).fetchone()
            if not plano["aceita_lancamento"] or plano["natureza"] != natureza_classificacao:
                raise ValueError("A conta contábil não aceita lançamentos desta natureza.")
        if referencias["categoria_id"] and natureza_classificacao != "Neutra":
            categoria = conexao.execute(
                "SELECT natureza FROM fin_categorias WHERE id=?",
                (referencias["categoria_id"],),
            ).fetchone()
            if categoria["natureza"] not in {natureza_classificacao, "Ambos"}:
                raise ValueError("A categoria não corresponde à natureza do lançamento.")
        if natureza == "Transferência":
            if not referencias["conta_id"] or not referencias["conta_destino_id"]:
                raise ValueError("Informe as contas de origem e destino.")
            if referencias["conta_id"] == referencias["conta_destino_id"]:
                raise ValueError("As contas de origem e destino precisam ser diferentes.")
        for indice in range(parcelas):
            valor_parcela = base + (1 if indice < resto else 0)
            vencimento_parcela = _somar_meses(vencimento, indice) if vencimento else None
            competencia_parcela = _somar_meses(competencia, indice) if dados.get("competencia_por_parcela") else competencia
            liquidado = valor_parcela if natureza == "Transferência" else 0
            cursor = conexao.execute(
                """
                INSERT INTO fin_lancamentos (
                    empresa_id,filial_id,departamento_id,centro_custo_id,
                    projeto_id,conta_id,conta_destino_id,plano_conta_id,
                    categoria_id,parte_id,natureza,descricao,competencia,
                    vencimento,valor_original_centavos,valor_liquidado_centavos,
                    status,forma_pagamento,documento_numero,nota_fiscal,
                    observacoes,tags,parcela_atual,total_parcelas,
                    grupo_parcelamento,origem_modulo,origem_recurso_tipo,
                    origem_recurso_id,contabilizado,criado_por,atualizado_por
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    empresa_id, filial_id, referencias["departamento_id"],
                    referencias["centro_custo_id"], referencias["projeto_id"],
                    referencias["conta_id"], referencias["conta_destino_id"],
                    referencias["plano_conta_id"], referencias["categoria_id"],
                    referencias["parte_id"], natureza,
                    f"{descricao} ({indice + 1}/{parcelas})" if parcelas > 1 else descricao,
                    competencia_parcela, vencimento_parcela, valor_parcela, liquidado,
                    status, _normalizar_texto(dados.get("forma_pagamento"), 80),
                    _normalizar_texto(dados.get("documento_numero"), 80),
                    _normalizar_texto(dados.get("nota_fiscal"), 80),
                    _normalizar_texto(dados.get("observacoes"), 2000),
                    _normalizar_texto(dados.get("tags"), 300), indice + 1, parcelas,
                    grupo, _normalizar_texto(dados.get("origem_modulo"), 60) or None,
                    _normalizar_texto(dados.get("origem_recurso_tipo"), 80) or None,
                    int(dados["origem_recurso_id"]) if dados.get("origem_recurso_id") else None,
                    int(natureza == "Transferência"), int(ator["id"]), int(ator["id"]),
                ),
            )
            lancamento_id = int(cursor.lastrowid)
            ids.append(lancamento_id)
            _registrar_evento(conexao, ator, "lancamento_criado", "fin_lancamentos", lancamento_id, depois={**dados, "valor_centavos": valor_parcela})
            if status == "Aguardando aprovação":
                _criar_etapas_aprovacao(conexao, lancamento_id, valor_parcela, ator)
        if dados.get("recorrente"):
            periodicidade = dados.get("periodicidade") or "Mensal"
            if periodicidade not in {"Semanal", "Mensal", "Trimestral", "Anual"}:
                raise ValueError("Periodicidade inválida.")
            conexao.execute(
                """
                INSERT INTO fin_recorrencias (
                    empresa_id,filial_id,descricao,periodicidade,inicio,fim,
                    proxima_geracao,modelo_json,criado_por
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    empresa_id, filial_id, descricao, periodicidade, competencia,
                    _data_iso(dados.get("recorrencia_fim")),
                    _proxima_periodicidade(competencia, periodicidade),
                    json.dumps(dados, ensure_ascii=False, default=str), int(ator["id"]),
                ),
            )
    return ids


def _criar_etapas_aprovacao(conexao, lancamento_id: int, valor_centavos: int, ator: dict) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    regras = conexao.execute(
        """
        SELECT nivel,perfil_aprovador FROM fin_regras_aprovacao
        WHERE empresa_id=? AND ativo=1 AND valor_minimo_centavos<=?
          AND (valor_maximo_centavos IS NULL OR valor_maximo_centavos>=?)
        ORDER BY nivel
        """,
        (empresa_id, valor_centavos, valor_centavos),
    ).fetchall()
    for regra in regras:
        conexao.execute(
            """
            INSERT OR IGNORE INTO fin_aprovacoes (
                empresa_id,filial_id,lancamento_id,nivel,perfil_aprovador
            ) VALUES (?,?,?,?,?)
            """,
            (empresa_id, filial_id, lancamento_id, regra["nivel"], regra["perfil_aprovador"]),
        )
    if not regras:
        conexao.execute(
            "UPDATE fin_lancamentos SET status='Aprovado',atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (lancamento_id,),
        )
    else:
        lancamento = conexao.execute(
            "SELECT descricao FROM fin_lancamentos WHERE id=?", (lancamento_id,)
        ).fetchone()
        conexao.execute(
            """
            INSERT INTO aprovacoes (
                empresa_id,filial_id,solicitante_id,modulo,recurso_tipo,
                recurso_id,titulo,valor,valor_centavos,status
            ) VALUES (?,?,?,'financeiro','fin_lancamentos',?,?,?,?,'Pendente')
            """,
            (
                empresa_id, filial_id, int(ator["id"]), lancamento_id,
                f"Aprovação financeira · {lancamento['descricao']}",
                valor_centavos / 100, valor_centavos,
            ),
        )


def submeter_aprovacao(lancamento_id: int, ator: dict) -> None:
    exigir_acao(ator, "solicitar_aprovacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None:
            raise ValueError("Lançamento não encontrado.")
        if registro["status"] not in {"Rascunho", "Previsto", "Faturado", "Enviado"}:
            raise ValueError("Este lançamento não pode ser submetido no status atual.")
        conexao.execute(
            "UPDATE fin_lancamentos SET status='Aguardando aprovação',atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(ator["id"]), int(lancamento_id)),
        )
        _criar_etapas_aprovacao(conexao, int(lancamento_id), int(registro["valor_original_centavos"]), ator)
        _registrar_evento(conexao, ator, "aprovacao_solicitada", "fin_lancamentos", int(lancamento_id), antes=dict(registro), depois={"status": "Aguardando aprovação"})


def _ator_atende_perfil_aprovador(ator: dict, perfil_exigido: str) -> bool:
    if str(ator.get("perfil", "")).lower() == "admin":
        return True
    perfil = str(ator.get("perfil_acesso") or "").strip().lower()
    exigido = str(perfil_exigido or "").strip().lower()
    if exigido == "financeiro":
        return perfil.startswith("financeiro") or perfil in {"compras_plus", "compras_gestor", "diretoria"}
    if exigido in {"gestor", "gerente", "gerência", "gerencia"}:
        return "gestor" in perfil or perfil in {"diretoria", "rh_diretoria"}
    if exigido in {"diretor", "diretoria"}:
        return perfil in {"diretoria", "rh_diretoria"}
    return perfil == exigido


def decidir_aprovacao(
    lancamento_id: int,
    decisao: str,
    comentario: str,
    ator: dict,
    *,
    aprovacao_id: int | None = None,
) -> None:
    exigir_acao(ator, "aprovar")
    if decisao not in {"Aprovado", "Rejeitado", "Alteração solicitada"}:
        raise ValueError("Decisão inválida.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None or registro["status"] != "Aguardando aprovação":
            raise ValueError("Lançamento não aguarda aprovação.")
        etapa = conexao.execute(
            "SELECT * FROM fin_aprovacoes WHERE lancamento_id=? AND status='Pendente' ORDER BY nivel LIMIT 1",
            (int(lancamento_id),),
        ).fetchone()
        if etapa is None:
            raise ValueError("Não existe etapa de aprovação pendente.")
        if aprovacao_id is not None and int(etapa["id"]) != int(aprovacao_id):
            raise ValueError("A etapa anterior precisa ser decidida antes desta aprovação.")
        if not _ator_atende_perfil_aprovador(ator, etapa["perfil_aprovador"]):
            raise PermissionError(
                f"Esta etapa exige o perfil de aprovação: {etapa['perfil_aprovador']}."
            )
        conexao.execute(
            "UPDATE fin_aprovacoes SET status=?,comentario=?,aprovador_id=?,decidido_em=CURRENT_TIMESTAMP WHERE id=?",
            (decisao, _normalizar_texto(comentario, 1000), int(ator["id"]), int(etapa["id"])),
        )
        proxima = conexao.execute(
            "SELECT 1 FROM fin_aprovacoes WHERE lancamento_id=? AND status='Pendente'",
            (int(lancamento_id),),
        ).fetchone()
        if decisao == "Aprovado" and proxima is None:
            novo_status = "Aprovado"
            central = "Aprovado"
        elif decisao == "Rejeitado":
            novo_status = "Cancelado"
            central = "Rejeitado"
        elif decisao == "Alteração solicitada":
            novo_status = "Rascunho"
            central = "Alteração solicitada"
        else:
            novo_status = "Aguardando aprovação"
            central = "Pendente"
        conexao.execute(
            "UPDATE fin_lancamentos SET status=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (novo_status, int(ator["id"]), int(lancamento_id)),
        )
        conexao.execute(
            "UPDATE aprovacoes SET status=?,responsavel_id=?,observacao=?,decidido_em=CASE WHEN ?!='Pendente' THEN CURRENT_TIMESTAMP ELSE decidido_em END "
            "WHERE modulo='financeiro' AND recurso_tipo='fin_lancamentos' AND recurso_id=? AND excluido_em IS NULL",
            (central, int(ator["id"]), _normalizar_texto(comentario, 1000), central, int(lancamento_id)),
        )
        _registrar_evento(conexao, ator, "aprovacao_decidida", "fin_lancamentos", int(lancamento_id), antes={"status": registro["status"]}, depois={"status": novo_status, "decisao": decisao})


def registrar_baixa(lancamento_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "liquidar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    principal = _centavos(dados.get("valor"))
    juros = _centavos(dados.get("juros", 0))
    multa = _centavos(dados.get("multa", 0))
    desconto = _centavos(dados.get("desconto", 0))
    if principal <= 0:
        raise ValueError("O valor da baixa deve ser maior que zero.")
    conta_id = int(dados.get("conta_id") or 0)
    if not conta_id:
        raise ValueError("Selecione a conta da liquidação.")
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None:
            raise ValueError("Lançamento não encontrado.")
        if registro["status"] in {"Aguardando aprovação", "Rascunho", "Cancelado", "Estornado", "Conciliado"}:
            raise ValueError("O lançamento não pode ser liquidado no status atual.")
        _validar_referencia(conexao, "fin_contas", conta_id, empresa_id, filial_id=filial_id)
        saldo = int(registro["valor_original_centavos"]) - int(registro["valor_liquidado_centavos"])
        if principal > saldo:
            raise ValueError(f"A baixa excede o saldo restante de {_moeda(saldo)}.")
        cursor = conexao.execute(
            """
            INSERT INTO fin_baixas (
                empresa_id,filial_id,lancamento_id,conta_id,data,
                principal_centavos,juros_centavos,multa_centavos,
                desconto_centavos,forma_pagamento,referencia,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id, filial_id, int(lancamento_id), conta_id,
                _data_iso(dados.get("data"), obrigatoria=True), principal,
                juros, multa, desconto,
                _normalizar_texto(dados.get("forma_pagamento"), 80),
                _normalizar_texto(dados.get("referencia"), 120), int(ator["id"]),
            ),
        )
        total = int(registro["valor_liquidado_centavos"]) + principal
        completo = total >= int(registro["valor_original_centavos"])
        if completo:
            novo_status = "Recebido" if registro["natureza"] in {"Receita", "Conta a receber"} else "Pago"
        else:
            novo_status = "Parcial"
        conexao.execute(
            """
            UPDATE fin_lancamentos SET
                conta_id=?,valor_liquidado_centavos=?,juros_centavos=juros_centavos+?,
                multa_centavos=multa_centavos+?,desconto_centavos=desconto_centavos+?,
                liquidacao=?,status=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                conta_id, total, juros, multa, desconto,
                _data_iso(dados.get("data"), obrigatoria=True), novo_status,
                int(ator["id"]), int(lancamento_id),
            ),
        )
        baixa_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "baixa_registrada", "fin_lancamentos", int(lancamento_id), antes=dict(registro), depois={"status": novo_status, "valor_liquidado_centavos": total})
    return baixa_id


def contabilizar_lancamento(lancamento_id: int, ator: dict) -> None:
    exigir_acao(ator, "contabilizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None or registro["status"] not in {"Pago", "Recebido", "Liquidado", "Conciliado"}:
            raise ValueError("Somente lançamentos liquidados podem ser contabilizados.")
        if not registro["plano_conta_id"] and registro["natureza"] != "Transferência":
            raise ValueError("Classifique o lançamento no plano de contas antes de contabilizar.")
        conexao.execute(
            "UPDATE fin_lancamentos SET contabilizado=1,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(ator["id"]), int(lancamento_id)),
        )
        _registrar_evento(conexao, ator, "lancamento_contabilizado", "fin_lancamentos", int(lancamento_id), antes={"contabilizado": 0}, depois={"contabilizado": 1})


def cancelar_lancamento(lancamento_id: int, motivo: str, ator: dict) -> None:
    exigir_acao(ator, "cancelar")
    motivo = _normalizar_texto(motivo, 1000)
    if len(motivo) < 5:
        raise ValueError("Informe o motivo do cancelamento.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None:
            raise ValueError("Lançamento não encontrado.")
        if int(registro["valor_liquidado_centavos"]) > 0 or registro["conciliado"]:
            raise ValueError("Um lançamento liquidado deve ser estornado, não excluído ou cancelado.")
        conexao.execute(
            "UPDATE fin_lancamentos SET status='Cancelado',cancelado_em=CURRENT_TIMESTAMP,cancelado_por=?,motivo_cancelamento=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(ator["id"]), motivo, int(ator["id"]), int(lancamento_id)),
        )
        _registrar_evento(conexao, ator, "lancamento_cancelado", "fin_lancamentos", int(lancamento_id), antes=dict(registro), depois={"status": "Cancelado", "motivo": motivo})


def estornar_lancamento(lancamento_id: int, motivo: str, ator: dict) -> None:
    """Estorna uma operação liquidada sem apagar sua trilha financeira.

    As baixas permanecem armazenadas e recebem a marca ``estornada``. Dessa
    forma o saldo bancário volta à posição anterior, enquanto o lançamento,
    seus documentos e toda a auditoria continuam consultáveis.
    """
    exigir_acao(ator, "cancelar")
    motivo = _normalizar_texto(motivo, 1000)
    if len(motivo) < 5:
        raise ValueError("Informe o motivo do estorno.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None:
            raise ValueError("Lançamento não encontrado.")
        if registro["status"] in {"Cancelado", "Estornado"}:
            raise ValueError("O lançamento já está cancelado ou estornado.")
        if not int(registro["valor_liquidado_centavos"]) and registro["natureza"] != "Transferência" and not registro["conciliado"]:
            raise ValueError("Utilize Cancelar para um lançamento que ainda não foi liquidado.")
        conexao.execute(
            "UPDATE fin_baixas SET estornada=1 WHERE lancamento_id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        )
        conexao.execute(
            """
            UPDATE fin_lancamentos SET
                status='Estornado',contabilizado=0,atualizado_por=?,
                motivo_cancelamento=?,cancelado_em=CURRENT_TIMESTAMP,
                cancelado_por=?,atualizado_em=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (int(ator["id"]), motivo, int(ator["id"]), int(lancamento_id)),
        )
        _registrar_evento(
            conexao, ator, "lancamento_estornado", "fin_lancamentos",
            int(lancamento_id), antes=dict(registro),
            depois={"status": "Estornado", "motivo": motivo},
        )


def listar_lancamentos(
    ator: dict,
    *,
    pagina=1,
    tamanho=50,
    pesquisa="",
    status="Todos",
    natureza="Todas",
    naturezas=None,
    inicio=None,
    fim=None,
    departamento_id=None,
    centro_custo_id=None,
    projeto_id=None,
    conta_id=None,
    categoria_id=None,
) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    pagina = max(1, int(pagina))
    tamanho = max(10, min(int(tamanho), 200))
    filtros = ["l.empresa_id=?", "l.filial_id=?"]
    parametros: list[object] = [empresa_id, filial_id]
    if status != "Todos":
        filtros.append("l.status=?")
        parametros.append(status)
    naturezas_validas = tuple(
        item for item in (naturezas or ()) if item in NATUREZAS
    )
    if naturezas_validas:
        marcadores = ",".join("?" for _ in naturezas_validas)
        filtros.append(f"l.natureza IN ({marcadores})")
        parametros.extend(naturezas_validas)
    elif natureza != "Todas":
        filtros.append("l.natureza=?")
        parametros.append(natureza)
    if inicio:
        filtros.append("l.competencia>=?")
        parametros.append(_data_iso(inicio))
    if fim:
        filtros.append("l.competencia<=?")
        parametros.append(_data_iso(fim))
    for coluna, valor in (
        ("departamento_id", departamento_id),
        ("centro_custo_id", centro_custo_id),
        ("projeto_id", projeto_id),
        ("conta_id", conta_id),
        ("categoria_id", categoria_id),
    ):
        if valor:
            filtros.append(f"l.{coluna}=?")
            parametros.append(int(valor))
    termo = _normalizar_texto(pesquisa, 120)
    if termo:
        filtros.append("(l.descricao LIKE ? OR l.documento_numero LIKE ? OR p.nome LIKE ? OR c.nome LIKE ?)")
        busca = f"%{termo}%"
        parametros.extend((busca, busca, busca, busca))
    where = " AND ".join(filtros)
    base = f"""
        FROM fin_lancamentos l
        LEFT JOIN fin_partes p ON p.id=l.parte_id
        LEFT JOIN fin_categorias c ON c.id=l.categoria_id
        LEFT JOIN centros_custo cc ON cc.id=l.centro_custo_id
        LEFT JOIN fin_contas ct ON ct.id=l.conta_id
        WHERE {where}
    """
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        total = int(conexao.execute("SELECT COUNT(*) total " + base, tuple(parametros)).fetchone()["total"])
        paginas = max(1, math.ceil(total / tamanho))
        pagina = min(pagina, paginas)
        linhas = conexao.execute(
            """
            SELECT l.*,p.nome parte_nome,c.nome categoria_nome,
                   cc.nome centro_custo_nome,ct.nome conta_nome,
                   (l.valor_original_centavos-l.valor_liquidado_centavos) saldo_centavos
            """ + base + " ORDER BY l.competencia DESC,l.id DESC LIMIT ? OFFSET ?",
            (*parametros, tamanho, (pagina - 1) * tamanho),
        ).fetchall()
    return {
        "registros": [dict(item) for item in linhas],
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "tamanho": tamanho,
    }


def obter_lancamento(lancamento_id: int, ator: dict) -> dict:
    resultado = listar_lancamentos(ator, tamanho=200)
    item = next((registro for registro in resultado["registros"] if int(registro["id"]) == int(lancamento_id)), None)
    if item is None:
        empresa_id, filial_id = obter_escopo_ator(ator)
        with conectar() as conexao:
            linha = conexao.execute(
                "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
                (int(lancamento_id), empresa_id, filial_id),
            ).fetchone()
        if linha is None:
            raise ValueError("Lançamento não encontrado.")
        item = dict(linha)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        item["baixas"] = [dict(linha) for linha in conexao.execute(
            "SELECT * FROM fin_baixas WHERE lancamento_id=? AND empresa_id=? AND filial_id=? ORDER BY data,id",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchall()]
        item["aprovacoes"] = [dict(linha) for linha in conexao.execute(
            "SELECT * FROM fin_aprovacoes WHERE lancamento_id=? ORDER BY nivel",
            (int(lancamento_id),),
        ).fetchall()]
        item["anexos"] = [dict(linha) for linha in conexao.execute(
            "SELECT id,nome,tamanho_bytes,criado_em FROM fin_anexos WHERE lancamento_id=? ORDER BY id",
            (int(lancamento_id),),
        ).fetchall()]
        item["auditoria"] = [dict(linha) for linha in conexao.execute(
            "SELECT acao,usuario_id,dados_antes,dados_depois,criado_em FROM historico_alteracoes "
            "WHERE empresa_id=? AND filial_id=? AND modulo='financeiro' AND entidade='fin_lancamentos' AND entidade_id=? ORDER BY id DESC",
            (empresa_id, filial_id, int(lancamento_id)),
        ).fetchall()]
    return item


def atualizar_lancamento(lancamento_id: int, dados: dict, ator: dict) -> None:
    """Edita somente campos operacionais enquanto não houver liquidação."""
    exigir_acao(ator, "editar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        anterior = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if anterior is None:
            raise ValueError("Lançamento não encontrado.")
        if int(anterior["valor_liquidado_centavos"]) or anterior["conciliado"] or anterior["contabilizado"]:
            raise ValueError("Lançamentos liquidados, conciliados ou contabilizados exigem estorno.")
        if anterior["status"] in {"Cancelado", "Estornado"}:
            raise ValueError("O lançamento cancelado não pode ser editado.")
        descricao = _normalizar_texto(dados.get("descricao", anterior["descricao"]), 240)
        valor = _centavos(dados.get("valor", int(anterior["valor_original_centavos"]) / 100))
        if not descricao or valor <= 0:
            raise ValueError("Descrição e valor são obrigatórios.")
        referencias = {}
        for chave, tabela in (
            ("departamento_id", "departamentos"),
            ("centro_custo_id", "centros_custo"),
            ("projeto_id", "fin_projetos"),
            ("conta_id", "fin_contas"),
            ("conta_destino_id", "fin_contas"),
            ("plano_conta_id", "fin_plano_contas"),
            ("categoria_id", "fin_categorias"),
            ("parte_id", "fin_partes"),
        ):
            valor_ref = dados.get(chave, anterior[chave])
            referencias[chave] = _validar_referencia(
                conexao, tabela, valor_ref, empresa_id,
                filial_id=filial_id if tabela in {"fin_contas", "fin_projetos", "fin_partes"} else None,
            )
        conexao.execute(
            """
            UPDATE fin_lancamentos SET
                descricao=?,competencia=?,vencimento=?,valor_original_centavos=?,
                departamento_id=?,centro_custo_id=?,projeto_id=?,conta_id=?,
                conta_destino_id=?,plano_conta_id=?,categoria_id=?,parte_id=?,
                forma_pagamento=?,documento_numero=?,nota_fiscal=?,observacoes=?,
                tags=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                descricao,
                _data_iso(dados.get("competencia", anterior["competencia"]), obrigatoria=True),
                _data_iso(dados.get("vencimento", anterior["vencimento"])), valor,
                referencias["departamento_id"], referencias["centro_custo_id"],
                referencias["projeto_id"], referencias["conta_id"],
                referencias["conta_destino_id"], referencias["plano_conta_id"],
                referencias["categoria_id"], referencias["parte_id"],
                _normalizar_texto(dados.get("forma_pagamento", anterior["forma_pagamento"]), 80),
                _normalizar_texto(dados.get("documento_numero", anterior["documento_numero"]), 80),
                _normalizar_texto(dados.get("nota_fiscal", anterior["nota_fiscal"]), 80),
                _normalizar_texto(dados.get("observacoes", anterior["observacoes"]), 2000),
                _normalizar_texto(dados.get("tags", anterior["tags"]), 300),
                int(ator["id"]), int(lancamento_id),
            ),
        )
        _registrar_evento(conexao, ator, "lancamento_atualizado", "fin_lancamentos", int(lancamento_id), antes=dict(anterior), depois=dados)


def listar_aprovacoes_financeiras(ator: dict, *, status="Pendente") -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtro = "" if status == "Todos" else " AND a.status=?"
    parametros: tuple = (empresa_id, filial_id) if not filtro else (empresa_id, filial_id, status)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT a.*,l.descricao,l.natureza,l.valor_original_centavos,
                   l.vencimento,l.status lancamento_status,u.nome aprovador_nome
            FROM fin_aprovacoes a
            JOIN fin_lancamentos l ON l.id=a.lancamento_id
            LEFT JOIN usuarios u ON u.id=a.aprovador_id
            WHERE a.empresa_id=? AND a.filial_id=?
            """ + filtro + " ORDER BY a.criado_em DESC,a.nivel",
            parametros,
        ).fetchall()]


def salvar_plano_conta(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar")
    empresa_id, _ = obter_escopo_ator(ator)
    codigo = _normalizar_texto(dados.get("codigo"), 30)
    nome = _normalizar_texto(dados.get("nome"), 140)
    natureza = dados.get("natureza") or "Despesa"
    grupo = dados.get("grupo_dre") or "Despesas operacionais"
    if not codigo or not nome or natureza not in {"Receita", "Despesa", "Neutra"}:
        raise ValueError("Código, nome e natureza válida são obrigatórios.")
    with conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO fin_plano_contas (empresa_id,codigo,nome,natureza,grupo_dre,aceita_lancamento) VALUES (?,?,?,?,?,?)",
            (empresa_id, codigo, nome, natureza, grupo, int(bool(dados.get("aceita_lancamento", True)))),
        )
        plano_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "plano_conta_criado", "fin_plano_contas", plano_id, depois=dados)
    return plano_id


def salvar_cartao(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _normalizar_texto(dados.get("nome"), 100)
    final = re.sub(r"\D", "", str(dados.get("final") or ""))[-4:]
    if not nome or len(final) != 4:
        raise ValueError("Informe o nome e os quatro últimos dígitos do cartão.")
    with conectar() as conexao:
        conta_id = _validar_referencia(conexao, "fin_contas", dados.get("conta_id"), empresa_id, filial_id=filial_id)
        centro_id = _validar_referencia(conexao, "centros_custo", dados.get("centro_custo_id"), empresa_id)
        cursor = conexao.execute(
            """
            INSERT INTO fin_cartoes (
                empresa_id,filial_id,conta_id,nome,final,limite_centavos,
                responsavel_id,centro_custo_id,fechamento_dia,vencimento_dia
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id, filial_id, conta_id, nome, final,
                _centavos(dados.get("limite", 0)),
                int(dados["responsavel_id"]) if dados.get("responsavel_id") else None,
                centro_id, int(dados.get("fechamento_dia") or 1),
                int(dados.get("vencimento_dia") or 10),
            ),
        )
        cartao_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "cartao_criado", "fin_cartoes", cartao_id, depois={**dados, "final": final})
    return cartao_id


def listar_cartoes(ator: dict) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT c.*,u.nome responsavel_nome,cc.nome centro_custo_nome,
                   ct.nome conta_nome
            FROM fin_cartoes c
            LEFT JOIN usuarios u ON u.id=c.responsavel_id
            LEFT JOIN centros_custo cc ON cc.id=c.centro_custo_id
            LEFT JOIN fin_contas ct ON ct.id=c.conta_id
            WHERE c.empresa_id=? AND c.filial_id=? ORDER BY c.nome
            """,
            (empresa_id, filial_id),
        ).fetchall()]


def atualizar_status_vencidos(ator: dict) -> int:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE fin_lancamentos SET status='Vencido',atualizado_em=CURRENT_TIMESTAMP
            WHERE empresa_id=? AND filial_id=? AND vencimento<?
              AND status IN ('Previsto','Faturado','Enviado','Aprovado','Agendado','A vencer','Parcial')
            """,
            (empresa_id, filial_id, date.today().isoformat()),
        )
    return int(cursor.rowcount)


def listar_recorrencias(ator: dict) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT id,descricao,periodicidade,inicio,fim,proxima_geracao,ativo,criado_em
            FROM fin_recorrencias
            WHERE empresa_id=? AND filial_id=? ORDER BY ativo DESC,descricao
            """,
            (empresa_id, filial_id),
        ).fetchall()]


def gerar_recorrencias_pendentes(ator: dict, *, ate=None) -> list[int]:
    """Materializa ocorrências vencidas sem duplicar o modelo recorrente."""
    exigir_acao(ator, "criar")
    limite = _data_iso(ate) or date.today().isoformat()
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        planos = [dict(item) for item in conexao.execute(
            """
            SELECT * FROM fin_recorrencias
            WHERE empresa_id=? AND filial_id=? AND ativo=1
              AND proxima_geracao IS NOT NULL AND proxima_geracao<=?
            ORDER BY proxima_geracao,id
            """,
            (empresa_id, filial_id, limite),
        ).fetchall()]
    gerados: list[int] = []
    for plano in planos:
        proxima = plano["proxima_geracao"]
        iteracoes = 0
        while proxima and proxima <= limite and iteracoes < 120:
            if plano.get("fim") and proxima > plano["fim"]:
                break
            modelo = json.loads(plano["modelo_json"] or "{}")
            modelo.update({
                "competencia": proxima,
                "vencimento": proxima,
                "recorrente": False,
                "parcelas": 1,
                "origem_modulo": "financeiro",
                "origem_recurso_tipo": "fin_recorrencias",
                "origem_recurso_id": plano["id"],
            })
            gerados.extend(criar_lancamento(modelo, ator))
            proxima = _proxima_periodicidade(proxima, plano["periodicidade"])
            iteracoes += 1
        ativo = int(not plano.get("fim") or proxima <= plano["fim"])
        with conectar() as conexao:
            conexao.execute(
                "UPDATE fin_recorrencias SET proxima_geracao=?,ativo=? WHERE id=? AND empresa_id=? AND filial_id=?",
                (proxima, ativo, int(plano["id"]), empresa_id, filial_id),
            )
            _registrar_evento(conexao, ator, "recorrencia_processada", "fin_recorrencias", int(plano["id"]), depois={"gerados": iteracoes, "proxima_geracao": proxima, "ativo": ativo})
    return gerados


def agendar_relatorio(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "exportar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _normalizar_texto(dados.get("nome"), 140)
    tipo = _normalizar_texto(dados.get("tipo"), 100)
    formato = dados.get("formato") or "PDF"
    frequencia = dados.get("frequencia") or "Mensal"
    if not nome or not tipo or formato not in {"PDF", "Excel", "CSV", "HTML"}:
        raise ValueError("Nome, tipo e formato de relatório são obrigatórios.")
    if frequencia not in {"Diário", "Semanal", "Mensal", "Trimestral", "Manual"}:
        raise ValueError("Frequência inválida.")
    proxima = _data_iso(dados.get("proxima_execucao"))
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO fin_relatorios_agendados (
                empresa_id,filial_id,nome,tipo,filtros_json,formato,
                destinatarios,frequencia,proxima_execucao,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id, filial_id, nome, tipo,
                json.dumps(dados.get("filtros") or {}, ensure_ascii=False),
                formato, _normalizar_texto(dados.get("destinatarios"), 1000),
                frequencia, proxima, int(ator["id"]),
            ),
        )
        agendamento_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "relatorio_agendado", "fin_relatorios_agendados", agendamento_id, depois=dados)
    from enterprise.automacao_motor import registrar_agendamento
    registrar_agendamento(
        modulo="financeiro", referencia_tipo="fin_relatorios_agendados",
        referencia_id=agendamento_id, handler="relatorio.gerar",
        payload={
            "modulo": "financeiro", "tipo": tipo, "formato": formato,
            "filtros": dados.get("filtros") or {},
            "destinatarios": _normalizar_texto(dados.get("destinatarios"), 1000),
        },
        frequencia=frequencia, proxima_execucao=proxima, ator=ator,
    )
    return agendamento_id


def listar_relatorios_agendados(ator: dict) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT * FROM fin_relatorios_agendados
            WHERE empresa_id=? AND filial_id=? ORDER BY ativo DESC,proxima_execucao,id
            """,
            (empresa_id, filial_id),
        ).fetchall()]


def anexar_documento(lancamento_id: int, caminho: str | Path, ator: dict) -> int:
    exigir_acao(ator, "editar")
    origem = Path(caminho).expanduser().resolve()
    if not origem.is_file():
        raise ValueError("O anexo selecionado não existe.")
    if origem.stat().st_size > 25 * 1024 * 1024:
        raise ValueError("O anexo excede o limite de 25 MB.")
    registro = obter_lancamento(lancamento_id, ator)
    empresa_id, _ = obter_escopo_ator(ator)
    digest = hashlib.sha256(origem.read_bytes()).hexdigest()
    destino_dir = banco_auth.STORAGE_DIR / "financeiro" / "anexos" / str(empresa_id)
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{uuid4().hex}_{origem.name}"
    destino.write_bytes(origem.read_bytes())
    relativo = str(destino.relative_to(banco_auth.STORAGE_DIR))
    with conectar() as conexao:
        cursor = conexao.execute(
            "INSERT INTO fin_anexos (empresa_id,lancamento_id,nome,caminho_relativo,hash_sha256,tamanho_bytes,criado_por) VALUES (?,?,?,?,?,?,?)",
            (empresa_id, int(lancamento_id), origem.name, relativo, digest, origem.stat().st_size, int(ator["id"])),
        )
        anexo_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "documento_anexado", "fin_lancamentos", int(lancamento_id), depois={"anexo_id": anexo_id, "nome": origem.name, "status_anterior": registro["status"]})
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="financeiro", categoria="anexo")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar anexo financeiro no servidor")
    return anexo_id


def salvar_orcamento(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    ano = int(dados.get("ano") or date.today().year)
    mes = int(dados.get("mes") or date.today().month)
    if not 2000 <= ano <= 2200 or not 1 <= mes <= 12:
        raise ValueError("Competência orçamentária inválida.")
    planejado = _centavos(dados.get("planejado"))
    if planejado <= 0:
        raise ValueError("O valor planejado precisa ser maior que zero.")
    alerta = int(dados.get("limite_alerta_percentual") or 85)
    if not 1 <= alerta <= 100:
        raise ValueError("O alerta deve estar entre 1% e 100%.")
    with conectar() as conexao:
        referencias = {
            chave: _validar_referencia(conexao, tabela, dados.get(chave), empresa_id, filial_id=filial_id if tabela.startswith("fin_") else None)
            for chave, tabela in (
                ("departamento_id", "departamentos"),
                ("centro_custo_id", "centros_custo"),
                ("projeto_id", "fin_projetos"),
                ("categoria_id", "fin_categorias"),
            )
        }
        cursor = conexao.execute(
            """
            INSERT INTO fin_orcamentos (
                empresa_id,filial_id,departamento_id,centro_custo_id,
                projeto_id,categoria_id,ano,mes,planejado_centavos,
                limite_alerta_percentual,status,criado_por,atualizado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id, filial_id, referencias["departamento_id"],
                referencias["centro_custo_id"], referencias["projeto_id"],
                referencias["categoria_id"], ano, mes, planejado, alerta,
                dados.get("status") or "Planejado", int(ator["id"]), int(ator["id"]),
            ),
        )
        orcamento_id = int(cursor.lastrowid)
        _registrar_evento(conexao, ator, "orcamento_criado", "fin_orcamentos", orcamento_id, depois=dados)
    return orcamento_id


from enterprise.domains.financeiro.catalogos import garantir_catalogos, listar_catalogos

# V9.5: implementação interna de conciliação/inteligência foi decomposta.
from enterprise.domains.financeiro.conciliacao import (
    _parse_ofx, _ler_extrato, importar_extrato, listar_conciliacoes, conciliar_item, saldo_conta,
)
from enterprise.domains.financeiro.inteligencia import (
    listar_contas_com_saldo, projetar_fluxo_caixa, calcular_dre, resumo_financeiro,
    analisar_financeiro, _dataframe_relatorio, exportar_dataframe_financeiro,
    gerar_relatorio_financeiro, gerar_alertas_financeiros, listar_auditoria_financeira,
    listar_orcamentos,
)

# V9.1+: em estações Central/Cliente, as APIs transacionais públicas desta fachada
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
