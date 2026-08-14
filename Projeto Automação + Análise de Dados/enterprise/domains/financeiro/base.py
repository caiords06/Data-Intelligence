"""Núcleo compartilhado do domínio Financeiro (V9.5)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from auth import banco as banco_auth
from enterprise.repositories import conectar
from enterprise.contexto import obter_escopo_ator, tem_permissao

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
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        ("lancamentos_financeiros",),
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
