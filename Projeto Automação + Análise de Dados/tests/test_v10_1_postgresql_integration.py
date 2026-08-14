"""Integração real PostgreSQL V10.1.

Executada no CI com um serviço PostgreSQL 17. Em ambientes locais sem o
serviço, permanece ignorada para não transformar a suíte unitária em uma
exigência de infraestrutura externa.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import tempfile

try:
    import pytest
except ModuleNotFoundError:
    # A suíte unitária mínima pode ser executada sem as ferramentas de build.
    # A integração real continua falhando explicitamente se for solicitada.
    if os.environ.get("RUN_POSTGRES_INTEGRATION") == "1":
        raise
    import unittest
    raise unittest.SkipTest("pytest/PostgreSQL real pertencem ao ambiente de integração do CI.")

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_INTEGRATION") != "1",
    reason="Integração PostgreSQL exige RUN_POSTGRES_INTEGRATION=1 e um servidor PostgreSQL real.",
)


def _resetar_postgres() -> None:
    from enterprise.postgresql.adapter import fechar_pool, obter_pool
    fechar_pool()
    pool = obter_pool()
    with pool.connection() as raw:
        anterior = raw.autocommit
        try:
            raw.autocommit = True
            raw.execute("DROP SCHEMA IF EXISTS public CASCADE", prepare=False)
            raw.execute("CREATE SCHEMA public", prepare=False)
        finally:
            raw.autocommit = anterior
    import enterprise.postgresql.bootstrap as bootstrap
    bootstrap._PRONTO = False


def test_schema_health_adapter_e_migracao_sqlite_reais():
    from enterprise.postgresql.adapter import conectar_postgresql, fechar_pool
    from enterprise.postgresql.bootstrap import health_postgresql, inicializar_schema_postgresql
    from enterprise.postgresql.migracao import migrar_sqlite_para_postgresql

    _resetar_postgres()
    inicializar_schema_postgresql(forcar=True)
    health = health_postgresql()
    assert health["backend"] == "postgresql"
    assert health["schema_pronto"] is True
    assert str(health["versao"]).startswith("17.")

    # Exercita o adapter de compatibilidade: qmark, HybridRow, lastrowid e
    # INSERT OR IGNORE -> ON CONFLICT DO NOTHING em uma tabela canônica.
    with conectar_postgresql() as pg:
        cur = pg.execute("INSERT INTO empresas (nome, cnpj) VALUES (?, ?)", ("Empresa Adapter", "ADAPTER-1"))
        empresa_id = int(cur.lastrowid)
        pg.execute("INSERT OR IGNORE INTO empresas (id, nome, cnpj) VALUES (?, ?, ?)", (empresa_id, "Duplicada", "ADAPTER-X"))
        row = pg.execute("SELECT id, nome FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        assert row[0] == empresa_id
        assert row["nome"] == "Empresa Adapter"

    # Recria o destino e prova a migração de uma base SQLite existente,
    # preservando IDs e reposicionando a sequence SERIAL.
    _resetar_postgres()
    inicializar_schema_postgresql(forcar=True)
    with tempfile.TemporaryDirectory() as tmp:
        origem = Path(tmp) / "app.db"
        con = sqlite3.connect(origem)
        con.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cnpj TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE filiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                cidade TEXT,
                estado TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, codigo),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            );
            """
        )
        con.execute("INSERT INTO empresas(id,nome,cnpj) VALUES (42,'Empresa Migrada','MIG-42')")
        con.execute("INSERT INTO filiais(id,empresa_id,nome,codigo) VALUES (77,42,'Recife','REC')")
        con.commit(); con.close()

        resultado = migrar_sqlite_para_postgresql(origem)
        assert resultado["ok"] is True
        assert resultado["registros_sqlite"] == 2
        assert resultado["registros_postgresql"] >= 2

    with conectar_postgresql() as pg:
        empresa = pg.execute("SELECT id,nome FROM empresas WHERE id=?", (42,)).fetchone()
        filial = pg.execute("SELECT id,empresa_id,codigo FROM filiais WHERE id=?", (77,)).fetchone()
        assert dict(empresa) == {"id": 42, "nome": "Empresa Migrada"}
        assert filial["empresa_id"] == 42
        assert filial["codigo"] == "REC"
        novo = pg.execute("INSERT INTO empresas(nome,cnpj) VALUES (?,?)", ("Após Migração", "SEQ"))
        assert int(novo.lastrowid) > 42

    fechar_pool()

def test_fluxos_departamentais_atuais_em_postgresql_real():
    """Homologa os domínios atuais contra PostgreSQL, não apenas o adapter.

    Este teste só roda no job com PostgreSQL 17 e cobre criação + leitura dos
    módulos adicionados nas V10.3/V10.4 e um lançamento do Financeiro.
    """
    from auth import banco
    from auth.autenticacao import criar_admin_inicial
    from auth.sessao import SESSAO
    from enterprise.banco import inicializar_enterprise
    from enterprise.postgresql.adapter import fechar_pool
    from services.contexto import obter_contexto
    from services.crm import criar_lead, contar_leads, listar_leads
    from services.departamentos.comercial import criar_oportunidade, contar_oportunidades, listar_oportunidades
    from services.departamentos.marketing import criar_campanha, contar_campanhas, listar_campanhas
    from services.departamentos.administrativo import criar_solicitacao, contar_solicitacoes, listar_solicitacoes
    from services.departamentos.juridico import criar_processo, contar_processos, listar_processos
    from services.analytics import gerar_insights, contar_insights, listar_insights
    from enterprise.financeiro import criar_conta, criar_lancamento, listar_lancamentos

    _resetar_postgres()
    try:
        # O bootstrap PostgreSQL é a fonte de verdade de autenticação e schema.
        banco.inicializar_banco()
        admin = criar_admin_inicial("Admin PostgreSQL", "adminpg", "Postgres#123456")
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        contexto = obter_contexto()
        assert int(contexto["empresa_id"]) > 0
        assert int(contexto["filial_id"]) > 0

        lead_id = criar_lead({"score": 88, "status": "MQL"}, admin)
        assert lead_id > 0
        assert contar_leads(admin, status="MQL") == 1
        assert [x["id"] for x in listar_leads(admin, status="MQL", limite=1, offset=0)] == [lead_id]

        oportunidade_id = criar_oportunidade({"titulo": "Contrato PostgreSQL", "valor": "25000"}, admin)
        assert oportunidade_id > 0
        assert contar_oportunidades(admin, status="Aberta") == 1
        assert listar_oportunidades(admin, status="Aberta", limite=1, offset=0)[0]["id"] == oportunidade_id

        campanha_id = criar_campanha({"nome": "Campanha PostgreSQL", "objetivo": "Pipeline", "status": "Ativa"}, admin)
        assert campanha_id > 0
        assert contar_campanhas(admin, status="Ativa") == 1
        assert listar_campanhas(admin, status="Ativa", limite=1, offset=0)[0]["id"] == campanha_id

        solicitacao_id = criar_solicitacao({"titulo": "Homologar sala PostgreSQL", "prioridade": "Alta"}, admin)
        assert solicitacao_id > 0
        assert contar_solicitacoes(admin, status="Aberta") == 1
        assert listar_solicitacoes(admin, status="Aberta", limite=1, offset=0)[0]["id"] == solicitacao_id

        processo_id = criar_processo({"numero": "PG-2026-0001", "titulo": "Processo PostgreSQL"}, admin)
        assert processo_id > 0
        assert contar_processos(admin) == 1
        assert listar_processos(admin, limite=1, offset=0)[0]["id"] == processo_id

        conta_id = criar_conta({"nome": "Conta PostgreSQL", "saldo_inicial": "1000"}, admin)
        lancamento_id = criar_lancamento({
            "natureza": "Receita",
            "descricao": "Receita de homologação PostgreSQL",
            "valor": "1234.56",
            "competencia": "2026-08-13",
            "conta_id": conta_id,
            "status": "Rascunho",
        }, admin)[0]
        pagina = listar_lancamentos(admin, pagina=1, tamanho=10, status="Rascunho")
        assert pagina["total"] >= 1
        assert any(int(x["id"]) == lancamento_id for x in pagina["itens"])

        # Analytics percorre os módulos reais e persiste insights no mesmo PG.
        gerados = gerar_insights(admin, persistir=True)
        assert "insights" in gerados
        total_insights = contar_insights(admin, status="Ativo")
        assert total_insights >= 0
        assert len(listar_insights(admin, status="Ativo", limite=10, offset=0)) <= 10
    finally:
        SESSAO.encerrar()
        fechar_pool()
