"""Indicadores, projeções e relatórios do Financeiro. V9.5."""
from __future__ import annotations

import html
import json
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import pandas as pd

from auth import banco as banco_auth
from enterprise.domains.financeiro.base import (
    GRUPOS_DRE, _data_iso, _moeda, _normalizar_texto, _notificar, _registrar_evento,
    _sincronizar_legado, conectar, exigir_acao, obter_escopo_ator,
)
from .catalogos import listar_catalogos
from .conciliacao import saldo_conta

def listar_contas_com_saldo(ator: dict) -> list[dict]:
    catalogos = listar_catalogos(ator)
    resultado = []
    for conta in catalogos["contas"]:
        item = dict(conta)
        item["saldo_centavos"] = saldo_conta(item["id"], ator)
        resultado.append(item)
    return resultado


def projetar_fluxo_caixa(ator: dict, *, dias=30, cenario="Realista") -> list[dict]:
    exigir_acao(ator, "visualizar")
    dias = max(1, min(int(dias), 730))
    if cenario not in {"Realista", "Otimista", "Pessimista"}:
        raise ValueError("Cenário inválido.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    contas = listar_contas_com_saldo(ator)
    saldo = sum(int(conta["saldo_centavos"]) for conta in contas)
    hoje = date.today()
    fim = hoje + timedelta(days=dias)
    with conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT COALESCE(vencimento,competencia) data,natureza,
                   SUM(valor_original_centavos-valor_liquidado_centavos) valor
            FROM fin_lancamentos
            WHERE empresa_id=? AND filial_id=? AND status IN (
                'Previsto','Faturado','Enviado','Aprovado','Agendado','A vencer','Vencido','Parcial'
            ) AND COALESCE(vencimento,competencia) BETWEEN ? AND ?
            GROUP BY COALESCE(vencimento,competencia),natureza
            """,
            (empresa_id, filial_id, hoje.isoformat(), fim.isoformat()),
        ).fetchall()
    por_data: dict[str, dict[str, int]] = {}
    fator_receita = {"Otimista": Decimal("1"), "Realista": Decimal("0.90"), "Pessimista": Decimal("0.75")}[cenario]
    fator_despesa = {"Otimista": Decimal("0.95"), "Realista": Decimal("1"), "Pessimista": Decimal("1.10")}[cenario]
    for linha in linhas:
        grupo = por_data.setdefault(linha["data"], {"entradas_centavos": 0, "saidas_centavos": 0})
        valor = int(linha["valor"] or 0)
        if linha["natureza"] in {"Receita", "Conta a receber"}:
            grupo["entradas_centavos"] += int(Decimal(valor) * fator_receita)
        elif linha["natureza"] in {"Despesa", "Conta a pagar", "Reembolso"}:
            grupo["saidas_centavos"] += int(Decimal(valor) * fator_despesa)
    resultado = []
    for indice in range(dias + 1):
        data_atual = (hoje + timedelta(days=indice)).isoformat()
        movimento = por_data.get(data_atual, {"entradas_centavos": 0, "saidas_centavos": 0})
        saldo += movimento["entradas_centavos"] - movimento["saidas_centavos"]
        resultado.append({"data": data_atual, **movimento, "saldo_projetado_centavos": saldo, "cenario": cenario})
    return resultado


def calcular_dre(ator: dict, inicio=None, fim=None) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    hoje = date.today()
    inicio = _data_iso(inicio) or hoje.replace(day=1).isoformat()
    fim = _data_iso(fim) or hoje.isoformat()
    with conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT COALESCE(pc.grupo_dre,'Não classificado') grupo,
                   l.natureza,SUM(CASE WHEN l.valor_liquidado_centavos>0
                       THEN l.valor_liquidado_centavos ELSE l.valor_original_centavos END) valor
            FROM fin_lancamentos l
            LEFT JOIN fin_plano_contas pc ON pc.id=l.plano_conta_id
            WHERE l.empresa_id=? AND l.filial_id=? AND l.competencia BETWEEN ? AND ?
              AND l.natureza!='Transferência' AND l.status NOT IN ('Rascunho','Cancelado','Estornado')
              AND l.contabilizado=1
            GROUP BY COALESCE(pc.grupo_dre,'Não classificado'),l.natureza
            """,
            (empresa_id, filial_id, inicio, fim),
        ).fetchall()
    totais = {grupo: 0 for grupo in GRUPOS_DRE}
    totais["Não classificado"] = 0
    for linha in linhas:
        sinal = 1 if linha["natureza"] in {"Receita", "Conta a receber"} else -1
        totais.setdefault(linha["grupo"], 0)
        totais[linha["grupo"]] += sinal * int(linha["valor"] or 0)
    receita_bruta = max(0, totais["Receita bruta"])
    deducoes = abs(min(0, totais["Deduções"]))
    receita_liquida = receita_bruta - deducoes
    custos = abs(min(0, totais["Custos"]))
    lucro_bruto = receita_liquida - custos
    despesas = abs(min(0, totais["Despesas operacionais"]))
    ebitda = lucro_bruto - despesas
    financeiro = totais["Resultado financeiro"]
    resultado = ebitda + financeiro
    return {
        "inicio": inicio,
        "fim": fim,
        "linhas": (
            ("RECEITA BRUTA", receita_bruta),
            ("(-) DEDUÇÕES", -deducoes),
            ("RECEITA LÍQUIDA", receita_liquida),
            ("(-) CUSTOS", -custos),
            ("LUCRO BRUTO", lucro_bruto),
            ("(-) DESPESAS OPERACIONAIS", -despesas),
            ("EBITDA", ebitda),
            ("RESULTADO FINANCEIRO", financeiro),
            ("RESULTADO", resultado),
        ),
        "nao_classificado_centavos": totais.get("Não classificado", 0),
    }


def resumo_financeiro(ator: dict, *, inicio=None, fim=None) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    hoje = date.today()
    inicio = _data_iso(inicio) or hoje.replace(day=1).isoformat()
    fim = _data_iso(fim) or hoje.isoformat()
    limite = (hoje + timedelta(days=7)).isoformat()
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        linha = conexao.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN natureza IN ('Receita','Conta a receber')
                AND status NOT IN ('Cancelado','Estornado') THEN valor_liquidado_centavos ELSE 0 END),0) receitas,
              COALESCE(SUM(CASE WHEN natureza IN ('Despesa','Conta a pagar','Reembolso')
                AND status NOT IN ('Cancelado','Estornado') THEN valor_liquidado_centavos ELSE 0 END),0) despesas,
              COALESCE(SUM(CASE WHEN status IN ('Rascunho','Previsto','Faturado','Enviado','Aguardando aprovação','Aprovado','Agendado','A vencer','Vencido','Parcial')
                THEN valor_original_centavos-valor_liquidado_centavos ELSE 0 END),0) pendente_valor,
              SUM(CASE WHEN status IN ('Rascunho','Previsto','Faturado','Enviado','Aguardando aprovação','Aprovado','Agendado','A vencer','Vencido','Parcial') THEN 1 ELSE 0 END) pendentes,
              SUM(CASE WHEN vencimento<? AND status IN ('Previsto','Faturado','Enviado','Aprovado','Agendado','A vencer','Vencido','Parcial') THEN 1 ELSE 0 END) vencidas,
              SUM(CASE WHEN vencimento BETWEEN ? AND ? AND status NOT IN ('Pago','Recebido','Liquidado','Conciliado','Cancelado','Estornado') THEN 1 ELSE 0 END) proximos_sete
            FROM fin_lancamentos
            WHERE empresa_id=? AND filial_id=? AND competencia BETWEEN ? AND ?
            """,
            (hoje.isoformat(), hoje.isoformat(), limite, empresa_id, filial_id, inicio, fim),
        ).fetchone()
        contas = conexao.execute(
            "SELECT id FROM fin_contas WHERE empresa_id=? AND filial_id=? AND status='Ativa'",
            (empresa_id, filial_id),
        ).fetchall()
    saldo = sum(saldo_conta(int(conta["id"]), ator) for conta in contas)
    projecao = projetar_fluxo_caixa(ator, dias=30, cenario="Realista")
    minimo = min((item["saldo_projetado_centavos"] for item in projecao), default=saldo)
    data_minimo = next((item["data"] for item in projecao if item["saldo_projetado_centavos"] == minimo), hoje.isoformat())
    orcamentos = listar_orcamentos(ator, ano=hoje.year, mes=hoje.month)
    alertas_orcamento = [item for item in orcamentos if item["utilizado_percentual"] >= item["limite_alerta_percentual"]]
    return {
        "inicio": inicio,
        "fim": fim,
        "receitas_centavos": int(linha["receitas"] or 0),
        "despesas_centavos": int(linha["despesas"] or 0),
        "resultado_centavos": int(linha["receitas"] or 0) - int(linha["despesas"] or 0),
        "saldo_centavos": saldo,
        "pendentes": int(linha["pendentes"] or 0),
        "pendente_valor_centavos": int(linha["pendente_valor"] or 0),
        "vencidas": int(linha["vencidas"] or 0),
        "proximos_sete": int(linha["proximos_sete"] or 0),
        "saldo_minimo_projetado_centavos": minimo,
        "data_saldo_minimo": data_minimo,
        "risco_caixa": minimo < 0,
        "alertas_orcamento": alertas_orcamento,
    }


def analisar_financeiro(ator: dict) -> dict:
    resumo = resumo_financeiro(ator)
    dre = calcular_dre(ator, resumo["inicio"], resumo["fim"])
    alertas = []
    if resumo["vencidas"]:
        alertas.append(f"Existem {resumo['vencidas']} obrigação(ões) vencida(s).")
    if resumo["proximos_sete"]:
        alertas.append(f"{resumo['proximos_sete']} conta(s) vencem nos próximos sete dias.")
    if resumo["risco_caixa"]:
        alertas.append(
            f"O saldo projetado fica negativo em {resumo['data_saldo_minimo']}, "
            f"atingindo {_moeda(resumo['saldo_minimo_projetado_centavos'])}."
        )
    for item in resumo["alertas_orcamento"]:
        nome = item.get("centro_custo_nome") or item.get("categoria_nome") or "Orçamento"
        alertas.append(f"{nome} consumiu {item['utilizado_percentual']:.1f}% do orçamento.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        duplicidades = conexao.execute(
            """
            SELECT COUNT(*) total FROM (
                SELECT COALESCE(parte_id,0),valor_original_centavos,competencia,COUNT(*) quantidade
                FROM fin_lancamentos
                WHERE empresa_id=? AND filial_id=?
                  AND natureza IN ('Despesa','Conta a pagar','Reembolso')
                  AND status NOT IN ('Cancelado','Estornado')
                GROUP BY COALESCE(parte_id,0),valor_original_centavos,competencia
                HAVING COUNT(*)>1
            )
            """,
            (empresa_id, filial_id),
        ).fetchone()["total"]
    if duplicidades:
        alertas.append(
            f"Foram encontrados {int(duplicidades)} grupo(s) de pagamentos semelhantes que merecem conferência."
        )
    recomendacoes = []
    if resumo["despesas_centavos"] > resumo["receitas_centavos"]:
        recomendacoes.append("Revisar as maiores despesas e o calendário de recebimentos do período.")
    if dre["nao_classificado_centavos"]:
        recomendacoes.append("Classificar os lançamentos pendentes no plano de contas para completar a DRE.")
    if resumo["vencidas"]:
        recomendacoes.append("Priorizar cobranças e renegociações das contas vencidas.")
    return {
        "resumo": resumo,
        "dre": dre,
        "alertas": alertas or ["Nenhuma anomalia crítica foi encontrada no contexto atual."],
        "recomendacoes": recomendacoes or ["Manter a conciliação e a classificação atualizadas."],
        "questoes_gestao": (
            "Quais centros de custo explicam a maior variação do resultado?",
            "O calendário de recebimentos cobre as obrigações dos próximos 30 dias?",
            "Existem fornecedores, clientes ou categorias com concentração excessiva?",
        ),
    }


def _dataframe_relatorio(tipo: str, ator: dict, inicio=None, fim=None) -> pd.DataFrame:
    """Prepara o conjunto correto para cada relatório, sem exportar dados irrelevantes."""
    normalizado = tipo.casefold()
    lancamentos = exportar_dataframe_financeiro(ator, inicio=inicio, fim=fim)
    if "contas a pagar" in normalizado:
        return lancamentos[lancamentos["tipo"].isin(("Despesa", "Conta a pagar", "Reembolso"))].copy()
    if "contas a receber" in normalizado:
        return lancamentos[lancamentos["tipo"].isin(("Receita", "Conta a receber"))].copy()
    if "fluxo" in normalizado:
        dados = pd.DataFrame(projetar_fluxo_caixa(ator, dias=90, cenario="Realista"))
        return dados.rename(columns={
            "data": "Data", "entradas_centavos": "Entradas (centavos)",
            "saidas_centavos": "Saídas (centavos)",
            "saldo_projetado_centavos": "Saldo projetado (centavos)",
            "cenario": "Cenário",
        })
    if "orçamento" in normalizado or "orcamento" in normalizado:
        dados = pd.DataFrame(listar_orcamentos(ator))
        if dados.empty:
            return pd.DataFrame(columns=("Competência", "Centro de custo", "Categoria", "Planejado", "Realizado", "Disponível", "Utilizado (%)"))
        return pd.DataFrame({
            "Competência": dados.apply(lambda item: f"{int(item['mes']):02d}/{int(item['ano'])}", axis=1),
            "Centro de custo": dados["centro_custo_nome"].fillna("Consolidado"),
            "Categoria": dados["categoria_nome"].fillna("Todas"),
            "Planejado": dados["planejado_centavos"] / 100,
            "Realizado": dados["realizado_centavos"] / 100,
            "Disponível": dados["disponivel_centavos"] / 100,
            "Utilizado (%)": dados["utilizado_percentual"],
        })
    if "auditoria" in normalizado:
        dados = listar_auditoria_financeira(ator, limite=5000)
        return pd.DataFrame(dados).rename(columns={
            "criado_em": "Data / hora", "usuario_nome": "Usuário",
            "acao": "Ação", "entidade": "Entidade", "entidade_id": "Registro",
        })
    if normalizado.strip() == "dre" or "demonstração" in normalizado:
        dre = calcular_dre(ator, inicio, fim)
        return pd.DataFrame(
            ((nome, valor / 100) for nome, valor in dre["linhas"]),
            columns=("DRE", "Valor"),
        )
    return lancamentos


def exportar_dataframe_financeiro(ator: dict, *, inicio=None, fim=None) -> pd.DataFrame:
    exigir_acao(ator, "exportar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtros = ["l.empresa_id=?", "l.filial_id=?"]
    parametros: list[object] = [empresa_id, filial_id]
    if inicio:
        filtros.append("l.competencia>=?")
        parametros.append(_data_iso(inicio))
    if fim:
        filtros.append("l.competencia<=?")
        parametros.append(_data_iso(fim))
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        dataframe = pd.read_sql_query(
            f"""
            SELECT l.id,l.competencia,l.vencimento,l.liquidacao,l.natureza AS tipo,
                   l.descricao,c.nome categoria,pc.codigo conta_contabil,
                   pc.grupo_dre,cc.nome centro_custo,p.nome parte,ct.nome conta,
                   l.valor_original_centavos/100.0 valor,
                   l.valor_liquidado_centavos/100.0 valor_liquidado,
                   (l.valor_original_centavos-l.valor_liquidado_centavos)/100.0 saldo,
                   l.status,l.contabilizado,l.conciliado
            FROM fin_lancamentos l
            LEFT JOIN fin_categorias c ON c.id=l.categoria_id
            LEFT JOIN fin_plano_contas pc ON pc.id=l.plano_conta_id
            LEFT JOIN centros_custo cc ON cc.id=l.centro_custo_id
            LEFT JOIN fin_partes p ON p.id=l.parte_id
            LEFT JOIN fin_contas ct ON ct.id=l.conta_id
            WHERE {' AND '.join(filtros)} ORDER BY l.competencia,l.id
            """,
            conexao,
            params=tuple(parametros),
        )
    return dataframe


def gerar_relatorio_financeiro(
    tipo: str,
    formato: str,
    ator: dict,
    *,
    inicio=None,
    fim=None,
) -> Path:
    exigir_acao(ator, "exportar")
    tipo = _normalizar_texto(tipo, 80) or "Lançamentos"
    formato = str(formato).strip().upper()
    if formato not in {"CSV", "XLSX", "EXCEL", "HTML", "PDF"}:
        raise ValueError("Formato de relatório inválido.")
    dataframe = _dataframe_relatorio(tipo, ator, inicio=inicio, fim=fim)
    empresa_id, filial_id = obter_escopo_ator(ator)
    pasta = banco_auth.STORAGE_DIR / "financeiro" / "relatorios" / str(empresa_id)
    pasta.mkdir(parents=True, exist_ok=True)
    base = f"{re.sub(r'[^a-z0-9]+', '_', tipo.lower())}_{datetime.now():%Y%m%d_%H%M%S}"
    if formato == "CSV":
        destino = pasta / f"{base}.csv"
        dataframe.to_csv(destino, index=False, encoding="utf-8-sig")
    elif formato in {"XLSX", "EXCEL"}:
        destino = pasta / f"{base}.xlsx"
        with pd.ExcelWriter(destino, engine="openpyxl") as writer:
            dataframe.to_excel(writer, sheet_name="Relatório", index=False)
            dre = pd.DataFrame(calcular_dre(ator, inicio, fim)["linhas"], columns=["Linha", "Valor (centavos)"])
            dre["Valor"] = dre.pop("Valor (centavos)") / 100
            dre.to_excel(writer, sheet_name="DRE", index=False)
    elif formato == "HTML":
        destino = pasta / f"{base}.html"
        destino.write_text(
            "<!doctype html><meta charset='utf-8'><title>Relatório financeiro</title>"
            "<style>body{font-family:Arial;margin:36px}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #ccc;padding:8px}</style>"
            f"<h1>{html.escape(tipo)}</h1>"
            f"<p>Período: {html.escape(str(inicio or 'início do período'))} a {html.escape(str(fim or 'data atual'))}</p>"
            f"{dataframe.to_html(index=False, escape=True)}",
            encoding="utf-8",
        )
    else:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as erro:
            raise RuntimeError("Instale reportlab para exportar relatórios em PDF.") from erro
        destino = pasta / f"{base}.pdf"
        estilos = getSampleStyleSheet()
        historia = [Paragraph(html.escape(tipo), estilos["Title"]), Spacer(1, 12)]
        limite_pdf = 5000
        colunas_pdf = list(dataframe.columns)
        dados_pdf = [[str(coluna)[:30] for coluna in colunas_pdf]]
        for _, linha in dataframe.head(limite_pdf).iterrows():
            dados_pdf.append([str(linha.get(chave, ""))[:70] for chave in colunas_pdf])
        if len(dataframe) > limite_pdf:
            historia.append(Paragraph(
                f"ATENÇÃO: o PDF contém {limite_pdf:,} de {len(dataframe):,} registros. "
                "Use XLSX ou CSV para o conjunto integral.", estilos["BodyText"]
            ))
            historia.append(Spacer(1, 8))
        if not colunas_pdf:
            dados_pdf = [["Resultado"], ["Nenhum dado encontrado para os filtros selecionados."]]
        largura_util = 740 / max(1, len(dados_pdf[0]))
        tabela = Table(dados_pdf, repeatRows=1, colWidths=[largura_util] * len(dados_pdf[0]))
        tabela.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15304D")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey), ("FONTSIZE", (0, 0), (-1, -1), 7), ("PADDING", (0, 0), (-1, -1), 4)]))
        historia.append(tabela)
        SimpleDocTemplate(str(destino), pagesize=landscape(A4), title=tipo).build(historia)
    formato_registro = "XLSX" if formato in {"XLSX", "EXCEL"} else formato
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO relatorios_corporativos (
                empresa_id,filial_id,modulo,titulo,descricao,formato,
                filtros_json,arquivo,status,criado_por
            ) VALUES (?,?,'financeiro',?,?,?,?,?,'Concluído',?)
            """,
            (
                empresa_id, filial_id, tipo, "Relatório financeiro especializado",
                formato_registro,
                json.dumps({"inicio": inicio, "fim": fim}, ensure_ascii=False),
                str(destino.relative_to(banco_auth.STORAGE_DIR)), int(ator["id"]),
            ),
        )
        _registrar_evento(conexao, ator, "relatorio_gerado", "relatorios_corporativos", int(cursor.lastrowid), depois={"tipo": tipo, "formato": formato})
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="financeiro", categoria="relatorio")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar relatório financeiro no servidor")
    return destino


def gerar_alertas_financeiros(ator: dict) -> list[str]:
    exigir_acao(ator, "visualizar")
    analise = analisar_financeiro(ator)
    with conectar() as conexao:
        for mensagem in analise["alertas"]:
            if mensagem.startswith("Nenhuma anomalia"):
                continue
            _notificar(conexao, ator, "Alerta financeiro", mensagem, "critico" if "negativo" in mensagem or "vencida" in mensagem else "aviso")
    return analise["alertas"]


def listar_auditoria_financeira(ator: dict, *, limite=300) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT h.id,h.acao,h.entidade,h.entidade_id,h.criado_em,
                   u.nome usuario_nome,h.dados_antes,h.dados_depois
            FROM historico_alteracoes h
            LEFT JOIN usuarios u ON u.id=h.usuario_id
            WHERE h.empresa_id=? AND h.filial_id=? AND h.modulo='financeiro'
            ORDER BY h.id DESC LIMIT ?
            """,
            (empresa_id, filial_id, max(1, min(int(limite), 1000))),
        ).fetchall()]


def listar_orcamentos(ator: dict, *, ano=None, mes=None) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    ano = int(ano or date.today().year)
    filtros = ["o.empresa_id=?", "o.filial_id=?", "o.ano=?"]
    parametros: list[object] = [empresa_id, filial_id, ano]
    if mes:
        filtros.append("o.mes=?")
        parametros.append(int(mes))
    with conectar() as conexao:
        linhas = conexao.execute(
            f"""
            SELECT o.*,cc.nome centro_custo_nome,c.nome categoria_nome,
                   COALESCE((
                       SELECT SUM(l.valor_liquidado_centavos)
                       FROM fin_lancamentos l
                       WHERE l.empresa_id=o.empresa_id AND l.filial_id=o.filial_id
                         AND l.natureza IN ('Despesa','Conta a pagar','Reembolso')
                         AND strftime('%Y',l.competencia)=printf('%04d',o.ano)
                         AND strftime('%m',l.competencia)=printf('%02d',o.mes)
                         AND (o.centro_custo_id IS NULL OR l.centro_custo_id=o.centro_custo_id)
                         AND (o.categoria_id IS NULL OR l.categoria_id=o.categoria_id)
                         AND l.status NOT IN ('Cancelado','Estornado')
                   ),0) realizado_centavos
            FROM fin_orcamentos o
            LEFT JOIN centros_custo cc ON cc.id=o.centro_custo_id
            LEFT JOIN fin_categorias c ON c.id=o.categoria_id
            WHERE {' AND '.join(filtros)} ORDER BY o.mes,cc.nome,c.nome
            """,
            tuple(parametros),
        ).fetchall()
    resultado = []
    for linha in linhas:
        item = dict(linha)
        planejado = int(item["planejado_centavos"])
        realizado = int(item["realizado_centavos"])
        item["disponivel_centavos"] = planejado - realizado
        item["utilizado_percentual"] = round(realizado * 100 / planejado, 1) if planejado else 0
        resultado.append(item)
    return resultado
