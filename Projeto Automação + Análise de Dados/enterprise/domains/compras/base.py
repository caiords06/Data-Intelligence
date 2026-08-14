"""Núcleo compartilhado do domínio Compras (V9.5)."""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from enterprise.repositories import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator, tem_permissao

ACOES_COMPRAS = {
    "consultar_valores", "criar_solicitacao", "enviar_solicitacao",
    "analisar_solicitacao", "aprovar_solicitacao", "criar_cotacao",
    "registrar_proposta", "negociar", "selecionar_fornecedor",
    "criar_pedido", "aprovar_pedido", "enviar_pedido",
    "receber", "resolver_divergencia", "integrar_estoque",
    "integrar_financeiro", "gerenciar_fornecedores", "homologar_fornecedor",
    "avaliar_fornecedor", "gerenciar_contratos", "gerenciar_catalogo",
    "gerar_relatorio", "consultar_auditoria", "configurar",
}

PERFIS_ACOES = {
    "compras_solicitante": {"criar_solicitacao", "enviar_solicitacao"},
    "compras_comprador": ACOES_COMPRAS - {
        "aprovar_solicitacao", "aprovar_pedido", "homologar_fornecedor",
        "resolver_divergencia", "configurar", "consultar_auditoria",
    },
    "compras_gestor": ACOES_COMPRAS,
    "compras_recebimento": {
        "consultar_valores", "receber", "resolver_divergencia",
        "integrar_estoque", "avaliar_fornecedor", "gerar_relatorio",
    },
    "compras_auditor": {
        "consultar_valores", "gerar_relatorio", "consultar_auditoria",
    },
    "compras": ACOES_COMPRAS - {
        "aprovar_solicitacao", "aprovar_pedido", "homologar_fornecedor",
        "configurar",
    },
    "compras_plus": ACOES_COMPRAS - {"configurar"},
}

STATUS_SOLICITACAO = {
    "Rascunho", "Enviada", "Em análise", "Aguardando aprovação",
    "Aprovada", "Rejeitada", "Alteração solicitada", "Em cotação",
    "Cotada", "Pedido criado", "Compra realizada", "Recebida",
    "Cancelada", "Encerrada",
}

STATUS_PEDIDO = {
    "Rascunho", "Aguardando aprovação", "Aprovado",
    "Enviado ao fornecedor", "Confirmado pelo fornecedor", "Em produção",
    "Em transporte", "Parcialmente recebido", "Recebido", "Cancelado",
    "Encerrado",
}


def _texto(valor, limite=500) -> str:
    return str(valor or "").strip()[:limite]


def _centavos(valor, *, permite_negativo=False) -> int:
    texto = str(valor if valor is not None else "0").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", texto):
        texto = texto.replace(".", "")
    try:
        numero = Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as erro:
        raise ValueError("Informe um valor monetário válido.") from erro
    if not numero.is_finite() or (numero < 0 and not permite_negativo):
        raise ValueError("O valor monetário não pode ser negativo.")
    return int(numero * 100)


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


def tem_permissao_compras(ator: dict | None, acao: str) -> bool:
    if acao not in ACOES_COMPRAS or not tem_permissao(ator, "compras", "ler"):
        return False
    if ator and ator.get("perfil") == "admin":
        return True
    try:
        empresa_id, _ = obter_escopo_ator(ator)
    except (PermissionError, RuntimeError):
        return False
    with conectar() as conexao:
        personalizado = conexao.execute(
            "SELECT permitido FROM cmp_permissoes_acoes WHERE usuario_id=? AND empresa_id=? AND acao=?",
            (int(ator["id"]), empresa_id, acao),
        ).fetchone()
    if personalizado is not None:
        return bool(personalizado["permitido"])
    perfil = _texto(ator.get("perfil_acesso"), 50).lower()
    if perfil in PERFIS_ACOES:
        return acao in PERFIS_ACOES[perfil]
    if acao in {"consultar_valores", "gerar_relatorio", "consultar_auditoria"}:
        return tem_permissao(ator, "compras", "ler")
    if acao.startswith("aprovar_") or acao in {"homologar_fornecedor", "resolver_divergencia"}:
        return tem_permissao(ator, "compras", "aprovar")
    return tem_permissao(ator, "compras", "escrever")


def exigir_acao(ator: dict, acao: str) -> None:
    if not tem_permissao_compras(ator, acao):
        raise PermissionError("Seu perfil não possui permissão para esta ação de Compras.")


def salvar_permissao_acao(usuario_id: int, acao: str, permitido: bool, ator: dict) -> None:
    if ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem configurar ações de Compras.")
    if acao not in ACOES_COMPRAS:
        raise ValueError("Ação de Compras inválida.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            """INSERT INTO cmp_permissoes_acoes (usuario_id,empresa_id,acao,permitido)
               VALUES (?,?,?,?) ON CONFLICT(usuario_id,empresa_id,acao) DO UPDATE SET
               permitido=excluded.permitido, atualizado_em=CURRENT_TIMESTAMP""",
            (int(usuario_id), empresa_id, acao, int(bool(permitido))),
        )


def _evento(conexao, ator, acao, recurso_tipo, recurso_id, antes=None, depois=None, observacao=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    antes_json = json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None
    depois_json = json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None
    conexao.execute(
        """INSERT INTO cmp_historico (
            empresa_id,filial_id,usuario_id,acao,recurso_tipo,recurso_id,
            antes_json,depois_json,observacao
        ) VALUES (?,?,?,?,?,?,?,?,?)""",
        (empresa_id, filial_id, int(ator["id"]), acao, recurso_tipo,
         int(recurso_id) if recurso_id is not None else None, antes_json, depois_json,
         _texto(observacao, 1000) or None),
    )
    conexao.execute(
        """INSERT INTO historico_alteracoes (
            operacao_id,empresa_id,filial_id,usuario_id,modulo,entidade,
            entidade_id,acao,dados_antes,dados_depois
        ) VALUES (?,?,?,?, 'compras',?,?,?,?,?)""",
        (str(uuid4()), empresa_id, filial_id, int(ator["id"]), recurso_tipo,
         int(recurso_id or 0), acao, antes_json, depois_json),
    )
    conexao.execute(
        """INSERT INTO atividades (
            usuario_id,empresa_id,filial_id,modulo,acao,descricao,recurso_tipo,recurso_id
        ) VALUES (?,?,?,'compras',?,?,?,?)""",
        (int(ator["id"]), empresa_id, filial_id, acao,
         f"Compras: {recurso_tipo} #{recurso_id}", recurso_tipo, recurso_id),
    )


def _notificar(conexao, ator, titulo, mensagem, nivel="aviso", recurso_tipo=None, recurso_id=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """INSERT INTO notificacoes (
            empresa_id,filial_id,modulo,titulo,mensagem,nivel,recurso_tipo,recurso_id
        ) VALUES (?,?,'compras',?,?,?,?,?)""",
        (empresa_id, filial_id, titulo, mensagem, nivel, recurso_tipo, recurso_id),
    )


def _tarefa(conexao, ator, modulo, titulo, descricao, recurso_tipo, recurso_id, prioridade="Média") -> int:
    empresa_id, filial_id = obter_escopo_ator(ator)
    return int(conexao.execute(
        """INSERT INTO tarefas (
            empresa_id,filial_id,modulo,titulo,descricao,prioridade,status,
            recurso_tipo,recurso_id
        ) VALUES (?,?,?,?,?,?,'Pendente',?,?)""",
        (empresa_id, filial_id, modulo, titulo, descricao, prioridade, recurso_tipo, int(recurso_id)),
    ).lastrowid)
