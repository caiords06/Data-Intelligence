"""Backend genérico dos espaços especializados da plataforma V8.

As entidades principais de cada departamento continuam em ``modulos.py``.
Este serviço persiste os recursos complementares exibidos nas sidebars, com
segregação por empresa/filial, permissão, paginação e exclusão lógica.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from auth.banco import conectar
from enterprise.catalogo import MODULOS
from enterprise.contexto import exigir_permissao, obter_escopo_ator


ESTADOS_REGISTRO = {"Ativo", "Arquivado", "Lixeira"}
PRIORIDADES = {"Baixa", "Média", "Alta", "Crítica"}


def _validar_destino(modulo: str, recurso: str) -> tuple[str, str]:
    modulo = str(modulo).strip().lower()
    recurso = str(recurso).strip().lower()
    if modulo not in MODULOS:
        raise ValueError("Módulo empresarial inválido.")
    if not recurso or len(recurso) > 60 or not recurso.replace("_", "").isalnum():
        raise ValueError("Recurso departamental inválido.")
    return modulo, recurso


def _centavos(valor) -> int:
    if valor in (None, ""):
        return 0
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as erro:
        raise ValueError("Valor monetário inválido.") from erro
    if not numero.is_finite():
        raise ValueError("Valor monetário inválido.")
    if numero < 0:
        raise ValueError("O valor não pode ser negativo.")
    return int(numero * 100)


def _data_iso(valor) -> str | None:
    if valor in (None, ""):
        return None
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Data inválida. Utilize DD/MM/AAAA ou AAAA-MM-DD.")


def _normalizar(dados: dict) -> dict:
    identificacao = str(dados.get("identificacao", "")).strip()
    if len(identificacao) < 2 or len(identificacao) > 160:
        raise ValueError("A identificação deve possuir entre 2 e 160 caracteres.")
    status = str(dados.get("status", "Pendente")).strip() or "Pendente"
    prioridade = str(dados.get("prioridade", "Média")).strip().title()
    if prioridade not in PRIORIDADES:
        raise ValueError("Prioridade inválida.")
    extras = dados.get("dados") or {}
    if not isinstance(extras, dict):
        raise ValueError("Os dados adicionais precisam formar um objeto.")
    dados_json = json.dumps(extras, ensure_ascii=False, default=str)
    if len(dados_json.encode("utf-8")) > 262_144:
        raise ValueError("Os dados adicionais excedem o limite de 256 KB.")
    return {
        "identificacao": identificacao,
        "descricao": str(dados.get("descricao", "")).strip()[:2000],
        "responsavel": str(dados.get("responsavel", "")).strip()[:160],
        "status": status[:80],
        "prioridade": prioridade,
        "valor_centavos": _centavos(dados.get("valor", 0)),
        "data_referencia": _data_iso(dados.get("data_referencia")),
        "dados_json": dados_json,
    }


def criar_recurso(modulo: str, recurso: str, dados: dict, ator: dict) -> int:
    modulo, recurso = _validar_destino(modulo, recurso)
    exigir_permissao(ator, modulo, "escrever")
    empresa_id, filial_id = obter_escopo_ator(ator)
    valores = _normalizar(dados)
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO recursos_departamentais (
                empresa_id, filial_id, modulo, recurso, identificacao,
                descricao, responsavel, status, prioridade, valor_centavos,
                data_referencia, dados_json, criado_por, atualizado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                empresa_id,
                filial_id,
                modulo,
                recurso,
                valores["identificacao"],
                valores["descricao"],
                valores["responsavel"],
                valores["status"],
                valores["prioridade"],
                valores["valor_centavos"],
                valores["data_referencia"],
                valores["dados_json"],
                int(ator["id"]),
                int(ator["id"]),
            ),
        )
        recurso_id = int(cursor.lastrowid)
        _registrar_evento(
            conexao,
            empresa_id,
            filial_id,
            ator,
            modulo,
            recurso,
            recurso_id,
            "Criado",
            None,
            valores,
        )
    from enterprise.workflows import executar_workflows

    executar_workflows(
        modulo,
        "registro_criado",
        {**valores, "recurso": recurso},
        ator,
        recurso_tipo="recursos_departamentais",
        recurso_id=recurso_id,
    )
    return recurso_id


def listar_recursos(
    modulo: str,
    recurso: str,
    ator: dict,
    *,
    pagina: int = 1,
    tamanho: int = 50,
    pesquisa: str = "",
    status: str = "Todos",
    estado: str = "Ativo",
) -> dict:
    modulo, recurso = _validar_destino(modulo, recurso)
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    pagina = max(1, int(pagina))
    tamanho = max(10, min(int(tamanho), 200))
    filtros = ["empresa_id = ?", "(filial_id = ? OR ? IS NULL)", "modulo = ?", "recurso = ?"]
    parametros: list[object] = [empresa_id, filial_id, filial_id, modulo, recurso]
    if estado != "Todos":
        if estado not in ESTADOS_REGISTRO:
            raise ValueError("Estado de registro inválido.")
        filtros.append("estado_registro = ?")
        parametros.append(estado)
    if status and status != "Todos":
        filtros.append("status = ?")
        parametros.append(str(status))
    termo = str(pesquisa).strip()
    if termo:
        filtros.append(
            "(identificacao LIKE ? OR descricao LIKE ? OR responsavel LIKE ?)"
        )
        busca = f"%{termo}%"
        parametros.extend((busca, busca, busca))
    where = " AND ".join(filtros)
    with conectar() as conexao:
        total = int(
            conexao.execute(
                f"SELECT COUNT(*) total FROM recursos_departamentais WHERE {where}",
                tuple(parametros),
            ).fetchone()["total"]
        )
        paginas = max(1, math.ceil(total / tamanho))
        pagina = min(pagina, paginas)
        registros = conexao.execute(
            f"""
            SELECT * FROM recursos_departamentais
            WHERE {where}
            ORDER BY atualizado_em DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (*parametros, tamanho, (pagina - 1) * tamanho),
        ).fetchall()
    itens = []
    for registro in registros:
        item = dict(registro)
        item["valor"] = int(item.get("valor_centavos") or 0) / 100
        try:
            item["dados"] = json.loads(item.pop("dados_json") or "{}")
        except json.JSONDecodeError:
            item["dados"] = {}
        itens.append(item)
    return {
        "registros": itens,
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "tamanho": tamanho,
    }


def obter_recurso(modulo: str, recurso: str, recurso_id: int, ator: dict) -> dict:
    modulo, recurso = _validar_destino(modulo, recurso)
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT * FROM recursos_departamentais
            WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)
              AND modulo = ? AND recurso = ?
            """,
            (int(recurso_id), empresa_id, filial_id, filial_id, modulo, recurso),
        ).fetchone()
    if registro is None:
        raise ValueError("Registro especializado não encontrado.")
    item = dict(registro)
    item["valor"] = int(item.get("valor_centavos") or 0) / 100
    try:
        item["dados"] = json.loads(item.pop("dados_json") or "{}")
    except json.JSONDecodeError:
        item["dados"] = {}
    return item


def atualizar_recurso(
    modulo: str,
    recurso: str,
    recurso_id: int,
    dados: dict,
    ator: dict,
) -> None:
    modulo, recurso = _validar_destino(modulo, recurso)
    exigir_permissao(ator, modulo, "escrever")
    empresa_id, filial_id = obter_escopo_ator(ator)
    valores = _normalizar(dados)
    with conectar() as conexao:
        anterior = conexao.execute(
            "SELECT * FROM recursos_departamentais "
            "WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL) "
            "AND modulo = ? AND recurso = ?",
            (int(recurso_id), empresa_id, filial_id, filial_id, modulo, recurso),
        ).fetchone()
        if anterior is None:
            raise ValueError("Registro especializado não encontrado.")
        conexao.execute(
            """
            UPDATE recursos_departamentais SET
                identificacao = ?, descricao = ?, responsavel = ?,
                status = ?, prioridade = ?, valor_centavos = ?,
                data_referencia = ?, dados_json = ?, atualizado_por = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)
            """,
            (
                valores["identificacao"],
                valores["descricao"],
                valores["responsavel"],
                valores["status"],
                valores["prioridade"],
                valores["valor_centavos"],
                valores["data_referencia"],
                valores["dados_json"],
                int(ator["id"]),
                int(recurso_id),
                empresa_id,
                filial_id,
                filial_id,
            ),
        )
        _registrar_evento(
            conexao,
            empresa_id,
            filial_id,
            ator,
            modulo,
            recurso,
            int(recurso_id),
            "Atualizado",
            dict(anterior),
            valores,
        )
    from enterprise.workflows import executar_workflows

    executar_workflows(
        modulo,
        "registro_atualizado",
        {**valores, "recurso": recurso},
        ator,
        recurso_tipo="recursos_departamentais",
        recurso_id=int(recurso_id),
    )


def alterar_estado_recurso(
    modulo: str,
    recurso: str,
    recurso_id: int,
    estado: str,
    ator: dict,
) -> None:
    modulo, recurso = _validar_destino(modulo, recurso)
    exigir_permissao(ator, modulo, "escrever")
    estado = str(estado).title()
    if estado not in ESTADOS_REGISTRO:
        raise ValueError("Estado de registro inválido.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        anterior = conexao.execute(
            "SELECT * FROM recursos_departamentais "
            "WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL) "
            "AND modulo = ? AND recurso = ?",
            (int(recurso_id), empresa_id, filial_id, filial_id, modulo, recurso),
        ).fetchone()
        if anterior is None:
            raise ValueError("Registro especializado não encontrado.")
        arquivado_em = None if estado == "Ativo" else datetime.now().isoformat(timespec="seconds")
        arquivado_por = None if estado == "Ativo" else int(ator["id"])
        conexao.execute(
            """
            UPDATE recursos_departamentais SET estado_registro = ?,
                arquivado_em = ?, arquivado_por = ?, atualizado_por = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)
            """,
            (
                estado,
                arquivado_em,
                arquivado_por,
                int(ator["id"]),
                int(recurso_id),
                empresa_id,
                filial_id,
                filial_id,
            ),
        )
        _registrar_evento(
            conexao,
            empresa_id,
            filial_id,
            ator,
            modulo,
            recurso,
            int(recurso_id),
            estado,
            dict(anterior),
            {"estado_registro": estado},
        )


def resumo_recursos(modulo: str, ator: dict) -> dict:
    modulo = str(modulo).strip().lower()
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT recurso, COUNT(*) total,
                   SUM(CASE WHEN status IN ('Pendente', 'Aberto', 'Planejado')
                       THEN 1 ELSE 0 END) pendentes
            FROM recursos_departamentais
            WHERE empresa_id = ? AND (filial_id = ? OR ? IS NULL) AND modulo = ?
              AND estado_registro = 'Ativo'
            GROUP BY recurso
            """,
            (empresa_id, filial_id, filial_id, modulo),
        ).fetchall()
    por_recurso = {
        str(item["recurso"]): {
            "total": int(item["total"] or 0),
            "pendentes": int(item["pendentes"] or 0),
        }
        for item in linhas
    }
    return {
        "total": sum(item["total"] for item in por_recurso.values()),
        "por_recurso": por_recurso,
    }


def _registrar_evento(
    conexao,
    empresa_id: int,
    filial_id: int | None,
    ator: dict,
    modulo: str,
    recurso: str,
    recurso_id: int,
    acao: str,
    antes: dict | None,
    depois: dict | None,
) -> None:
    operacao_id = f"V8-{uuid4().hex[:12].upper()}"
    conexao.execute(
        """
        INSERT INTO historico_alteracoes (
            operacao_id, empresa_id, filial_id, usuario_id, modulo,
            entidade, entidade_id, acao, dados_antes, dados_depois
        ) VALUES (?, ?, ?, ?, ?, 'recursos_departamentais', ?, ?, ?, ?)
        """,
        (
            operacao_id,
            empresa_id,
            filial_id,
            int(ator["id"]),
            modulo,
            recurso_id,
            acao,
            json.dumps(antes, ensure_ascii=False, default=str) if antes else None,
            json.dumps(depois, ensure_ascii=False, default=str) if depois else None,
        ),
    )
    conexao.execute(
        """
        INSERT INTO atividades (
            usuario_id, empresa_id, filial_id, modulo, acao, descricao,
            recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, ?, ?, ?, 'recursos_departamentais', ?)
        """,
        (
            int(ator["id"]),
            empresa_id,
            filial_id,
            modulo,
            f"recurso_{acao.lower()}",
            f"{recurso.replace('_', ' ').title()}: {acao.lower()}",
            recurso_id,
        ),
    )

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
