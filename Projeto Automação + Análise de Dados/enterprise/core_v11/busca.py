"""Busca universal escopada por empresa, módulo e classificação."""
from __future__ import annotations

from auth.banco import conectar
from enterprise.contexto import listar_modulos_permitidos
from enterprise.core_v11.common import escopo


def busca_universal(
    termo: str,
    ator: dict,
    *,
    modulo: str | None = None,
    pagina: int = 1,
    tamanho: int = 50,
) -> dict:
    empresa_id, _ = escopo(ator)
    termo = str(termo or "").strip()
    if len(termo) < 2:
        raise ValueError("A busca deve possuir ao menos dois caracteres.")
    pagina = max(1, int(pagina)); tamanho = max(1, min(int(tamanho), 100))
    modulos = set(listar_modulos_permitidos(ator))
    if "comercial" in modulos:
        modulos.add("crm")
    if "administrativo" in modulos:
        modulos.add("documentos")
    if "analytics" in modulos:
        modulos.add("automacao")
    if str(ator.get("perfil", "")).lower() == "admin":
        modulos.update({"crm", "automacao", "documentos"})
    if modulo:
        if modulo not in modulos:
            raise PermissionError("Módulo não autorizado para busca.")
        modulos = {modulo}
    if not modulos:
        return {"itens": [], "total": 0, "pagina": pagina, "tamanho": tamanho}
    marcadores = ",".join("?" for _ in modulos)
    filtros = ["empresa_id=?", f"modulo IN ({marcadores})", "(titulo LIKE ? OR subtitulo LIKE ? OR termos LIKE ?)"]
    parametros: list = [empresa_id, *sorted(modulos), f"%{termo}%", f"%{termo}%", f"%{termo}%"]
    if str(ator.get("perfil", "")).lower() != "admin":
        filtros.append("classificacao<>'Restrito'")
    where = " AND ".join(filtros)
    with conectar() as con:
        total = int(con.execute(f"SELECT COUNT(*) total FROM core_busca_indice WHERE {where}", tuple(parametros)).fetchone()["total"])
        rows = con.execute(
            f"""SELECT recurso_tipo,recurso_id,modulo,titulo,subtitulo,classificacao,atualizado_em
                FROM core_busca_indice WHERE {where}
                ORDER BY CASE WHEN titulo LIKE ? THEN 0 ELSE 1 END,atualizado_em DESC
                LIMIT ? OFFSET ?""",
            (*parametros, f"{termo}%", tamanho, (pagina - 1) * tamanho),
        ).fetchall()
    return {"itens": [dict(x) for x in rows], "total": total, "pagina": pagina, "tamanho": tamanho}


def reindexar_core(ator: dict) -> dict:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Reindexação exige administrador.")
    empresa_id, _ = escopo(ator)
    total = 0
    with conectar() as con:
        con.execute("DELETE FROM core_busca_indice WHERE empresa_id=?", (empresa_id,))
        pessoas = con.execute("SELECT id,nome,nome_social_fantasia,email_corporativo,classificacao FROM core_pessoas WHERE empresa_id=? AND ativo=1", (empresa_id,)).fetchall()
        for p in pessoas:
            con.execute(
                """INSERT INTO core_busca_indice
                   (empresa_id,recurso_tipo,recurso_id,modulo,titulo,subtitulo,termos,classificacao)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (empresa_id, "core_pessoas", int(p["id"]), "rh", p["nome"], p["nome_social_fantasia"], f"{p['nome']} {p['email_corporativo'] or ''}", p["classificacao"]),
            ); total += 1
        registros = con.execute("SELECT * FROM v11_registros_operacionais WHERE empresa_id=? AND estado_registro='Ativo'", (empresa_id,)).fetchall()
        for r in registros:
            con.execute(
                """INSERT INTO core_busca_indice
                   (empresa_id,recurso_tipo,recurso_id,modulo,titulo,subtitulo,termos,classificacao)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (empresa_id, "v11_registros_operacionais", int(r["id"]), r["modulo"], r["titulo"], r["codigo"], f"{r['titulo']} {r['descricao'] or ''} {r['codigo']}", "Interno"),
            ); total += 1
        documentos = con.execute("SELECT id,titulo,tipo_documento,recurso_tipo,classificacao FROM core_documentos_v11 WHERE empresa_id=? AND status='Ativo'", (empresa_id,)).fetchall()
        for d in documentos:
            con.execute(
                """INSERT INTO core_busca_indice
                   (empresa_id,recurso_tipo,recurso_id,modulo,titulo,subtitulo,termos,classificacao)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (empresa_id, "core_documentos_v11", int(d["id"]), "documentos", d["titulo"], d["tipo_documento"], f"{d['titulo']} {d['tipo_documento'] or ''} {d['recurso_tipo']}", d["classificacao"]),
            ); total += 1
    return {"indexados": total}


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = ("busca_universal", "reindexar_core")
