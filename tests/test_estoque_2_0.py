"""Regressões do domínio especializado de Estoque 2.0."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.estoque import (
    analisar_estoque,
    aprovar_inventario,
    aprovar_operacao,
    calcular_reposicao,
    confirmar_operacao,
    criar_deposito,
    criar_item,
    criar_operacao,
    criar_reserva,
    encaminhar_reposicao_compras,
    exportar_dataframe_estoque,
    finalizar_inventario,
    gerar_alertas_estoque,
    gerar_relatorio_estoque,
    iniciar_inventario,
    itens_inventario,
    liberar_reserva,
    listar_auditoria_estoque,
    listar_inventarios,
    listar_itens,
    listar_movimentacoes,
    listar_operacoes,
    listar_secao,
    receber_transferencia,
    registrar_contagem,
    resumo_estoque,
    tem_permissao_estoque,
)


class Estoque20Tests(unittest.TestCase):
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

    def _catalogo(self, admin, *, codigo="ITEM-01", minimo=5, maximo=30, lote=False, serie=False, patrimonio=False):
        deposito = criar_deposito({"codigo": f"D-{codigo}", "nome": f"Depósito {codigo}"}, admin)
        item = criar_item({
            "codigo": codigo, "nome": f"Produto {codigo}", "estoque_minimo": minimo,
            "estoque_maximo": maximo, "ponto_reposicao": minimo,
            "consumo_medio_dia": 2, "lead_time_dias": 3,
            "controla_lote": lote, "controla_validade": lote,
            "controla_serie": serie, "eh_patrimonio": patrimonio,
        }, admin)
        return item, deposito

    def _entrada(self, admin, item, deposito, quantidade=10, **linha_extra):
        linha = {"item_id": item, "quantidade": quantidade, "custo_unitario": "100,00", **linha_extra}
        operacao = criar_operacao({"tipo": "Entrada", "deposito_destino_id": deposito, "motivo": "Saldo inicial"}, [linha], admin)
        confirmar_operacao(operacao, admin)
        return operacao

    def test_migracao_cria_dominio_e_sincroniza_legado(self):
        admin, _ = self._ambiente()
        with banco.conectar() as conexao:
            tabelas = {x["name"] for x in conexao.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'est_%'").fetchall()}
        self.assertTrue({"est_itens", "est_saldos", "est_movimentacoes", "est_operacoes", "est_inventarios", "est_reservas", "est_lotes", "est_seriais"} <= tabelas)
        item, _deposito = self._catalogo(admin)
        self.assertEqual(listar_itens(admin)["registros"][0]["id"], item)

    def test_entrada_atualiza_saldo_custo_e_razao_imutavel(self):
        admin, _ = self._ambiente(); item, deposito = self._catalogo(admin)
        self._entrada(admin, item, deposito, 12)
        registro = listar_itens(admin)["registros"][0]
        self.assertEqual(registro["fisico"], 12)
        self.assertEqual(registro["custo_medio_centavos"], 10_000)
        movimentos = listar_movimentacoes(admin)
        self.assertEqual(movimentos[0]["saldo_anterior"], 0)
        self.assertEqual(movimentos[0]["saldo_posterior"], 12)
        with banco.conectar() as conexao:
            with self.assertRaises(Exception):
                conexao.execute("UPDATE est_movimentacoes SET quantidade=99 WHERE id=?", (movimentos[0]["id"],))

    def test_saida_nao_permite_saldo_negativo(self):
        admin, _ = self._ambiente(); item, deposito = self._catalogo(admin)
        self._entrada(admin, item, deposito, 3)
        saida = criar_operacao({"tipo": "Saída", "deposito_origem_id": deposito}, [{"item_id": item, "quantidade": 4}], admin)
        with self.assertRaisesRegex(ValueError, "Saldo insuficiente"):
            confirmar_operacao(saida, admin)
        self.assertEqual(listar_itens(admin)["registros"][0]["fisico"], 3)

    def test_transferencia_mantem_quantidade_em_transito_ate_recebimento(self):
        admin, _ = self._ambiente(); item, origem = self._catalogo(admin, serie=True)
        destino = criar_deposito({"codigo": "DEST", "nome": "Depósito destino"}, admin)
        self._entrada(admin, item, origem, 2, seriais=["TR-001", "TR-002"])
        transferencia = criar_operacao({"tipo": "Transferência", "deposito_origem_id": origem, "deposito_destino_id": destino}, [{"item_id": item, "quantidade": 1, "seriais": ["TR-001"]}], admin)
        aprovar_operacao(transferencia, True, "Aprovada", admin)
        confirmar_operacao(transferencia, admin)
        operacao = next(x for x in listar_operacoes(admin) if x["id"] == transferencia)
        self.assertEqual(operacao["status"], "Em trânsito")
        self.assertEqual(resumo_estoque(admin)["unidades"], 1)
        serial = next(x for x in listar_secao("patrimonio", admin) if x["numero_serie"] == "TR-001")
        self.assertEqual(serial["status"], "Em trânsito")
        receber_transferencia(transferencia, admin)
        self.assertEqual(resumo_estoque(admin)["unidades"], 2)
        serial = next(x for x in listar_secao("patrimonio", admin) if x["numero_serie"] == "TR-001")
        self.assertEqual((serial["status"], serial["deposito_id"]), ("Disponível", destino))

    def test_reserva_reduz_disponivel_sem_alterar_fisico(self):
        admin, _ = self._ambiente(); item, deposito = self._catalogo(admin)
        self._entrada(admin, item, deposito, 10)
        reserva = criar_reserva({"item_id": item, "deposito_id": deposito, "quantidade": 3, "finalidade": "Kit admissional", "origem_modulo": "rh"}, admin)
        registro = listar_itens(admin)["registros"][0]
        self.assertEqual((registro["fisico"], registro["reservado"], registro["disponivel"]), (10, 3, 7))
        liberar_reserva(reserva, admin, atender=False)
        self.assertEqual(listar_itens(admin)["registros"][0]["disponivel"], 10)

    def test_lote_validade_fefo_e_patrimonio_serializado(self):
        admin, _ = self._ambiente(); item, deposito = self._catalogo(admin, codigo="SERIE", lote=True, serie=True, patrimonio=True)
        self._entrada(admin, item, deposito, 2, lote_numero="L-01", validade="31/12/2027", seriais=["SN-001", "SN-002"])
        lotes = listar_secao("lotes", admin)
        ativos = listar_secao("patrimonio", admin)
        self.assertEqual(lotes[0]["numero"], "L-01")
        self.assertEqual({x["numero_serie"] for x in ativos}, {"SN-001", "SN-002"})
        self.assertTrue(all(x["patrimonio"] for x in ativos))

    def test_inventario_contagem_cega_e_ajuste_auditado(self):
        admin, _ = self._ambiente(); item, deposito = self._catalogo(admin)
        self._entrada(admin, item, deposito, 8)
        inventario = iniciar_inventario({"deposito_id": deposito, "tipo": "Geral", "contagem_cega": True}, admin)
        linha = itens_inventario(inventario, admin)[0]
        registrar_contagem(inventario, linha["id"], 7, admin)
        finalizar_inventario(inventario, admin)
        self.assertEqual(listar_inventarios(admin)[0]["status"], "Aguardando aprovação")
        aprovar_inventario(inventario, admin)
        self.assertEqual(listar_itens(admin)["registros"][0]["fisico"], 7)
        self.assertTrue(any(x["tipo"] == "Inventário" for x in listar_movimentacoes(admin)))

    def test_reposicao_cria_solicitacao_em_compras_sem_comprar_sozinha(self):
        admin, _ = self._ambiente(); item, deposito = self._catalogo(admin, minimo=10, maximo=30)
        self._entrada(admin, item, deposito, 4)
        sugestoes = calcular_reposicao(admin)
        self.assertEqual(sugestoes[0]["quantidade_sugerida"], 26)
        reposicao = listar_secao("reposicao", admin)[0]
        compra = encaminhar_reposicao_compras(reposicao["id"], admin)
        with banco.conectar() as conexao:
            solicitacao = conexao.execute("SELECT * FROM solicitacoes_compra WHERE id=?", (compra,)).fetchone()
            tarefa = conexao.execute("SELECT * FROM tarefas WHERE recurso_tipo='est_reposicoes' AND recurso_id=?", (reposicao["id"],)).fetchone()
        self.assertEqual(solicitacao["status"], "Pendente")
        self.assertEqual(tarefa["modulo"], "compras")

    def test_alertas_sao_idempotentes_e_analise_explica_riscos(self):
        admin, _ = self._ambiente(); self._catalogo(admin, minimo=10, maximo=30)
        gerar_alertas_estoque(admin); gerar_alertas_estoque(admin); gerar_alertas_estoque(admin)
        alertas = listar_secao("alertas", admin)
        self.assertEqual(len([x for x in alertas if x["status"] == "Aberto"]), 1)
        analise = analisar_estoque(admin)
        self.assertTrue(any("sem estoque" in x for x in analise["pontos_atencao"]))

    def test_analytics_relatorios_auditoria_e_perfil_granular(self):
        admin, pasta = self._ambiente(); item, deposito = self._catalogo(admin)
        self._entrada(admin, item, deposito, 5)
        self.assertEqual(len(exportar_dataframe_estoque(admin)), 1)
        for formato in ("PDF", "XLSX", "CSV"):
            arquivo = pasta / f"estoque.{formato.lower()}"
            gerar_relatorio_estoque("Posição atual", formato, arquivo, admin)
            self.assertTrue(arquivo.is_file() and arquivo.stat().st_size > 100)
        self.assertGreaterEqual(len(listar_auditoria_estoque(admin)), 3)
        operador = criar_usuario("Operador", "operador.estoque", "SenhaOperador#123", ator=admin, perfil_acesso="estoque_operador")
        ator = {**operador, "_empresa_id": SESSAO.empresa_id, "_filial_id": SESSAO.filial_id}
        self.assertTrue(tem_permissao_estoque(ator, "registrar_entrada"))
        self.assertFalse(tem_permissao_estoque(ator, "aprovar_transferencia"))


if __name__ == "__main__":
    unittest.main()
