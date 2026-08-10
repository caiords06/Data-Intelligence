"""Repositório SQLite do histórico resumido de análises."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from auth.banco import conectar, registrar_auditoria


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


def registrar_analise(resultado: dict, usuario_id: int) -> int:
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
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO historico_analises (
                usuario_id, categoria, fonte, quantidade_arquivos,
                total_registros, total_colunas, score_qualidade,
                nivel_qualidade, status, resumo_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'concluida', ?)
            """,
            (
                int(usuario_id),
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
    with conectar() as conexao:
        if ator.get("perfil") == "admin":
            registros = conexao.execute(
                """
                SELECT h.*, u.nome AS nome_usuario
                FROM historico_analises h
                LEFT JOIN usuarios u ON u.id = h.usuario_id
                ORDER BY h.id DESC LIMIT ?
                """,
                (limite,),
            ).fetchall()
        else:
            registros = conexao.execute(
                """
                SELECT h.*, u.nome AS nome_usuario
                FROM historico_analises h
                LEFT JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.usuario_id = ?
                ORDER BY h.id DESC LIMIT ?
                """,
                (int(ator["id"]), limite),
            ).fetchall()
    return [dict(registro) for registro in registros]


def obter_analise(historico_id: int, ator: dict) -> dict:
    inicializar_historico()
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM historico_analises WHERE id = ?",
            (int(historico_id),),
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
            "DELETE FROM historico_analises WHERE id = ?",
            (int(historico_id),),
        )
    registrar_auditoria(
        "historico_excluido",
        usuario_id=int(ator["id"]),
        detalhes=f"historico_id={historico_id};dono={registro['usuario_id']}",
    )
