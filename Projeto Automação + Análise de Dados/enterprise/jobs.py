"""Gerenciador persistente de trabalhos longos da aplicação."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from auth.banco import conectar
from enterprise.contexto import obter_escopo_ator


STATUS_FINAIS = {"Concluído", "Falhou", "Cancelado"}
STATUS_BLOQUEADORES = STATUS_FINAIS | {"Cancelamento solicitado"}


def _escopo(ator):
    return obter_escopo_ator(ator)


def criar_job(tipo: str, titulo: str, ator: dict) -> dict:
    empresa_id, filial_id = _escopo(ator)
    codigo = f"JOB-{datetime.now():%Y%m%d}-{uuid4().hex[:8].upper()}"
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO jobs (
                codigo, empresa_id, filial_id, usuario_id, tipo, titulo
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (codigo, empresa_id, filial_id, ator["id"], str(tipo), str(titulo)),
        )
        job_id = int(cursor.lastrowid)
    return {"id": job_id, "codigo": codigo}


def iniciar_job(job_id: int, ator: dict) -> None:
    _atualizar_job(
        job_id,
        ator,
        status="Executando",
        progresso=1,
        mensagem="Trabalho iniciado.",
        iniciar=True,
    )


def atualizar_job(job_id: int, progresso: int, mensagem: str, ator: dict) -> None:
    _atualizar_job(
        job_id,
        ator,
        status="Executando",
        progresso=progresso,
        mensagem=mensagem,
    )


def concluir_job(job_id: int, ator: dict, resultado: dict | None = None) -> None:
    _atualizar_job(
        job_id,
        ator,
        status="Concluído",
        progresso=100,
        mensagem="Trabalho concluído.",
        resultado=resultado,
        concluir=True,
    )


def falhar_job(job_id: int, ator: dict, erro: str) -> None:
    _atualizar_job(
        job_id,
        ator,
        status="Falhou",
        mensagem="O trabalho falhou.",
        erro=str(erro)[:4000],
        concluir=True,
    )


def solicitar_cancelamento(job_id: int, ator: dict) -> None:
    empresa_id, filial_id = _escopo(ator)
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE jobs
            SET cancelamento_solicitado = 1,
                status = CASE
                    WHEN status = 'Pendente' THEN 'Cancelado'
                    WHEN status = 'Executando' THEN 'Cancelamento solicitado'
                    ELSE status
                END,
                mensagem = CASE WHEN status='Pendente'
                    THEN 'Trabalho cancelado antes da execução.'
                    ELSE 'Cancelamento solicitado pelo usuário.' END,
                concluido_em = CASE WHEN status='Pendente'
                    THEN CURRENT_TIMESTAMP ELSE concluido_em END
            WHERE id = ? AND empresa_id = ? AND filial_id IS ?
              AND usuario_id = ?
            """,
            (int(job_id), empresa_id, filial_id, int(ator["id"])),
        )
        if cursor.rowcount == 0:
            raise ValueError("Job não encontrado ou não cancelável.")


def cancelamento_solicitado(job_id: int, ator: dict) -> bool:
    empresa_id, filial_id = _escopo(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT cancelamento_solicitado FROM jobs "
            "WHERE id = ? AND empresa_id = ? AND filial_id IS ? AND usuario_id = ?",
            (int(job_id), empresa_id, filial_id, int(ator["id"])),
        ).fetchone()
    return bool(registro and registro["cancelamento_solicitado"])



def cancelar_job(job_id: int, ator: dict, mensagem: str = "Trabalho cancelado com segurança.") -> None:
    """Confirma o cancelamento de um job sem classificá-lo como falha."""
    empresa_id, filial_id = _escopo(ator)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT status FROM jobs WHERE id=? AND empresa_id=? AND filial_id IS ? AND usuario_id=?",
            (int(job_id), empresa_id, filial_id, int(ator["id"])),
        ).fetchone()
        if atual is None:
            raise ValueError("Job não encontrado.")
        if atual["status"] in STATUS_FINAIS:
            return
        conexao.execute(
            """
            UPDATE jobs
            SET status='Cancelado', cancelamento_solicitado=1,
                mensagem=?, concluido_em=CURRENT_TIMESTAMP
            WHERE id=? AND empresa_id=? AND filial_id IS ? AND usuario_id=?
            """,
            (str(mensagem)[:500], int(job_id), empresa_id, filial_id, int(ator["id"])),
        )

def listar_jobs(ator: dict, limite: int = 50) -> list[dict]:
    empresa_id, filial_id = _escopo(ator)
    administrador = str(ator.get("perfil", "")).lower() == "admin"
    filtro_usuario = "" if administrador else "AND usuario_id = ?"
    parametros = [empresa_id, filial_id]
    if not administrador:
        parametros.append(int(ator["id"]))
    parametros.append(max(1, min(int(limite), 200)))
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT * FROM jobs
            WHERE empresa_id = ? AND filial_id IS ? {filtro_usuario}
            ORDER BY id DESC LIMIT ?
            """,
            parametros,
        ).fetchall()
    return [dict(item) for item in registros]


def _atualizar_job(
    job_id,
    ator,
    *,
    status,
    progresso=None,
    mensagem=None,
    resultado=None,
    erro=None,
    iniciar=False,
    concluir=False,
):
    empresa_id, filial_id = _escopo(ator)
    progresso = None if progresso is None else max(0, min(100, int(progresso)))
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT status, cancelamento_solicitado FROM jobs WHERE id = ? AND empresa_id = ? "
            "AND filial_id IS ? AND usuario_id = ?",
            (int(job_id), empresa_id, filial_id, int(ator["id"])),
        ).fetchone()
        if atual is None:
            raise ValueError("Job não encontrado.")
        if atual["status"] in STATUS_FINAIS:
            return
        if atual["status"] == "Cancelamento solicitado" or atual["cancelamento_solicitado"]:
            conexao.execute(
                """
                UPDATE jobs
                SET status='Cancelado',
                    mensagem='Trabalho cancelado com segurança.',
                    concluido_em=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (int(job_id),),
            )
            return
        conexao.execute(
            """
            UPDATE jobs
            SET status = ?,
                progresso = COALESCE(?, progresso),
                mensagem = COALESCE(?, mensagem),
                resultado_json = COALESCE(?, resultado_json),
                erro = COALESCE(?, erro),
                iniciado_em = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE iniciado_em END,
                concluido_em = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE concluido_em END
            WHERE id = ?
            """,
            (
                status,
                progresso,
                mensagem,
                json.dumps(resultado, ensure_ascii=False, default=str)
                if resultado is not None
                else None,
                erro,
                1 if iniciar else 0,
                1 if concluir else 0,
                int(job_id),
            ),
        )

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
