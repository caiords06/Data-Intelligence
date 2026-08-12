"""Serviços do departamento Financeiro.

O módulo concentra o ciclo completo:
registrar -> classificar -> aprovar -> liquidar -> conciliar -> contabilizar
-> analisar -> auditar. Valores monetários são sempre persistidos em centavos.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

import pandas as pd

from auth import banco as banco_auth
from auth.banco import conectar
from enterprise.contexto import (
    obter_escopo_ator,
    tem_permissao,
)


ACOES_FINANCEIRAS = {
    "visualizar": "ler",
    "criar": "escrever",
    "editar": "escrever",
    "classificar": "escrever",
    "importar": "escrever",
    "transferir": "escrever",
    "solicitar_aprovacao": "escrever",
    "aprovar": "aprovar",
    "liquidar": "escrever",
    "conciliar": "escrever",
    "contabilizar": "aprovar",
    "cancelar": "aprovar",
    "exportar": "ler",
}

NATUREZAS = {
    "Receita",
    "Despesa",
    "Transferência",
    "Ajuste",
    "Conta a pagar",
    "Conta a receber",
    "Reembolso",
}

STATUS_ABERTOS = {
    "Rascunho",
    "Previsto",
    "Faturado",
    "Enviado",
    "Aguardando aprovação",
    "Aprovado",
    "Agendado",
    "A vencer",
    "Vencido",
    "Parcial",
}

STATUS_TERMINAIS = {"Pago", "Recebido", "Liquidado", "Conciliado", "Cancelado", "Estornado"}

GRUPOS_DRE = (
    "Receita bruta",
    "Deduções",
    "Custos",
    "Despesas operacionais",
    "Resultado financeiro",
)


def _centavos(valor, *, permite_negativo=False) -> int:
    if valor in (None, ""):
        return 0
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", texto):
        # Na interface brasileira, um ponto isolado seguido por grupos de
        # três algarismos é separador de milhar: 2.500 = R$ 2.500,00.
        texto = texto.replace(".", "")
    try:
        numero = Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as erro:
        raise ValueError(f"Valor monetário inválido: {valor}") from erro
    if not numero.is_finite() or (numero < 0 and not permite_negativo):
        raise ValueError("O valor monetário informado é inválido.")
    return int(numero * 100)


def _moeda(centavos: int) -> str:
    valor = Decimal(int(centavos or 0)) / 100
    texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def _data_iso(valor, *, obrigatoria=False) -> str | None:
    if valor in (None, ""):
        if obrigatoria:
            raise ValueError("Informe a data obrigatória.")
        return None
    if isinstance(valor, (datetime, date)):
        return valor.date().isoformat() if isinstance(valor, datetime) else valor.isoformat()
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Data inválida. Utilize DD/MM/AAAA ou AAAA-MM-DD.")


def _somar_meses(data_iso: str, meses: int) -> str:
    base = datetime.strptime(data_iso, "%Y-%m-%d").date()
    indice = base.month - 1 + meses
    ano = base.year + indice // 12
    mes = indice % 12 + 1
    dias = (31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return date(ano, mes, min(base.day, dias[mes - 1])).isoformat()


def _proxima_periodicidade(data_iso: str, periodicidade: str) -> str:
    base = datetime.strptime(data_iso, "%Y-%m-%d").date()
    if periodicidade == "Semanal":
        return (base + timedelta(days=7)).isoformat()
    if periodicidade == "Trimestral":
        return _somar_meses(data_iso, 3)
    if periodicidade == "Anual":
        return _somar_meses(data_iso, 12)
    return _somar_meses(data_iso, 1)


def _normalizar_texto(valor, limite=500) -> str:
    return " ".join(str(valor or "").strip().split())[:limite]


def tem_permissao_financeira(ator: dict | None, acao: str) -> bool:
    acao = str(acao).strip().lower()
    basica = ACOES_FINANCEIRAS.get(acao)
    if basica is None or not ator or not ator.get("id"):
        return False
    if ator.get("perfil") == "admin":
        return True
    try:
        empresa_id, _ = obter_escopo_ator(ator)
    except (PermissionError, RuntimeError):
        return False
    with conectar() as conexao:
        especifica = conexao.execute(
            "SELECT permitido FROM fin_permissoes_acoes "
            "WHERE usuario_id=? AND empresa_id=? AND acao=?",
            (int(ator["id"]), empresa_id, acao),
        ).fetchone()
    if especifica is not None:
        return bool(especifica["permitido"])
    return tem_permissao(ator, "financeiro", basica)


def exigir_acao(ator: dict | None, acao: str) -> None:
    if not tem_permissao_financeira(ator, acao):
        raise PermissionError(
            f"Seu perfil não possui permissão financeira para {acao.replace('_', ' ')}."
        )


def salvar_permissao_acao(usuario_id: int, acao: str, permitido: bool, ator: dict) -> None:
    if ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem configurar ações financeiras.")
    acao = str(acao).strip().lower()
    if acao not in ACOES_FINANCEIRAS:
        raise ValueError("Ação financeira inválida.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        vinculo = conexao.execute(
            "SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(usuario_id), empresa_id),
        ).fetchone()
        if vinculo is None:
            raise ValueError("O usuário não pertence à empresa atual.")
        conexao.execute(
            """
            INSERT INTO fin_permissoes_acoes (
                usuario_id, empresa_id, acao, permitido, atualizado_por
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(usuario_id, empresa_id, acao) DO UPDATE SET
                permitido=excluded.permitido,
                atualizado_por=excluded.atualizado_por,
                atualizado_em=CURRENT_TIMESTAMP
            """,
            (int(usuario_id), empresa_id, acao, int(bool(permitido)), int(ator["id"])),
        )


def _registrar_evento(conexao, ator, acao, entidade, entidade_id, antes=None, depois=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    operacao_id = str(uuid4())
    conexao.execute(
        """
        INSERT INTO historico_alteracoes (
            operacao_id, empresa_id, filial_id, usuario_id, modulo,
            entidade, entidade_id, acao, dados_antes, dados_depois
        ) VALUES (?, ?, ?, ?, 'financeiro', ?, ?, ?, ?, ?)
        """,
        (
            operacao_id,
            empresa_id,
            filial_id,
            int(ator["id"]),
            entidade,
            int(entidade_id),
            acao,
            json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
            json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None,
        ),
    )
    conexao.execute(
        """
        INSERT INTO atividades (
            usuario_id, empresa_id, filial_id, modulo, acao, descricao,
            recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, 'financeiro', ?, ?, ?, ?)
        """,
        (
            int(ator["id"]), empresa_id, filial_id, acao,
            f"Financeiro: {acao.replace('_', ' ')} em {entidade} #{entidade_id}",
            entidade, int(entidade_id),
        ),
    )


def _notificar(conexao, ator, titulo, mensagem, nivel="aviso", entidade=None, entidade_id=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """
        INSERT INTO notificacoes (
            empresa_id, filial_id, modulo, titulo, mensagem, nivel,
            recurso_tipo, recurso_id
        ) VALUES (?, ?, 'financeiro', ?, ?, ?, ?, ?)
        """,
        (empresa_id, filial_id, titulo, mensagem, nivel, entidade, entidade_id),
    )


def _sincronizar_legado(conexao, empresa_id: int, filial_id: int | None) -> None:
    """Importa registros criados pela API V5/V6 depois da migração.

    Extensões antigas e testes de compatibilidade ainda podem chamar
    ``enterprise.modulos.criar_registro('financeiro', ...)``. A sincronização
    incremental impede que esses lançamentos desapareçam do novo Analytics.
    """
    tabela = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lancamentos_financeiros'"
    ).fetchone()
    if tabela is None:
        return
    conexao.execute(
        """
        INSERT INTO fin_lancamentos (
            id,empresa_id,filial_id,centro_custo_id,natureza,descricao,
            competencia,vencimento,liquidacao,valor_original_centavos,
            valor_liquidado_centavos,status,criado_por,atualizado_por,
            criado_em,atualizado_em,origem_modulo,origem_recurso_tipo,
            origem_recurso_id,contabilizado,conciliado
        )
        SELECT
            -id,empresa_id,filial_id,centro_custo_id,tipo,descricao,
            COALESCE(vencimento,substr(criado_em,1,10)),vencimento,
            CASE WHEN status IN ('Pago','Recebido') THEN vencimento END,
            COALESCE(valor_centavos,ROUND(valor*100)),
            CASE WHEN status IN ('Pago','Recebido')
                 THEN COALESCE(valor_centavos,ROUND(valor*100)) ELSE 0 END,
            status,criado_por,criado_por,criado_em,
            COALESCE(atualizado_em,criado_em),'legado',
            'lancamentos_financeiros',id,
            CASE WHEN status IN ('Pago','Recebido') THEN 1 ELSE 0 END,0
        FROM lancamentos_financeiros legado
        WHERE legado.empresa_id=? AND legado.filial_id=?
          AND NOT EXISTS (
              SELECT 1 FROM fin_lancamentos novo
              WHERE novo.origem_modulo='legado'
                AND novo.origem_recurso_id=legado.id
          )
        """,
        (empresa_id, filial_id),
    )


def garantir_catalogos(ator: dict) -> None:
    """Cria o plano mínimo também para empresas abertas após a migração."""
    exigir_acao(ator, "visualizar")
    empresa_id, _ = obter_escopo_ator(ator)
    planos = (
        ("1.1", "Vendas", "Receita", "Receita bruta"),
        ("1.2", "Serviços", "Receita", "Receita bruta"),
        ("1.3", "Receitas financeiras", "Receita", "Resultado financeiro"),
        ("2.1", "Impostos sobre vendas", "Despesa", "Deduções"),
        ("3.1", "Mercadorias e produção", "Despesa", "Custos"),
        ("4.1", "Administrativo", "Despesa", "Despesas operacionais"),
        ("4.2", "Marketing", "Despesa", "Despesas operacionais"),
        ("4.3", "Tecnologia", "Despesa", "Despesas operacionais"),
        ("4.4", "Recursos Humanos", "Despesa", "Despesas operacionais"),
        ("5.1", "Juros e tarifas", "Despesa", "Resultado financeiro"),
        ("9.1", "Transferências internas", "Neutra", "Não operacional"),
    )
    with conectar() as conexao:
        for codigo, nome, natureza, grupo in planos:
            conexao.execute(
                "INSERT OR IGNORE INTO fin_plano_contas "
                "(empresa_id,codigo,nome,natureza,grupo_dre) VALUES (?,?,?,?,?)",
                (empresa_id, codigo, nome, natureza, grupo),
            )


def listar_catalogos(ator: dict) -> dict:
    garantir_catalogos(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        def linhas(sql, parametros=()):
            return [dict(item) for item in conexao.execute(sql, parametros).fetchall()]
        return {
            "contas": linhas(
                "SELECT id,nome,banco,tipo,status FROM fin_contas "
                "WHERE empresa_id=? AND filial_id=? ORDER BY nome",
                (empresa_id, filial_id),
            ),
            "partes": linhas(
                "SELECT id,nome,tipo,documento,status FROM fin_partes "
                "WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL) ORDER BY nome",
                (empresa_id, filial_id),
            ),
            "plano_contas": linhas(
                "SELECT id,codigo,nome,natureza,grupo_dre FROM fin_plano_contas "
                "WHERE empresa_id=? AND ativo=1 ORDER BY codigo",
                (empresa_id,),
            ),
            "categorias": linhas(
                "SELECT id,nome,natureza,plano_conta_id FROM fin_categorias "
                "WHERE empresa_id=? AND ativo=1 ORDER BY nome",
                (empresa_id,),
            ),
            "projetos": linhas(
                "SELECT id,codigo,nome,status FROM fin_projetos "
                "WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL) ORDER BY nome",
                (empresa_id, filial_id),
            ),
            "departamentos": linhas(
                "SELECT id,codigo,nome FROM departamentos WHERE empresa_id=? AND ativo=1 ORDER BY nome",
                (empresa_id,),
            ),
            "centros_custo": linhas(
                "SELECT id,codigo,nome,departamento_id FROM centros_custo "
                "WHERE empresa_id=? AND ativo=1 ORDER BY nome",
                (empresa_id,),
            ),
        }


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


def _validar_referencia(conexao, tabela: str, identificador, empresa_id: int, *, filial_id=None) -> int | None:
    if identificador in (None, ""):
        return None
    filtros = "id=? AND empresa_id=?"
    parametros: list[object] = [int(identificador), empresa_id]
    colunas = {item["name"] for item in conexao.execute(f"PRAGMA table_info({tabela})")}
    if filial_id is not None and "filial_id" in colunas:
        filtros += " AND (filial_id=? OR filial_id IS NULL)"
        parametros.append(filial_id)
    if conexao.execute(f"SELECT id FROM {tabela} WHERE {filtros}", tuple(parametros)).fetchone() is None:
        raise ValueError("Uma das referências informadas não pertence ao contexto atual.")
    return int(identificador)


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


def listar_auditoria_financeira(ator: dict, *, limite=300) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT h.id,h.acao,h.entidade,h.entidade_id,h.criado_em,
                   u.nome usuario_nome,h.dados_antes,h.dados_depois
            FROM historico_alteracoes h
            LEFT JOIN usuarios u ON u.id=h.usuario_id
            WHERE h.empresa_id=? AND h.filial_id=? AND h.modulo='financeiro'
            ORDER BY h.id DESC LIMIT ?
            """,
            (empresa_id, filial_id, max(1, min(int(limite), 1000))),
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
        pass
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


def listar_orcamentos(ator: dict, *, ano=None, mes=None) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    ano = int(ano or date.today().year)
    filtros = ["o.empresa_id=?", "o.filial_id=?", "o.ano=?"]
    parametros: list[object] = [empresa_id, filial_id, ano]
    if mes:
        filtros.append("o.mes=?")
        parametros.append(int(mes))
    with conectar() as conexao:
        linhas = conexao.execute(
            f"""
            SELECT o.*,cc.nome centro_custo_nome,c.nome categoria_nome,
                   COALESCE((
                       SELECT SUM(l.valor_liquidado_centavos)
                       FROM fin_lancamentos l
                       WHERE l.empresa_id=o.empresa_id AND l.filial_id=o.filial_id
                         AND l.natureza IN ('Despesa','Conta a pagar','Reembolso')
                         AND strftime('%Y',l.competencia)=printf('%04d',o.ano)
                         AND strftime('%m',l.competencia)=printf('%02d',o.mes)
                         AND (o.centro_custo_id IS NULL OR l.centro_custo_id=o.centro_custo_id)
                         AND (o.categoria_id IS NULL OR l.categoria_id=o.categoria_id)
                         AND l.status NOT IN ('Cancelado','Estornado')
                   ),0) realizado_centavos
            FROM fin_orcamentos o
            LEFT JOIN centros_custo cc ON cc.id=o.centro_custo_id
            LEFT JOIN fin_categorias c ON c.id=o.categoria_id
            WHERE {' AND '.join(filtros)} ORDER BY o.mes,cc.nome,c.nome
            """,
            tuple(parametros),
        ).fetchall()
    resultado = []
    for linha in linhas:
        item = dict(linha)
        planejado = int(item["planejado_centavos"])
        realizado = int(item["realizado_centavos"])
        item["disponivel_centavos"] = planejado - realizado
        item["utilizado_percentual"] = round(realizado * 100 / planejado, 1) if planejado else 0
        resultado.append(item)
    return resultado


def _parse_ofx(caminho: Path) -> list[dict]:
    texto = caminho.read_text(encoding="utf-8", errors="ignore")
    blocos = re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|<STMTTRN>|</BANKTRANLIST>)", texto, flags=re.I | re.S)
    itens = []
    for bloco in blocos:
        def tag(nome):
            encontrado = re.search(rf"<{nome}>([^<\r\n]+)", bloco, flags=re.I)
            return encontrado.group(1).strip() if encontrado else ""
        data_raw = tag("DTPOSTED")[:8]
        if len(data_raw) != 8:
            continue
        itens.append({
            "data": f"{data_raw[:4]}-{data_raw[4:6]}-{data_raw[6:8]}",
            "descricao": tag("MEMO") or tag("NAME") or "Movimentação bancária",
            "documento": tag("CHECKNUM"),
            "valor": tag("TRNAMT"),
            "identificador": tag("FITID") or hashlib.sha256(bloco.encode()).hexdigest(),
        })
    return itens


def _ler_extrato(caminho: Path) -> list[dict]:
    extensao = caminho.suffix.lower()
    if extensao == ".ofx":
        return _parse_ofx(caminho)
    if extensao == ".csv":
        dataframe = pd.read_csv(caminho, sep=None, engine="python")
    elif extensao in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(caminho)
    else:
        raise ValueError("Formato não suportado. Utilize OFX, CSV ou XLSX.")
    normalizadas = {str(coluna).strip().lower(): coluna for coluna in dataframe.columns}
    def achar(*nomes):
        for nome in nomes:
            for normalizada, original in normalizadas.items():
                if nome in normalizada:
                    return original
        return None
    col_data = achar("data", "date")
    col_desc = achar("descri", "histor", "memo", "name")
    col_valor = achar("valor", "amount", "trnamt")
    col_doc = achar("document", "id", "fitid")
    if col_data is None or col_desc is None or col_valor is None:
        raise ValueError("O extrato precisa conter colunas de data, descrição e valor.")
    itens = []
    for indice, linha in dataframe.iterrows():
        data_item = pd.to_datetime(linha[col_data], errors="coerce", dayfirst=True)
        if pd.isna(data_item):
            continue
        itens.append({
            "data": data_item.date().isoformat(),
            "descricao": str(linha[col_desc]),
            "documento": str(linha[col_doc]) if col_doc is not None and pd.notna(linha[col_doc]) else "",
            "valor": linha[col_valor],
            "identificador": str(linha[col_doc]) if col_doc is not None and pd.notna(linha[col_doc]) else f"linha-{indice + 2}",
        })
    return itens


def importar_extrato(conta_id: int, caminho: str | Path, ator: dict) -> dict:
    exigir_acao(ator, "importar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    caminho = Path(caminho).expanduser().resolve()
    if not caminho.is_file():
        raise ValueError("Arquivo de extrato não encontrado.")
    digest = hashlib.sha256(caminho.read_bytes()).hexdigest()
    formato = caminho.suffix.lstrip(".").upper()
    if formato == "XLS":
        formato = "XLSX"
    itens = _ler_extrato(caminho)
    if not itens:
        raise ValueError("Nenhuma movimentação válida foi encontrada no extrato.")
    with conectar() as conexao:
        _validar_referencia(conexao, "fin_contas", conta_id, empresa_id, filial_id=filial_id)
        cursor = conexao.execute(
            "INSERT INTO fin_extratos (empresa_id,filial_id,conta_id,arquivo_nome,arquivo_hash,formato,importado_por) VALUES (?,?,?,?,?,?,?)",
            (empresa_id, filial_id, int(conta_id), caminho.name, digest, formato, int(ator["id"])),
        )
        extrato_id = int(cursor.lastrowid)
        inseridos = 0
        for item in itens:
            valor = _centavos(item["valor"], permite_negativo=True)
            descricao = _normalizar_texto(item["descricao"], 240)
            candidatos = conexao.execute(
                """
                SELECT id,descricao,natureza,valor_original_centavos,vencimento,liquidacao
                FROM fin_lancamentos
                WHERE empresa_id=? AND filial_id=? AND status NOT IN ('Cancelado','Estornado')
                  AND ABS(valor_original_centavos-ABS(?))<=5
                  AND ABS(julianday(COALESCE(liquidacao,vencimento,competencia))-julianday(?))<=7
                LIMIT 20
                """,
                (empresa_id, filial_id, valor, item["data"]),
            ).fetchall()
            melhor = None
            melhor_score = 0
            for candidato in candidatos:
                score = int(SequenceMatcher(None, descricao.lower(), str(candidato["descricao"]).lower()).ratio() * 100)
                if score > melhor_score:
                    melhor, melhor_score = candidato, score
            status = "Sugerido" if melhor is not None and melhor_score >= 45 else "Sem correspondência"
            conexao.execute(
                """
                INSERT OR IGNORE INTO fin_extrato_itens (
                    extrato_id,data,descricao,documento,valor_centavos,
                    identificador_banco,status,lancamento_id,score
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    extrato_id, item["data"], descricao,
                    _normalizar_texto(item.get("documento"), 120), valor,
                    _normalizar_texto(item["identificador"], 160), status,
                    int(melhor["id"]) if melhor is not None else None, melhor_score,
                ),
            )
            inseridos += 1
        _registrar_evento(conexao, ator, "extrato_importado", "fin_extratos", extrato_id, depois={"arquivo": caminho.name, "itens": inseridos})
    return {"extrato_id": extrato_id, "itens": inseridos}


def listar_conciliacoes(ator: dict, *, status="Todos") -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtro = "" if status == "Todos" else " AND i.status=?"
    parametros: tuple = (empresa_id, filial_id) if not filtro else (empresa_id, filial_id, status)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT i.*,e.arquivo_nome,c.nome conta_nome,l.descricao lancamento_descricao
            FROM fin_extrato_itens i
            JOIN fin_extratos e ON e.id=i.extrato_id
            JOIN fin_contas c ON c.id=e.conta_id
            LEFT JOIN fin_lancamentos l ON l.id=i.lancamento_id
            WHERE e.empresa_id=? AND e.filial_id=?
            """ + filtro + " ORDER BY i.data DESC,i.id DESC",
            parametros,
        ).fetchall()]


def conciliar_item(item_id: int, lancamento_id: int, ator: dict) -> None:
    exigir_acao(ator, "conciliar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        item = conexao.execute(
            """
            SELECT i.*,e.conta_id FROM fin_extrato_itens i
            JOIN fin_extratos e ON e.id=i.extrato_id
            WHERE i.id=? AND e.empresa_id=? AND e.filial_id=?
            """,
            (int(item_id), empresa_id, filial_id),
        ).fetchone()
        lancamento = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if item is None or lancamento is None:
            raise ValueError("Movimentação ou lançamento não encontrado.")
        if abs(abs(int(item["valor_centavos"])) - int(lancamento["valor_original_centavos"])) > 5:
            raise ValueError("Existe divergência de valor; ajuste ou registre a baixa antes de conciliar.")
        conexao.execute(
            "UPDATE fin_extrato_itens SET status='Conciliado',lancamento_id=?,score=100,conciliado_por=?,conciliado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(lancamento_id), int(ator["id"]), int(item_id)),
        )
        conexao.execute(
            "UPDATE fin_lancamentos SET conta_id=COALESCE(conta_id,?),conciliado=1,status='Conciliado',atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(item["conta_id"]), int(ator["id"]), int(lancamento_id)),
        )
        _registrar_evento(conexao, ator, "lancamento_conciliado", "fin_lancamentos", int(lancamento_id), antes={"status": lancamento["status"]}, depois={"status": "Conciliado", "extrato_item_id": int(item_id)})


def saldo_conta(conta_id: int, ator: dict) -> int:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        conta = conexao.execute(
            "SELECT saldo_inicial_centavos FROM fin_contas WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(conta_id), empresa_id, filial_id),
        ).fetchone()
        if conta is None:
            raise ValueError("Conta não encontrada.")
        baixas = conexao.execute(
            """
            SELECT COALESCE(SUM(CASE
                WHEN l.natureza IN ('Receita','Conta a receber') THEN b.principal_centavos+b.juros_centavos+b.multa_centavos-b.desconto_centavos
                WHEN l.natureza IN ('Despesa','Conta a pagar','Reembolso') THEN -(b.principal_centavos+b.juros_centavos+b.multa_centavos-b.desconto_centavos)
                ELSE 0 END),0) valor
            FROM fin_baixas b JOIN fin_lancamentos l ON l.id=b.lancamento_id
            WHERE b.empresa_id=? AND b.filial_id=? AND b.conta_id=? AND b.estornada=0
            """,
            (empresa_id, filial_id, int(conta_id)),
        ).fetchone()["valor"]
        transferencias = conexao.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN conta_destino_id=? THEN valor_original_centavos ELSE 0 END),0)
                 - COALESCE(SUM(CASE WHEN conta_id=? THEN valor_original_centavos ELSE 0 END),0) valor
            FROM fin_lancamentos
            WHERE empresa_id=? AND filial_id=? AND natureza='Transferência'
              AND status NOT IN ('Cancelado','Estornado')
            """,
            (int(conta_id), int(conta_id), empresa_id, filial_id),
        ).fetchone()["valor"]
    return int(conta["saldo_inicial_centavos"]) + int(baixas or 0) + int(transferencias or 0)


def listar_contas_com_saldo(ator: dict) -> list[dict]:
    catalogos = listar_catalogos(ator)
    resultado = []
    for conta in catalogos["contas"]:
        item = dict(conta)
        item["saldo_centavos"] = saldo_conta(item["id"], ator)
        resultado.append(item)
    return resultado


def projetar_fluxo_caixa(ator: dict, *, dias=30, cenario="Realista") -> list[dict]:
    exigir_acao(ator, "visualizar")
    dias = max(1, min(int(dias), 730))
    if cenario not in {"Realista", "Otimista", "Pessimista"}:
        raise ValueError("Cenário inválido.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    contas = listar_contas_com_saldo(ator)
    saldo = sum(int(conta["saldo_centavos"]) for conta in contas)
    hoje = date.today()
    fim = hoje + timedelta(days=dias)
    with conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT COALESCE(vencimento,competencia) data,natureza,
                   SUM(valor_original_centavos-valor_liquidado_centavos) valor
            FROM fin_lancamentos
            WHERE empresa_id=? AND filial_id=? AND status IN (
                'Previsto','Faturado','Enviado','Aprovado','Agendado','A vencer','Vencido','Parcial'
            ) AND COALESCE(vencimento,competencia) BETWEEN ? AND ?
            GROUP BY COALESCE(vencimento,competencia),natureza
            """,
            (empresa_id, filial_id, hoje.isoformat(), fim.isoformat()),
        ).fetchall()
    por_data: dict[str, dict[str, int]] = {}
    fator_receita = {"Otimista": Decimal("1"), "Realista": Decimal("0.90"), "Pessimista": Decimal("0.75")}[cenario]
    fator_despesa = {"Otimista": Decimal("0.95"), "Realista": Decimal("1"), "Pessimista": Decimal("1.10")}[cenario]
    for linha in linhas:
        grupo = por_data.setdefault(linha["data"], {"entradas_centavos": 0, "saidas_centavos": 0})
        valor = int(linha["valor"] or 0)
        if linha["natureza"] in {"Receita", "Conta a receber"}:
            grupo["entradas_centavos"] += int(Decimal(valor) * fator_receita)
        elif linha["natureza"] in {"Despesa", "Conta a pagar", "Reembolso"}:
            grupo["saidas_centavos"] += int(Decimal(valor) * fator_despesa)
    resultado = []
    for indice in range(dias + 1):
        data_atual = (hoje + timedelta(days=indice)).isoformat()
        movimento = por_data.get(data_atual, {"entradas_centavos": 0, "saidas_centavos": 0})
        saldo += movimento["entradas_centavos"] - movimento["saidas_centavos"]
        resultado.append({"data": data_atual, **movimento, "saldo_projetado_centavos": saldo, "cenario": cenario})
    return resultado


def calcular_dre(ator: dict, inicio=None, fim=None) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    hoje = date.today()
    inicio = _data_iso(inicio) or hoje.replace(day=1).isoformat()
    fim = _data_iso(fim) or hoje.isoformat()
    with conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT COALESCE(pc.grupo_dre,'Não classificado') grupo,
                   l.natureza,SUM(CASE WHEN l.valor_liquidado_centavos>0
                       THEN l.valor_liquidado_centavos ELSE l.valor_original_centavos END) valor
            FROM fin_lancamentos l
            LEFT JOIN fin_plano_contas pc ON pc.id=l.plano_conta_id
            WHERE l.empresa_id=? AND l.filial_id=? AND l.competencia BETWEEN ? AND ?
              AND l.natureza!='Transferência' AND l.status NOT IN ('Rascunho','Cancelado','Estornado')
              AND l.contabilizado=1
            GROUP BY COALESCE(pc.grupo_dre,'Não classificado'),l.natureza
            """,
            (empresa_id, filial_id, inicio, fim),
        ).fetchall()
    totais = {grupo: 0 for grupo in GRUPOS_DRE}
    totais["Não classificado"] = 0
    for linha in linhas:
        sinal = 1 if linha["natureza"] in {"Receita", "Conta a receber"} else -1
        totais.setdefault(linha["grupo"], 0)
        totais[linha["grupo"]] += sinal * int(linha["valor"] or 0)
    receita_bruta = max(0, totais["Receita bruta"])
    deducoes = abs(min(0, totais["Deduções"]))
    receita_liquida = receita_bruta - deducoes
    custos = abs(min(0, totais["Custos"]))
    lucro_bruto = receita_liquida - custos
    despesas = abs(min(0, totais["Despesas operacionais"]))
    ebitda = lucro_bruto - despesas
    financeiro = totais["Resultado financeiro"]
    resultado = ebitda + financeiro
    return {
        "inicio": inicio,
        "fim": fim,
        "linhas": (
            ("RECEITA BRUTA", receita_bruta),
            ("(-) DEDUÇÕES", -deducoes),
            ("RECEITA LÍQUIDA", receita_liquida),
            ("(-) CUSTOS", -custos),
            ("LUCRO BRUTO", lucro_bruto),
            ("(-) DESPESAS OPERACIONAIS", -despesas),
            ("EBITDA", ebitda),
            ("RESULTADO FINANCEIRO", financeiro),
            ("RESULTADO", resultado),
        ),
        "nao_classificado_centavos": totais.get("Não classificado", 0),
    }


def resumo_financeiro(ator: dict, *, inicio=None, fim=None) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    hoje = date.today()
    inicio = _data_iso(inicio) or hoje.replace(day=1).isoformat()
    fim = _data_iso(fim) or hoje.isoformat()
    limite = (hoje + timedelta(days=7)).isoformat()
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        linha = conexao.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN natureza IN ('Receita','Conta a receber')
                AND status NOT IN ('Cancelado','Estornado') THEN valor_liquidado_centavos ELSE 0 END),0) receitas,
              COALESCE(SUM(CASE WHEN natureza IN ('Despesa','Conta a pagar','Reembolso')
                AND status NOT IN ('Cancelado','Estornado') THEN valor_liquidado_centavos ELSE 0 END),0) despesas,
              COALESCE(SUM(CASE WHEN status IN ('Rascunho','Previsto','Faturado','Enviado','Aguardando aprovação','Aprovado','Agendado','A vencer','Vencido','Parcial')
                THEN valor_original_centavos-valor_liquidado_centavos ELSE 0 END),0) pendente_valor,
              SUM(CASE WHEN status IN ('Rascunho','Previsto','Faturado','Enviado','Aguardando aprovação','Aprovado','Agendado','A vencer','Vencido','Parcial') THEN 1 ELSE 0 END) pendentes,
              SUM(CASE WHEN vencimento<? AND status IN ('Previsto','Faturado','Enviado','Aprovado','Agendado','A vencer','Vencido','Parcial') THEN 1 ELSE 0 END) vencidas,
              SUM(CASE WHEN vencimento BETWEEN ? AND ? AND status NOT IN ('Pago','Recebido','Liquidado','Conciliado','Cancelado','Estornado') THEN 1 ELSE 0 END) proximos_sete
            FROM fin_lancamentos
            WHERE empresa_id=? AND filial_id=? AND competencia BETWEEN ? AND ?
            """,
            (hoje.isoformat(), hoje.isoformat(), limite, empresa_id, filial_id, inicio, fim),
        ).fetchone()
        contas = conexao.execute(
            "SELECT id FROM fin_contas WHERE empresa_id=? AND filial_id=? AND status='Ativa'",
            (empresa_id, filial_id),
        ).fetchall()
    saldo = sum(saldo_conta(int(conta["id"]), ator) for conta in contas)
    projecao = projetar_fluxo_caixa(ator, dias=30, cenario="Realista")
    minimo = min((item["saldo_projetado_centavos"] for item in projecao), default=saldo)
    data_minimo = next((item["data"] for item in projecao if item["saldo_projetado_centavos"] == minimo), hoje.isoformat())
    orcamentos = listar_orcamentos(ator, ano=hoje.year, mes=hoje.month)
    alertas_orcamento = [item for item in orcamentos if item["utilizado_percentual"] >= item["limite_alerta_percentual"]]
    return {
        "inicio": inicio,
        "fim": fim,
        "receitas_centavos": int(linha["receitas"] or 0),
        "despesas_centavos": int(linha["despesas"] or 0),
        "resultado_centavos": int(linha["receitas"] or 0) - int(linha["despesas"] or 0),
        "saldo_centavos": saldo,
        "pendentes": int(linha["pendentes"] or 0),
        "pendente_valor_centavos": int(linha["pendente_valor"] or 0),
        "vencidas": int(linha["vencidas"] or 0),
        "proximos_sete": int(linha["proximos_sete"] or 0),
        "saldo_minimo_projetado_centavos": minimo,
        "data_saldo_minimo": data_minimo,
        "risco_caixa": minimo < 0,
        "alertas_orcamento": alertas_orcamento,
    }


def analisar_financeiro(ator: dict) -> dict:
    resumo = resumo_financeiro(ator)
    dre = calcular_dre(ator, resumo["inicio"], resumo["fim"])
    alertas = []
    if resumo["vencidas"]:
        alertas.append(f"Existem {resumo['vencidas']} obrigação(ões) vencida(s).")
    if resumo["proximos_sete"]:
        alertas.append(f"{resumo['proximos_sete']} conta(s) vencem nos próximos sete dias.")
    if resumo["risco_caixa"]:
        alertas.append(
            f"O saldo projetado fica negativo em {resumo['data_saldo_minimo']}, "
            f"atingindo {_moeda(resumo['saldo_minimo_projetado_centavos'])}."
        )
    for item in resumo["alertas_orcamento"]:
        nome = item.get("centro_custo_nome") or item.get("categoria_nome") or "Orçamento"
        alertas.append(f"{nome} consumiu {item['utilizado_percentual']:.1f}% do orçamento.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        duplicidades = conexao.execute(
            """
            SELECT COUNT(*) total FROM (
                SELECT COALESCE(parte_id,0),valor_original_centavos,competencia,COUNT(*) quantidade
                FROM fin_lancamentos
                WHERE empresa_id=? AND filial_id=?
                  AND natureza IN ('Despesa','Conta a pagar','Reembolso')
                  AND status NOT IN ('Cancelado','Estornado')
                GROUP BY COALESCE(parte_id,0),valor_original_centavos,competencia
                HAVING COUNT(*)>1
            )
            """,
            (empresa_id, filial_id),
        ).fetchone()["total"]
    if duplicidades:
        alertas.append(
            f"Foram encontrados {int(duplicidades)} grupo(s) de pagamentos semelhantes que merecem conferência."
        )
    recomendacoes = []
    if resumo["despesas_centavos"] > resumo["receitas_centavos"]:
        recomendacoes.append("Revisar as maiores despesas e o calendário de recebimentos do período.")
    if dre["nao_classificado_centavos"]:
        recomendacoes.append("Classificar os lançamentos pendentes no plano de contas para completar a DRE.")
    if resumo["vencidas"]:
        recomendacoes.append("Priorizar cobranças e renegociações das contas vencidas.")
    return {
        "resumo": resumo,
        "dre": dre,
        "alertas": alertas or ["Nenhuma anomalia crítica foi encontrada no contexto atual."],
        "recomendacoes": recomendacoes or ["Manter a conciliação e a classificação atualizadas."],
        "questoes_gestao": (
            "Quais centros de custo explicam a maior variação do resultado?",
            "O calendário de recebimentos cobre as obrigações dos próximos 30 dias?",
            "Existem fornecedores, clientes ou categorias com concentração excessiva?",
        ),
    }


def _dataframe_relatorio(tipo: str, ator: dict, inicio=None, fim=None) -> pd.DataFrame:
    """Prepara o conjunto correto para cada relatório, sem exportar dados irrelevantes."""
    normalizado = tipo.casefold()
    lancamentos = exportar_dataframe_financeiro(ator, inicio=inicio, fim=fim)
    if "contas a pagar" in normalizado:
        return lancamentos[lancamentos["tipo"].isin(("Despesa", "Conta a pagar", "Reembolso"))].copy()
    if "contas a receber" in normalizado:
        return lancamentos[lancamentos["tipo"].isin(("Receita", "Conta a receber"))].copy()
    if "fluxo" in normalizado:
        dados = pd.DataFrame(projetar_fluxo_caixa(ator, dias=90, cenario="Realista"))
        return dados.rename(columns={
            "data": "Data", "entradas_centavos": "Entradas (centavos)",
            "saidas_centavos": "Saídas (centavos)",
            "saldo_projetado_centavos": "Saldo projetado (centavos)",
            "cenario": "Cenário",
        })
    if "orçamento" in normalizado or "orcamento" in normalizado:
        dados = pd.DataFrame(listar_orcamentos(ator))
        if dados.empty:
            return pd.DataFrame(columns=("Competência", "Centro de custo", "Categoria", "Planejado", "Realizado", "Disponível", "Utilizado (%)"))
        return pd.DataFrame({
            "Competência": dados.apply(lambda item: f"{int(item['mes']):02d}/{int(item['ano'])}", axis=1),
            "Centro de custo": dados["centro_custo_nome"].fillna("Consolidado"),
            "Categoria": dados["categoria_nome"].fillna("Todas"),
            "Planejado": dados["planejado_centavos"] / 100,
            "Realizado": dados["realizado_centavos"] / 100,
            "Disponível": dados["disponivel_centavos"] / 100,
            "Utilizado (%)": dados["utilizado_percentual"],
        })
    if "auditoria" in normalizado:
        dados = listar_auditoria_financeira(ator, limite=5000)
        return pd.DataFrame(dados).rename(columns={
            "criado_em": "Data / hora", "usuario_nome": "Usuário",
            "acao": "Ação", "entidade": "Entidade", "entidade_id": "Registro",
        })
    if normalizado.strip() == "dre" or "demonstração" in normalizado:
        dre = calcular_dre(ator, inicio, fim)
        return pd.DataFrame(
            ((nome, valor / 100) for nome, valor in dre["linhas"]),
            columns=("DRE", "Valor"),
        )
    return lancamentos


def exportar_dataframe_financeiro(ator: dict, *, inicio=None, fim=None) -> pd.DataFrame:
    exigir_acao(ator, "exportar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtros = ["l.empresa_id=?", "l.filial_id=?"]
    parametros: list[object] = [empresa_id, filial_id]
    if inicio:
        filtros.append("l.competencia>=?")
        parametros.append(_data_iso(inicio))
    if fim:
        filtros.append("l.competencia<=?")
        parametros.append(_data_iso(fim))
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        dataframe = pd.read_sql_query(
            f"""
            SELECT l.id,l.competencia,l.vencimento,l.liquidacao,l.natureza AS tipo,
                   l.descricao,c.nome categoria,pc.codigo conta_contabil,
                   pc.grupo_dre,cc.nome centro_custo,p.nome parte,ct.nome conta,
                   l.valor_original_centavos/100.0 valor,
                   l.valor_liquidado_centavos/100.0 valor_liquidado,
                   (l.valor_original_centavos-l.valor_liquidado_centavos)/100.0 saldo,
                   l.status,l.contabilizado,l.conciliado
            FROM fin_lancamentos l
            LEFT JOIN fin_categorias c ON c.id=l.categoria_id
            LEFT JOIN fin_plano_contas pc ON pc.id=l.plano_conta_id
            LEFT JOIN centros_custo cc ON cc.id=l.centro_custo_id
            LEFT JOIN fin_partes p ON p.id=l.parte_id
            LEFT JOIN fin_contas ct ON ct.id=l.conta_id
            WHERE {' AND '.join(filtros)} ORDER BY l.competencia,l.id
            """,
            conexao,
            params=tuple(parametros),
        )
    return dataframe


def gerar_relatorio_financeiro(
    tipo: str,
    formato: str,
    ator: dict,
    *,
    inicio=None,
    fim=None,
) -> Path:
    exigir_acao(ator, "exportar")
    tipo = _normalizar_texto(tipo, 80) or "Lançamentos"
    formato = str(formato).strip().upper()
    if formato not in {"CSV", "XLSX", "EXCEL", "HTML", "PDF"}:
        raise ValueError("Formato de relatório inválido.")
    dataframe = _dataframe_relatorio(tipo, ator, inicio=inicio, fim=fim)
    empresa_id, filial_id = obter_escopo_ator(ator)
    pasta = banco_auth.STORAGE_DIR / "financeiro" / "relatorios" / str(empresa_id)
    pasta.mkdir(parents=True, exist_ok=True)
    base = f"{re.sub(r'[^a-z0-9]+', '_', tipo.lower())}_{datetime.now():%Y%m%d_%H%M%S}"
    if formato == "CSV":
        destino = pasta / f"{base}.csv"
        dataframe.to_csv(destino, index=False, encoding="utf-8-sig")
    elif formato in {"XLSX", "EXCEL"}:
        destino = pasta / f"{base}.xlsx"
        with pd.ExcelWriter(destino, engine="openpyxl") as writer:
            dataframe.to_excel(writer, sheet_name="Relatório", index=False)
            dre = pd.DataFrame(calcular_dre(ator, inicio, fim)["linhas"], columns=["Linha", "Valor (centavos)"])
            dre["Valor"] = dre.pop("Valor (centavos)") / 100
            dre.to_excel(writer, sheet_name="DRE", index=False)
    elif formato == "HTML":
        destino = pasta / f"{base}.html"
        destino.write_text(
            "<!doctype html><meta charset='utf-8'><title>Relatório financeiro</title>"
            "<style>body{font-family:Arial;margin:36px}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #ccc;padding:8px}</style>"
            f"<h1>{html.escape(tipo)}</h1>"
            f"<p>Período: {html.escape(str(inicio or 'início do período'))} a {html.escape(str(fim or 'data atual'))}</p>"
            f"{dataframe.to_html(index=False, escape=True)}",
            encoding="utf-8",
        )
    else:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as erro:
            raise RuntimeError("Instale reportlab para exportar relatórios em PDF.") from erro
        destino = pasta / f"{base}.pdf"
        estilos = getSampleStyleSheet()
        historia = [Paragraph(html.escape(tipo), estilos["Title"]), Spacer(1, 12)]
        limite_pdf = 5000
        colunas_pdf = list(dataframe.columns)
        dados_pdf = [[str(coluna)[:30] for coluna in colunas_pdf]]
        for _, linha in dataframe.head(limite_pdf).iterrows():
            dados_pdf.append([str(linha.get(chave, ""))[:70] for chave in colunas_pdf])
        if len(dataframe) > limite_pdf:
            historia.append(Paragraph(
                f"ATENÇÃO: o PDF contém {limite_pdf:,} de {len(dataframe):,} registros. "
                "Use XLSX ou CSV para o conjunto integral.", estilos["BodyText"]
            ))
            historia.append(Spacer(1, 8))
        if not colunas_pdf:
            dados_pdf = [["Resultado"], ["Nenhum dado encontrado para os filtros selecionados."]]
        largura_util = 740 / max(1, len(dados_pdf[0]))
        tabela = Table(dados_pdf, repeatRows=1, colWidths=[largura_util] * len(dados_pdf[0]))
        tabela.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15304D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey), ("FONTSIZE", (0, 0), (-1, -1), 7), ("PADDING", (0, 0), (-1, -1), 4)]))
        historia.append(tabela)
        SimpleDocTemplate(str(destino), pagesize=landscape(A4), title=tipo).build(historia)
    formato_registro = "XLSX" if formato in {"XLSX", "EXCEL"} else formato
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO relatorios_corporativos (
                empresa_id,filial_id,modulo,titulo,descricao,formato,
                filtros_json,arquivo,status,criado_por
            ) VALUES (?,?,'financeiro',?,?,?,?,?,'Concluído',?)
            """,
            (
                empresa_id, filial_id, tipo, "Relatório financeiro especializado",
                formato_registro,
                json.dumps({"inicio": inicio, "fim": fim}, ensure_ascii=False),
                str(destino.relative_to(banco_auth.STORAGE_DIR)), int(ator["id"]),
            ),
        )
        _registrar_evento(conexao, ator, "relatorio_gerado", "relatorios_corporativos", int(cursor.lastrowid), depois={"tipo": tipo, "formato": formato})
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="financeiro", categoria="relatorio")
    except Exception:
        pass
    return destino


def gerar_alertas_financeiros(ator: dict) -> list[str]:
    exigir_acao(ator, "visualizar")
    analise = analisar_financeiro(ator)
    with conectar() as conexao:
        for mensagem in analise["alertas"]:
            if mensagem.startswith("Nenhuma anomalia"):
                continue
            _notificar(conexao, ator, "Alerta financeiro", mensagem, "critico" if "negativo" in mensagem or "vencida" in mensagem else "aviso")
    return analise["alertas"]

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
