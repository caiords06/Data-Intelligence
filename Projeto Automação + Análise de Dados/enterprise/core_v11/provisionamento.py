"""Provisionamento idempotente do catálogo configurável por empresa."""
from __future__ import annotations

from auth.banco import conectar
from enterprise.core_v11.catalogo import FLUXOS, TIPOS_POR_MODULO, schema_padrao
from enterprise.core_v11.common import dump


def provisionar_empresa_v11(empresa_id: int, ator: dict | None = None) -> dict:
    empresa_id = int(empresa_id)
    usuario_id = int(ator["id"]) if ator and ator.get("id") is not None else None
    tipos = 0
    fluxos = 0
    with conectar() as con:
        empresa = con.execute("SELECT id FROM empresas WHERE id=? AND ativo=1", (empresa_id,)).fetchone()
        if empresa is None:
            raise ValueError("Empresa não encontrada para provisionamento V11.")
        for codigo_fluxo, definicao in FLUXOS.items():
            etapas = [
                {"codigo": codigo, "titulo": titulo, "modulo": modulo, "requer_aprovacao": bool(aprovacao), "ordem": ordem}
                for ordem, (codigo, titulo, modulo, aprovacao) in enumerate(definicao["etapas"], start=1)
            ]
            transicoes = [
                {"de": etapas[indice]["codigo"], "para": etapas[indice + 1]["codigo"]}
                for indice in range(len(etapas) - 1)
            ]
            con.execute(
                """INSERT INTO v11_fluxos_modelos
                   (empresa_id,codigo,nome,modulo,etapas_json,transicoes_json,configuracao_json,criado_por)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(empresa_id,codigo,versao) DO UPDATE SET
                   nome=excluded.nome,modulo=excluded.modulo,etapas_json=excluded.etapas_json,
                   transicoes_json=excluded.transicoes_json,atualizado_em=CURRENT_TIMESTAMP""",
                (
                    empresa_id, codigo_fluxo, definicao["nome"], definicao["modulo"],
                    dump(etapas), dump(transicoes), dump({"origem": "catalogo_v11"}), usuario_id,
                ),
            )
            fluxos += 1
        for modulo, definicoes in TIPOS_POR_MODULO.items():
            for codigo_tipo, nome, fluxo_codigo in definicoes:
                con.execute(
                    """INSERT INTO v11_tipos_registro
                       (empresa_id,modulo,codigo,nome,descricao,schema_json,configuracao_json,fluxo_codigo,criado_por)
                       VALUES (?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(empresa_id,modulo,codigo) DO UPDATE SET
                       nome=excluded.nome,descricao=excluded.descricao,
                       fluxo_codigo=COALESCE(v11_tipos_registro.fluxo_codigo,excluded.fluxo_codigo),
                       atualizado_em=CURRENT_TIMESTAMP""",
                    (
                        empresa_id, modulo, codigo_tipo, nome,
                        f"Recurso configurável de {nome}.", dump(schema_padrao(nome)),
                        dump({"auditoria": True, "comentarios": True, "anexos": True, "etiquetas": True}),
                        fluxo_codigo, usuario_id,
                    ),
                )
                con.execute(
                    """INSERT INTO v11_configuracoes_modulos
                       (empresa_id,modulo,recurso,configuracao_json,atualizado_por)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(empresa_id,modulo,recurso) DO NOTHING""",
                    (
                        empresa_id, modulo, codigo_tipo,
                        dump({"habilitado": True, "tela": "lista_formulario", "multi_filial": True}), usuario_id,
                    ),
                )
                tipos += 1
    return {"empresa_id": empresa_id, "tipos": tipos, "fluxos": fluxos}


def provisionar_empresas_existentes() -> int:
    with conectar() as con:
        empresas = [int(item["id"]) for item in con.execute("SELECT id FROM empresas WHERE ativo=1").fetchall()]
    for empresa_id in empresas:
        provisionar_empresa_v11(empresa_id)
    return len(empresas)


__all__ = ("provisionar_empresa_v11", "provisionar_empresas_existentes")
