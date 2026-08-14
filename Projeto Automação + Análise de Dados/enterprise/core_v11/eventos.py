"""Outbox corporativo para integrações, webhooks e automações transversais."""
from __future__ import annotations

from auth.banco import conectar
from enterprise.core_v11.common import load


def listar_eventos(ator: dict, *, modulo: str | None = None, limite: int = 200) -> list[dict]:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("A consulta do barramento exige administrador.")
    empresa_id = int(ator.get("_empresa_id") or 0)
    filtros = ["empresa_id=?"]; parametros: list = [empresa_id]
    if modulo:
        filtros.append("modulo=?"); parametros.append(str(modulo))
    parametros.append(max(1, min(int(limite), 2000)))
    with conectar() as con:
        rows = con.execute(
            f"SELECT * FROM core_eventos_corporativos WHERE {' AND '.join(filtros)} ORDER BY id DESC LIMIT ?",
            tuple(parametros),
        ).fetchall()
    return [{**dict(x), "payload": load(x["payload_json"], {})} for x in rows]


def publicar_eventos_pendentes(*, limite: int = 100) -> dict:
    with conectar() as con:
        rows = con.execute(
            """SELECT e.*,u.nome,u.usuario,u.perfil,u.perfil_acesso,u.email_corporativo,u.ativo,u.sessao_epoch
               FROM core_eventos_corporativos e LEFT JOIN usuarios u ON u.id=e.criado_por
               WHERE e.publicado_em IS NULL ORDER BY e.id LIMIT ?""",
            (max(1, min(int(limite), 500)),),
        ).fetchall()
    publicados = 0; falhas: list[dict] = []
    for row in rows:
        item = dict(row)
        ator = {
            "id": int(item["criado_por"] or 0), "nome": item.get("nome") or "Sistema V11",
            "usuario": item.get("usuario") or "sistema", "perfil": item.get("perfil") or "admin",
            "perfil_acesso": item.get("perfil_acesso") or "analista", "ativo": bool(item.get("ativo", 1)),
            "sessao_epoch": int(item.get("sessao_epoch") or 0), "_empresa_id": int(item["empresa_id"]),
            "_filial_id": int(item["filial_id"]) if item["filial_id"] is not None else None,
        }
        try:
            from enterprise.webhooks import publicar_evento
            publicar_evento(
                f"{item['modulo']}.{item['tipo']}", load(item["payload_json"], {}), ator,
                evento_id=str(item["evento_uuid"]),
            )
            with conectar() as con:
                con.execute(
                    "UPDATE core_eventos_corporativos SET publicado_em=CURRENT_TIMESTAMP WHERE id=? AND publicado_em IS NULL",
                    (int(item["id"]),),
                )
            publicados += 1
        except Exception as exc:
            falhas.append({"id": int(item["id"]), "erro": str(exc)[:500]})
    return {"encontrados": len(rows), "publicados": publicados, "falhas": falhas}


__all__ = ("listar_eventos", "publicar_eventos_pendentes")
