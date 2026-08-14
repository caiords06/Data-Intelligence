"""Adapter PostgreSQL compatível com o contrato sqlite3 usado pelos domínios.

A V10.1 mantém as APIs de domínio estáveis enquanto o servidor passa a poder
usar PostgreSQL. O adapter normaliza placeholders e alguns idiomatismos SQLite
legados; novas consultas devem preferir SQL portátil.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
import logging
import sqlite3
from pathlib import Path
import re
import threading
from typing import Any, Iterable


class DependenciaPostgresAusente(RuntimeError):
    pass


class HybridRow(dict):
    """Linha indexável por nome e por posição, como ``sqlite3.Row``."""
    __slots__ = ("_ordem",)
    def __init__(self, nomes: Iterable[str], valores: Iterable[Any]):
        self._ordem = tuple(nomes)
        super().__init__(zip(self._ordem, valores))
    def __getitem__(self, chave):
        if isinstance(chave, int):
            return super().__getitem__(self._ordem[chave])
        return super().__getitem__(chave)


@dataclass(frozen=True, slots=True)
class ConfigPostgres:
    host: str
    porta: int
    banco: str
    usuario: str
    senha: str
    sslmode: str = "prefer"
    pool_min: int = 2
    pool_max: int = 12
    timeout: int = 10

    @classmethod
    def do_ambiente(cls) -> "ConfigPostgres":
        return cls(
            host=os.environ.get("DATA_INTELLIGENCE_PG_HOST", "127.0.0.1"),
            porta=int(os.environ.get("DATA_INTELLIGENCE_PG_PORT", "5432")),
            banco=os.environ.get("DATA_INTELLIGENCE_PG_DATABASE", "dataintelligence"),
            usuario=os.environ.get("DATA_INTELLIGENCE_PG_USER", "dataintelligence"),
            senha=os.environ.get("DATA_INTELLIGENCE_PG_PASSWORD", ""),
            sslmode=os.environ.get("DATA_INTELLIGENCE_PG_SSLMODE", "prefer"),
            pool_min=max(1, int(os.environ.get("DATA_INTELLIGENCE_PG_POOL_MIN", "2"))),
            pool_max=max(2, int(os.environ.get("DATA_INTELLIGENCE_PG_POOL_MAX", "12"))),
            timeout=max(2, int(os.environ.get("DATA_INTELLIGENCE_PG_TIMEOUT", "10"))),
        ).validar()

    def validar(self) -> "ConfigPostgres":
        if not self.host.strip(): raise ValueError("Host PostgreSQL inválido.")
        if not 1 <= int(self.porta) <= 65535: raise ValueError("Porta PostgreSQL inválida.")
        if not self.banco.strip() or not self.usuario.strip(): raise ValueError("Banco e usuário PostgreSQL são obrigatórios.")
        if not self.senha: raise ValueError("Senha PostgreSQL não configurada.")
        if self.sslmode not in {"disable","allow","prefer","require","verify-ca","verify-full"}:
            raise ValueError("sslmode PostgreSQL inválido.")
        if self.pool_max < self.pool_min: raise ValueError("pool_max precisa ser >= pool_min.")
        return self

    def conninfo(self) -> str:
        # A senha é passada como kwarg na abertura do pool, nunca interpolada no SQL/log.
        return f"host={self.host} port={self.porta} dbname={self.banco} user={self.usuario} sslmode={self.sslmode} connect_timeout={self.timeout}"


_POOL = None
_POOL_CFG: ConfigPostgres | None = None
_POOL_LOCK = threading.RLock()


def _deps():
    try:
        import psycopg  # type: ignore
        from psycopg_pool import ConnectionPool  # type: ignore
        return psycopg, ConnectionPool
    except ImportError as exc:
        raise DependenciaPostgresAusente(
            "PostgreSQL requer psycopg 3 e psycopg-pool. Instale as dependências do servidor V10.1."
        ) from exc


def obter_pool():
    global _POOL, _POOL_CFG
    cfg = ConfigPostgres.do_ambiente()
    with _POOL_LOCK:
        if _POOL is not None and cfg == _POOL_CFG:
            return _POOL
        if _POOL is not None:
            try:
                _POOL.close()
            except Exception:
                logging.getLogger(__name__).exception("Falha ao fechar pool PostgreSQL substituído")
        _, ConnectionPool = _deps()
        _POOL = ConnectionPool(
            conninfo=cfg.conninfo(),
            kwargs={"password": cfg.senha, "autocommit": False, "prepare_threshold": None},
            min_size=cfg.pool_min, max_size=cfg.pool_max,
            timeout=cfg.timeout, open=True,
            name="data-intelligence",
        )
        _POOL_CFG = cfg
        return _POOL


def fechar_pool() -> None:
    global _POOL, _POOL_CFG
    with _POOL_LOCK:
        if _POOL is not None:
            try: _POOL.close()
            finally: _POOL = None; _POOL_CFG = None


def _replace_qmarks(sql: str) -> str:
    out=[]; quote=None; i=0
    while i < len(sql):
        ch=sql[i]
        if quote:
            out.append(ch)
            if ch==quote:
                if i+1 < len(sql) and sql[i+1]==quote:
                    out.append(sql[i+1]); i+=1
                else: quote=None
        elif ch in {"'", '"'}:
            quote=ch; out.append(ch)
        elif ch=='?': out.append('%s')
        else: out.append(ch)
        i+=1
    return ''.join(out)


def traduzir_sql(sql: str) -> str:
    s=str(sql)
    # Sentinels para expressões SQLite que precisam de aritmética temporal real.
    s=s.replace("MAX(0,CAST((julianday('now')-julianday(iniciado_em))*86400 AS INTEGER))", "__DI_DURACAO_SEGUNDOS__")
    s=s.replace("CAST((julianday(datetime(c.sla_inicia_em,'+'||c.sla_solucao_minutos||' minutes'))-julianday('now'))*1440 AS INTEGER)", "__DI_SLA_RESTANTE_MINUTOS__")
    # Null-safe equality. Psycopg/PostgreSQL não aceitam ``IS %s``.
    s=re.sub(r"\bIS\s+\?", "IS NOT DISTINCT FROM ?", s, flags=re.I)
    # SQLite case-insensitive collation. PostgreSQL usa ordenação padrão aqui;
    # unicidade do login é garantida por índice funcional LOWER(usuario).
    s=re.sub(r"\s+COLLATE\s+NOCASE\b", "", s, flags=re.I)
    # SQLite LIKE é case-insensitive para texto ASCII por padrão; PostgreSQL
    # LIKE é case-sensitive. ILIKE preserva o comportamento esperado das buscas
    # da interface (nomes, documentos, chamados, fornecedores etc.).
    s=re.sub(r"\bLIKE\b", "ILIKE", s, flags=re.I)
    # INSERT OR IGNORE -> ON CONFLICT DO NOTHING.
    ignorar=bool(re.match(r"\s*INSERT\s+OR\s+IGNORE\s+INTO\b",s,re.I))
    if ignorar:
        s=re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", s, count=1, flags=re.I)
        if not re.search(r"\bON\s+CONFLICT\b",s,re.I): s=s.rstrip().rstrip(';')+" ON CONFLICT DO NOTHING"
    # Introspecção SQLite usada por alguns recursos legados.
    m=re.match(r"\s*PRAGMA\s+table_info\(([^)]+)\)\s*;?\s*$",s,re.I)
    if m:
        tabela=m.group(1).strip().strip('"\'')
        return ("SELECT column_name AS name, ordinal_position-1 AS cid, data_type AS type, "
                "CASE WHEN is_nullable='NO' THEN 1 ELSE 0 END AS notnull, column_default AS dflt_value, 0 AS pk "
                "FROM information_schema.columns WHERE table_schema='public' AND table_name='"+tabela.replace("'","''")+"' ORDER BY ordinal_position")
    if re.search(r"FROM\s+sqlite_master\s+WHERE\s+type\s*=\s*'table'\s+AND\s+name\s*=\s*\?", s, re.I):
        return _replace_qmarks(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=?"
        )

    # Alguns caminhos legados antigos usam o nome da tabela como literal em vez
    # de parâmetro. PostgreSQL não possui sqlite_master; convertemos a consulta
    # completa para information_schema.tables, preservando o contrato SELECT 1.
    m = re.match(
        r"\s*SELECT\s+1\s+FROM\s+sqlite_master\s+WHERE\s+"
        r"type\s*=\s*'table'\s+AND\s+name\s*=\s*'([^']+)'\s*;?\s*$",
        s,
        re.I,
    )
    if m:
        tabela = m.group(1).replace("'", "''")
        return (
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='"
            + tabela
            + "'"
        )
    # Datas/horas SQLite mais frequentes. O schema histórico armazena datas
    # como ISO-text; mantemos essa representação para preservar ordenação e
    # compatibilidade com UI/exportações. Expressões que precisam de aritmética
    # usam o sentinel e são restauradas para timestamp real ao final.
    _now_ts = "__DI_NOW_REAL__"
    _now_text = f"TO_CHAR({_now_ts} AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')"
    _today_text = "TO_CHAR(CURRENT_DATE,'YYYY-MM-DD')"
    replacements={
        r"date\('now'\)":_today_text,
        r"datetime\('now'\)":_now_text,
        r"date\('now','start of month'\)":f"TO_CHAR(DATE_TRUNC('month', {_now_ts})::date,'YYYY-MM-DD')",
        r"date\('now','\+30 day'\)":"TO_CHAR((CURRENT_DATE + INTERVAL '30 days')::date,'YYYY-MM-DD')",
        r"date\('now','\+45 day'\)":"TO_CHAR((CURRENT_DATE + INTERVAL '45 days')::date,'YYYY-MM-DD')",
        r"date\('now','-90 day'\)":"TO_CHAR((CURRENT_DATE - INTERVAL '90 days')::date,'YYYY-MM-DD')",
        r"date\('now','-5 year'\)":"TO_CHAR((CURRENT_DATE - INTERVAL '5 years')::date,'YYYY-MM-DD')",
        r"datetime\('now','-5 minute'\)":f"TO_CHAR(({_now_ts} - INTERVAL '5 minutes') AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')",
        r"datetime\('now','-30 day'\)":f"TO_CHAR(({_now_ts} - INTERVAL '30 days') AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')",
        r"datetime\('now','-90 day'\)":f"TO_CHAR(({_now_ts} - INTERVAL '90 days') AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')",
        r"datetime\('now','-180 seconds'\)":f"TO_CHAR(({_now_ts} - INTERVAL '180 seconds') AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')",
    }
    for pat,repl in replacements.items(): s=re.sub(pat,repl,s,flags=re.I)

    # Compatibilidade genérica para offsets que não estavam na lista histórica
    # (ex.: date('now','-90 day')). Assim um novo relatório não volta a vazar
    # sintaxe SQLite para o PostgreSQL apenas por usar outro intervalo.
    def _date_offset(match):
        quantidade = int(match.group(1))
        return f"TO_CHAR((CURRENT_DATE + INTERVAL '{quantidade} days')::date,'YYYY-MM-DD')"

    def _datetime_offset(match):
        quantidade = int(match.group(1))
        unidade = match.group(2).lower()
        if not unidade.endswith('s'):
            unidade += 's'
        return (
            f"TO_CHAR((CURRENT_TIMESTAMP + INTERVAL '{quantidade} {unidade}') "
            "AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')"
        )

    s=re.sub(r"date\('now'\s*,\s*'([+-]\d+)\s+days?'\)", _date_offset, s, flags=re.I)
    s=re.sub(
        r"datetime\('now'\s*,\s*'([+-]\d+)\s+(second|seconds|minute|minutes|hour|hours|day|days)'\)",
        _datetime_offset, s, flags=re.I,
    )
    s=re.sub(r"date\(\?\s*,\s*'\+30 day'\)", "TO_CHAR((CAST(? AS date) + INTERVAL '30 days')::date,'YYYY-MM-DD')", s, flags=re.I)
    s=re.sub(r"\bdate\(([_a-zA-Z0-9.]+)\)", r"SUBSTRING(CAST(\1 AS text) FROM 1 FOR 10)", s, flags=re.I)
    s=re.sub(r"datetime\(([_a-zA-Z0-9.]+)\)", r"CAST(\1 AS text)", s, flags=re.I)
    # Formatação usada em orçamento e RH legado.
    s=s.replace("strftime('%Y',l.competencia)", "TO_CHAR(CAST(l.competencia AS date),'YYYY')")
    s=s.replace("strftime('%m',l.competencia)", "TO_CHAR(CAST(l.competencia AS date),'MM')")
    s=s.replace("printf('%04d',o.ano)", "LPAD(CAST(o.ano AS text),4,'0')")
    s=s.replace("printf('%02d',o.mes)", "LPAD(CAST(o.mes AS text),2,'0')")
    s=re.sub(r"printf\('%06d',\s*id\)", "LPAD(CAST(id AS text),6,'0')", s, flags=re.I)
    # SLA/durações específicas, preservando a semântica.
    s=s.replace("datetime(sla_inicia_em,'+'||sla_solucao_minutos||' minutes')", "TO_CHAR((CAST(sla_inicia_em AS timestamp) + (sla_solucao_minutos || ' minutes')::interval) AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')")
    s=s.replace("datetime(c.sla_inicia_em,'+'||c.sla_solucao_minutos||' minutes')", "TO_CHAR((CAST(c.sla_inicia_em AS timestamp) + (c.sla_solucao_minutos || ' minutes')::interval) AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')")
    s=re.sub(r"MAX\(0,CAST\(\(julianday\('now'\)-julianday\(iniciado_em\)\)\*86400 AS INTEGER\)\)",
             "GREATEST(0, CAST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - CAST(iniciado_em AS timestamp))) AS INTEGER))",s,flags=re.I)
    s=re.sub(r"CAST\(\(julianday\(\(CAST\(c\.sla_inicia_em AS timestamp\) \+ \(c\.sla_solucao_minutos \|\| ' minutes'\)::interval\)\)-julianday\('now'\)\)\*1440 AS INTEGER\)",
             "CAST(EXTRACT(EPOCH FROM ((CAST(c.sla_inicia_em AS timestamp) + (c.sla_solucao_minutos || ' minutes')::interval) - CURRENT_TIMESTAMP))/60 AS INTEGER)",s,flags=re.I)
    s=re.sub(r"ABS\(julianday\(COALESCE\(liquidacao,vencimento,competencia\)\)-julianday\(\?\)\)<=7",
             "ABS(EXTRACT(EPOCH FROM (CAST(COALESCE(liquidacao,vencimento,competencia) AS timestamp) - CAST(? AS timestamp)))/86400)<=7",s,flags=re.I)
    # Colunas temporais históricas permanecem TEXT no baseline. DML legado usa
    # CURRENT_TIMESTAMP diretamente; convertemos para ISO-text. Sentinels de
    # aritmética temporal são restaurados depois.
    s=s.replace("CURRENT_TIMESTAMP", _now_text)
    s=s.replace(_now_ts, "CURRENT_TIMESTAMP")
    s=s.replace("__DI_DURACAO_SEGUNDOS__", "GREATEST(0, CAST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - CAST(iniciado_em AS timestamp))) AS INTEGER))")
    s=s.replace("__DI_SLA_RESTANTE_MINUTOS__", "CAST(EXTRACT(EPOCH FROM ((CAST(c.sla_inicia_em AS timestamp) + (c.sla_solucao_minutos || ' minutes')::interval) - CURRENT_TIMESTAMP))/60 AS INTEGER)")
    return _replace_qmarks(s)


def _normalizar_erro(exc: Exception) -> Exception:
    """Mapeia erros DB-API do psycopg para exceções já tratadas pelo legado."""
    try:
        psycopg,_ = _deps()
        if isinstance(exc, psycopg.IntegrityError): return sqlite3.IntegrityError(str(exc))
        if isinstance(exc, psycopg.OperationalError): return sqlite3.OperationalError(str(exc))
        if isinstance(exc, psycopg.DatabaseError): return sqlite3.DatabaseError(str(exc))
    except DependenciaPostgresAusente:
        pass
    return exc


def _tabela_insert(sql: str) -> str | None:
    """Extrai a relação alvo de INSERT simples para lastrowid determinístico."""
    m = re.match(
        r'\s*INSERT(?:\s+OR\s+IGNORE)?\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)',
        str(sql),
        re.I,
    )
    return m.group(1) if m else None


class CursorCompat:
    def __init__(self, conexao: "ConexaoCompat", cursor, tabela_insert: str | None = None):
        self._conexao=conexao; self._cursor=cursor; self._tabela_insert=tabela_insert
    @property
    def rowcount(self): return self._cursor.rowcount
    @property
    def lastrowid(self):
        # LASTVAL() pode ser contaminado por uma trigger que avance outra
        # sequence. Consultamos a sequence do ID da tabela realmente inserida.
        if not self._tabela_insert:
            return None
        try:
            seq_cur = self._conexao._raw.execute(
                "SELECT pg_get_serial_sequence(%s, 'id')",
                (self._tabela_insert,),
                prepare=False,
            )
            seq_row = seq_cur.fetchone()
            seq = seq_row[0] if seq_row else None
            if not seq:
                return None
            cur = self._conexao._raw.execute(
                "SELECT currval(%s::regclass)",
                (seq,),
                prepare=False,
            )
            row=cur.fetchone(); return row[0] if row else None
        except Exception:
            return None
    def _nomes(self): return [d.name if hasattr(d,'name') else d[0] for d in (self._cursor.description or [])]
    def fetchone(self):
        r=self._cursor.fetchone(); return None if r is None else HybridRow(self._nomes(),r)
    def fetchall(self):
        nomes=self._nomes(); return [HybridRow(nomes,r) for r in self._cursor.fetchall()]
    def fetchmany(self,size=None):
        nomes=self._nomes(); rows=self._cursor.fetchmany(size) if size else self._cursor.fetchmany(); return [HybridRow(nomes,r) for r in rows]
    def __iter__(self):
        nomes=self._nomes()
        for r in self._cursor: yield HybridRow(nomes,r)


class ConexaoCompat:
    def __init__(self, raw): self._raw=raw
    def execute(self, sql: str, parametros=()):
        cur=self._raw.cursor()
        try:
            cur.execute(traduzir_sql(sql), parametros or (), prepare=False)
        except Exception as exc:
            raise _normalizar_erro(exc) from exc
        return CursorCompat(self,cur,_tabela_insert(sql))
    def executemany(self, sql: str, parametros):
        cur=self._raw.cursor()
        try:
            cur.executemany(traduzir_sql(sql), parametros)
        except Exception as exc:
            raise _normalizar_erro(exc) from exc
        return CursorCompat(self,cur)
    def executescript(self, sql: str):
        # Usado apenas por código legado; sem parâmetros, PostgreSQL aceita o lote.
        cur=self._raw.cursor()
        try:
            cur.execute(str(sql), prepare=False)
        except Exception as exc:
            raise _normalizar_erro(exc) from exc
        return CursorCompat(self,cur)
    def commit(self): return self._raw.commit()
    def rollback(self): return self._raw.rollback()
    def close(self): return None  # conexão pertence ao pool/contexto


@contextmanager
def conectar_postgresql():
    pool=obter_pool()
    with pool.connection() as raw:
        compat=ConexaoCompat(raw)
        try:
            yield compat
            raw.commit()
        except Exception:
            raw.rollback(); raise


def testar_conexao() -> dict:
    inicio=__import__('time').perf_counter()
    with conectar_postgresql() as con:
        row=con.execute("SELECT current_database() banco, current_user usuario, version() versao").fetchone()
    return {**dict(row), "latencia_ms": round((__import__('time').perf_counter()-inicio)*1000,2)}
