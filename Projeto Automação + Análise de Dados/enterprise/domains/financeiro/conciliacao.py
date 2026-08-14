"""Conciliação bancária do Financeiro. Extraído do monólito na V9.5."""
from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd

from enterprise.domains.financeiro.base import (
    _centavos, _normalizar_texto, _registrar_evento, _validar_referencia,
    conectar, exigir_acao, obter_escopo_ator,
)

def _parse_ofx(caminho: Path) -> list[dict]:
    texto = caminho.read_text(encoding="utf-8", errors="ignore")
    blocos = re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|<STMTTRN>|</BANKTRANLIST>)", texto, flags=re.I | re.S)
    itens = []
    for bloco in blocos:
        def tag(nome):
            encontrado = re.search(rf"<{nome}>([^<\r\n]+)", bloco, flags=re.I)
            return encontrado.group(1).strip() if encontrado else ""
        data_raw = tag("DTPOSTED")[:8]
        if len(data_raw) != 8:
            continue
        itens.append({
            "data": f"{data_raw[:4]}-{data_raw[4:6]}-{data_raw[6:8]}",
            "descricao": tag("MEMO") or tag("NAME") or "Movimentação bancária",
            "documento": tag("CHECKNUM"),
            "valor": tag("TRNAMT"),
            "identificador": tag("FITID") or hashlib.sha256(bloco.encode()).hexdigest(),
        })
    return itens


def _ler_extrato(caminho: Path) -> list[dict]:
    extensao = caminho.suffix.lower()
    if extensao == ".ofx":
        return _parse_ofx(caminho)
    if extensao == ".csv":
        dataframe = pd.read_csv(caminho, sep=None, engine="python")
    elif extensao in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(caminho)
    else:
        raise ValueError("Formato não suportado. Utilize OFX, CSV ou XLSX.")
    normalizadas = {str(coluna).strip().lower(): coluna for coluna in dataframe.columns}
    def achar(*nomes):
        for nome in nomes:
            for normalizada, original in normalizadas.items():
                if nome in normalizada:
                    return original
        return None
    col_data = achar("data", "date")
    col_desc = achar("descri", "histor", "memo", "name")
    col_valor = achar("valor", "amount", "trnamt")
    col_doc = achar("document", "id", "fitid")
    if col_data is None or col_desc is None or col_valor is None:
        raise ValueError("O extrato precisa conter colunas de data, descrição e valor.")
    itens = []
    for indice, linha in dataframe.iterrows():
        data_item = pd.to_datetime(linha[col_data], errors="coerce", dayfirst=True)
        if pd.isna(data_item):
            continue
        itens.append({
            "data": data_item.date().isoformat(),
            "descricao": str(linha[col_desc]),
            "documento": str(linha[col_doc]) if col_doc is not None and pd.notna(linha[col_doc]) else "",
            "valor": linha[col_valor],
            "identificador": str(linha[col_doc]) if col_doc is not None and pd.notna(linha[col_doc]) else f"linha-{indice + 2}",
        })
    return itens


def importar_extrato(conta_id: int, caminho: str | Path, ator: dict) -> dict:
    exigir_acao(ator, "importar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    caminho = Path(caminho).expanduser().resolve()
    if not caminho.is_file():
        raise ValueError("Arquivo de extrato não encontrado.")
    digest = hashlib.sha256(caminho.read_bytes()).hexdigest()
    formato = caminho.suffix.lstrip(".").upper()
    if formato == "XLS":
        formato = "XLSX"
    itens = _ler_extrato(caminho)
    if not itens:
        raise ValueError("Nenhuma movimentação válida foi encontrada no extrato.")
    with conectar() as conexao:
        _validar_referencia(conexao, "fin_contas", conta_id, empresa_id, filial_id=filial_id)
        cursor = conexao.execute(
            "INSERT INTO fin_extratos (empresa_id,filial_id,conta_id,arquivo_nome,arquivo_hash,formato,importado_por) VALUES (?,?,?,?,?,?,?)",
            (empresa_id, filial_id, int(conta_id), caminho.name, digest, formato, int(ator["id"])),
        )
        extrato_id = int(cursor.lastrowid)
        inseridos = 0
        for item in itens:
            valor = _centavos(item["valor"], permite_negativo=True)
            descricao = _normalizar_texto(item["descricao"], 240)
            candidatos = conexao.execute(
                """
                SELECT id,descricao,natureza,valor_original_centavos,vencimento,liquidacao
                FROM fin_lancamentos
                WHERE empresa_id=? AND filial_id=? AND status NOT IN ('Cancelado','Estornado')
                  AND ABS(valor_original_centavos-ABS(?))<=5
                  AND ABS(julianday(COALESCE(liquidacao,vencimento,competencia))-julianday(?))<=7
                LIMIT 20
                """,
                (empresa_id, filial_id, valor, item["data"]),
            ).fetchall()
            melhor = None
            melhor_score = 0
            for candidato in candidatos:
                score = int(SequenceMatcher(None, descricao.lower(), str(candidato["descricao"]).lower()).ratio() * 100)
                if score > melhor_score:
                    melhor, melhor_score = candidato, score
            status = "Sugerido" if melhor is not None and melhor_score >= 45 else "Sem correspondência"
            conexao.execute(
                """
                INSERT OR IGNORE INTO fin_extrato_itens (
                    extrato_id,data,descricao,documento,valor_centavos,
                    identificador_banco,status,lancamento_id,score
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    extrato_id, item["data"], descricao,
                    _normalizar_texto(item.get("documento"), 120), valor,
                    _normalizar_texto(item["identificador"], 160), status,
                    int(melhor["id"]) if melhor is not None else None, melhor_score,
                ),
            )
            inseridos += 1
        _registrar_evento(conexao, ator, "extrato_importado", "fin_extratos", extrato_id, depois={"arquivo": caminho.name, "itens": inseridos})
    return {"extrato_id": extrato_id, "itens": inseridos}


def listar_conciliacoes(ator: dict, *, status="Todos") -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtro = "" if status == "Todos" else " AND i.status=?"
    parametros: tuple = (empresa_id, filial_id) if not filtro else (empresa_id, filial_id, status)
    with conectar() as conexao:
        return [dict(item) for item in conexao.execute(
            """
            SELECT i.*,e.arquivo_nome,c.nome conta_nome,l.descricao lancamento_descricao
            FROM fin_extrato_itens i
            JOIN fin_extratos e ON e.id=i.extrato_id
            JOIN fin_contas c ON c.id=e.conta_id
            LEFT JOIN fin_lancamentos l ON l.id=i.lancamento_id
            WHERE e.empresa_id=? AND e.filial_id=?
            """ + filtro + " ORDER BY i.data DESC,i.id DESC",
            parametros,
        ).fetchall()]


def conciliar_item(item_id: int, lancamento_id: int, ator: dict) -> None:
    exigir_acao(ator, "conciliar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        item = conexao.execute(
            """
            SELECT i.*,e.conta_id FROM fin_extrato_itens i
            JOIN fin_extratos e ON e.id=i.extrato_id
            WHERE i.id=? AND e.empresa_id=? AND e.filial_id=?
            """,
            (int(item_id), empresa_id, filial_id),
        ).fetchone()
        lancamento = conexao.execute(
            "SELECT * FROM fin_lancamentos WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(lancamento_id), empresa_id, filial_id),
        ).fetchone()
        if item is None or lancamento is None:
            raise ValueError("Movimentação ou lançamento não encontrado.")
        if abs(abs(int(item["valor_centavos"])) - int(lancamento["valor_original_centavos"])) > 5:
            raise ValueError("Existe divergência de valor; ajuste ou registre a baixa antes de conciliar.")
        conexao.execute(
            "UPDATE fin_extrato_itens SET status='Conciliado',lancamento_id=?,score=100,conciliado_por=?,conciliado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(lancamento_id), int(ator["id"]), int(item_id)),
        )
        conexao.execute(
            "UPDATE fin_lancamentos SET conta_id=COALESCE(conta_id,?),conciliado=1,status='Conciliado',atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(item["conta_id"]), int(ator["id"]), int(lancamento_id)),
        )
        _registrar_evento(conexao, ator, "lancamento_conciliado", "fin_lancamentos", int(lancamento_id), antes={"status": lancamento["status"]}, depois={"status": "Conciliado", "extrato_item_id": int(item_id)})


def saldo_conta(conta_id: int, ator: dict) -> int:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        conta = conexao.execute(
            "SELECT saldo_inicial_centavos FROM fin_contas WHERE id=? AND empresa_id=? AND filial_id=?",
            (int(conta_id), empresa_id, filial_id),
        ).fetchone()
        if conta is None:
            raise ValueError("Conta não encontrada.")
        baixas = conexao.execute(
            """
            SELECT COALESCE(SUM(CASE
                WHEN l.natureza IN ('Receita','Conta a receber') THEN b.principal_centavos+b.juros_centavos+b.multa_centavos-b.desconto_centavos
                WHEN l.natureza IN ('Despesa','Conta a pagar','Reembolso') THEN -(b.principal_centavos+b.juros_centavos+b.multa_centavos-b.desconto_centavos)
                ELSE 0 END),0) valor
            FROM fin_baixas b JOIN fin_lancamentos l ON l.id=b.lancamento_id
            WHERE b.empresa_id=? AND b.filial_id=? AND b.conta_id=? AND b.estornada=0
            """,
            (empresa_id, filial_id, int(conta_id)),
        ).fetchone()["valor"]
        transferencias = conexao.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN conta_destino_id=? THEN valor_original_centavos ELSE 0 END),0)
                 - COALESCE(SUM(CASE WHEN conta_id=? THEN valor_original_centavos ELSE 0 END),0) valor
            FROM fin_lancamentos
            WHERE empresa_id=? AND filial_id=? AND natureza='Transferência'
              AND status NOT IN ('Cancelado','Estornado')
            """,
            (int(conta_id), int(conta_id), empresa_id, filial_id),
        ).fetchone()["valor"]
    return int(conta["saldo_inicial_centavos"]) + int(baixas or 0) + int(transferencias or 0)
