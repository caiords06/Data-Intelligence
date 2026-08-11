"""Contratos funcionais do workspace Financeiro 2.0."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto, salvar_permissoes_usuario
from enterprise.financeiro import (
    agendar_relatorio,
    analisar_financeiro,
    anexar_documento,
    cancelar_lancamento,
    conciliar_item,
    contabilizar_lancamento,
    criar_conta,
    criar_lancamento,
    decidir_aprovacao,
    estornar_lancamento,
    exportar_dataframe_financeiro,
    gerar_recorrencias_pendentes,
    gerar_relatorio_financeiro,
    importar_extrato,
    listar_aprovacoes_financeiras,
    listar_auditoria_financeira,
    listar_catalogos,
    listar_conciliacoes,
    listar_contas_com_saldo,
    listar_lancamentos,
    listar_recorrencias,
    listar_relatorios_agendados,
    obter_lancamento,
    registrar_baixa,
    salvar_orcamento,
    salvar_permissao_acao,
    submeter_aprovacao,
    tem_permissao_financeira,
)


class FinanceiroDepartamentalTests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
        patch_db.start()
        patch_storage.start()
        self.addCleanup(patch_db.stop)
        self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        obter_contexto()
        return admin, pasta

    def _contas_e_classificacao(self, admin):
        origem = criar_conta(
            {"nome": "Itaú", "saldo_inicial": "10.000,00", "data_saldo_inicial": "10/08/2026"},
            admin,
        )
        destino = criar_conta(
            {"nome": "Reserva", "saldo_inicial": "0", "data_saldo_inicial": "10/08/2026"},
            admin,
        )
        catalogos = listar_catalogos(admin)
        plano_despesa = next(item["id"] for item in catalogos["plano_contas"] if item["codigo"] == "4.3")
        categoria_despesa = next(item["id"] for item in catalogos["categorias"] if item["nome"] == "Tecnologia")
        return origem, destino, plano_despesa, categoria_despesa

    def test_ciclo_aprovacao_baixa_contabilizacao_e_auditoria(self):
        admin, pasta = self._ambiente()
        conta, _, plano, categoria = self._contas_e_classificacao(admin)
        lancamento_id = criar_lancamento(
            {
                "natureza": "Conta a pagar",
                "descricao": "Infraestrutura em nuvem",
                "valor": "12.000,00",
                "competencia": "10/08/2026",
                "vencimento": "20/08/2026",
                "conta_id": conta,
                "plano_conta_id": plano,
                "categoria_id": categoria,
            },
            admin,
        )[0]
        etapas = listar_aprovacoes_financeiras(admin, status="Pendente")
        self.assertEqual(len(etapas), 2)
        decidir_aprovacao(lancamento_id, "Aprovado", "Diretoria aprovou", admin)
        decidir_aprovacao(lancamento_id, "Aprovado", "Financeiro conferiu", admin)
        registrar_baixa(
            lancamento_id,
            {"valor": "7.000", "data": "20/08/2026", "conta_id": conta},
            admin,
        )
        self.assertEqual(obter_lancamento(lancamento_id, admin)["status"], "Parcial")
        registrar_baixa(
            lancamento_id,
            {"valor": "5.000", "data": "21/08/2026", "conta_id": conta},
            admin,
        )
        contabilizar_lancamento(lancamento_id, admin)
        registro = obter_lancamento(lancamento_id, admin)
        self.assertEqual(registro["status"], "Pago")
        self.assertEqual(registro["valor_liquidado_centavos"], 1_200_000)
        self.assertTrue(registro["contabilizado"])
        anexo = pasta / "nota.txt"
        anexo.write_text("documento fiscal", encoding="utf-8")
        anexar_documento(lancamento_id, anexo, admin)
        self.assertGreaterEqual(len(listar_auditoria_financeira(admin)), 7)
        with self.assertRaises(ValueError):
            cancelar_lancamento(lancamento_id, "cancelamento indevido", admin)
        estornar_lancamento(lancamento_id, "Documento pago em duplicidade", admin)
        self.assertEqual(obter_lancamento(lancamento_id, admin)["status"], "Estornado")
        saldo = next(
            item["saldo_centavos"]
            for item in listar_contas_com_saldo(admin)
            if item["id"] == conta
        )
        self.assertEqual(saldo, 1_000_000)

    def test_transferencia_nao_altera_resultado(self):
        admin, _ = self._ambiente()
        origem, destino, _, _ = self._contas_e_classificacao(admin)
        criar_lancamento(
            {
                "natureza": "Transferência",
                "descricao": "Reserva de liquidez",
                "valor": "2.500",
                "competencia": "10/08/2026",
                "conta_id": origem,
                "conta_destino_id": destino,
            },
            admin,
        )
        contas = {item["nome"]: item["saldo_centavos"] for item in listar_contas_com_saldo(admin)}
        self.assertEqual(contas["Itaú"], 750_000)
        self.assertEqual(contas["Reserva"], 250_000)
        analise = analisar_financeiro(admin)["resumo"]
        self.assertEqual(analise["receitas_centavos"], 0)
        self.assertEqual(analise["despesas_centavos"], 0)

    def test_extrato_sugestao_conciliacao_e_relatorios(self):
        admin, pasta = self._ambiente()
        conta, _, plano, categoria = self._contas_e_classificacao(admin)
        lancamento_id = criar_lancamento(
            {
                "natureza": "Despesa",
                "descricao": "Amazon AWS",
                "valor": "1.250,00",
                "competencia": "10/08/2026",
                "vencimento": "10/08/2026",
                "status": "Aprovado",
                "conta_id": conta,
                "plano_conta_id": plano,
                "categoria_id": categoria,
            },
            admin,
        )[0]
        extrato = pasta / "extrato.csv"
        pd.DataFrame(
            [{"Data": "10/08/2026", "Descrição": "AWS AMAZON", "Valor": -1250.0, "ID": "mov-001"}]
        ).to_csv(extrato, index=False)
        resultado = importar_extrato(conta, extrato, admin)
        self.assertEqual(resultado["itens"], 1)
        item = listar_conciliacoes(admin)[0]
        self.assertEqual(item["lancamento_id"], lancamento_id)
        conciliar_item(item["id"], lancamento_id, admin)
        self.assertTrue(obter_lancamento(lancamento_id, admin)["conciliado"])
        for formato, sufixo in (("CSV", ".csv"), ("Excel", ".xlsx"), ("HTML", ".html"), ("PDF", ".pdf")):
            arquivo = gerar_relatorio_financeiro("DRE", formato, admin)
            self.assertTrue(arquivo.is_file())
            self.assertEqual(arquivo.suffix, sufixo)

    def test_orcamento_recorrencia_agendamento_e_permissoes_granulares(self):
        admin, _ = self._ambiente()
        conta, _, plano, categoria = self._contas_e_classificacao(admin)
        salvar_orcamento(
            {"ano": 2026, "mes": 8, "categoria_id": categoria, "planejado": "20.000", "limite_alerta_percentual": 85},
            admin,
        )
        criar_lancamento(
            {
                "natureza": "Conta a pagar", "descricao": "Assinatura mensal",
                "valor": "500", "competencia": "01/07/2026", "vencimento": "01/07/2026",
                "conta_id": conta, "plano_conta_id": plano, "categoria_id": categoria,
                "recorrente": True, "periodicidade": "Mensal", "recorrencia_fim": "01/12/2026",
            },
            admin,
        )
        self.assertEqual(len(listar_recorrencias(admin)), 1)
        gerados = gerar_recorrencias_pendentes(admin, ate="10/08/2026")
        self.assertEqual(len(gerados), 1)
        agendar_relatorio(
            {"nome": "DRE mensal", "tipo": "DRE", "formato": "PDF", "frequencia": "Mensal", "proxima_execucao": "05/09/2026", "destinatarios": "diretoria@empresa.com"},
            admin,
        )
        self.assertEqual(len(listar_relatorios_agendados(admin)), 1)

        usuario = criar_usuario("Analista financeiro", "financeiro", "SenhaAnalista#123", ator=admin)
        salvar_permissoes_usuario(
            usuario["id"],
            {"financeiro": {"ler": True, "escrever": True, "aprovar": False}},
            admin,
        )
        self.assertFalse(tem_permissao_financeira(usuario, "aprovar"))
        salvar_permissao_acao(usuario["id"], "conciliar", False, admin)
        self.assertFalse(tem_permissao_financeira(usuario, "conciliar"))

    def test_analytics_recebe_universo_do_novo_livro(self):
        admin, _ = self._ambiente()
        conta, _, plano, categoria = self._contas_e_classificacao(admin)
        for indice in range(25):
            criar_lancamento(
                {
                    "natureza": "Despesa", "descricao": f"Despesa {indice}",
                    "valor": "10", "competencia": "10/08/2026", "status": "Aprovado",
                    "conta_id": conta, "plano_conta_id": plano, "categoria_id": categoria,
                },
                admin,
            )
        dataframe = exportar_dataframe_financeiro(admin)
        self.assertEqual(len(dataframe), 25)
        self.assertIn("centro_custo", dataframe.columns)
        self.assertIn("grupo_dre", dataframe.columns)
        filtrados = listar_lancamentos(
            admin, naturezas=("Despesa", "Conta a pagar"), tamanho=200,
        )
        self.assertEqual(filtrados["total"], 25)


if __name__ == "__main__":
    unittest.main()
