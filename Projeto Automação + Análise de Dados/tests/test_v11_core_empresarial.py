"""Regressões do CORE empresarial e Funcionário 360° da V11."""
from __future__ import annotations

import base64
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial
from enterprise.banco import inicializar_enterprise
from enterprise.organizacao import criar_empresa

CHAVE = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class CoreEmpresarialV11Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.raiz = Path(self.tmp.name)
        self.ambiente = patch.dict(os.environ, {
            "DATA_INTELLIGENCE_DB_BACKEND": "sqlite", "DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE": "1",
            "DATA_INTELLIGENCE_NODE_ROLE": "servidor", "DATA_INTELLIGENCE_PII_MASTER_KEY": CHAVE,
            "DATA_INTELLIGENCE_MEDIA_MASTER_KEY": CHAVE, "DATA_INTELLIGENCE_MFA_MASTER_KEY": CHAVE,
            "DATA_INTELLIGENCE_WEBHOOK_MASTER_KEY": CHAVE,
        }); self.ambiente.start()
        self.p_storage = patch.object(banco, "STORAGE_DIR", self.raiz); self.p_db = patch.object(banco, "DB_PATH", self.raiz / "app.db")
        self.p_storage.start(); self.p_db.start(); banco.inicializar_banco(); inicializar_enterprise()
        self.admin = criar_admin_inicial("Administrador V11", "adminv11", "SenhaForte#V11-2026")
        self.empresa_id = criar_empresa("Empresa V11", "11000000000000", ator=self.admin)
        self.ator = {**self.admin, "_empresa_id": self.empresa_id, "_filial_id": None}

    def tearDown(self):
        self.p_db.stop(); self.p_storage.stop(); self.ambiente.stop(); self.tmp.cleanup()

    def test_migration_catalogo_e_fluxos_completos(self):
        from enterprise.core_v11.registros import listar_tipos
        tipos = listar_tipos(self.ator)
        self.assertEqual(len(tipos), 108)
        self.assertEqual({x["modulo"] for x in tipos}, {
            "financeiro", "rh", "compras", "estoque", "crm", "comercial", "marketing",
            "administrativo", "juridico", "ti", "analytics", "automacao", "documentos",
        })
        with banco.conectar() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) n FROM v11_fluxos_modelos WHERE empresa_id=?", (self.empresa_id,)).fetchone()["n"], 12)
            existentes = {x["name"] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"core_pessoas", "core_midias", "core_eventos_corporativos", "funcionario_360_vinculos", "v11_registros_operacionais"}.issubset(existentes))

    def test_pessoa_campos_personalizados_e_organizacao(self):
        from services.core_empresarial import criar_pessoa, definir_campo, obter_campos_valores, salvar_campos_valores, criar_unidade, arvore_organizacional
        pessoa = criar_pessoa({
            "nome": "Maria Segura", "documento_tipo": "CPF", "documento": "12345678901",
            "dados_sensiveis": {"endereco": "Rua Confidencial"},
        }, self.ator)
        campo = definir_campo({"modulo": "rh", "recurso_tipo": "core_pessoas", "codigo": "restricao_medica", "rotulo": "Restrição médica", "tipo": "texto", "sensivel": True}, self.ator)
        self.assertGreater(campo, 0)
        salvar_campos_valores("core_pessoas", pessoa, {"restricao_medica": "Dado clínico"}, self.ator, modulo="rh")
        self.assertEqual(obter_campos_valores("core_pessoas", pessoa, self.ator)["restricao_medica"], "***")
        unidade = criar_unidade({"codigo": "OP-NE", "nome": "Operação Nordeste", "tipo": "Unidade"}, self.ator)
        self.assertGreater(unidade, 0); self.assertEqual(arvore_organizacional(self.ator)[0]["nome"], "Operação Nordeste")
        with banco.conectar() as con:
            row = con.execute("SELECT documento_mascarado,dados_sensiveis_cifrados FROM core_pessoas WHERE id=?", (pessoa,)).fetchone()
        self.assertEqual(row["documento_mascarado"], "***.***.789-**")
        self.assertNotIn("Rua Confidencial", row["dados_sensiveis_cifrados"])

    def test_registro_operacional_workflow_aprovacao_e_concorrencia(self):
        from services.operacoes_v11 import alterar_estado_registro, avancar_fluxo, atualizar_registro, criar_registro, listar_registros, obter_registro
        criado = criar_registro("financeiro", "conta_pagar", {"titulo": "Fatura de fornecedor", "valor": "1.250,90", "dados": {"descricao": "Serviço mensal"}}, self.ator)
        detalhe = obter_registro(criado["id"], self.ator)
        self.assertEqual(detalhe["fluxo"]["etapa_atual"], "documento")
        versao = atualizar_registro(criado["id"], {"descricao": "Documento conferido"}, self.ator, expected_version=1)
        self.assertEqual(versao, 2)
        with self.assertRaises(ValueError):
            atualizar_registro(criado["id"], {"descricao": "Versão obsoleta"}, self.ator, expected_version=1)
        resultado = avancar_fluxo(criado["id"], self.ator, expected_version=2)
        self.assertEqual(resultado["etapa"], "obrigacao")
        removido = alterar_estado_registro(criado["id"], "Lixeira", self.ator, expected_version=3)
        self.assertEqual(removido, 4)
        self.assertEqual(listar_registros(self.ator, modulo="financeiro")["total"], 0)
        self.assertEqual(listar_registros(self.ator, modulo="financeiro", estado="Lixeira")["total"], 1)
        restaurado = alterar_estado_registro(criado["id"], "Ativo", self.ator, expected_version=4)
        self.assertEqual(restaurado, 5)
        self.assertEqual(listar_registros(self.ator, modulo="financeiro")["total"], 1)
        with banco.conectar() as con:
            self.assertGreater(con.execute("SELECT COUNT(*) n FROM tarefas WHERE empresa_id=?", (self.empresa_id,)).fetchone()["n"], 0)

    def test_colaboracao_busca_dashboard_calendario(self):
        from services.core_empresarial import busca_universal, criar_evento_calendario, listar_calendario, listar_dashboards, salvar_dashboard
        from services.operacoes_v11 import criar_registro
        registro = criar_registro("crm", "lead", {"titulo": "Lead Varejo Recife", "dados": {"descricao": "Conta prioritária"}}, self.ator)
        busca = busca_universal("Varejo Recife", self.ator)
        self.assertEqual(busca["total"], 1); self.assertEqual(busca["itens"][0]["recurso_id"], registro["id"])
        evento = criar_evento_calendario({"modulo": "administrativo", "titulo": "Reunião executiva", "inicio": "2026-09-01 09:00", "fim": "2026-09-01 10:00"}, self.ator)
        self.assertGreater(evento, 0); self.assertEqual(len(listar_calendario(self.ator, inicio="2026-09-01", fim="2026-09-02")), 1)
        painel = salvar_dashboard({"nome": "Cockpit", "layout": {"colunas": 12}, "widgets": [{"tipo": "indicador", "titulo": "Pipeline", "fonte": "crm.leads"}]}, self.ator)
        self.assertEqual(painel["versao_registro"], 0); self.assertEqual(listar_dashboards(self.ator)[0]["widgets"][0]["titulo"], "Pipeline")

    def test_funcionario_360_avatar_e_secoes(self):
        from services.departamentos.rh import criar_colaborador
        from services.funcionario_360 import obter_funcionario_360, registrar_avatar_bytes, carregar_avatar
        colaborador = criar_colaborador({"nome_completo": "Pessoa 360", "cpf": "98765432100", "data_admissao": "2026-08-14", "cargo_texto": "Analista"}, self.ator)
        perfil = obter_funcionario_360(colaborador, self.ator, visao="rh")
        self.assertTrue({"identidade", "dados_pessoais", "remuneracao", "equipamentos", "acessos", "desempenho"}.issubset(perfil["secoes"]))
        midia = registrar_avatar_bytes(colaborador, PNG_1X1, "avatar.png", self.ator, mime_type="image/png")
        bruto, meta = carregar_avatar(colaborador, self.ator, miniatura=False)
        self.assertEqual(bruto, PNG_1X1); self.assertEqual(meta["versao"], 1); self.assertEqual(midia["hash_sha256"], __import__("hashlib").sha256(PNG_1X1).hexdigest())
        arquivos = list((self.raiz / "midias_v11").rglob("*.dimedia"))
        self.assertEqual(len(arquivos), 1); self.assertNotIn(PNG_1X1, arquivos[0].read_bytes())

    def test_transferencias_api_openapi_e_rpc(self):
        from services.core_empresarial import exportar_registros, importar_registros_bytes
        from services.operacoes_v11 import criar_registro
        from servidor_corporativo.api_v1 import eh_endpoint_publico
        from servidor_corporativo.openapi import documento_openapi
        from core.rpc_central import RPC_ALLOWLIST
        criar_registro("financeiro", "conta_pagar", {"titulo": "Conta exportável", "dados": {}}, self.ator)
        exportacao = exportar_registros("financeiro", self.ator, formato="CSV")
        self.assertEqual(exportacao["status"], "Concluida")
        importacao = importar_registros_bytes("financeiro", "conta_pagar", b"titulo,descricao\nConta importada,Origem CSV\n", "dados.csv", self.ator)
        self.assertEqual(importacao["processados"], 1)
        self.assertTrue(eh_endpoint_publico("/api/v1/employees/42/360"))
        self.assertIn("/api/v1/operations/records", documento_openapi()["paths"])
        self.assertIn("delete", documento_openapi()["paths"]["/api/v1/operations/records/{record_id}"])
        self.assertIn("enterprise.core_v11.funcionarios", RPC_ALLOWLIST)


if __name__ == "__main__":
    unittest.main()
