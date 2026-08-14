"""Exportação, auditoria e relatórios de Estoque. Extraído na V9.5."""
from __future__ import annotations

import json
import math
import logging
from pathlib import Path
import pandas as pd

from enterprise.domains.estoque.base import (
    _evento, _texto, conectar, exigir_acao, obter_escopo_ator, tem_permissao_estoque,
)
from .consultas import listar_inventarios, listar_itens, listar_movimentacoes
from .inteligencia import listar_secao

def exportar_dataframe_estoque(ator: dict) -> pd.DataFrame:
    registros = listar_itens(ator, por_pagina=200)["registros"]
    # Analytics nunca fica silenciosamente limitado à página visual.
    total = listar_itens(ator, por_pagina=1)["total"]
    todas = []
    for pagina in range(1, math.ceil(total / 200) + 1):
        todas.extend(listar_itens(ator, pagina=pagina, por_pagina=200)["registros"])
    colunas = ["codigo", "sku", "nome", "categoria_nome", "unidade", "fisico", "reservado", "bloqueado", "disponivel", "estoque_minimo", "estoque_maximo", "ponto_reposicao", "status"]
    if tem_permissao_estoque(ator, "consultar_custos"):
        colunas.extend(["custo_medio_centavos", "ultimo_custo_centavos"])
    return pd.DataFrame([{k: x.get(k) for k in colunas} for x in todas])


def _dataframe_relatorio(tipo: str, ator: dict) -> pd.DataFrame:
    normal = _texto(tipo, 80).lower()
    if normal in {"posição atual", "posicao atual", "estoque", "itens"}:
        return exportar_dataframe_estoque(ator)
    if normal in {"movimentações", "movimentacoes", "razão", "razao"}:
        return pd.DataFrame(listar_movimentacoes(ator, limite=100000))
    if normal in {"inventários", "inventarios"}:
        return pd.DataFrame(listar_inventarios(ator))
    if normal in {"lotes", "validade"}:
        return pd.DataFrame(listar_secao("lotes", ator, limite=100000))
    if normal in {"alertas", "críticos", "criticos"}:
        return pd.DataFrame(listar_secao("alertas", ator, limite=100000))
    if normal in {"rastreabilidade", "patrimônio", "patrimonio"}:
        return pd.DataFrame(listar_secao("patrimonio", ator, limite=100000))
    raise ValueError("Tipo de relatório de estoque não reconhecido.")


def gerar_relatorio_estoque(tipo: str, formato: str, destino: str | Path, ator: dict) -> str:
    exigir_acao(ator, "gerar_relatorio")
    dataframe = _dataframe_relatorio(tipo, ator)
    destino = Path(destino); destino.parent.mkdir(parents=True, exist_ok=True)
    formato = _texto(formato, 10).upper()
    if formato == "XLSX":
        dataframe.to_excel(destino, index=False)
    elif formato == "CSV":
        dataframe.to_csv(destino, index=False, encoding="utf-8-sig")
    elif formato == "PDF":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        documento = SimpleDocTemplate(str(destino), pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        estilos = getSampleStyleSheet(); elementos = [Paragraph(f"Estoque 2.0 · {tipo}", estilos["Title"]), Spacer(1, 8)]
        if dataframe.empty:
            elementos.append(Paragraph("Nenhum registro encontrado para os filtros selecionados.", estilos["BodyText"]))
        else:
            quadro = dataframe.fillna("").astype(str)
            limite_pdf = 5000
            if len(quadro) > limite_pdf:
                elementos.append(Paragraph(
                    f"ATENÇÃO: o PDF contém {limite_pdf:,} de {len(quadro):,} registros. Use XLSX/CSV para o conjunto integral.",
                    estilos["BodyText"],
                ))
                elementos.append(Spacer(1, 6))
            dados = [list(quadro.columns)] + quadro.head(limite_pdf).values.tolist()
            tabela = Table(dados, repeatRows=1, colWidths=[max(0.8*cm, 25*cm/max(1,len(dados[0])))]*len(dados[0]))
            tabela.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#142B48")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#94A3B8")), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 6), ("VALIGN", (0,0), (-1,-1), "TOP")]))
            elementos.append(tabela)
        documento.build(elementos)
    else:
        raise ValueError("Formato suportado: PDF, XLSX ou CSV.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        _evento(conexao, ator, "relatorio_gerado", "est_relatorios_agendados", 0, depois={"tipo": tipo, "formato": formato, "destino": str(destino)})
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="estoque", categoria="relatorio")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar relatório de estoque no servidor")
    return str(destino)


def agendar_relatorio(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerar_relatorio")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        identificador = int(conexao.execute(
            """INSERT INTO est_relatorios_agendados (
                empresa_id, filial_id, tipo, formato, filtros_json, frequencia,
                horario, destinatarios, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, _texto(dados.get("tipo"), 80) or "Posição atual",
             _texto(dados.get("formato"), 10).upper() or "PDF",
             json.dumps(dados.get("filtros") or {}, ensure_ascii=False),
             _texto(dados.get("frequencia"), 40) or "Mensal",
             _texto(dados.get("horario"), 10) or "08:00",
             _texto(dados.get("destinatarios"), 1000), int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "relatorio_agendado", "est_relatorios_agendados", identificador, depois=dados)
    from enterprise.automacao_motor import registrar_agendamento
    registrar_agendamento(
        modulo="estoque", referencia_tipo="est_relatorios_agendados", referencia_id=identificador,
        handler="relatorio.gerar",
        payload={
            "modulo": "estoque", "tipo": dados.get("tipo") or "Posição atual",
            "formato": dados.get("formato") or "PDF", "filtros": dados.get("filtros") or {},
            "destinatarios": dados.get("destinatarios") or "",
        },
        frequencia=dados.get("frequencia") or "Mensal",
        proxima_execucao=dados.get("proxima_execucao"), ator=ator,
    )
    return identificador


def listar_auditoria_estoque(ator: dict, *, limite=500) -> list[dict]:
    exigir_acao(ator, "consultar_auditoria")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT h.*, u.nome usuario_nome FROM historico_alteracoes h
               LEFT JOIN usuarios u ON u.id=h.usuario_id
               WHERE h.empresa_id=? AND h.filial_id IS ? AND h.modulo='estoque'
               ORDER BY h.id DESC LIMIT ?""", (empresa_id, filial_id, int(limite))).fetchall()]


def obter_primeiro_item_operacao(operacao_id: int, ator: dict) -> int:
    """Retorna a primeira linha da operação respeitando empresa/filial.

    Existe para impedir que a interface faça SQL direto no banco-cache quando
    estiver conectada ao Servidor Corporativo.
    """
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT oi.id FROM est_operacao_itens oi
               JOIN est_operacoes o ON o.id=oi.operacao_id
               WHERE oi.operacao_id=? AND o.empresa_id=? AND o.filial_id IS ?
               ORDER BY oi.id LIMIT 1""",
            (int(operacao_id), empresa_id, filial_id),
        ).fetchone()
    if linha is None:
        raise ValueError("Operação sem itens.")
    return int(linha["id"])
