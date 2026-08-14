"""Núcleo compartilhado do domínio Estoque (V9.5)."""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from enterprise.repositories import conectar
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
