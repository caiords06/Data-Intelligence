import sqlite3,re
from pathlib import Path
import os, tempfile
DB=os.environ.get('DATA_INTELLIGENCE_SCHEMA_SQLITE','storage/app.db'); out=Path('enterprise/postgresql/schema_v10_1.sql')
c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
objs=c.execute("select type,name,tbl_name,sql from sqlite_master where sql is not null and name not like 'sqlite_%' order by type,name").fetchall()
tables=[r for r in objs if r['type']=='table']

def strip_fks(sql):
    lines=sql.strip().splitlines()
    kept=[]
    for line in lines:
        if re.search(r'\bFOREIGN\s+KEY\b',line,re.I):
            continue
        kept.append(line)
    # Remove trailing comma before closing paren.
    for i in range(len(kept)-2,-1,-1):
        if kept[i].strip():
            kept[i]=re.sub(r',\s*$', '', kept[i])
            break
    return '\n'.join(kept)

def table_sql(sql):
    s=strip_fks(sql)
    s=re.sub(r"usuario\s+TEXT\s+NOT\s+NULL\s+UNIQUE\s+COLLATE\s+NOCASE", "usuario TEXT NOT NULL", s, flags=re.I)
    s=re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "SERIAL PRIMARY KEY", s, flags=re.I)
    s=re.sub(r"\bAUTOINCREMENT\b", "", s, flags=re.I)
    s=re.sub(r"\bREAL\b", "DOUBLE PRECISION", s, flags=re.I)
    s=re.sub(r"DEFAULT\s+CURRENT_TIMESTAMP", "DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))", s, flags=re.I)
    s=re.sub(r"\s+COLLATE\s+NOCASE\b", "", s, flags=re.I)
    return s.rstrip(';')+';'

def index_sql(sql):
    s = re.sub(r"\s+COLLATE\s+NOCASE\b", "", sql.strip(), flags=re.I)
    # SQLite aceita IFNULL(); PostgreSQL usa COALESCE().
    s = re.sub(r"\bIFNULL\s*\(", "COALESCE(", s, flags=re.I)
    return s.rstrip(';')+';'

L=["-- Data Intelligence V10.1 — baseline PostgreSQL gerado do schema SQLite canônico V10.0.","-- Não editar manualmente sem atualizar scripts/gerar_schema_postgresql.py.","BEGIN;","SET TIME ZONE 'UTC';"]
for r in tables: L.append('\n'+table_sql(r['sql']))
L.append("\n-- Índices")
for r in objs:
    if r['type']=='index': L.append(index_sql(r['sql']))
L.append("CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_usuario_ci ON usuarios (LOWER(usuario));")
L.append("\n-- Foreign keys do schema canônico.")
for r in tables:
    table=r['name']
    fks=c.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
    # Group composite FKs by id.
    groups={}
    for fk in fks: groups.setdefault(fk[0],[]).append(fk)
    for fid,items in groups.items():
        items=sorted(items,key=lambda x:x[1])
        ref=items[0][2]
        from_cols=', '.join(x[3] for x in items); to_cols=', '.join(x[4] for x in items)
        cname=f"fk_{table}_{fid}"
        L.append(f"ALTER TABLE {table} ADD CONSTRAINT {cname} FOREIGN KEY ({from_cols}) REFERENCES {ref}({to_cols});")
# Replace filial/company validation triggers with composite FK.
L += ["\n-- Integridade empresa/filial: FK composta em vez de triggers SQLite.","CREATE UNIQUE INDEX IF NOT EXISTS ux_filiais_id_empresa ON filiais(id, empresa_id);"]
for r in tables:
    table=r['name']; cols={x[1] for x in c.execute(f'PRAGMA table_info("{table}")')}
    if table!='filiais' and {'empresa_id','filial_id'}<=cols:
        L.append(f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;")
        L.append(f"ALTER TABLE {table} VALIDATE CONSTRAINT fk_{table}_filial_empresa;")
L += [
"\n-- Compatibilidade centavos/valor para aprovações.",
"CREATE OR REPLACE FUNCTION di_aprovacoes_sync_insert() RETURNS trigger LANGUAGE plpgsql AS $$",
"BEGIN",
"  IF COALESCE(NEW.valor_centavos, 0) = 0 AND ABS(COALESCE(NEW.valor, 0)) > 0 THEN NEW.valor_centavos := ROUND(COALESCE(NEW.valor,0) * 100);",
"  ELSIF COALESCE(NEW.valor_centavos, 0) <> 0 THEN NEW.valor := NEW.valor_centavos / 100.0; END IF;",
"  RETURN NEW;",
"END $$;",
"CREATE TRIGGER trg_aprovacoes_valor_insert BEFORE INSERT ON aprovacoes FOR EACH ROW EXECUTE FUNCTION di_aprovacoes_sync_insert();",
"CREATE OR REPLACE FUNCTION di_aprovacoes_sync_update() RETURNS trigger LANGUAGE plpgsql AS $$",
"BEGIN",
"  IF NEW.valor IS DISTINCT FROM OLD.valor THEN NEW.valor_centavos := ROUND(COALESCE(NEW.valor,0)*100); END IF;",
"  IF NEW.valor_centavos IS DISTINCT FROM OLD.valor_centavos THEN NEW.valor := COALESCE(NEW.valor_centavos,0)/100.0; END IF;",
"  RETURN NEW;",
"END $$;",
"CREATE TRIGGER trg_aprovacoes_valor_update BEFORE UPDATE OF valor, valor_centavos ON aprovacoes FOR EACH ROW EXECUTE FUNCTION di_aprovacoes_sync_update();",
"\n-- Persistência PostgreSQL-only adicionada após o schema SQLite canônico.",
"CREATE TABLE IF NOT EXISTS historico_analises (",
"  id BIGSERIAL PRIMARY KEY,",
"  usuario_id INTEGER NOT NULL REFERENCES usuarios(id),",
"  empresa_id INTEGER REFERENCES empresas(id),",
"  filial_id INTEGER,",
"  categoria TEXT NOT NULL, fonte TEXT NOT NULL, quantidade_arquivos INTEGER NOT NULL,",
"  total_registros INTEGER NOT NULL, total_colunas INTEGER NOT NULL, score_qualidade DOUBLE PRECISION,",
"  nivel_qualidade TEXT, status TEXT NOT NULL DEFAULT 'concluida', resumo_json TEXT NOT NULL,",
"  estado_registro TEXT NOT NULL DEFAULT 'Ativo', excluido_em TEXT, excluido_por INTEGER REFERENCES usuarios(id),",
"  criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),",
"  FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id)",
");",
"CREATE INDEX IF NOT EXISTS idx_historico_analises_escopo ON historico_analises (empresa_id, filial_id, usuario_id, estado_registro, id DESC);",
"CREATE TABLE IF NOT EXISTS preferencias_usuarios (",
"  usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,",
"  preferencias_json TEXT NOT NULL,",
"  atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))",
");",
"\n-- O baseline já incorpora as migrations SQLite 001..019.",
]
for (name,) in c.execute("select chave from migracoes_sistema order by chave").fetchall():
    L.append(f"INSERT INTO migracoes_sistema (chave) VALUES ('{name.replace(chr(39),chr(39)*2)}') ON CONFLICT (chave) DO NOTHING;")
L.append("INSERT INTO migracoes_sistema (chave) VALUES ('postgresql_baseline_v10_1') ON CONFLICT (chave) DO NOTHING;")
L.append("COMMIT;\n")
out.write_text('\n'.join(L),encoding='utf-8')
print(out,'lines',len(L),'bytes',out.stat().st_size)
