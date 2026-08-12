"""Regressões do domínio especializado de Compras e Suprimentos 2.0."""

from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.compras import (
    adicionar_aditivo,
    analisar_compras,
    aprovar_pedido,
    avaliar_fornecedor,
    criar_contrato,
    criar_cotacao,
    criar_fornecedor,
    criar_pedido,
    criar_solicitacao,
    decidir_solicitacao,
    enviar_pedido,
    enviar_solicitacao,
    exportar_dataframe_compras,
    gerar_alertas_compras,
    gerar_pdf_pedido,
    gerar_relatorio_compras,
    homologar_fornecedor,
    integrar_recebimento_financeiro,
    listar_historico,
    listar_secao,
    obter_fornecedores_cotacao,
    obter_itens_pedido,
    obter_itens_solicitacao,
    registrar_negociacao,
    registrar_documento_fornecedor,
    registrar_proposta,
    registrar_recebimento,
    resolver_divergencia,
    resumo_compras,
    selecionar_fornecedor,
    salvar_regra_aprovacao,
    tem_permissao_compras,
)
from enterprise.contexto import obter_contexto
from enterprise.estoque import criar_deposito, criar_item, listar_itens


class Compras20Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
        patch_db.start(); patch_storage.start()
        self.addCleanup(patch_db.stop); self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(admin); inicializar_enterprise(); obter_contexto()
        return admin, pasta

    def _fornecedor(self, admin, sufixo, *, homologar=True):
        identificador = criar_fornecedor({
            "codigo": f"FOR-{sufixo}", "razao_social": f"Fornecedor {sufixo}",
            "cnpj_cpf": f"10.000.000/000{sufixo}/00", "email": f"{sufixo}@fornecedor.test",
            "prazo_medio_dias": 5,
        }, admin)
        if homologar:
            homologar_fornecedor(identificador, "Homologado", "", admin)
        return identificador

    def _solicitacao(self, admin, *, quantidade=10, valor="100,00", item_estoque=None):
        solicitacao = criar_solicitacao({
            "titulo": "Aquisição de equipamentos", "justificativa": "Reposição do parque operacional",
            "prioridade": "Alta", "necessario_em": (date.today() + timedelta(days=15)).isoformat(),
        }, [{
            "descricao": "Notebook corporativo", "especificacao": "16 GB RAM e SSD",
            "quantidade": quantidade, "unidade": "UN", "valor_estimado_unitario": valor,
            "estoque_item_id": item_estoque,
        }], admin)
        aprovacao = enviar_solicitacao(solicitacao, admin)
        decidir_solicitacao(solicitacao, "Aprovar", "Necessidade e orçamento validados.", admin)
        return solicitacao, aprovacao

    def _cotacao(self, admin, *, item_estoque=None):
        fornecedor_a = self._fornecedor(admin, "1")
        fornecedor_b = self._fornecedor(admin, "2")
        solicitacao, _ = self._solicitacao(admin, item_estoque=item_estoque)
        cotacao = criar_cotacao(solicitacao, [fornecedor_a, fornecedor_b], {
            "resposta_ate": (date.today() + timedelta(days=5)).isoformat(),
            "condicoes_desejadas": "Entrega completa e garantia mínima de 12 meses.",
        }, admin)
        item = obter_itens_solicitacao(solicitacao, admin)[0]
        proposta_a = registrar_proposta(cotacao, fornecedor_a, {
            "prazo_entrega_dias": 7, "frete": "100,00", "forma_pagamento": "30 dias",
        }, [{"solicitacao_item_id": item["id"], "quantidade": 10, "valor_unitario": "95,00"}], admin)
        proposta_b = registrar_proposta(cotacao, fornecedor_b, {
            "prazo_entrega_dias": 3, "frete": "0", "forma_pagamento": "30/60 dias",
        }, [{"solicitacao_item_id": item["id"], "quantidade": 10, "valor_unitario": "105,00"}], admin)
        return solicitacao, cotacao, fornecedor_a, fornecedor_b, proposta_a, proposta_b

    def _pedido_enviado(self, admin, *, item_estoque=None):
        _solicitacao, cotacao, fornecedor_a, fornecedor_b, proposta_a, proposta_b = self._cotacao(admin, item_estoque=item_estoque)
        registrar_negociacao(proposta_b, {"valor_novo": "980,00", "prazo_novo_dias": 3, "condicoes": "Frete incluso"}, admin)
        selecionar_fornecedor(cotacao, fornecedor_b, "Melhor equilíbrio entre prazo, valor e condição de pagamento.", admin)
        pedido = criar_pedido(cotacao, {
            "entrega_endereco": "Matriz", "entrega_contato": "Almoxarifado",
            "previsao_entrega": (date.today() + timedelta(days=3)).isoformat(),
            "vencimento": (date.today() + timedelta(days=30)).isoformat(), "parcelas": 1,
        }, admin)
        aprovar_pedido(pedido, True, "Pedido autorizado.", admin)
        enviar_pedido(pedido, admin)
        return pedido, fornecedor_a, fornecedor_b, proposta_a, proposta_b

    def test_migracao_cria_dominio_regras_e_historico_imutavel(self):
        admin, _ = self._ambiente()
        with banco.conectar() as conexao:
            tabelas = {x["name"] for x in conexao.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cmp_%'")}
            migracao = conexao.execute("SELECT 1 FROM migracoes_sistema WHERE chave='enterprise_009_compras_departamental'").fetchone()
            regras = conexao.execute("SELECT COUNT(*) n FROM cmp_regras_aprovacao WHERE empresa_id=?", (SESSAO.empresa_id,)).fetchone()["n"]
        self.assertGreaterEqual(len(tabelas), 28)
        self.assertIn("cmp_aprovacoes_solicitacao", tabelas)
        self.assertIsNotNone(migracao)
        self.assertEqual(regras, 4)
        salvar_regra_aprovacao({
            "nome": "Compras emergenciais", "valor_minimo": "0", "valor_maximo": "2500,00",
            "prioridade": "Urgente", "nivel": 2, "exige_financeiro": True,
        }, admin)
        self.assertEqual(len(listar_secao("regras", admin)), 5)
        fornecedor = self._fornecedor(admin, "1")
        historico = listar_historico("cmp_fornecedores", fornecedor, admin)
        self.assertTrue(historico)
        with banco.conectar() as conexao:
            with self.assertRaises(Exception):
                conexao.execute("DELETE FROM cmp_historico WHERE id=?", (historico[0]["id"],))

    def test_fornecedor_sincroniza_homologacao_avaliacao_e_documento(self):
        admin, pasta = self._ambiente(); fornecedor = self._fornecedor(admin, "1")
        avaliar_fornecedor(fornecedor, {"preco": 8, "prazo": 9, "qualidade": 10, "atendimento": 8, "conformidade": 10}, admin)
        origem = pasta / "certidao.txt"; origem.write_text("documento de teste", encoding="utf-8")
        registrar_documento_fornecedor(fornecedor, {
            "tipo": "Certidão", "titulo": "Certidão fiscal", "classificacao": "Confidencial",
            "validade": (date.today() + timedelta(days=20)).isoformat(),
        }, origem, admin)
        registro = listar_secao("fornecedores", admin)[0]
        self.assertEqual(registro["status_homologacao"], "Homologado")
        self.assertEqual(registro["score"], 9)
        with banco.conectar() as conexao:
            self.assertIsNotNone(conexao.execute("SELECT 1 FROM est_fornecedores WHERE id=?", (registro["estoque_fornecedor_id"],)).fetchone())
            self.assertIsNotNone(conexao.execute("SELECT 1 FROM fin_partes WHERE id=?", (registro["financeiro_parte_id"],)).fetchone())
        self.assertEqual(listar_secao("documentos", admin)[0]["razao_social"], "Fornecedor 1")

    def test_solicitacao_multiitem_aprovacao_e_alcada(self):
        admin, _ = self._ambiente()
        solicitacao = criar_solicitacao({"titulo": "Materiais de escritório", "justificativa": "Reposição mensal", "prioridade": "Normal"}, [
            {"descricao": "Papel A4", "quantidade": 5, "valor_estimado_unitario": "40,00"},
            {"descricao": "Toner", "quantidade": 2, "valor_estimado_unitario": "300,00"},
        ], admin)
        aprovacao = enviar_solicitacao(solicitacao, admin)
        with banco.conectar() as conexao:
            central = conexao.execute("SELECT * FROM aprovacoes WHERE id=?", (aprovacao,)).fetchone()
        self.assertIn("Supervisor", central["observacao"])
        decidir_solicitacao(solicitacao, "Aprovar", "Aprovado pelo responsável.", admin)
        registro = listar_secao("solicitacoes", admin)[0]
        self.assertEqual((registro["status"], registro["valor_aprovado_centavos"]), ("Aprovada", 80_000))
        self.assertEqual(len(obter_itens_solicitacao(solicitacao, admin)), 2)

    def test_cotacao_calcula_scores_mas_escolha_permanece_humana(self):
        admin, _ = self._ambiente()
        _sol, cotacao, fornecedor_a, fornecedor_b, _prop_a, _prop_b = self._cotacao(admin)
        propostas = obter_fornecedores_cotacao(cotacao, admin)
        self.assertTrue(all(x["score_total"] >= 0 for x in propostas))
        selecionar_fornecedor(cotacao, fornecedor_b, "Prazo menor e parcelamento mais aderente à necessidade.", admin)
        selecionada = next(x for x in listar_secao("comparativo", admin) if x["selecionado"])
        self.assertEqual(selecionada["fornecedor_id"], fornecedor_b)
        self.assertNotEqual(selecionada["fornecedor_id"], fornecedor_a)

    def test_negociacao_pedido_aprovacao_envio_e_pdf(self):
        admin, pasta = self._ambiente(); pedido, _a, _b, _pa, _pb = self._pedido_enviado(admin)
        registro = listar_secao("pedidos", admin)[0]
        self.assertEqual(registro["status"], "Enviado ao fornecedor")
        self.assertEqual(resumo_compras(admin)["saving_centavos"], 2_000)
        destino = pasta / "pedido.pdf"
        gerar_pdf_pedido(pedido, destino, admin)
        self.assertTrue(destino.is_file() and destino.stat().st_size > 500)

    def test_recebimento_parcial_nao_cria_falsa_divergencia_e_integra_estoque(self):
        admin, _ = self._ambiente()
        deposito = criar_deposito({"codigo": "REC", "nome": "Recebimento"}, admin)
        item = criar_item({"codigo": "NB-CMP", "nome": "Notebook compras", "estoque_minimo": 0}, admin)
        pedido, *_ = self._pedido_enviado(admin, item_estoque=item)
        pedido_item = obter_itens_pedido(pedido, admin)[0]
        primeiro = registrar_recebimento(pedido, {"deposito_id": deposito, "nota_fiscal": "NF-001", "recebido_em": date.today().isoformat()}, [
            {"pedido_item_id": pedido_item["id"], "quantidade_recebida": 4, "quantidade_aceita": 4, "quantidade_recusada": 0},
        ], admin)
        recebimento = next(x for x in listar_secao("recebimentos", admin) if x["id"] == primeiro)
        self.assertEqual((recebimento["status"], recebimento["possui_divergencia"]), ("Conferido", 0))
        self.assertEqual(listar_secao("pedidos", admin)[0]["status"], "Parcialmente recebido")
        self.assertEqual(listar_itens(admin)["registros"][0]["fisico"], 4)
        registrar_recebimento(pedido, {"deposito_id": deposito, "nota_fiscal": "NF-002", "recebido_em": date.today().isoformat()}, [
            {"pedido_item_id": pedido_item["id"], "quantidade_recebida": 6, "quantidade_aceita": 6, "quantidade_recusada": 0},
        ], admin)
        self.assertEqual(listar_secao("pedidos", admin)[0]["status"], "Recebido")
        self.assertEqual(listar_itens(admin)["registros"][0]["fisico"], 10)

    def test_divergencia_exige_resolucao_e_recebimento_gera_financeiro(self):
        admin, _ = self._ambiente(); pedido, *_ = self._pedido_enviado(admin)
        pedido_item = obter_itens_pedido(pedido, admin)[0]
        recebimento = registrar_recebimento(pedido, {"nota_fiscal": "NF-DIV", "documento_valor": "980,00", "recebido_em": date.today().isoformat()}, [
            {"pedido_item_id": pedido_item["id"], "quantidade_recebida": 10, "quantidade_aceita": 8, "quantidade_recusada": 2, "motivo_recusa": "Duas unidades avariadas"},
        ], admin)
        divergencia = listar_secao("divergencias", admin)[0]
        self.assertEqual(divergencia["status"], "Aberta")
        resolver_divergencia(divergencia["id"], "Fornecedor emitirá reposição e nota de crédito.", admin)
        self.assertEqual(listar_secao("divergencias", admin)[0]["status"], "Resolvida")
        lancamento = integrar_recebimento_financeiro(recebimento, {"vencimento": (date.today() + timedelta(days=30)).isoformat()}, admin)
        with banco.conectar() as conexao:
            financeiro = conexao.execute("SELECT * FROM fin_lancamentos WHERE id=?", (lancamento,)).fetchone()
        self.assertEqual((financeiro["natureza"], financeiro["origem_modulo"]), ("Conta a pagar", "compras"))

    def test_contrato_aditivo_e_alertas_sao_idempotentes(self):
        admin, _ = self._ambiente(); fornecedor = self._fornecedor(admin, "1")
        contrato = criar_contrato({
            "numero": "CTR-001", "fornecedor_id": fornecedor, "objeto": "Fornecimento recorrente",
            "inicio": date.today().isoformat(), "termino": (date.today() + timedelta(days=10)).isoformat(),
            "valor": "50000,00", "reajuste_indice": "IPCA", "aviso_dias": 30,
        }, admin)
        adicionar_aditivo(contrato, {"numero": "ADT-001", "tipo": "Renovação", "descricao": "Prorrogação negociada", "novo_termino": (date.today() + timedelta(days=20)).isoformat(), "valor_adicional": "1000,00"}, admin)
        gerar_alertas_compras(admin); gerar_alertas_compras(admin)
        alertas = [x for x in listar_secao("alertas", admin) if x["status"] == "Aberto"]
        self.assertEqual(len([x for x in alertas if x["recurso_tipo"] == "cmp_contratos"]), 1)
        self.assertEqual(len(listar_secao("aditivos", admin)), 1)

    def test_analytics_relatorios_e_auditoria_preservam_universo(self):
        admin, pasta = self._ambiente(); self._solicitacao(admin)
        frame = exportar_dataframe_compras(admin)
        self.assertEqual(len(frame), 1)
        analise = analisar_compras(admin)
        self.assertIn("pontos_atencao", analise)
        for formato in ("PDF", "XLSX", "CSV"):
            destino = pasta / f"compras.{formato.lower()}"
            gerar_relatorio_compras("Solicitações", formato, destino, admin)
            self.assertTrue(destino.is_file() and destino.stat().st_size > 100)
        self.assertGreaterEqual(len(listar_secao("auditoria", admin)), 3)

    def test_perfis_granulares_separam_solicitacao_aprovacao_e_auditoria(self):
        admin, _ = self._ambiente()
        solicitante = criar_usuario("Solicitante", "solicitante.compras", "SenhaSolicitante#123", ator=admin, perfil_acesso="compras_solicitante")
        ator = {**solicitante, "_empresa_id": SESSAO.empresa_id, "_filial_id": SESSAO.filial_id}
        self.assertTrue(tem_permissao_compras(ator, "criar_solicitacao"))
        self.assertFalse(tem_permissao_compras(ator, "aprovar_solicitacao"))
        self.assertFalse(tem_permissao_compras(ator, "consultar_auditoria"))


if __name__ == "__main__":
    unittest.main()
