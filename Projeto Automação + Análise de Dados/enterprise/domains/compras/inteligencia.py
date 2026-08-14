"""Consultas, alertas e inteligência de Compras. Extraído na V9.5."""
from __future__ import annotations

from datetime import date, timedelta

from enterprise.domains.compras.base import (
    _evento, _texto, conectar, exigir_permissao, obter_escopo_ator, tem_permissao_compras,
)

def gerar_alertas_compras(ator: dict) -> list[str]:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    hoje = date.today().isoformat()
    limite_contrato = (date.today() + timedelta(days=30)).isoformat()
    mensagens = []
    candidatos = []
    with conectar() as conexao:
        pedidos = conexao.execute(
            """SELECT id,numero,previsao_entrega FROM cmp_pedidos
               WHERE empresa_id=? AND filial_id IS ? AND previsao_entrega<?
                 AND status NOT IN ('Recebido','Encerrado','Cancelado')""",
            (empresa_id, filial_id, hoje),
        ).fetchall()
        for pedido in pedidos:
            candidatos.append(("Entrega atrasada", "Crítico", f"Pedido {pedido['numero']} atrasado", f"Previsão de entrega: {pedido['previsao_entrega']}.", "cmp_pedidos", int(pedido["id"])))
        contratos = conexao.execute(
            """SELECT id,numero,termino FROM cmp_contratos WHERE empresa_id=? AND filial_id IS ?
               AND status='Ativo' AND termino BETWEEN ? AND ?""",
            (empresa_id, filial_id, hoje, limite_contrato),
        ).fetchall()
        for contrato in contratos:
            candidatos.append(("Contrato vencendo", "Aviso", f"Contrato {contrato['numero']} vencendo", f"Término: {contrato['termino']}.", "cmp_contratos", int(contrato["id"])))
        documentos = conexao.execute(
            """SELECT d.id,d.tipo,d.validade,f.razao_social FROM cmp_fornecedor_documentos d
               JOIN cmp_fornecedores f ON f.id=d.fornecedor_id WHERE f.empresa_id=?
               AND d.validade BETWEEN ? AND ? AND d.status!='Vencido'""",
            (empresa_id, hoje, limite_contrato),
        ).fetchall()
        for documento in documentos:
            candidatos.append(("Documento vencendo", "Aviso", f"Documento de {documento['razao_social']} vencendo", f"{documento['tipo']} vence em {documento['validade']}.", "cmp_fornecedor_documentos", int(documento["id"])))
        divergencias = conexao.execute("SELECT id,tipo,descricao FROM cmp_divergencias WHERE empresa_id=? AND filial_id IS ? AND status='Aberta'", (empresa_id, filial_id)).fetchall()
        for divergencia in divergencias:
            candidatos.append(("Divergência", "Crítico", divergencia["tipo"], divergencia["descricao"], "cmp_divergencias", int(divergencia["id"])))
        chaves_ativas = {(x[0], x[4], x[5]) for x in candidatos}
        abertos = conexao.execute("SELECT id,tipo,recurso_tipo,recurso_id FROM cmp_alertas WHERE empresa_id=? AND filial_id IS ? AND status='Aberto'", (empresa_id, filial_id)).fetchall()
        for alerta in abertos:
            if (alerta["tipo"], alerta["recurso_tipo"], alerta["recurso_id"]) not in chaves_ativas:
                conexao.execute("UPDATE cmp_alertas SET status='Resolvido',resolvido_em=CURRENT_TIMESTAMP WHERE id=?", (int(alerta["id"]),))
        for tipo, severidade, titulo, mensagem, recurso_tipo, recurso_id in candidatos:
            existente = conexao.execute("""SELECT id FROM cmp_alertas WHERE empresa_id=? AND filial_id IS ? AND tipo=? AND recurso_tipo=? AND recurso_id=?""", (empresa_id, filial_id, tipo, recurso_tipo, recurso_id)).fetchone()
            if existente:
                conexao.execute("UPDATE cmp_alertas SET severidade=?,titulo=?,mensagem=?,status='Aberto',resolvido_em=NULL WHERE id=?", (severidade, titulo, mensagem, int(existente["id"])))
            else:
                conexao.execute("""INSERT INTO cmp_alertas (empresa_id,filial_id,tipo,severidade,titulo,mensagem,recurso_tipo,recurso_id) VALUES (?,?,?,?,?,?,?,?)""", (empresa_id, filial_id, tipo, severidade, titulo, mensagem, recurso_tipo, recurso_id))
            mensagens.append(titulo)
    return mensagens


def resolver_alerta(alerta_id: int, ator: dict) -> None:
    exigir_permissao(ator, "compras", "escrever")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        alerta = conexao.execute("SELECT * FROM cmp_alertas WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(alerta_id), empresa_id, filial_id)).fetchone()
        if alerta is None:
            raise ValueError("Alerta não encontrado.")
        conexao.execute("UPDATE cmp_alertas SET status='Resolvido',resolvido_em=CURRENT_TIMESTAMP WHERE id=?", (int(alerta_id),))
        _evento(conexao, ator, "alerta_resolvido", "cmp_alertas", alerta_id, antes={"status": alerta["status"]}, depois={"status": "Resolvido"})


def resumo_compras(ator: dict) -> dict:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    valores = tem_permissao_compras(ator, "consultar_valores")
    with conectar() as conexao:
        q = lambda sql, params=(): conexao.execute(sql, params).fetchone()[0]
        parametros = (empresa_id, filial_id)
        resumo = {
            "solicitacoes_abertas": int(q("SELECT COUNT(*) FROM cmp_solicitacoes WHERE empresa_id=? AND filial_id IS ? AND status NOT IN ('Recebida','Encerrada','Rejeitada','Cancelada')", parametros)),
            "urgentes": int(q("SELECT COUNT(*) FROM cmp_solicitacoes WHERE empresa_id=? AND filial_id IS ? AND prioridade IN ('Urgente','Crítica') AND status NOT IN ('Recebida','Encerrada','Rejeitada','Cancelada')", parametros)),
            "aguardando_aprovacao": int(q("SELECT COUNT(*) FROM cmp_solicitacoes WHERE empresa_id=? AND filial_id IS ? AND status='Aguardando aprovação'", parametros)),
            "cotacoes_abertas": int(q("SELECT COUNT(*) FROM cmp_cotacoes WHERE empresa_id=? AND filial_id IS ? AND status='Em andamento'", parametros)),
            "pedidos_abertos": int(q("SELECT COUNT(*) FROM cmp_pedidos WHERE empresa_id=? AND filial_id IS ? AND status NOT IN ('Recebido','Encerrado','Cancelado')", parametros)),
            "entregas_atrasadas": int(q("SELECT COUNT(*) FROM cmp_pedidos WHERE empresa_id=? AND filial_id IS ? AND previsao_entrega<date('now') AND status NOT IN ('Recebido','Encerrado','Cancelado')", parametros)),
            "divergencias": int(q("SELECT COUNT(*) FROM cmp_divergencias WHERE empresa_id=? AND filial_id IS ? AND status='Aberta'", parametros)),
            "contratos_vencendo": int(q("SELECT COUNT(*) FROM cmp_contratos WHERE empresa_id=? AND filial_id IS ? AND status='Ativo' AND termino BETWEEN date('now') AND date('now','+30 day')", parametros)),
            "fornecedores": int(q("SELECT COUNT(*) FROM cmp_fornecedores WHERE empresa_id=? AND ativo=1", (empresa_id,))),
            "alertas": int(q("SELECT COUNT(*) FROM cmp_alertas WHERE empresa_id=? AND filial_id IS ? AND status='Aberto'", parametros)),
        }
        resumo["valor_aberto_centavos"] = int(q("SELECT COALESCE(SUM(valor_estimado_centavos),0) FROM cmp_solicitacoes WHERE empresa_id=? AND filial_id IS ? AND status NOT IN ('Recebida','Encerrada','Rejeitada','Cancelada')", parametros)) if valores else None
        resumo["valor_pedidos_centavos"] = int(q("SELECT COALESCE(SUM(valor_total_centavos),0) FROM cmp_pedidos WHERE empresa_id=? AND filial_id IS ? AND status NOT IN ('Cancelado')", parametros)) if valores else None
        resumo["saving_centavos"] = int(q("SELECT COALESCE(SUM(saving_centavos),0) FROM cmp_cotacoes WHERE empresa_id=? AND filial_id IS ? AND status='Encerrada'", parametros)) if valores else None
        resumo["valor_contratos_centavos"] = int(q("SELECT COALESCE(SUM(valor_centavos),0) FROM cmp_contratos WHERE empresa_id=? AND filial_id IS ? AND status='Ativo'", parametros)) if valores else None
        return resumo


def listar_secao(secao: str, ator: dict, *, pesquisa="", limite=500) -> list[dict]:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    termo = f"%{_texto(pesquisa, 100)}%"
    consultas = {
        "solicitacoes": ("""SELECT s.*,u.nome solicitante_nome,d.nome departamento_nome,cc.nome centro_custo_nome FROM cmp_solicitacoes s LEFT JOIN usuarios u ON u.id=s.solicitante_id LEFT JOIN departamentos d ON d.id=s.departamento_id LEFT JOIN centros_custo cc ON cc.id=s.centro_custo_id WHERE s.empresa_id=? AND s.filial_id IS ? AND (s.numero LIKE ? OR s.titulo LIKE ? OR s.status LIKE ?) ORDER BY s.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "minhas_solicitacoes": ("""SELECT s.*,u.nome solicitante_nome FROM cmp_solicitacoes s LEFT JOIN usuarios u ON u.id=s.solicitante_id WHERE s.empresa_id=? AND s.filial_id IS ? AND s.solicitante_id=? AND (s.numero LIKE ? OR s.titulo LIKE ?) ORDER BY s.criado_em DESC""", (empresa_id, filial_id, int(ator["id"]), termo, termo)),
        "aprovacoes": ("""SELECT s.*,u.nome solicitante_nome FROM cmp_solicitacoes s LEFT JOIN usuarios u ON u.id=s.solicitante_id WHERE s.empresa_id=? AND s.filial_id IS ? AND s.status='Aguardando aprovação' AND (s.numero LIKE ? OR s.titulo LIKE ?) ORDER BY s.criado_em""", (empresa_id, filial_id, termo, termo)),
        "cotacoes": ("""SELECT c.*,s.titulo solicitacao_titulo,f.razao_social fornecedor_selecionado FROM cmp_cotacoes c JOIN cmp_solicitacoes s ON s.id=c.solicitacao_id LEFT JOIN cmp_fornecedores f ON f.id=c.fornecedor_selecionado_id WHERE c.empresa_id=? AND c.filial_id IS ? AND (c.numero LIKE ? OR s.titulo LIKE ?) ORDER BY c.criado_em DESC""", (empresa_id, filial_id, termo, termo)),
        "comparativo": ("""SELECT cf.*,c.numero cotacao_numero,f.razao_social,f.status_homologacao,f.score fornecedor_score FROM cmp_cotacao_fornecedores cf JOIN cmp_cotacoes c ON c.id=cf.cotacao_id JOIN cmp_fornecedores f ON f.id=cf.fornecedor_id WHERE c.empresa_id=? AND c.filial_id IS ? AND (c.numero LIKE ? OR f.razao_social LIKE ?) ORDER BY c.id DESC,cf.score_total DESC""", (empresa_id, filial_id, termo, termo)),
        "negociacoes": ("""SELECT n.*,c.numero cotacao_numero,f.razao_social,u.nome responsavel_nome FROM cmp_negociacoes n JOIN cmp_cotacao_fornecedores cf ON cf.id=n.cotacao_fornecedor_id JOIN cmp_cotacoes c ON c.id=cf.cotacao_id JOIN cmp_fornecedores f ON f.id=cf.fornecedor_id LEFT JOIN usuarios u ON u.id=n.responsavel_id WHERE c.empresa_id=? AND c.filial_id IS ? AND (c.numero LIKE ? OR f.razao_social LIKE ?) ORDER BY n.criado_em DESC""", (empresa_id, filial_id, termo, termo)),
        "pedidos": ("""SELECT p.*,f.razao_social fornecedor_nome,u.nome comprador_nome FROM cmp_pedidos p JOIN cmp_fornecedores f ON f.id=p.fornecedor_id LEFT JOIN usuarios u ON u.id=p.comprador_id WHERE p.empresa_id=? AND p.filial_id IS ? AND (p.numero LIKE ? OR f.razao_social LIKE ? OR p.status LIKE ?) ORDER BY p.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "fornecedores": ("""SELECT * FROM cmp_fornecedores WHERE empresa_id=? AND ativo=1 AND (codigo LIKE ? OR razao_social LIKE ? OR cnpj_cpf LIKE ?) ORDER BY razao_social""", (empresa_id, termo, termo, termo)),
        "homologacao": ("""SELECT * FROM cmp_fornecedores WHERE empresa_id=? AND ativo=1 AND (codigo LIKE ? OR razao_social LIKE ? OR status_homologacao LIKE ?) ORDER BY CASE status_homologacao WHEN 'Em análise' THEN 0 ELSE 1 END,razao_social""", (empresa_id, termo, termo, termo)),
        "avaliacoes": ("""SELECT a.*,f.razao_social,u.nome avaliador_nome FROM cmp_fornecedor_avaliacoes a JOIN cmp_fornecedores f ON f.id=a.fornecedor_id LEFT JOIN usuarios u ON u.id=a.avaliado_por WHERE a.empresa_id=? AND a.filial_id IS ? AND f.razao_social LIKE ? ORDER BY a.criado_em DESC""", (empresa_id, filial_id, termo)),
        "documentos": ("""SELECT fd.*,f.razao_social,d.titulo,d.classificacao,d.hash_sha256,
                            d.caminho_relativo,d.criado_em documento_criado_em
                     FROM cmp_fornecedor_documentos fd
                     JOIN cmp_fornecedores f ON f.id=fd.fornecedor_id
                     JOIN documentos d ON d.id=fd.documento_id
                     WHERE f.empresa_id=? AND COALESCE(d.estado_registro,'Ativo')='Ativo'
                       AND (f.razao_social LIKE ? OR fd.tipo LIKE ? OR d.titulo LIKE ?)
                     ORDER BY COALESCE(fd.validade,'9999-12-31'),fd.id DESC""",
                    (empresa_id, termo, termo, termo)),
        "recebimentos": ("""SELECT r.*,p.numero pedido_numero,f.razao_social fornecedor_nome FROM cmp_recebimentos r JOIN cmp_pedidos p ON p.id=r.pedido_id JOIN cmp_fornecedores f ON f.id=r.fornecedor_id WHERE r.empresa_id=? AND r.filial_id IS ? AND (r.numero LIKE ? OR p.numero LIKE ? OR f.razao_social LIKE ? OR r.nota_fiscal LIKE ?) ORDER BY r.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo, termo)),
        "divergencias": ("""SELECT d.*,r.numero recebimento_numero,p.numero pedido_numero FROM cmp_divergencias d JOIN cmp_recebimentos r ON r.id=d.recebimento_id JOIN cmp_pedidos p ON p.id=r.pedido_id WHERE d.empresa_id=? AND d.filial_id IS ? AND (d.tipo LIKE ? OR d.descricao LIKE ? OR p.numero LIKE ?) ORDER BY CASE d.status WHEN 'Aberta' THEN 0 ELSE 1 END,d.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "contratos": ("""SELECT c.*,f.razao_social fornecedor_nome,u.nome responsavel_nome FROM cmp_contratos c JOIN cmp_fornecedores f ON f.id=c.fornecedor_id LEFT JOIN usuarios u ON u.id=c.responsavel_id WHERE c.empresa_id=? AND c.filial_id IS ? AND (c.numero LIKE ? OR c.objeto LIKE ? OR f.razao_social LIKE ?) ORDER BY c.termino""", (empresa_id, filial_id, termo, termo, termo)),
        "aditivos": ("""SELECT a.*,c.numero contrato_numero,f.razao_social fornecedor_nome FROM cmp_contrato_aditivos a JOIN cmp_contratos c ON c.id=a.contrato_id JOIN cmp_fornecedores f ON f.id=c.fornecedor_id WHERE c.empresa_id=? AND c.filial_id IS ? AND (a.numero LIKE ? OR c.numero LIKE ? OR f.razao_social LIKE ?) ORDER BY a.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "catalogo": ("""SELECT c.*,f.razao_social fornecedor_nome,ca.nome categoria_nome,i.codigo estoque_codigo FROM cmp_catalogo c JOIN cmp_fornecedores f ON f.id=c.fornecedor_id LEFT JOIN cmp_categorias ca ON ca.id=c.categoria_id LEFT JOIN est_itens i ON i.id=c.estoque_item_id WHERE c.empresa_id=? AND c.ativo=1 AND (c.codigo LIKE ? OR c.descricao LIKE ? OR f.razao_social LIKE ?) ORDER BY c.descricao""", (empresa_id, termo, termo, termo)),
        "alertas": ("""SELECT * FROM cmp_alertas WHERE empresa_id=? AND filial_id IS ? AND (titulo LIKE ? OR mensagem LIKE ? OR tipo LIKE ?) ORDER BY CASE severidade WHEN 'Crítico' THEN 0 ELSE 1 END,criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "auditoria": ("""SELECT h.*,u.nome usuario_nome FROM cmp_historico h LEFT JOIN usuarios u ON u.id=h.usuario_id WHERE h.empresa_id=? AND h.filial_id IS ? AND (h.acao LIKE ? OR h.recurso_tipo LIKE ? OR u.nome LIKE ?) ORDER BY h.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "regras": ("""SELECT * FROM cmp_regras_aprovacao WHERE empresa_id=? AND ativo=1 AND nome LIKE ? ORDER BY nivel""", (empresa_id, termo)),
        "relatorios_agendados": ("""SELECT * FROM cmp_relatorios_agendados WHERE empresa_id=? AND filial_id IS ? AND nome LIKE ? ORDER BY criado_em DESC""", (empresa_id, filial_id, termo)),
    }
    if secao not in consultas:
        return []
    sql, parametros = consultas[secao]
    with conectar() as conexao:
        registros = [dict(x) for x in conexao.execute(f"{sql} LIMIT ?", (*parametros, int(limite))).fetchall()]
    if not tem_permissao_compras(ator, "consultar_valores"):
        for registro in registros:
            for chave in list(registro):
                if "centavos" in chave or chave in {"valor", "saving"}:
                    registro[chave] = None
    return registros


def obter_itens_solicitacao(solicitacao_id: int, ator: dict) -> list[dict]:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        existe = conexao.execute("SELECT id FROM cmp_solicitacoes WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(solicitacao_id), empresa_id, filial_id)).fetchone()
        if existe is None:
            raise ValueError("Solicitação não encontrada.")
        return [dict(x) for x in conexao.execute("SELECT * FROM cmp_solicitacao_itens WHERE solicitacao_id=? ORDER BY id", (int(solicitacao_id),)).fetchall()]


def obter_itens_pedido(pedido_id: int, ator: dict) -> list[dict]:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        existe = conexao.execute("SELECT id FROM cmp_pedidos WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(pedido_id), empresa_id, filial_id)).fetchone()
        if existe is None:
            raise ValueError("Pedido não encontrado.")
        return [dict(x) for x in conexao.execute("SELECT * FROM cmp_pedido_itens WHERE pedido_id=? ORDER BY id", (int(pedido_id),)).fetchall()]


def obter_fornecedores_cotacao(cotacao_id: int, ator: dict) -> list[dict]:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT cf.*,f.razao_social,f.status_homologacao,f.score fornecedor_score
               FROM cmp_cotacao_fornecedores cf JOIN cmp_fornecedores f ON f.id=cf.fornecedor_id
               JOIN cmp_cotacoes c ON c.id=cf.cotacao_id WHERE c.id=? AND c.empresa_id=?
               AND c.filial_id IS ? ORDER BY cf.score_total DESC""", (int(cotacao_id), empresa_id, filial_id)
        ).fetchall()]


def analisar_compras(ator: dict) -> dict:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    resumo = resumo_compras(ator)
    with conectar() as conexao:
        concentracao = [dict(x) for x in conexao.execute(
            """SELECT f.razao_social,COUNT(*) pedidos,SUM(p.valor_total_centavos) valor_centavos
               FROM cmp_pedidos p JOIN cmp_fornecedores f ON f.id=p.fornecedor_id
               WHERE p.empresa_id=? AND p.filial_id IS ? AND p.status!='Cancelado'
               GROUP BY f.id ORDER BY valor_centavos DESC LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
        atrasos = [dict(x) for x in conexao.execute(
            """SELECT f.razao_social,COUNT(*) pedidos_atrasados FROM cmp_pedidos p
               JOIN cmp_fornecedores f ON f.id=p.fornecedor_id
               WHERE p.empresa_id=? AND p.filial_id IS ? AND p.previsao_entrega<date('now')
                 AND p.status NOT IN ('Recebido','Encerrado','Cancelado')
               GROUP BY f.id ORDER BY pedidos_atrasados DESC LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
        baixa_concorrencia = int(conexao.execute(
            """SELECT COUNT(*) n FROM cmp_cotacoes c WHERE c.empresa_id=? AND c.filial_id IS ?
               AND (SELECT COUNT(*) FROM cmp_cotacao_fornecedores cf WHERE cf.cotacao_id=c.id)<3""", (empresa_id, filial_id)
        ).fetchone()["n"])
        recorrentes = [dict(x) for x in conexao.execute(
            """SELECT MIN(si.descricao) descricao,COUNT(DISTINCT s.id) ocorrencias,SUM(si.quantidade) quantidade
               FROM cmp_solicitacao_itens si JOIN cmp_solicitacoes s ON s.id=si.solicitacao_id
               WHERE s.empresa_id=? AND s.filial_id IS ? AND s.criado_em>=datetime('now','-90 day')
               GROUP BY lower(si.descricao) HAVING COUNT(DISTINCT s.id)>=3 ORDER BY ocorrencias DESC LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
        fracionamentos = [dict(x) for x in conexao.execute(
            """SELECT lower(si.descricao) item,COUNT(*) quantidade_solicitacoes,
                      SUM(si.valor_estimado_total_centavos) valor_centavos
               FROM cmp_solicitacao_itens si JOIN cmp_solicitacoes s ON s.id=si.solicitacao_id
               WHERE s.empresa_id=? AND s.filial_id IS ? AND s.criado_em>=datetime('now','-30 day')
               GROUP BY lower(si.descricao) HAVING COUNT(*)>=3 ORDER BY valor_centavos DESC LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
    total_fornecedores = sum(int(x["valor_centavos"] or 0) for x in concentracao)
    pontos = []
    if concentracao and total_fornecedores:
        percentual = int(concentracao[0]["valor_centavos"] or 0) / total_fornecedores * 100
        if percentual >= 50:
            pontos.append(f"{percentual:.1f}% do valor comprado está concentrado em {concentracao[0]['razao_social']}.")
    if baixa_concorrencia:
        pontos.append(f"{baixa_concorrencia} cotação(ões) tiveram menos de três fornecedores convidados.")
    if atrasos:
        pontos.append(f"{atrasos[0]['razao_social']} concentra {atrasos[0]['pedidos_atrasados']} pedido(s) atrasado(s).")
    if recorrentes:
        pontos.append(f"{recorrentes[0]['descricao']} aparece repetidamente; avalie catálogo ou contrato recorrente.")
    if fracionamentos:
        pontos.append(f"Foram detectadas solicitações semelhantes em curto intervalo para {fracionamentos[0]['item']}.")
    if not pontos:
        pontos.append("Nenhum risco relevante foi detectado no universo atual de Compras.")
    return {"resumo": resumo, "pontos_atencao": pontos, "concentracao": concentracao,
            "atrasos": atrasos, "baixa_concorrencia": baixa_concorrencia,
            "recorrentes": recorrentes, "fracionamentos": fracionamentos}
