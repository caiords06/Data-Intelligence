"""Reposição, alertas e inteligência de Estoque. Extraído na V9.5."""
from __future__ import annotations

from datetime import date, timedelta

from enterprise.domains.estoque.base import (
    _criar_tarefa, _evento, conectar, exigir_acao, exigir_permissao,
    obter_escopo_ator, tem_permissao_estoque,
)
from .catalogos import garantir_catalogos

def listar_secao(secao: str, ator: dict, *, limite=500) -> list[dict]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    consultas = {
        "depositos": ("SELECT d.*, u.nome responsavel_nome FROM est_depositos d LEFT JOIN usuarios u ON u.id=d.responsavel_id WHERE d.empresa_id=? AND d.filial_id IS ? ORDER BY d.nome", (empresa_id, filial_id)),
        "localizacoes": ("SELECT l.*, d.nome deposito_nome FROM est_localizacoes l JOIN est_depositos d ON d.id=l.deposito_id WHERE d.empresa_id=? AND d.filial_id IS ? ORDER BY d.nome,l.codigo", (empresa_id, filial_id)),
        "lotes": ("SELECT l.*, i.codigo, i.nome item_nome, COALESCE(SUM(s.quantidade_fisica),0) quantidade_restante FROM est_lotes l JOIN est_itens i ON i.id=l.item_id LEFT JOIN est_saldos s ON s.lote_id=l.id WHERE l.empresa_id=? GROUP BY l.id, i.codigo, i.nome ORDER BY l.validade,l.id DESC", (empresa_id,)),
        "patrimonio": ("SELECT s.*, i.codigo, i.nome item_nome, d.nome deposito_nome, c.nome_completo colaborador_nome FROM est_seriais s JOIN est_itens i ON i.id=s.item_id LEFT JOIN est_depositos d ON d.id=s.deposito_id LEFT JOIN rh_colaboradores c ON c.id=s.colaborador_id WHERE s.empresa_id=? ORDER BY s.id DESC", (empresa_id,)),
        "avarias": ("SELECT o.*, i.nome item_nome, d.nome deposito_nome FROM est_ocorrencias o JOIN est_itens i ON i.id=o.item_id JOIN est_depositos d ON d.id=o.deposito_id WHERE o.empresa_id=? AND o.filial_id IS ? ORDER BY o.criado_em DESC", (empresa_id, filial_id)),
        "alertas": ("SELECT a.*, i.nome item_nome, d.nome deposito_nome FROM est_alertas a LEFT JOIN est_itens i ON i.id=a.item_id LEFT JOIN est_depositos d ON d.id=a.deposito_id WHERE a.empresa_id=? AND a.filial_id IS ? ORDER BY CASE a.severidade WHEN 'Crítico' THEN 0 ELSE 1 END,a.criado_em DESC", (empresa_id, filial_id)),
        "reposicao": ("SELECT r.*, i.codigo, i.nome item_nome, d.nome deposito_nome FROM est_reposicoes r JOIN est_itens i ON i.id=r.item_id JOIN est_depositos d ON d.id=r.deposito_id WHERE r.empresa_id=? AND r.filial_id IS ? ORDER BY r.criado_em DESC", (empresa_id, filial_id)),
        "solicitacoes": ("SELECT s.*, i.codigo, i.nome item_nome, u.nome solicitante_nome FROM est_solicitacoes s JOIN est_itens i ON i.id=s.item_id LEFT JOIN usuarios u ON u.id=s.solicitante_id WHERE s.empresa_id=? AND s.filial_id IS ? ORDER BY s.criado_em DESC", (empresa_id, filial_id)),
    }
    if secao not in consultas: return []
    sql, params = consultas[secao]
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(f"{sql} LIMIT ?", (*params, int(limite))).fetchall()]


def calcular_reposicao(ator: dict, *, criar_sugestoes=True) -> list[dict]:
    exigir_acao(ator, "gerar_reposicao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registros = conexao.execute(
            """SELECT i.id item_id, i.codigo, i.nome, i.estoque_minimo, i.estoque_maximo,
                i.ponto_reposicao, i.estoque_seguranca, i.consumo_medio_dia, i.lead_time_dias,
                d.id deposito_id, d.nome deposito_nome,
                COALESCE(SUM(s.quantidade_fisica-s.quantidade_reservada-s.quantidade_bloqueada),0) disponivel
                FROM est_itens i CROSS JOIN est_depositos d
                LEFT JOIN est_saldos s ON s.item_id=i.id AND s.deposito_id=d.id
                WHERE i.empresa_id=? AND i.status='Ativo' AND d.empresa_id=? AND d.filial_id IS ? AND d.ativo=1
                GROUP BY i.id,d.id""", (empresa_id, empresa_id, filial_id)).fetchall()
        sugestoes = []
        for linha in registros:
            disponivel = float(linha["disponivel"] or 0)
            consumo = float(linha["consumo_medio_dia"] or 0)
            ponto = max(float(linha["ponto_reposicao"] or 0), consumo * int(linha["lead_time_dias"] or 0) + float(linha["estoque_seguranca"] or 0), float(linha["estoque_minimo"] or 0))
            if disponivel > ponto:
                continue
            alvo = float(linha["estoque_maximo"] or 0) or max(ponto * 2, float(linha["estoque_minimo"] or 0))
            quantidade = max(0, alvo - disponivel)
            if quantidade <= 0: continue
            cobertura = disponivel / consumo if consumo > 0 else None
            item = {**dict(linha), "quantidade_sugerida": quantidade, "cobertura_dias": cobertura, "ponto_calculado": ponto}
            sugestoes.append(item)
            if criar_sugestoes:
                existente = conexao.execute("SELECT id FROM est_reposicoes WHERE item_id=? AND deposito_id=? AND status IN ('Sugerida','Encaminhada') ORDER BY id DESC LIMIT 1", (linha["item_id"], linha["deposito_id"])).fetchone()
                if existente is None:
                    conexao.execute(
                        """INSERT INTO est_reposicoes (
                            empresa_id, filial_id, item_id, deposito_id, saldo_disponivel,
                            consumo_medio_dia, cobertura_dias, quantidade_sugerida, justificativa
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (empresa_id, filial_id, linha["item_id"], linha["deposito_id"], disponivel,
                         consumo, cobertura, quantidade, f"Saldo {disponivel:g} abaixo do ponto de reposição {ponto:g}."),
                    )
        return sugestoes


def encaminhar_reposicao_compras(reposicao_id: int, ator: dict) -> int:
    exigir_acao(ator, "gerar_reposicao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        reposicao = conexao.execute("SELECT r.*, i.nome item_nome FROM est_reposicoes r JOIN est_itens i ON i.id=r.item_id WHERE r.id=? AND r.empresa_id=? AND r.filial_id IS ?", (int(reposicao_id), empresa_id, filial_id)).fetchone()
        if reposicao is None or reposicao["status"] != "Sugerida":
            raise ValueError("Sugestão de reposição indisponível.")
        compra_id = int(conexao.execute(
            """INSERT INTO solicitacoes_compra (
                empresa_id, filial_id, item, quantidade, fornecedor, valor_estimado,
                status, criado_por
            ) VALUES (?, ?, ?, ?, '', 0, 'Pendente', ?)""",
            (empresa_id, filial_id, reposicao["item_nome"], reposicao["quantidade_sugerida"], int(ator["id"])),
        ).lastrowid)
        tarefa_id = _criar_tarefa(conexao, ator, "compras", f"Cotizar reposição de {reposicao['item_nome']}", reposicao["justificativa"], "est_reposicoes", reposicao_id, "Alta")
        conexao.execute("UPDATE est_reposicoes SET status='Encaminhada', solicitacao_compra_id=?, tarefa_id=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (compra_id, tarefa_id, int(reposicao_id)))
        _evento(conexao, ator, "reposicao_encaminhada", "est_reposicoes", reposicao_id, depois={"solicitacao_compra_id": compra_id})
    return compra_id


def gerar_alertas_estoque(ator: dict) -> list[str]:
    exigir_permissao(ator, "estoque", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    mensagens = []
    with conectar() as conexao:
        # Alertas recalculáveis são resolvidos e reabertos somente quando a condição persiste.
        conexao.execute("UPDATE est_alertas SET status='Resolvido', resolvido_em=CURRENT_TIMESTAMP WHERE empresa_id=? AND filial_id IS ? AND status='Aberto' AND tipo IN ('Crítico','Zerado','Acima do máximo','Validade','Vencido','Sem localização')", (empresa_id, filial_id))
        itens = conexao.execute(
            """SELECT i.*, d.id deposito_id, d.nome deposito_nome,
                COALESCE(SUM(s.quantidade_fisica-s.quantidade_reservada-s.quantidade_bloqueada),0) disponivel,
                MAX(s.localizacao_id) localizacao_id
                FROM est_itens i CROSS JOIN est_depositos d
                LEFT JOIN est_saldos s ON s.item_id=i.id AND s.deposito_id=d.id
                WHERE i.empresa_id=? AND i.status='Ativo' AND d.empresa_id=? AND d.filial_id IS ? AND d.ativo=1
                GROUP BY i.id,d.id""", (empresa_id, empresa_id, filial_id)).fetchall()
        for item in itens:
            disponivel = float(item["disponivel"] or 0)
            alertas = []
            if disponivel <= 0:
                alertas.append(("Zerado", "Crítico", f"{item['nome']} está sem saldo disponível."))
            elif disponivel < float(item["estoque_minimo"] or 0):
                alertas.append(("Crítico", "Crítico", f"{item['nome']}: {disponivel:g} disponível; mínimo {float(item['estoque_minimo'] or 0):g}."))
            if float(item["estoque_maximo"] or 0) > 0 and disponivel > float(item["estoque_maximo"]):
                alertas.append(("Acima do máximo", "Aviso", f"{item['nome']} está acima do estoque máximo."))
            if item["localizacao_id"] is None and disponivel > 0:
                alertas.append(("Sem localização", "Aviso", f"{item['nome']} possui saldo sem endereçamento definido."))
            for tipo, severidade, mensagem in alertas:
                mensagens.append(mensagem)
                existente = conexao.execute(
                    """SELECT id FROM est_alertas WHERE empresa_id=? AND tipo=?
                       AND item_id IS ? AND deposito_id IS ? AND lote_id IS NULL""",
                    (empresa_id, tipo, item["id"], item["deposito_id"]),
                ).fetchone()
                if existente:
                    conexao.execute(
                        """UPDATE est_alertas SET filial_id=?, severidade=?, titulo=?,
                           mensagem=?, status='Aberto', resolvido_por=NULL, resolvido_em=NULL
                           WHERE id=?""",
                        (filial_id, severidade, tipo, mensagem, existente["id"]),
                    )
                else:
                    conexao.execute(
                        """INSERT INTO est_alertas (
                            empresa_id, filial_id, tipo, severidade, titulo, mensagem,
                            item_id, deposito_id, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Aberto')""",
                        (empresa_id, filial_id, tipo, severidade, tipo, mensagem, item["id"], item["deposito_id"]),
                    )
        lotes = conexao.execute(
            """SELECT l.*, i.nome item_nome, s.deposito_id, SUM(s.quantidade_fisica) quantidade
               FROM est_lotes l JOIN est_itens i ON i.id=l.item_id JOIN est_saldos s ON s.lote_id=l.id
               WHERE l.empresa_id=? AND s.filial_id IS ? AND s.quantidade_fisica>0 AND l.validade IS NOT NULL
               GROUP BY l.id, i.nome, s.deposito_id""", (empresa_id, filial_id)).fetchall()
        limite = (date.today() + timedelta(days=30)).isoformat()
        for lote in lotes:
            if lote["validade"] < date.today().isoformat():
                tipo, severidade, mensagem = "Vencido", "Crítico", f"Lote {lote['numero']} de {lote['item_nome']} está vencido."
                conexao.execute("UPDATE est_lotes SET status='Vencido' WHERE id=?", (lote["id"],))
            elif lote["validade"] <= limite:
                tipo, severidade, mensagem = "Validade", "Aviso", f"Lote {lote['numero']} de {lote['item_nome']} vence em {lote['validade']}."
            else:
                continue
            mensagens.append(mensagem)
            existente = conexao.execute(
                """SELECT id FROM est_alertas WHERE empresa_id=? AND tipo=?
                   AND item_id IS ? AND deposito_id IS ? AND lote_id IS ?""",
                (empresa_id, tipo, lote["item_id"], lote["deposito_id"], lote["id"]),
            ).fetchone()
            if existente:
                conexao.execute(
                    """UPDATE est_alertas SET filial_id=?, severidade=?, titulo=?, mensagem=?,
                       status='Aberto', resolvido_por=NULL, resolvido_em=NULL WHERE id=?""",
                    (filial_id, severidade, tipo, mensagem, existente["id"]),
                )
            else:
                conexao.execute(
                    """INSERT INTO est_alertas (
                        empresa_id, filial_id, tipo, severidade, titulo, mensagem,
                        item_id, deposito_id, lote_id, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Aberto')""",
                    (empresa_id, filial_id, tipo, severidade, tipo, mensagem, lote["item_id"], lote["deposito_id"], lote["id"]),
                )
    return mensagens


def resolver_alerta(alerta_id: int, ator: dict) -> None:
    exigir_acao(ator, "confirmar_operacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute("UPDATE est_alertas SET status='Resolvido', resolvido_por=?, resolvido_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(ator["id"]), int(alerta_id), empresa_id, filial_id))
        if cursor.rowcount == 0: raise ValueError("Alerta não encontrado.")
        _evento(conexao, ator, "alerta_resolvido", "est_alertas", alerta_id)


def resumo_estoque(ator: dict) -> dict:
    exigir_permissao(ator, "estoque", "ler")
    garantir_catalogos(ator)
    gerar_alertas_estoque(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        itens = conexao.execute(
            """SELECT i.id, i.estoque_minimo, i.estoque_maximo, i.custo_medio_centavos,
                COALESCE(SUM(s.quantidade_fisica),0) fisico,
                COALESCE(SUM(s.quantidade_reservada),0) reservado,
                COALESCE(SUM(s.quantidade_bloqueada),0) bloqueado
                FROM est_itens i LEFT JOIN est_saldos s ON s.item_id=i.id AND s.filial_id IS ?
                WHERE i.empresa_id=? AND i.status='Ativo' GROUP BY i.id""", (filial_id, empresa_id)).fetchall()
        disponiveis = [float(x["fisico"])-float(x["reservado"])-float(x["bloqueado"]) for x in itens]
        valor = sum(round(float(x["fisico"]) * int(x["custo_medio_centavos"] or 0)) for x in itens)
        hoje = date.today().isoformat()
        primeiro_mes = date.today().replace(day=1).isoformat()
        tipos = conexao.execute("SELECT tipo, COUNT(*) n FROM est_movimentacoes WHERE empresa_id=? AND filial_id IS ? AND criado_em>=? GROUP BY tipo", (empresa_id, filial_id, primeiro_mes)).fetchall()
        contagens = {x["tipo"]: int(x["n"]) for x in tipos}
        return {
            "itens": len(itens), "unidades": sum(float(x["fisico"]) for x in itens),
            "disponiveis": sum(disponiveis), "reservadas": sum(float(x["reservado"]) for x in itens),
            "valor_centavos": valor if tem_permissao_estoque(ator, "consultar_custos") else None,
            "criticos": sum(1 for x, d in zip(itens, disponiveis) if d > 0 and d < float(x["estoque_minimo"] or 0)),
            "zerados": sum(1 for d in disponiveis if d <= 0),
            "excedentes": sum(1 for x, d in zip(itens, disponiveis) if float(x["estoque_maximo"] or 0)>0 and d>float(x["estoque_maximo"])),
            "alertas": int(conexao.execute("SELECT COUNT(*) n FROM est_alertas WHERE empresa_id=? AND filial_id IS ? AND status='Aberto'", (empresa_id, filial_id)).fetchone()["n"]),
            "vencendo": int(conexao.execute("SELECT COUNT(*) n FROM est_lotes l JOIN est_saldos s ON s.lote_id=l.id WHERE l.empresa_id=? AND s.filial_id IS ? AND s.quantidade_fisica>0 AND l.validade BETWEEN ? AND date(?, '+30 day')", (empresa_id, filial_id, hoje, hoje)).fetchone()["n"]),
            "inventarios": int(conexao.execute("SELECT COUNT(*) n FROM est_inventarios WHERE empresa_id=? AND filial_id IS ? AND status!='Finalizado'", (empresa_id, filial_id)).fetchone()["n"]),
            "transferencias": int(conexao.execute("SELECT COUNT(*) n FROM est_operacoes WHERE empresa_id=? AND filial_id IS ? AND tipo='Transferência' AND status NOT IN ('Concluída','Cancelada','Rejeitada')", (empresa_id, filial_id)).fetchone()["n"]),
            "recebimentos": int(conexao.execute("SELECT COUNT(*) n FROM est_operacoes WHERE empresa_id=? AND filial_id IS ? AND tipo IN ('Entrada','Recebimento de compra') AND status NOT IN ('Concluída','Cancelada')", (empresa_id, filial_id)).fetchone()["n"]),
            "entradas_mes": sum(v for k,v in contagens.items() if "Entrada" in k or "Recebimento" in k),
            "saidas_mes": sum(v for k,v in contagens.items() if "Saída" in k or k in {"Consumo interno","Perda","Avaria","Vencimento"}),
        }


def analisar_estoque(ator: dict) -> dict:
    resumo = resumo_estoque(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        parados = [dict(x) for x in conexao.execute(
            """SELECT i.codigo, i.nome, COALESCE(MAX(m.criado_em), i.criado_em) ultima_movimentacao,
                COALESCE(SUM(s.quantidade_fisica),0) saldo, i.custo_medio_centavos
                FROM est_itens i LEFT JOIN est_movimentacoes m ON m.item_id=i.id
                LEFT JOIN est_saldos s ON s.item_id=i.id AND s.filial_id IS ?
                WHERE i.empresa_id=? GROUP BY i.id
                HAVING COALESCE(SUM(s.quantidade_fisica),0)>0 AND SUBSTR(COALESCE(MAX(m.criado_em), i.criado_em),1,10)<date('now','-90 day')
                ORDER BY saldo*i.custo_medio_centavos DESC LIMIT 10""", (filial_id, empresa_id)).fetchall()]
        perdas = conexao.execute("SELECT COALESCE(SUM(ABS(quantidade)*custo_unitario_centavos),0) valor FROM est_movimentacoes WHERE empresa_id=? AND filial_id IS ? AND tipo IN ('Perda','Avaria','Vencimento') AND criado_em>=date('now','start of month')", (empresa_id, filial_id)).fetchone()["valor"]
        top = [dict(x) for x in conexao.execute(
            """SELECT i.codigo, i.nome, SUM(ABS(m.quantidade)) movimentado
               FROM est_movimentacoes m JOIN est_itens i ON i.id=m.item_id
               WHERE m.empresa_id=? AND m.filial_id IS ? AND m.criado_em>=date('now','-90 day')
               GROUP BY i.id ORDER BY movimentado DESC LIMIT 10""", (empresa_id, filial_id)).fetchall()]
    pontos = []
    if resumo["zerados"]: pontos.append(f"{resumo['zerados']} item(ns) estão sem estoque disponível.")
    if resumo["criticos"]: pontos.append(f"{resumo['criticos']} item(ns) estão abaixo do estoque mínimo.")
    if resumo["vencendo"]: pontos.append(f"{resumo['vencendo']} lote(s) vencem nos próximos 30 dias.")
    if parados: pontos.append(f"{len(parados)} item(ns) com saldo não se movimentam há pelo menos 90 dias.")
    if perdas: pontos.append(f"Perdas do mês representam R$ {int(perdas)/100:,.2f}.")
    return {"resumo": resumo, "pontos_atencao": pontos or ["Nenhuma anomalia relevante foi detectada."], "itens_parados": parados, "mais_movimentados": top, "perdas_centavos": int(perdas or 0)}
