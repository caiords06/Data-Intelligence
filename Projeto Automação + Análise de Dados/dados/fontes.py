"""Aquisição segura de fontes externas suportadas pela análise V8.2."""

from __future__ import annotations

import ipaddress
import re
import socket
import sqlite3
from contextlib import closing
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

import pandas as pd

from auth import banco


EXTENSOES = {".xlsx", ".xls", ".csv", ".json", ".parquet", ".txt"}
LIMITE_BYTES = 100 * 1024 * 1024


class _RedirectSeguro(HTTPRedirectHandler):
    """Bloqueia SSRF também em cada salto de redirecionamento."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validar_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validar_url(url: str) -> str:
    url = str(url).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Informe uma URL HTTP ou HTTPS válida.")
    host = parsed.hostname.casefold()
    if host in {"localhost", "localhost.localdomain"}:
        raise ValueError("Endereços locais não são permitidos nesta fonte.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
        raise ValueError("Endereços de rede privada não são permitidos.")
    if ip is None:
        try:
            enderecos = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)
            }
        except (OSError, ValueError) as erro:
            raise ValueError("Não foi possível validar o endereço informado.") from erro
        if any(
            endereco.is_private
            or endereco.is_loopback
            or endereco.is_link_local
            or endereco.is_reserved
            or endereco.is_multicast
            or endereco.is_unspecified
            for endereco in enderecos
        ):
            raise ValueError("O endereço informado aponta para uma rede não permitida.")
    return url


def _url_google_drive(url: str) -> str:
    if "/folders/" in url:
        raise ValueError(
            "Links de pasta exigem OAuth no Integration Hub. Use o link público de um arquivo."
        )
    padroes = (r"/file/d/([A-Za-z0-9_-]+)", r"[?&]id=([A-Za-z0-9_-]+)")
    arquivo_id = next(
        (resultado.group(1) for padrao in padroes if (resultado := re.search(padrao, url))),
        None,
    )
    if not arquivo_id:
        raise ValueError("Não foi possível identificar o arquivo do Google Drive.")
    return f"https://drive.usercontent.google.com/download?id={arquivo_id}&export=download&confirm=t"


def _url_onedrive(url: str) -> str:
    parsed = urlparse(url)
    consulta = parse_qs(parsed.query)
    consulta["download"] = ["1"]
    return urlunparse(parsed._replace(query=urlencode(consulta, doseq=True)))


def baixar_fonte(url: str, origem: str = "URL") -> str:
    url = _validar_url(url)
    origem = str(origem).strip().casefold()
    if origem == "google drive":
        url = _url_google_drive(url)
    elif origem == "onedrive":
        url = _url_onedrive(url)
    requisicao = Request(
        url,
        headers={"User-Agent": "Data-Intelligence-V8.2/1.0"},
    )
    pasta = banco.STORAGE_DIR / "importacoes_temp"
    pasta.mkdir(parents=True, exist_ok=True)
    abridor = build_opener(_RedirectSeguro())
    with abridor.open(requisicao, timeout=30) as resposta:
        _validar_url(resposta.geturl())
        tamanho = resposta.headers.get("Content-Length")
        if tamanho and int(tamanho) > LIMITE_BYTES:
            raise ValueError("O arquivo remoto excede o limite de 100 MB.")
        nome_header = resposta.headers.get_filename()
        nome_url = Path(urlparse(resposta.geturl()).path).name
        nome = nome_header or nome_url or "dados.csv"
        extensao = Path(nome).suffix.lower()
        if extensao not in EXTENSOES:
            tipo = str(resposta.headers.get_content_type()).casefold()
            extensao = {
                "text/csv": ".csv",
                "application/json": ".json",
                "text/plain": ".txt",
                "application/vnd.ms-excel": ".xls",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                "application/vnd.apache.parquet": ".parquet",
            }.get(tipo, "")
        if extensao not in EXTENSOES:
            raise ValueError("O link não retornou um formato de dados suportado.")
        destino = pasta / f"fonte_{uuid4().hex}{extensao}"
        total = 0
        try:
            with destino.open("wb") as arquivo:
                while bloco := resposta.read(1024 * 1024):
                    total += len(bloco)
                    if total > LIMITE_BYTES:
                        raise ValueError(
                            "O arquivo remoto excede o limite de 100 MB."
                        )
                    arquivo.write(bloco)
        except Exception:
            destino.unlink(missing_ok=True)
            raise
    return str(destino)


def importar_sqlite(caminho: str, tabela: str) -> str:
    origem = Path(caminho).expanduser().resolve()
    if not origem.is_file():
        raise ValueError("Banco SQLite não encontrado.")
    tabela = str(tabela).strip()
    if not tabela:
        raise ValueError("Informe a tabela que será importada.")
    uri = f"file:{origem.as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as conexao:
        existe = conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
            (tabela,),
        ).fetchone()
        if existe is None:
            raise ValueError("Tabela ou view não encontrada no banco informado.")
        identificador = '"' + tabela.replace('"', '""') + '"'
        pasta = banco.STORAGE_DIR / "importacoes_temp"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"sqlite_{uuid4().hex}.csv"
        primeiro_bloco = True
        try:
            for dataframe in pd.read_sql_query(
                f"SELECT * FROM {identificador}",
                conexao,
                chunksize=25_000,
            ):
                dataframe.to_csv(
                    destino,
                    mode="w" if primeiro_bloco else "a",
                    header=primeiro_bloco,
                    index=False,
                    encoding="utf-8-sig" if primeiro_bloco else "utf-8",
                )
                primeiro_bloco = False
                if destino.stat().st_size > LIMITE_BYTES:
                    raise ValueError(
                        "A tabela convertida excede o limite de 100 MB. "
                        "Aplique um filtro ou exporte um recorte."
                    )
            if primeiro_bloco:
                cursor = conexao.execute(f"SELECT * FROM {identificador} LIMIT 0")
                colunas = [item[0] for item in cursor.description or ()]
                pd.DataFrame(columns=colunas).to_csv(
                    destino, index=False, encoding="utf-8-sig"
                )
        except Exception:
            destino.unlink(missing_ok=True)
            raise
    return str(destino)


def limpar_arquivo_temporario(caminho: str | Path) -> bool:
    """Remove somente arquivos pertencentes ao diretório temporário gerenciado."""
    alvo = Path(caminho).expanduser().resolve()
    pasta = (banco.STORAGE_DIR / "importacoes_temp").resolve()
    if alvo.parent != pasta or not alvo.name.startswith(("fonte_", "sqlite_")):
        return False
    alvo.unlink(missing_ok=True)
    return True


def limpar_temporarios_antigos(horas: int = 24) -> int:
    """Remove sobras gerenciadas antigas sem tocar em arquivos do usuário."""
    pasta = banco.STORAGE_DIR / "importacoes_temp"
    if not pasta.exists():
        return 0
    limite = time.time() - max(1, int(horas)) * 3600
    removidos = 0
    for alvo in pasta.iterdir():
        if (
            alvo.is_file()
            and alvo.name.startswith(("fonte_", "sqlite_"))
            and alvo.stat().st_mtime < limite
            and limpar_arquivo_temporario(alvo)
        ):
            removidos += 1
    return removidos
