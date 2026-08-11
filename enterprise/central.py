"""Cockpit, atividades, notificações, aprovações e busca transversal."""

from __future__ import annotations

from auth.banco import conectar, registrar_auditoria
from enterprise.catalogo import MODULOS
from enterprise.contexto import (
    exigir_permissao,
    listar_modulos_permitidos,
    obter_escopo_ator,
    tem_permissao,
)
from enterprise.modulos import calcular_resumo_modulo


def listar_atividades(ator: dict, limite: int = 20) -> list[dict]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    permitidos = list(listar_modulos_permitidos(ator))
    if not permitidos:
        return []
    marcadores = ",".join("?" for _ in permitidos)
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT a.*, u.nome AS usuario_nome
            FROM atividades a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.empresa_id = ?
              AND (a.filial_id = ? OR a.filial_id IS NULL)
              AND a.modulo IN ({marcadores})
            ORDER BY a.id DESC LIMIT ?
            """,
            (
                empresa_id,
                filial_id,
                *permitidos,
                max(1, min(int(limite), 200)),
            ),
        ).fetchall()
    return [dict(item) for item in registros]


def listar_notificacoes(
    ator: dict,
    limite: int = 30,
    somente_nao_lidas: bool = False,
) -> list[dict]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    permitidos = list(listar_modulos_permitidos(ator))
    if not permitidos:
        return []
    marcadores = ",".join("?" for _ in permitidos)
    filtro_lida = "AND n.lida = 0" if somente_nao_lidas else ""
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT n.* FROM notificacoes n
            WHERE n.empresa_id = ?
              AND (n.usuario_id IS NULL OR n.usuario_id = ?)
              AND (n.filial_id = ? OR n.filial_id IS NULL)
              AND n.modulo IN ({marcadores})
              {filtro_lida}
            ORDER BY n.id DESC LIMIT ?
            """,
            (
                empresa_id,
                int(ator["id"]),
                filial_id,
                *permitidos,
                max(1, min(int(limite), 200)),
            ),
        ).fetchall()
    return [dict(item) for item in registros]


def marcar_notificacao_lida(notificacao_id: int, ator: dict) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT * FROM notificacoes
            WHERE id = ? AND empresa_id = ?
              AND (filial_id = ? OR filial_id IS NULL)
              AND (usuario_id IS NULL OR usuario_id = ?)
            """,
            (int(notificacao_id), empresa_id, filial_id, int(ator["id"])),
        ).fetchone()
        if registro is None or not tem_permissao(ator, registro["modulo"], "ler"):
            raise PermissionError("Notificação não disponível para este usuário.")
        conexao.execute(
            "UPDATE notificacoes SET lida = 1 WHERE id = ?",
            (int(notificacao_id),),
        )


def listar_aprovacoes(ator: dict, limite: int = 200) -> list[dict]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    permitidos_aprovar = [
        modulo
        for modulo in listar_modulos_permitidos(ator)
        if tem_permissao(ator, modulo, "aprovar")
    ]
    condicao = "a.solicitante_id = ?"
    parametros_permissao = [int(ator["id"])]
    if permitidos_aprovar:
        marcadores = ",".join("?" for _ in permitidos_aprovar)
        condicao += f" OR a.modulo IN ({marcadores})"
        parametros_permissao.extend(permitidos_aprovar)
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT a.*, u.nome AS solicitante_nome
            FROM aprovacoes a
            LEFT JOIN usuarios u ON u.id = a.solicitante_id
            WHERE a.empresa_id = ? AND (a.filial_id = ? OR ? IS NULL)
              AND a.excluido_em IS NULL
              AND ({condicao})
            ORDER BY CASE WHEN a.status='Pendente' THEN 0 ELSE 1 END, a.id DESC
            LIMIT ?
            """,
            (
                empresa_id,
                filial_id,
                filial_id,
                *parametros_permissao,
                max(1, min(int(limite), 1000)),
            ),
        ).fetchall()
    return [dict(item) for item in registros]


def _despachar_decisao_nativa(registro: dict, decisao: str, observacao: str, ator: dict) -> bool:
    """Entrega a decisão ao módulo dono do recurso.

    A Central é uma fila/orquestrador; a regra de negócio permanece no módulo
    original para evitar estados divergentes.
    """
    recurso = registro.get("recurso_tipo")
    rid = int(registro.get("recurso_id") or 0)
    if recurso == "fin_lancamentos":
        from enterprise.financeiro import decidir_aprovacao as decidir_financeiro
        decidir_financeiro(rid, decisao, observacao, ator)
        return True
    if recurso == "cmp_solicitacoes":
        from enterprise.compras import decidir_solicitacao
        mapa = {"Aprovado": "Aprovar", "Rejeitado": "Rejeitar", "Alteração solicitada": "Solicitar alteração"}
        decidir_solicitacao(rid, mapa[decisao], observacao, ator)
        return True
    if recurso == "cmp_pedidos":
        if decisao == "Alteração solicitada":
            raise ValueError("Pedidos aceitam aprovação ou rejeição pela Central.")
        from enterprise.compras import aprovar_pedido
        aprovar_pedido(rid, decisao == "Aprovado", observacao, ator)
        return True
    if recurso == "rh_ferias_ausencias":
        if decisao == "Alteração solicitada":
            raise ValueError("Férias/ausências aceitam aprovação ou rejeição pela Central.")
        from enterprise.rh import decidir_ferias_ausencia
        decidir_ferias_ausencia(rid, decisao == "Aprovado", observacao, ator)
        return True
    if recurso == "rh_solicitacoes":
        if decisao == "Alteração solicitada":
            raise ValueError("Solicitações de RH aceitam aprovação ou rejeição pela Central.")
        from enterprise.rh import decidir_solicitacao as decidir_rh
        decidir_rh(rid, decisao == "Aprovado", observacao, ator)
        return True
    if recurso == "est_operacoes":
        if decisao == "Alteração solicitada":
            raise ValueError("Operações de Estoque aceitam aprovação ou rejeição pela Central.")
        from enterprise.estoque import aprovar_operacao
        aprovar_operacao(rid, decisao == "Aprovado", observacao, ator)
        return True
    if recurso == "est_solicitacoes":
        if decisao == "Alteração solicitada":
            raise ValueError("Solicitações de Estoque aceitam aprovação ou rejeição pela Central.")
        from enterprise.estoque import decidir_solicitacao as decidir_estoque
        decidir_estoque(rid, decisao == "Aprovado", ator)
        return True
    if recurso == "est_inventarios":
        if decisao != "Aprovado":
            raise ValueError("Inventários com divergência devem ser aprovados no módulo ou devolvidos para nova contagem.")
        from enterprise.estoque import aprovar_inventario
        aprovar_inventario(rid, ator)
        return True
    if recurso == "ti_mudancas":
        from enterprise.tecnologia import decidir_mudanca
        mapa = {"Aprovado": "Aprovar", "Rejeitado": "Rejeitar", "Alteração solicitada": "Solicitar alteração"}
        decidir_mudanca(rid, mapa[decisao], ator, observacao)
        return True
    return False


def decidir_aprovacao(
    aprovacao_id: int,
    decisao: str,
    observacao: str,
    ator: dict,
) -> None:
    if decisao not in {"Aprovado", "Rejeitado", "Alteração solicitada"}:
        raise ValueError("Decisão inválida.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT * FROM aprovacoes WHERE id=? AND empresa_id=?
               AND (filial_id=? OR ? IS NULL) AND excluido_em IS NULL""",
            (int(aprovacao_id), empresa_id, filial_id, filial_id),
        ).fetchone()
    if linha is None:
        raise ValueError("Aprovação não encontrada.")
    registro = dict(linha)
    exigir_permissao(ator, registro["modulo"], "aprovar")
    if registro["status"] != "Pendente":
        raise ValueError("Esta solicitação já foi decidida.")

    # Fluxos departamentais modernos são decididos pelo serviço nativo.
    if _despachar_decisao_nativa(registro, decisao, observacao, ator):
        return

    # Compatibilidade com recursos legados sem motor próprio.
    with conectar() as conexao:
        conexao.execute(
            """UPDATE aprovacoes SET status=?,observacao=?,responsavel_id=?,
               decidido_em=CURRENT_TIMESTAMP WHERE id=?""",
            (decisao, str(observacao).strip(), ator["id"], int(aprovacao_id)),
        )
        status_recurso = "Aprovado" if decisao == "Aprovado" else "Rejeitado"
        if decisao in {"Aprovado", "Rejeitado"} and registro["recurso_tipo"] in {"solicitacoes_compra", "solicitacoes_administrativas"}:
            conexao.execute(
                f"""UPDATE {registro['recurso_tipo']} SET status=?,atualizado_em=CURRENT_TIMESTAMP
                    WHERE id=? AND empresa_id=? AND (filial_id=? OR ? IS NULL)""",
                (status_recurso, registro["recurso_id"], empresa_id, filial_id, filial_id),
            )
        conexao.execute(
            """INSERT INTO atividades (usuario_id,empresa_id,filial_id,modulo,acao,descricao,recurso_tipo,recurso_id)
               VALUES (?,?,?,?, 'aprovacao_decidida', ?, 'aprovacoes', ?)""",
            (ator["id"], empresa_id, registro["filial_id"], registro["modulo"], f"{registro['titulo']}: {decisao}", int(aprovacao_id)),
        )
        conexao.execute(
            """INSERT INTO notificacoes (usuario_id,empresa_id,filial_id,modulo,titulo,mensagem,nivel,recurso_tipo,recurso_id)
               VALUES (?,?,?,?,?,?,?,'aprovacoes',?)""",
            (registro["solicitante_id"], empresa_id, registro["filial_id"], registro["modulo"], "Solicitação analisada", f"{registro['titulo']}: {decisao}", "sucesso" if decisao == "Aprovado" else "aviso", int(aprovacao_id)),
        )
    registrar_auditoria(
        "aprovacao_decidida", usuario_id=ator["id"], detalhes=f"aprovacao_id={aprovacao_id};decisao={decisao}",
        empresa_id=empresa_id, filial_id=registro["filial_id"], modulo=registro["modulo"], entidade="aprovacoes", entidade_id=int(aprovacao_id),
    )

def remover_aprovacao_da_fila(aprovacao_id: int, ator: dict) -> None:
    """Oculta uma aprovação preservando decisão e trilha de auditoria."""
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM aprovacoes WHERE id = ? AND empresa_id = ? "
            "AND (filial_id = ? OR ? IS NULL) AND excluido_em IS NULL",
            (int(aprovacao_id), empresa_id, filial_id, filial_id),
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
                usuario_id, empresa_id, filial_id, modulo, acao, descricao,
                recurso_tipo, recurso_id
            ) VALUES (?, ?, ?, ?, 'aprovacao_removida', ?, 'aprovacoes', ?)
            """,
            (
                ator["id"],
                empresa_id,
                filial_id,
                registro["modulo"],
                f"Removida da fila: {registro['titulo']}",
                int(aprovacao_id),
            ),
        )
    registrar_auditoria(
        "aprovacao_removida_fila",
        usuario_id=ator["id"],
        detalhes=f"aprovacao_id={aprovacao_id}",
        empresa_id=empresa_id,
        filial_id=filial_id,
        modulo=registro["modulo"],
        entidade="aprovacoes",
        entidade_id=int(aprovacao_id),
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
    empresa_id, filial_id = obter_escopo_ator(ator)
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
                WHERE empresa_id = ? AND (filial_id = ? OR ? IS NULL)
                  AND estado_registro = 'Ativo'
                  AND (LOWER({titulo}) LIKE LOWER(?) OR LOWER(COALESCE({detalhe}, '')) LIKE LOWER(?))
                ORDER BY id DESC LIMIT 10
                """,
                (empresa_id, filial_id, filial_id, f"%{termo}%", f"%{termo}%"),
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
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO atividades (
                usuario_id, empresa_id, filial_id, modulo, acao, descricao,
                recurso_tipo, recurso_id
            ) VALUES (?, ?, ?, 'analytics', 'analise_concluida', ?,
                      'historico_analises', ?)
            """,
            (
                int(ator["id"]),
                empresa_id,
                filial_id,
                f"Análise {str(categoria).replace('_', ' ').title()} concluída",
                int(historico_id),
            ),
        )

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
