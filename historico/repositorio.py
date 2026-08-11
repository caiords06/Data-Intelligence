"""Repositório SQLite do histórico resumido de análises."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from auth.banco import conectar, registrar_auditoria
from auth.sessao import SESSAO
from enterprise.contexto import garantir_contexto_sessao


def _contexto_historico() -> tuple[int | None, int | None]:
    """Retorna o contexto ativo sem quebrar bases legadas sem Enterprise Core.

    A interface sempre trabalha com uma sessão autenticada e, nesse caso, o
    isolamento por empresa/filial continua obrigatório. A alternativa ``NULL``
    existe somente para migrações, testes e registros criados antes do suporte
    multiempresa.
    """
    if SESSAO.usuario is None:
        return None, None
    return garantir_contexto_sessao()


def inicializar_historico() -> None:
    with conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_analises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                fonte TEXT NOT NULL,
                quantidade_arquivos INTEGER NOT NULL,
                total_registros INTEGER NOT NULL,
                total_colunas INTEGER NOT NULL,
                score_qualidade REAL,
                nivel_qualidade TEXT,
                status TEXT NOT NULL DEFAULT 'concluida',
                resumo_json TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        colunas = {
            item["name"]
            for item in conexao.execute(
                "PRAGMA table_info(historico_analises)"
            ).fetchall()
        }
        for nome, definicao in (
            ("empresa_id", "INTEGER"),
            ("filial_id", "INTEGER"),
            ("estado_registro", "TEXT NOT NULL DEFAULT 'Ativo'"),
            ("excluido_em", "TEXT"),
            ("excluido_por", "INTEGER"),
        ):
            if nome not in colunas:
                conexao.execute(
                    f"ALTER TABLE historico_analises ADD COLUMN {nome} {definicao}"
                )


def _json_seguro(valor):
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, dict):
        return {str(chave): _json_seguro(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [_json_seguro(item) for item in valor]
    if hasattr(valor, "item"):
        try:
            return valor.item()
        except (TypeError, ValueError):
            pass
    return str(valor)


def registrar_analise(
    resultado: dict,
    usuario_id: int,
    *,
    empresa_id: int | None = None,
    filial_id: int | None = None,
) -> int:
    inicializar_historico()
    df = resultado.get("dataframe")
    total_registros = int(len(df)) if isinstance(df, pd.DataFrame) else 0
    total_colunas = int(len(df.columns)) if isinstance(df, pd.DataFrame) else 0
    qualidade = resultado.get("qualidade") or {}
    arquivos = [Path(caminho).name for caminho in resultado.get("arquivos", [])]
    resumo = {
        "arquivos": arquivos,
        "categoria": resultado.get("categoria"),
        "configuracao": resultado.get("configuracao") or {},
        "indicadores": resultado.get("indicadores") or {},
        "qualidade": {
            chave: qualidade.get(chave)
            for chave in (
                "completude",
                "unicidade",
                "validade",
                "consistencia",
                "score_qualidade",
                "nivel_qualidade",
                "linhas_duplicadas",
                "valores_ausentes",
            )
        },
        "temporal": resultado.get("temporal") or {},
    }
    configuracao = resultado.get("configuracao") or {}
    if empresa_id is None:
        if SESSAO.empresa_id is not None:
            empresa_id, filial_id = SESSAO.empresa_id, SESSAO.filial_id
        else:
            try:
                empresa_id, filial_id = garantir_contexto_sessao()
            except (PermissionError, RuntimeError):
                empresa_id, filial_id = None, None
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO historico_analises (
                usuario_id, empresa_id, filial_id,
                categoria, fonte, quantidade_arquivos,
                total_registros, total_colunas, score_qualidade,
                nivel_qualidade, status, resumo_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'concluida', ?)
            """,
            (
                int(usuario_id),
                empresa_id,
                filial_id,
                str(resultado.get("categoria") or "desconhecida"),
                str(configuracao.get("fonte") or "computador"),
                len(arquivos),
                total_registros,
                total_colunas,
                qualidade.get("score_qualidade"),
                qualidade.get("nivel_qualidade"),
                json.dumps(_json_seguro(resumo), ensure_ascii=False),
            ),
        )
        historico_id = int(cursor.lastrowid)
    registrar_auditoria(
        "analise_concluida",
        usuario_id=int(usuario_id),
        detalhes=f"historico_id={historico_id};categoria={resultado.get('categoria')}",
    )
    return historico_id


def listar_historico(ator: dict, limite: int = 200) -> list[dict]:
    inicializar_historico()
    limite = max(1, min(int(limite), 1000))
    empresa_id, filial_id = _contexto_historico()
    with conectar() as conexao:
        if empresa_id is None:
            restricao_dono = "" if ator.get("perfil") == "admin" else "AND h.usuario_id = ?"
            parametros = (() if ator.get("perfil") == "admin" else (int(ator["id"]),))
            registros = conexao.execute(
                f"""
                SELECT h.*, u.nome AS nome_usuario
                FROM historico_analises h
                LEFT JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.empresa_id IS NULL {restricao_dono}
                  AND COALESCE(h.estado_registro, 'Ativo') = 'Ativo'
                ORDER BY h.id DESC LIMIT ?
                """,
                (*parametros, limite),
            ).fetchall()
        elif ator.get("perfil") == "admin":
            registros = conexao.execute(
                """
                SELECT h.*, u.nome AS nome_usuario
                FROM historico_analises h
                LEFT JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.empresa_id = ?
                  AND (h.filial_id = ? OR h.filial_id IS NULL)
                  AND COALESCE(h.estado_registro, 'Ativo') = 'Ativo'
                ORDER BY h.id DESC LIMIT ?
                """,
                (empresa_id, filial_id, limite),
            ).fetchall()
        else:
            registros = conexao.execute(
                """
                SELECT h.*, u.nome AS nome_usuario
                FROM historico_analises h
                LEFT JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.usuario_id = ? AND h.empresa_id = ?
                  AND (h.filial_id = ? OR h.filial_id IS NULL)
                  AND COALESCE(h.estado_registro, 'Ativo') = 'Ativo'
                ORDER BY h.id DESC LIMIT ?
                """,
                (int(ator["id"]), empresa_id, filial_id, limite),
            ).fetchall()
    return [dict(registro) for registro in registros]


def obter_analise(historico_id: int, ator: dict) -> dict:
    inicializar_historico()
    empresa_id, filial_id = _contexto_historico()
    with conectar() as conexao:
        if empresa_id is None:
            registro = conexao.execute(
                """
                SELECT * FROM historico_analises
                WHERE id=? AND empresa_id IS NULL
                  AND COALESCE(estado_registro, 'Ativo')='Ativo'
                """,
                (int(historico_id),),
            ).fetchone()
        else:
            registro = conexao.execute(
                """
                SELECT * FROM historico_analises
                WHERE id=? AND empresa_id=?
                  AND (filial_id=? OR filial_id IS NULL)
                  AND COALESCE(estado_registro, 'Ativo')='Ativo'
                """,
                (int(historico_id), empresa_id, filial_id),
            ).fetchone()
    if registro is None:
        raise ValueError("Registro de histórico não encontrado.")
    if ator.get("perfil") != "admin" and int(registro["usuario_id"]) != int(ator["id"]):
        raise PermissionError("Você não possui acesso a esta análise.")
    resultado = dict(registro)
    resultado["resumo"] = json.loads(resultado.pop("resumo_json"))
    return resultado


def excluir_analise(historico_id: int, ator: dict) -> None:
    registro = obter_analise(historico_id, ator)
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE historico_analises
            SET estado_registro='Lixeira', excluido_em=CURRENT_TIMESTAMP,
                excluido_por=?
            WHERE id=?
            """,
            (int(ator["id"]), int(historico_id)),
        )
    registrar_auditoria(
        "historico_excluido",
        usuario_id=int(ator["id"]),
        detalhes=f"historico_id={historico_id};dono={registro['usuario_id']}",
    )


def excluir_analises(historico_ids, ator: dict) -> int:
    """Move vários registros autorizados para a lixeira em uma transação.

    Todos os IDs são validados antes da primeira alteração para evitar uma
    exclusão parcial quando a seleção contém um registro fora do escopo do
    usuário/empresa/filial atual.
    """
    ids = tuple(dict.fromkeys(int(item) for item in historico_ids))
    if not ids:
        return 0

    registros = [obter_analise(item, ator) for item in ids]
    placeholders = ",".join("?" for _ in ids)
    with conectar() as conexao:
        cursor = conexao.execute(
            f"""
            UPDATE historico_analises
            SET estado_registro='Lixeira', excluido_em=CURRENT_TIMESTAMP,
                excluido_por=?
            WHERE id IN ({placeholders})
              AND COALESCE(estado_registro, 'Ativo')='Ativo'
            """,
            (int(ator["id"]), *ids),
        )
        quantidade = int(cursor.rowcount or 0)

    registrar_auditoria(
        "historico_exclusao_multipla",
        usuario_id=int(ator["id"]),
        detalhes=(
            f"quantidade={quantidade};ids={','.join(str(item) for item in ids)};"
            f"donos={','.join(str(item['usuario_id']) for item in registros)}"
        ),
    )
    return quantidade
