"""Cockpit, atividades, notificações, aprovações e busca transversal."""

from __future__ import annotations

from auth.banco import conectar, registrar_auditoria
from enterprise.catalogo import MODULOS
from enterprise.contexto import (
    exigir_permissao,
    garantir_contexto_sessao,
    listar_modulos_permitidos,
    tem_permissao,
)
from enterprise.modulos import calcular_resumo_modulo


def listar_atividades(ator: dict, limite: int = 20) -> list[dict]:
    empresa_id, _ = garantir_contexto_sessao()
    permitidos = set(listar_modulos_permitidos(ator))
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT a.*, u.nome AS usuario_nome
            FROM atividades a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.empresa_id = ?
            ORDER BY a.id DESC LIMIT ?
            """,
            (empresa_id, max(1, min(int(limite), 200))),
        ).fetchall()
    return [dict(item) for item in registros if item["modulo"] in permitidos]


def listar_notificacoes(
    ator: dict,
    limite: int = 30,
    somente_nao_lidas: bool = False,
) -> list[dict]:
    empresa_id, _ = garantir_contexto_sessao()
    permitidos = set(listar_modulos_permitidos(ator))
    filtro_lida = "AND n.lida = 0" if somente_nao_lidas else ""
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT n.* FROM notificacoes n
            WHERE n.empresa_id = ?
              AND (n.usuario_id IS NULL OR n.usuario_id = ?)
              {filtro_lida}
            ORDER BY n.id DESC LIMIT ?
            """,
            (empresa_id, int(ator["id"]), max(1, min(int(limite), 200))),
        ).fetchall()
    return [dict(item) for item in registros if item["modulo"] in permitidos]


def marcar_notificacao_lida(notificacao_id: int, ator: dict) -> None:
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT * FROM notificacoes
            WHERE id = ? AND empresa_id = ?
              AND (usuario_id IS NULL OR usuario_id = ?)
            """,
            (int(notificacao_id), empresa_id, int(ator["id"])),
        ).fetchone()
        if registro is None or not tem_permissao(ator, registro["modulo"], "ler"):
            raise PermissionError("Notificação não disponível para este usuário.")
        conexao.execute(
            "UPDATE notificacoes SET lida = 1 WHERE id = ?",
            (int(notificacao_id),),
        )


def listar_aprovacoes(ator: dict, limite: int = 200) -> list[dict]:
    empresa_id, filial_id = garantir_contexto_sessao()
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT a.*, u.nome AS solicitante_nome
            FROM aprovacoes a
            LEFT JOIN usuarios u ON u.id = a.solicitante_id
            WHERE a.empresa_id = ? AND a.filial_id = ?
              AND a.excluido_em IS NULL
            ORDER BY CASE WHEN a.status='Pendente' THEN 0 ELSE 1 END, a.id DESC
            LIMIT ?
            """,
            (empresa_id, filial_id, max(1, min(int(limite), 1000))),
        ).fetchall()
    return [
        dict(item)
        for item in registros
        if int(item["solicitante_id"]) == int(ator["id"])
        or tem_permissao(ator, item["modulo"], "aprovar")
    ]


def decidir_aprovacao(
    aprovacao_id: int,
    decisao: str,
    observacao: str,
    ator: dict,
) -> None:
    if decisao not in {"Aprovado", "Rejeitado", "Alteração solicitada"}:
        raise ValueError("Decisão inválida.")
    empresa_id, filial_id = garantir_contexto_sessao()
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM aprovacoes WHERE id = ? AND empresa_id = ? "
            "AND filial_id = ? AND excluido_em IS NULL",
            (int(aprovacao_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None:
            raise ValueError("Aprovação não encontrada.")
        exigir_permissao(ator, registro["modulo"], "aprovar")
        if registro["status"] != "Pendente":
            raise ValueError("Esta solicitação já foi decidida.")
        conexao.execute(
            """
            UPDATE aprovacoes
            SET status = ?, observacao = ?, responsavel_id = ?,
                decidido_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (decisao, str(observacao).strip(), ator["id"], int(aprovacao_id)),
        )
        status_recurso = "Aprovado" if decisao == "Aprovado" else "Rejeitado"
        if decisao in {"Aprovado", "Rejeitado"}:
            tabelas = {
                "solicitacoes_compra",
                "solicitacoes_administrativas",
            }
            if registro["recurso_tipo"] in tabelas:
                conexao.execute(
                    f"UPDATE {registro['recurso_tipo']} SET status = ?, "
                    "atualizado_em = CURRENT_TIMESTAMP "
                    "WHERE id = ? AND empresa_id = ? AND filial_id = ?",
                    (
                        status_recurso,
                        registro["recurso_id"],
                        empresa_id,
                        filial_id,
                    ),
                )
        conexao.execute(
            """
            INSERT INTO atividades (
                usuario_id, empresa_id, modulo, acao, descricao,
                recurso_tipo, recurso_id
            ) VALUES (?, ?, ?, 'aprovacao_decidida', ?, 'aprovacoes', ?)
            """,
            (
                ator["id"],
                empresa_id,
                registro["modulo"],
                f"{registro['titulo']}: {decisao}",
                int(aprovacao_id),
            ),
        )
        conexao.execute(
            """
            INSERT INTO notificacoes (
                usuario_id, empresa_id, modulo, titulo, mensagem, nivel,
                recurso_tipo, recurso_id
            ) VALUES (?, ?, ?, ?, ?, ?, 'aprovacoes', ?)
            """,
            (
                registro["solicitante_id"],
                empresa_id,
                registro["modulo"],
                "Solicitação analisada",
                f"{registro['titulo']}: {decisao}",
                "sucesso" if decisao == "Aprovado" else "aviso",
                int(aprovacao_id),
            ),
        )
    registrar_auditoria(
        "aprovacao_decidida",
        usuario_id=ator["id"],
        detalhes=f"aprovacao_id={aprovacao_id};decisao={decisao}",
    )


def remover_aprovacao_da_fila(aprovacao_id: int, ator: dict) -> None:
    """Oculta uma aprovação preservando decisão e trilha de auditoria."""
    empresa_id, filial_id = garantir_contexto_sessao()
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM aprovacoes WHERE id = ? AND empresa_id = ? "
            "AND filial_id = ? AND excluido_em IS NULL",
            (int(aprovacao_id), empresa_id, filial_id),
        ).fetchone()
        if registro is None:
            raise ValueError("Aprovação não encontrada.")

        administrador = str(ator.get("perfil", "")).lower() == "admin"
        solicitante = int(registro["solicitante_id"]) == int(ator["id"])
        aprovador = tem_permissao(ator, registro["modulo"], "aprovar")
        if registro["status"] != "Pendente" and not administrador:
            raise PermissionError(
                "Somente administradores podem remover decisões concluídas da fila."
            )
        if not (administrador or solicitante or aprovador):
            raise PermissionError("Você não possui permissão para remover esta solicitação.")

        conexao.execute(
            "UPDATE aprovacoes SET excluido_em = CURRENT_TIMESTAMP, excluido_por = ? "
            "WHERE id = ?",
            (int(ator["id"]), int(aprovacao_id)),
        )
        conexao.execute(
            """
            INSERT INTO atividades (
                usuario_id, empresa_id, modulo, acao, descricao,
                recurso_tipo, recurso_id
            ) VALUES (?, ?, ?, 'aprovacao_removida', ?, 'aprovacoes', ?)
            """,
            (
                ator["id"],
                empresa_id,
                registro["modulo"],
                f"Removida da fila: {registro['titulo']}",
                int(aprovacao_id),
            ),
        )
    registrar_auditoria(
        "aprovacao_removida_fila",
        usuario_id=ator["id"],
        detalhes=f"aprovacao_id={aprovacao_id}",
    )


def resumo_cockpit(ator: dict) -> dict:
    modulos = [
        modulo
        for modulo in listar_modulos_permitidos(ator)
        if modulo != "analytics"
    ]
    resumos = {}
    for modulo in modulos:
        try:
            resumos[modulo] = calcular_resumo_modulo(modulo, ator)
        except (PermissionError, ValueError):
            continue
    notificacoes = listar_notificacoes(ator, limite=8, somente_nao_lidas=True)
    atividades = listar_atividades(ator, limite=10)
    aprovacoes = [
        item for item in listar_aprovacoes(ator, limite=100) if item["status"] == "Pendente"
    ]
    return {
        "modulos": resumos,
        "notificacoes": notificacoes,
        "atividades": atividades,
        "aprovacoes_pendentes": len(aprovacoes),
    }


def busca_universal(termo: str, ator: dict, limite: int = 50) -> list[dict]:
    termo = str(termo).strip()
    if len(termo) < 2:
        return []
    empresa_id, filial_id = garantir_contexto_sessao()
    permitidos = set(listar_modulos_permitidos(ator))
    consultas = {
        "rh": ("colaboradores", "nome", "cargo"),
        "financeiro": ("lancamentos_financeiros", "descricao", "categoria"),
        "estoque": ("itens_estoque", "descricao", "codigo"),
        "compras": ("solicitacoes_compra", "item", "fornecedor"),
        "ti": ("chamados_ti", "titulo", "categoria"),
        "marketing": ("campanhas_marketing", "nome", "canal"),
        "administrativo": ("solicitacoes_administrativas", "titulo", "categoria"),
        "juridico": ("contratos_juridicos", "titulo", "parte"),
        "comercial": ("oportunidades_comerciais", "cliente", "etapa"),
    }
    resultados = []
    with conectar() as conexao:
        for modulo, (tabela, titulo, detalhe) in consultas.items():
            if modulo not in permitidos:
                continue
            registros = conexao.execute(
                f"""
                SELECT id, {titulo} AS titulo, {detalhe} AS detalhe
                FROM {tabela}
                WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                  AND (LOWER({titulo}) LIKE LOWER(?) OR LOWER(COALESCE({detalhe}, '')) LIKE LOWER(?))
                ORDER BY id DESC LIMIT 10
                """,
                (empresa_id, filial_id, f"%{termo}%", f"%{termo}%"),
            ).fetchall()
            resultados.extend(
                {
                    "modulo": modulo,
                    "modulo_nome": MODULOS[modulo]["nome"],
                    "id": int(item["id"]),
                    "titulo": item["titulo"],
                    "detalhe": item["detalhe"] or "",
                }
                for item in registros
            )
    return resultados[: max(1, min(int(limite), 100))]


def registrar_atividade_analytics(
    historico_id: int,
    categoria: str,
    ator: dict,
) -> None:
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO atividades (
                usuario_id, empresa_id, modulo, acao, descricao,
                recurso_tipo, recurso_id
            ) VALUES (?, ?, 'analytics', 'analise_concluida', ?,
                      'historico_analises', ?)
            """,
            (
                int(ator["id"]),
                empresa_id,
                f"Análise {str(categoria).replace('_', ' ').title()} concluída",
                int(historico_id),
            ),
        )
