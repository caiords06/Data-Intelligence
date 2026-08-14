"""Núcleo compartilhado do domínio Tecnologia (V9.5)."""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from enterprise.repositories import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator, tem_permissao

ACOES_TECNOLOGIA = {
    "consultar", "consultar_meus_chamados", "abrir_chamado", "atender_chamado", "resolver_chamado",
    "gerenciar_ativos", "registrar_telemetria", "gerenciar_manutencao",
    "gerenciar_rede", "autorizar_descoberta", "registrar_descoberta",
    "gerenciar_licencas", "gerenciar_sistemas", "gerenciar_monitoramento",
    "gerenciar_conhecimento", "gerenciar_contratos", "gerenciar_problemas",
    "gerenciar_mudancas", "aprovar_mudancas", "gerenciar_seguranca",
    "acessar_remotamente", "consultar_auditoria", "gerar_relatorio",
    "configurar",
}

PERFIS_ACOES = {
    "ti_solicitante": {"consultar", "consultar_meus_chamados", "abrir_chamado"},
    "ti_suporte_n1": {
        "consultar", "consultar_meus_chamados", "abrir_chamado", "atender_chamado", "resolver_chamado",
        "registrar_telemetria", "gerenciar_conhecimento", "gerar_relatorio",
    },
    "ti_suporte_n2": ACOES_TECNOLOGIA - {
        "autorizar_descoberta", "aprovar_mudancas", "configurar",
    },
    "ti_gestor": ACOES_TECNOLOGIA,
    "ti_auditor": {"consultar", "consultar_auditoria", "gerar_relatorio"},
    "ti": ACOES_TECNOLOGIA - {
        "autorizar_descoberta", "aprovar_mudancas", "configurar",
    },
    "ti_plus": ACOES_TECNOLOGIA - {"configurar"},
}

SLA_MINUTOS = {
    "Baixa": (480, 4320),
    "Média": (240, 1440),
    "Alta": (60, 480),
    "Crítica": (15, 120),
}

STATUS_CHAMADO = {
    "Novo", "Triagem", "Em atendimento", "Aguardando usuário",
    "Aguardando terceiro", "Resolvido", "Reaberto", "Cancelado",
}

PROVEDORES_REMOTOS = {"AnyDesk", "TeamViewer", "RustDesk"}


def _texto(valor, limite=500) -> str:
    return str(valor or "").strip()[:limite]


def _inteiro(valor, *, minimo=0) -> int:
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError) as erro:
        raise ValueError("Informe um número inteiro válido.") from erro
    if numero < minimo:
        raise ValueError(f"O valor deve ser maior ou igual a {minimo}.")
    return numero


def _decimal(valor, *, minimo=0.0, maximo=None, permite_vazio=True):
    if valor in (None, "") and permite_vazio:
        return None
    try:
        numero = float(str(valor).replace(",", "."))
    except (TypeError, ValueError) as erro:
        raise ValueError("Informe um valor numérico válido.") from erro
    if not math.isfinite(numero) or numero < minimo or (maximo is not None and numero > maximo):
        raise ValueError("O valor numérico está fora do intervalo permitido.")
    return numero


def _centavos(valor) -> int:
    texto = str(valor if valor not in (None, "") else "0").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", texto):
        texto = texto.replace(".", "")
    try:
        numero = Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as erro:
        raise ValueError("Informe um valor monetário válido.") from erro
    if not numero.is_finite() or numero < 0:
        raise ValueError("O valor monetário não pode ser negativo.")
    return int(numero * 100)


def _data(valor, *, obrigatoria=False):
    texto = _texto(valor, 30)
    if not texto and not obrigatoria:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(texto, formato).isoformat(sep=" ")[:19]
        except ValueError:
            continue
    raise ValueError("Data inválida. Utilize DD/MM/AAAA ou AAAA-MM-DD.")


def _numero(prefixo: str) -> str:
    return f"{prefixo}-{datetime.now():%Y%m%d%H%M%S}-{uuid4().hex[:4].upper()}"


def tem_permissao_tecnologia(ator: dict | None, acao: str) -> bool:
    if acao not in ACOES_TECNOLOGIA:
        return False
    # O portal de suporte é corporativo: qualquer usuário autenticado pode
    # abrir e consultar os próprios chamados, mesmo sem acesso operacional a TI.
    if acao in {"abrir_chamado", "consultar_meus_chamados"}:
        return bool(ator and ator.get("id"))
    if not tem_permissao(ator, "ti", "ler"):
        return False
    if ator and ator.get("perfil") == "admin":
        return True
    try:
        empresa_id, _ = obter_escopo_ator(ator)
    except (PermissionError, RuntimeError):
        return False
    with conectar() as conexao:
        personalizado = conexao.execute(
            "SELECT permitido FROM ti_permissoes_acoes WHERE usuario_id=? AND empresa_id=? AND acao=?",
            (int(ator["id"]), empresa_id, acao),
        ).fetchone()
    if personalizado is not None:
        return bool(personalizado["permitido"])
    perfil = _texto((ator or {}).get("perfil_acesso"), 50).lower()
    if perfil in PERFIS_ACOES:
        return acao in PERFIS_ACOES[perfil]
    if acao in {"consultar", "gerar_relatorio", "consultar_auditoria"}:
        return tem_permissao(ator, "ti", "ler")
    if acao in {"aprovar_mudancas", "autorizar_descoberta"}:
        return tem_permissao(ator, "ti", "aprovar")
    return tem_permissao(ator, "ti", "escrever")


def exigir_acao(ator: dict, acao: str) -> None:
    if not tem_permissao_tecnologia(ator, acao):
        raise PermissionError("Seu perfil não possui permissão para esta ação de Tecnologia.")


def salvar_permissao_acao(usuario_id: int, acao: str, permitido: bool, ator: dict) -> None:
    if ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem configurar ações de Tecnologia.")
    if acao not in ACOES_TECNOLOGIA:
        raise ValueError("Ação de Tecnologia inválida.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            """INSERT INTO ti_permissoes_acoes (usuario_id,empresa_id,acao,permitido)
               VALUES (?,?,?,?) ON CONFLICT(usuario_id,empresa_id,acao) DO UPDATE SET
               permitido=excluded.permitido,atualizado_em=CURRENT_TIMESTAMP""",
            (int(usuario_id), empresa_id, acao, int(bool(permitido))),
        )


def _evento(conexao, ator, acao, recurso_tipo, recurso_id, antes=None, depois=None, observacao=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    antes_json = json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None
    depois_json = json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None
    conexao.execute(
        """INSERT INTO ti_historico (
            empresa_id,filial_id,usuario_id,acao,recurso_tipo,recurso_id,
            antes_json,depois_json,observacao
        ) VALUES (?,?,?,?,?,?,?,?,?)""",
        (empresa_id, filial_id, int(ator["id"]), acao, recurso_tipo,
         int(recurso_id) if recurso_id is not None else None, antes_json, depois_json,
         _texto(observacao, 1500) or None),
    )
    conexao.execute(
        """INSERT INTO historico_alteracoes (
            operacao_id,empresa_id,filial_id,usuario_id,modulo,entidade,
            entidade_id,acao,dados_antes,dados_depois
        ) VALUES (?,?,?,?, 'ti',?,?,?,?,?)""",
        (f"TI-{uuid4().hex[:14].upper()}", empresa_id, filial_id, int(ator["id"]),
         recurso_tipo, int(recurso_id or 0), acao, antes_json, depois_json),
    )
    conexao.execute(
        """INSERT INTO atividades (
            usuario_id,empresa_id,filial_id,modulo,acao,descricao,recurso_tipo,recurso_id
        ) VALUES (?,?,?,'ti',?,?,?,?)""",
        (int(ator["id"]), empresa_id, filial_id, acao,
         f"Tecnologia: {recurso_tipo} #{recurso_id}", recurso_tipo, recurso_id),
    )


def _notificar(conexao, ator, titulo, mensagem, nivel="aviso", recurso_tipo=None, recurso_id=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """INSERT INTO notificacoes (
            empresa_id,filial_id,modulo,titulo,mensagem,nivel,recurso_tipo,recurso_id
        ) VALUES (?,?,'ti',?,?,?,?,?)""",
        (empresa_id, filial_id, titulo, mensagem, nivel, recurso_tipo, recurso_id),
    )


def _abrir_alerta(conexao, ator, tipo, titulo, mensagem, severidade, recurso_tipo, recurso_id) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """INSERT OR IGNORE INTO ti_alertas (
            empresa_id,filial_id,tipo,titulo,mensagem,severidade,recurso_tipo,recurso_id,status
        ) VALUES (?,?,?,?,?,?,?,?,'Aberto')""",
        (empresa_id, filial_id, tipo, titulo, mensagem, severidade, recurso_tipo, int(recurso_id)),
    )
