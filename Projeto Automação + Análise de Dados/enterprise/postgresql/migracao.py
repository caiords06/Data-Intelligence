"""Migração segura do banco SQLite legado para PostgreSQL V10.1."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sqlite3
from typing import Iterable

from .bootstrap import inicializar_schema_postgresql
from .adapter import conectar_postgresql


def _tabelas_sqlite(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]


def _ordem_fk(con: sqlite3.Connection, tabelas: Iterable[str]) -> list[str]:
    tabelas=list(tabelas); conjunto=set(tabelas); deps={t:set() for t in tabelas}
    for tabela in tabelas:
        for fk in con.execute(f'PRAGMA foreign_key_list("{tabela}")').fetchall():
            ref=str(fk[2])
            if ref in conjunto and ref != tabela: deps[tabela].add(ref)
    restante=set(tabelas); ordem=[]
    while restante:
        prontas=sorted(t for t in restante if not (deps[t] & restante))
        if not prontas:
            raise RuntimeError("O schema SQLite possui ciclo de foreign keys não suportado pela migração automática.")
        ordem.extend(prontas); restante.difference_update(prontas)
    return ordem


def _colunas(con: sqlite3.Connection, tabela: str) -> list[str]:
    return [str(r[1]) for r in con.execute(f'PRAGMA table_info("{tabela}")').fetchall()]


def _count_pg(tabela: str) -> int:
    with conectar_postgresql() as pg:
        return int(pg.execute(f'SELECT COUNT(*) n FROM "{tabela}"').fetchone()["n"])


def migrar_sqlite_para_postgresql(caminho: str | Path, *, exigir_destino_vazio: bool=True, lote: int=500) -> dict:
    origem=Path(caminho).expanduser().resolve()
    if not origem.is_file(): raise FileNotFoundError(origem)
    inicializar_schema_postgresql()
    sqlite=sqlite3.connect(f"file:{origem.as_posix()}?mode=ro", uri=True)
    sqlite.row_factory=sqlite3.Row
    try:
        tabelas=_tabelas_sqlite(sqlite)
        ordem=_ordem_fk(sqlite,tabelas)
        if exigir_destino_vazio:
            ocupadas=[]
            for nome in ("usuarios","empresas","filiais"):
                if nome in tabelas and _count_pg(nome)>0: ocupadas.append(nome)
            if ocupadas:
                raise RuntimeError(
                    "O PostgreSQL de destino já possui dados corporativos ("+", ".join(ocupadas)+"). "
                    "A migração automática só opera sobre destino vazio para evitar mescla destrutiva."
                )
        totais={}; migradas={}
        for tabela in ordem:
            cols=_colunas(sqlite,tabela)
            if not cols: continue
            total=int(sqlite.execute(f'SELECT COUNT(*) FROM "{tabela}"').fetchone()[0]); totais[tabela]=total
            if total==0: migradas[tabela]=0; continue
            nomes=", ".join(f'"{c}"' for c in cols); marcas=", ".join("?" for _ in cols)
            sql=f'INSERT INTO "{tabela}" ({nomes}) VALUES ({marcas}) ON CONFLICT DO NOTHING'
            offset=0; inseridas=0
            while offset<total:
                rows=sqlite.execute(f'SELECT {nomes} FROM "{tabela}" LIMIT ? OFFSET ?', (int(lote),offset)).fetchall()
                if not rows: break
                valores=[tuple(r[c] for c in cols) for r in rows]
                with conectar_postgresql() as pg:
                    cur=pg.executemany(sql,valores); inseridas += max(0,int(cur.rowcount or 0))
                offset += len(rows)
            migradas[tabela]=inseridas
        # Reposiciona sequences SERIAL depois de preservar IDs do SQLite.
        with conectar_postgresql() as pg:
            for tabela in ordem:
                if "id" not in _colunas(sqlite,tabela): continue
                pg.execute(
                    "SELECT setval(pg_get_serial_sequence(?, 'id')::regclass, COALESCE((SELECT MAX(id) FROM \""+tabela+"\"), 1), COALESCE((SELECT MAX(id) FROM \""+tabela+"\"),0) > 0)",
                    (tabela,),
                )
        verificacao={t:_count_pg(t) for t in ordem}
        divergencias={t:{"sqlite":totais.get(t,0),"postgresql":verificacao.get(t,0)} for t in ordem if verificacao.get(t,0)<totais.get(t,0)}
        return {"origem":str(origem),"tabelas":len(ordem),"registros_sqlite":sum(totais.values()),"registros_postgresql":sum(verificacao.values()),"migradas":migradas,"divergencias":divergencias,"ok":not divergencias}
    finally:
        sqlite.close()
