"""Importação e exportação configuráveis, rastreáveis e independentes da UI."""
from __future__ import annotations

from io import BytesIO, StringIO
import csv
import json

import pandas as pd

from auth.banco import conectar
from enterprise.core_v11.common import dump, escopo, json_objeto, load, registrar_evento
from enterprise.core_v11.documentos import carregar_midia_bytes, registrar_midia_bytes
from enterprise.core_v11.registros import criar_registro, listar_registros

FORMATOS = {"CSV", "JSON", "XLSX"}


def _nova_transferencia(tipo: str, modulo: str, recurso_tipo: str, formato: str, mapeamento: dict, filtros: dict, ator: dict) -> int:
    empresa_id, filial_id = escopo(ator, modulo, "escrever" if tipo == "Importacao" else "ler")
    formato = str(formato).upper()
    if formato not in FORMATOS:
        raise ValueError("Formato deve ser CSV, JSON ou XLSX.")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_transferencias_dados
               (empresa_id,filial_id,tipo,modulo,recurso_tipo,formato,mapeamento_json,filtros_json,status,solicitado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, tipo, str(modulo), str(recurso_tipo), formato,
             dump(json_objeto(mapeamento, campo="Mapeamento")), dump(json_objeto(filtros, campo="Filtros")),
             "Processando", int(ator["id"])),
        )
        return int(cursor.lastrowid)


def _serializar(itens: list[dict], formato: str) -> tuple[bytes, str, str]:
    linhas = []
    for item in itens:
        linha = dict(item)
        for chave, valor in list(linha.items()):
            if isinstance(valor, (dict, list)):
                linha[chave] = json.dumps(valor, ensure_ascii=False, default=str)
        linhas.append(linha)
    if formato == "JSON":
        return json.dumps(linhas, ensure_ascii=False, indent=2, default=str).encode("utf-8"), "application/json", "json"
    if formato == "CSV":
        campos = sorted({chave for linha in linhas for chave in linha})
        destino = StringIO(newline="")
        writer = csv.DictWriter(destino, fieldnames=campos, extrasaction="ignore")
        writer.writeheader(); writer.writerows(linhas)
        return destino.getvalue().encode("utf-8-sig"), "text/csv", "csv"
    destino = BytesIO(); pd.DataFrame(linhas).to_excel(destino, index=False)
    return destino.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"


def exportar_registros(
    modulo: str,
    ator: dict,
    *,
    formato: str = "XLSX",
    tipo: str | None = None,
    status: str | None = None,
    pesquisa: str = "",
) -> dict:
    filtros = {"tipo": tipo, "status": status, "pesquisa": pesquisa}
    transferencia_id = _nova_transferencia("Exportacao", modulo, "v11_registros_operacionais", formato, {}, filtros, ator)
    try:
        resultado = listar_registros(ator, modulo=modulo, tipo=tipo, status=status, pesquisa=pesquisa, pagina=1, tamanho=200)
        itens = list(resultado["itens"])
        # Exportações grandes são paginadas sem retirar o limite defensivo por consulta.
        pagina = 2
        while len(itens) < int(resultado["total"]):
            lote = listar_registros(ator, modulo=modulo, tipo=tipo, status=status, pesquisa=pesquisa, pagina=pagina, tamanho=200)
            if not lote["itens"]:
                break
            itens.extend(lote["itens"]); pagina += 1
            if len(itens) > 100_000:
                raise ValueError("A exportação excede 100.000 registros; refine os filtros.")
        bruto, mime_type, extensao = _serializar(itens, str(formato).upper())
        midia = registrar_midia_bytes(
            bruto, f"exportacao_{modulo}_{transferencia_id}.{extensao}", ator, modulo=modulo,
            recurso_tipo="core_transferencias_dados", recurso_id=transferencia_id, finalidade="Exportacao",
            titulo=f"Exportação {modulo}", classificacao="Confidencial", mime_type=mime_type,
        )
        empresa_id, filial_id = escopo(ator)
        with conectar() as con:
            con.execute(
                """UPDATE core_transferencias_dados SET status='Concluida',total_registros=?,
                   registros_processados=?,arquivo_midia_id=?,concluido_em=CURRENT_TIMESTAMP WHERE id=?""",
                (len(itens), len(itens), int(midia["id"]), transferencia_id),
            )
            registrar_evento(
                con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="dados.exportados",
                recurso_tipo="core_transferencias_dados", recurso_id=transferencia_id, ator=ator,
                payload={"formato": formato, "total": len(itens), "midia_id": int(midia["id"])},
            )
        return {"id": transferencia_id, "status": "Concluida", "total": len(itens), "midia_id": int(midia["id"])}
    except Exception as exc:
        with conectar() as con:
            con.execute(
                "UPDATE core_transferencias_dados SET status='Falhou',erros_json=?,concluido_em=CURRENT_TIMESTAMP WHERE id=?",
                (dump([str(exc)[:500]]), transferencia_id),
            )
        raise


def _ler_linhas(bruto: bytes, formato: str) -> list[dict]:
    if len(bruto) > 100 * 1024 * 1024:
        raise ValueError("Arquivo de importação excede 100 MB.")
    if formato == "JSON":
        dados = json.loads(bruto.decode("utf-8-sig"))
        if not isinstance(dados, list) or not all(isinstance(item, dict) for item in dados):
            raise ValueError("JSON deve conter uma lista de objetos.")
        return dados
    if formato == "CSV":
        return list(csv.DictReader(StringIO(bruto.decode("utf-8-sig"))))
    quadro = pd.read_excel(BytesIO(bruto))
    return json.loads(quadro.where(pd.notna(quadro), None).to_json(orient="records", force_ascii=False))


def importar_registros_bytes(
    modulo: str,
    codigo_tipo: str,
    bruto: bytes,
    nome_arquivo: str,
    ator: dict,
    *,
    formato: str | None = None,
    mapeamento: dict | None = None,
    continuar_com_erros: bool = True,
) -> dict:
    formato = str(formato or nome_arquivo.rsplit(".", 1)[-1]).upper()
    transferencia_id = _nova_transferencia("Importacao", modulo, "v11_registros_operacionais", formato, mapeamento or {}, {}, ator)
    try:
        linhas = _ler_linhas(bytes(bruto), formato)
        if len(linhas) > 100_000:
            raise ValueError("A importação excede 100.000 registros.")
        mapa = json_objeto(mapeamento, campo="Mapeamento")
    except Exception as exc:
        with conectar() as con:
            con.execute(
                "UPDATE core_transferencias_dados SET status='Falhou',erros_json=?,concluido_em=CURRENT_TIMESTAMP WHERE id=?",
                (dump([str(exc)[:500]]), transferencia_id),
            )
        raise
    processados = 0; erros: list[dict] = []
    for indice, origem in enumerate(linhas, start=2):
        try:
            item = {destino: origem.get(fonte) for fonte, destino in mapa.items()} if mapa else dict(origem)
            extras = item.pop("dados", {})
            if isinstance(extras, str):
                extras = json.loads(extras or "{}")
            item["dados"] = extras if isinstance(extras, dict) else {}
            criar_registro(modulo, codigo_tipo, item, ator)
            processados += 1
        except Exception as exc:
            erros.append({"linha": indice, "erro": str(exc)[:500]})
            if not continuar_com_erros:
                break
            if len(erros) >= 1_000:
                break
    status = "Concluida" if not erros else ("Concluida com erros" if processados else "Falhou")
    empresa_id, filial_id = escopo(ator)
    with conectar() as con:
        con.execute(
            """UPDATE core_transferencias_dados SET status=?,total_registros=?,registros_processados=?,
               erros_json=?,concluido_em=CURRENT_TIMESTAMP WHERE id=?""",
            (status, len(linhas), processados, dump(erros), transferencia_id),
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="dados.importados",
            recurso_tipo="core_transferencias_dados", recurso_id=transferencia_id, ator=ator,
            payload={"tipo": codigo_tipo, "total": len(linhas), "processados": processados, "erros": len(erros)},
        )
    return {"id": transferencia_id, "status": status, "total": len(linhas), "processados": processados, "erros": erros}


def listar_transferencias(ator: dict, *, modulo: str | None = None, limite: int = 100) -> list[dict]:
    empresa_id, filial_id = escopo(ator)
    filtros = ["empresa_id=?", "(filial_id=? OR ? IS NULL)"]; parametros: list = [empresa_id, filial_id, filial_id]
    if modulo:
        escopo(ator, modulo, "ler"); filtros.append("modulo=?"); parametros.append(str(modulo))
    with conectar() as con:
        rows = con.execute(
            f"SELECT * FROM core_transferencias_dados WHERE {' AND '.join(filtros)} ORDER BY id DESC LIMIT ?",
            (*parametros, max(1, min(int(limite), 1000))),
        ).fetchall()
    return [{**dict(x), "mapeamento": load(x["mapeamento_json"], {}), "filtros": load(x["filtros_json"], {}), "erros": load(x["erros_json"], [])} for x in rows]


def baixar_exportacao(transferencia_id: int, ator: dict) -> tuple[bytes, dict]:
    empresa_id, _ = escopo(ator)
    with conectar() as con:
        row = con.execute(
            "SELECT modulo,arquivo_midia_id FROM core_transferencias_dados WHERE id=? AND empresa_id=?",
            (int(transferencia_id), empresa_id),
        ).fetchone()
    if row is None or not row["arquivo_midia_id"]:
        raise ValueError("Exportação não encontrada ou ainda indisponível.")
    return carregar_midia_bytes(int(row["arquivo_midia_id"]), ator, modulo=str(row["modulo"]))


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = ("baixar_exportacao", "exportar_registros", "importar_registros_bytes", "listar_transferencias")
