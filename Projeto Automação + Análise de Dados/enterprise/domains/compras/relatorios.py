"""Exportação e relatórios de Compras. Extraído na V9.5."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import pandas as pd

from enterprise.domains.compras.base import (
    _data, _evento, _texto, conectar, exigir_acao, exigir_permissao,
    obter_escopo_ator, tem_permissao_compras,
)
from .inteligencia import listar_secao

def exportar_dataframe_compras(ator: dict) -> pd.DataFrame:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linhas = conexao.execute(
            """SELECT s.numero solicitacao,s.titulo,s.prioridade,s.status solicitacao_status,
                      s.criado_em,s.necessario_em,si.descricao item,si.quantidade,si.unidade,
                      si.valor_estimado_total_centavos,p.numero pedido,p.status pedido_status,
                      p.valor_total_centavos,p.previsao_entrega,f.razao_social fornecedor,
                      c.numero cotacao,c.saving_centavos,r.numero recebimento,r.status recebimento_status
               FROM cmp_solicitacoes s JOIN cmp_solicitacao_itens si ON si.solicitacao_id=s.id
               LEFT JOIN cmp_cotacoes c ON c.solicitacao_id=s.id
               LEFT JOIN cmp_pedidos p ON p.solicitacao_id=s.id AND p.status!='Cancelado'
               LEFT JOIN cmp_fornecedores f ON f.id=p.fornecedor_id
               LEFT JOIN cmp_recebimentos r ON r.pedido_id=p.id
               WHERE s.empresa_id=? AND s.filial_id IS ? ORDER BY s.criado_em""",
            (empresa_id, filial_id),
        ).fetchall()
    frame = pd.DataFrame([dict(x) for x in linhas])
    if frame.empty:
        return frame
    if not tem_permissao_compras(ator, "consultar_valores"):
        frame = frame.drop(columns=[x for x in frame.columns if "centavos" in x], errors="ignore")
    else:
        for coluna in [x for x in frame.columns if "centavos" in x]:
            valores = pd.to_numeric(frame[coluna], errors="coerce").fillna(0)
            frame[coluna.replace("_centavos", "")] = valores / 100
            frame = frame.drop(columns=[coluna])
    return frame


def gerar_pdf_pedido(pedido_id: int, destino: str | Path, ator: dict) -> Path:
    exigir_acao(ator, "gerar_relatorio")
    empresa_id, filial_id = obter_escopo_ator(ator)
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    with conectar() as conexao:
        pedido = conexao.execute(
            """SELECT p.*,f.razao_social,f.nome_fantasia,f.cnpj_cpf,f.endereco,
                      e.nome empresa_nome,fi.nome filial_nome,u.nome comprador_nome
               FROM cmp_pedidos p JOIN cmp_fornecedores f ON f.id=p.fornecedor_id
               JOIN empresas e ON e.id=p.empresa_id LEFT JOIN filiais fi ON fi.id=p.filial_id
               LEFT JOIN usuarios u ON u.id=p.comprador_id
               WHERE p.id=? AND p.empresa_id=? AND p.filial_id IS ?""",
            (int(pedido_id), empresa_id, filial_id),
        ).fetchone()
        if pedido is None:
            raise ValueError("Pedido não encontrado.")
        itens = conexao.execute("SELECT * FROM cmp_pedido_itens WHERE pedido_id=? ORDER BY id", (int(pedido_id),)).fetchall()
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    estilos = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(caminho), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=15*mm)
    elementos = [Paragraph(f"PEDIDO DE COMPRA Nº {pedido['numero']}", estilos["Title"]), Spacer(1, 8)]
    elementos.append(Paragraph(f"<b>Empresa:</b> {pedido['empresa_nome']} &nbsp;&nbsp; <b>Filial:</b> {pedido['filial_nome'] or '—'}", estilos["BodyText"]))
    elementos.append(Paragraph(f"<b>Fornecedor:</b> {pedido['razao_social']} &nbsp;&nbsp; <b>Documento:</b> {pedido['cnpj_cpf'] or '—'}", estilos["BodyText"]))
    elementos.append(Paragraph(f"<b>Entrega:</b> {pedido['entrega_endereco'] or '—'} &nbsp;&nbsp; <b>Previsão:</b> {pedido['previsao_entrega'] or '—'}", estilos["BodyText"]))
    elementos.append(Spacer(1, 12))
    dados = [["Descrição", "Qtd.", "Un.", "Unitário", "Total"]]
    for item in itens:
        dados.append([item["descricao"], f"{float(item['quantidade']):g}", item["unidade"], f"R$ {int(item['valor_unitario_centavos'])/100:,.2f}", f"R$ {int(item['valor_total_centavos'])/100:,.2f}"])
    tabela = Table(dados, colWidths=[75*mm, 18*mm, 15*mm, 28*mm, 30*mm], repeatRows=1)
    tabela.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#163A63")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#94A3B8")), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("FONTSIZE", (0,0), (-1,-1), 8), ("ALIGN", (1,1), (-1,-1), "RIGHT"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F1F5F9")])]))
    elementos.extend([tabela, Spacer(1, 12), Paragraph(f"<b>Valor total:</b> R$ {int(pedido['valor_total_centavos'])/100:,.2f}", estilos["Heading2"]), Paragraph(f"<b>Condição de pagamento:</b> {pedido['condicao_pagamento'] or '—'}", estilos["BodyText"]), Paragraph(f"<b>Aprovado:</b> {'Sim' if pedido['status'] not in ('Rascunho','Aguardando aprovação','Cancelado') else 'Não'}", estilos["BodyText"])])
    doc.build(elementos)
    return caminho


def gerar_relatorio_compras(tipo: str, formato: str, destino: str | Path, ator: dict) -> Path:
    exigir_acao(ator, "gerar_relatorio")
    formato = formato.upper()
    mapas = {
        "Solicitações": "solicitacoes", "Cotações": "comparativo",
        "Pedidos": "pedidos", "Fornecedores": "fornecedores",
        "Recebimentos": "recebimentos", "Divergências": "divergencias",
        "Contratos": "contratos", "Auditoria": "auditoria",
    }
    if tipo not in mapas or formato not in {"PDF", "XLSX", "CSV"}:
        raise ValueError("Relatório ou formato inválido.")
    registros = listar_secao(mapas[tipo], ator, limite=100_000)
    frame = pd.DataFrame(registros)
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if formato == "CSV":
        frame.to_csv(caminho, index=False, sep=";", encoding="utf-8-sig")
    elif formato == "XLSX":
        frame.to_excel(caminho, index=False, sheet_name="Compras")
    else:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        doc = SimpleDocTemplate(str(caminho), pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
        estilos = getSampleStyleSheet()
        elementos = [Paragraph(f"Compras e Suprimentos · {tipo}", estilos["Title"]), Spacer(1, 8)]
        if frame.empty:
            elementos.append(Paragraph("Nenhum registro no contexto selecionado.", estilos["BodyText"]))
        else:
            limite_pdf = 5000
            colunas = list(frame.columns)
            if len(frame) > limite_pdf:
                elementos.append(Paragraph(
                    f"ATENÇÃO: o PDF contém {limite_pdf:,} de {len(frame):,} registros. Use XLSX/CSV para o conjunto integral.",
                    estilos["BodyText"],
                ))
                elementos.append(Spacer(1, 6))
            dados = [colunas] + [[str(valor if valor is not None else "")[:42] for valor in linha] for linha in frame[colunas].head(limite_pdf).itertuples(index=False, name=None)]
            tabela = Table(dados, repeatRows=1)
            tabela.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#163A63")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .25, colors.HexColor("#94A3B8")), ("FONTSIZE", (0,0), (-1,-1), 6), ("VALIGN", (0,0), (-1,-1), "TOP")]))
            elementos.append(tabela)
        doc.build(elementos)
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(caminho, modulo="compras", categoria="relatorio")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar relatório de compras no servidor")
    return caminho


def agendar_relatorio(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerar_relatorio")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 150)
    if len(nome) < 2:
        raise ValueError("Informe um nome para o agendamento.")
    with conectar() as conexao:
        identificador = int(conexao.execute(
            """INSERT INTO cmp_relatorios_agendados (
                empresa_id,filial_id,nome,tipo,formato,frequencia,
                proxima_execucao,destinatarios,filtros_json,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, nome, _texto(dados.get("tipo"), 100) or "Pedidos",
             _texto(dados.get("formato"), 10).upper() or "PDF", _texto(dados.get("frequencia"), 100),
             _data(dados.get("proxima_execucao")), _texto(dados.get("destinatarios"), 1000) or None,
             json.dumps(dados.get("filtros") or {}, ensure_ascii=False), int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "relatorio_agendado", "cmp_relatorios_agendados", identificador, depois=dados)
    from enterprise.automacao_motor import registrar_agendamento
    registrar_agendamento(
        modulo="compras", referencia_tipo="cmp_relatorios_agendados", referencia_id=identificador,
        handler="relatorio.gerar",
        payload={
            "modulo": "compras", "tipo": dados.get("tipo") or "Pedidos",
            "formato": dados.get("formato") or "PDF", "filtros": dados.get("filtros") or {},
            "destinatarios": dados.get("destinatarios") or "",
        },
        frequencia=dados.get("frequencia") or "Mensal",
        proxima_execucao=dados.get("proxima_execucao"), ator=ator,
    )
    return identificador


def listar_historico(recurso_tipo: str, recurso_id: int, ator: dict) -> list[dict]:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT h.*,u.nome usuario_nome FROM cmp_historico h LEFT JOIN usuarios u ON u.id=h.usuario_id
               WHERE h.empresa_id=? AND h.filial_id IS ? AND h.recurso_tipo=? AND h.recurso_id=?
               ORDER BY h.criado_em""", (empresa_id, filial_id, recurso_tipo, int(recurso_id))
        ).fetchall()]
