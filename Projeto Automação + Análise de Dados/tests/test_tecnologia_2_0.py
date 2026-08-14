"""Regressões do domínio especializado de Tecnologia e Serviços 2.0."""

from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.tecnologia import (
    adicionar_comentario,
    analisar_tecnologia,
    atribuir_licenca,
    atualizar_chamado,
    autorizar_segmento_rede,
    concluir_manutencao,
    criar_ativo,
    criar_chamado,
    criar_incidente_seguranca,
    criar_licenca,
    criar_monitor,
    criar_mudanca,
    criar_segmento_rede,
    criar_sistema,
    decidir_mudanca,
    encerrar_acesso_remoto,
    exportar_dataframe_tecnologia,
    gerar_alertas_tecnologia,
    gerar_relatorio_tecnologia,
    iniciar_manutencao,
    listar_secao,
    registrar_dispositivo_descoberto,
    registrar_evento_monitoramento,
    registrar_heartbeat,
    resumo_tecnologia,
    salvar_permissao_acao,
    solicitar_acesso_remoto,
    tem_permissao_tecnologia,
)


class Tecnologia20Tests(unittest.TestCase):
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

    def _ativo(self, admin, patrimonio="TI-001", *, remoto=True):
        return criar_ativo({
            "patrimonio": patrimonio, "nome": "Notebook corporativo", "tipo": "Notebook",
            "hostname": patrimonio, "endereco_ip": "10.0.0.10", "memoria_gb": 16,
            "armazenamento_gb": 512, "criticidade": "Alta", "status": "Em uso",
            "remote_provider": "AnyDesk" if remoto else "", "remote_id": "123456789" if remoto else "",
        }, admin)

    def test_migracao_cria_dominio_e_historico_imutavel(self):
        admin, _ = self._ambiente()
        ativo = self._ativo(admin)
        with banco.conectar() as conexao:
            tabelas = {x["name"] for x in conexao.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ti_%'")}
            migracao = conexao.execute("SELECT 1 FROM migracoes_sistema WHERE chave='enterprise_010_tecnologia_departamental'").fetchone()
            historico = conexao.execute("SELECT id FROM ti_historico WHERE recurso_tipo='ti_ativos' AND recurso_id=?", (ativo,)).fetchone()
            self.assertEqual(conexao.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(conexao.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertGreaterEqual(len(tabelas), 24)
            self.assertIn("ti_agentes", tabelas)
            self.assertIn("ti_agente_nonces", tabelas)
            self.assertIsNotNone(migracao)
            with self.assertRaises(Exception):
                conexao.execute("DELETE FROM ti_historico WHERE id=?", (historico["id"],))

    def test_service_desk_aplica_sla_fluxo_e_comentarios(self):
        admin, _ = self._ambiente(); ativo = self._ativo(admin)
        chamado = criar_chamado({
            "titulo": "ERP não inicializa", "descricao": "Erro ao abrir o sistema de produção.",
            "categoria": "Sistema", "prioridade": "Crítica", "impacto": "Departamento",
            "urgencia": "Imediata", "ativo_id": ativo,
        }, admin)
        adicionar_comentario(chamado, "Diagnóstico iniciado pela equipe de suporte.", admin, interno=True)
        atualizar_chamado(chamado, {"status": "Em atendimento", "tecnico_id": admin["id"]}, admin)
        atualizar_chamado(chamado, {"status": "Resolvido", "solucao": "Serviço reiniciado e validado."}, admin)
        registro = listar_secao("chamados", admin)[0]
        self.assertEqual((registro["sla_atendimento_minutos"], registro["sla_solucao_minutos"]), (15, 120))
        self.assertEqual(registro["status"], "Resolvido")
        self.assertIsNotNone(registro["primeira_resposta_em"])
        with banco.conectar() as conexao:
            self.assertEqual(conexao.execute("SELECT COUNT(*) FROM ti_chamado_comentarios WHERE chamado_id=?", (chamado,)).fetchone()[0], 1)

    def test_ativo_heartbeat_alerta_manutencao_e_retorno(self):
        admin, _ = self._ambiente(); ativo = self._ativo(admin)
        registrar_heartbeat(ativo, {
            "cpu_percentual": 95, "memoria_percentual": 80, "disco_percentual": 91,
            "espaco_livre_gb": 8, "uptime_segundos": 3600, "latencia_ms": 8,
            "agente_versao": "2.0.0",
        }, admin)
        registro = listar_secao("ativos", admin)[0]
        self.assertEqual(registro["estado_conectividade"], "Com alerta")
        manutencao = iniciar_manutencao(ativo, "SSD com falhas intermitentes", admin, previsao=(date.today() + timedelta(days=3)).isoformat())
        self.assertEqual(listar_secao("ativos", admin)[0]["status"], "Em manutenção")
        concluir_manutencao(manutencao, "SSD substituído e testes concluídos.", admin, custo="450,00")
        self.assertEqual(listar_secao("ativos", admin)[0]["status"], "Disponível")
        self.assertEqual(listar_secao("manutencoes", admin)[0]["custo_centavos"], 45_000)

    def test_rede_exige_segmento_privado_autorizado_e_escopo(self):
        admin, _ = self._ambiente()
        with self.assertRaises(ValueError):
            criar_segmento_rede({"nome": "Internet", "cidr": "8.8.8.0/24"}, admin)
        segmento = criar_segmento_rede({"nome": "Financeiro", "cidr": "10.0.1.0/24", "vlan": "10"}, admin)
        with self.assertRaises(PermissionError):
            registrar_dispositivo_descoberto(segmento, {"endereco_ip": "10.0.1.23"}, admin)
        autorizar_segmento_rede(segmento, "Rede corporativa administrada e aprovada para inventário de ativos.", admin)
        with self.assertRaises(ValueError):
            registrar_dispositivo_descoberto(segmento, {"endereco_ip": "10.0.2.23"}, admin)
        dispositivo = registrar_dispositivo_descoberto(segmento, {
            "endereco_ip": "10.0.1.23", "hostname": "FIN-PC-023", "fabricante": "Dell",
            "status": "Online", "origem": "Agente",
        }, admin)
        self.assertEqual(listar_secao("rede", admin)[0]["id"], dispositivo)
        self.assertEqual(resumo_tecnologia(admin)["desconhecidos"], 1)

    def test_licencas_controlam_capacidade_e_renovacao(self):
        admin, _ = self._ambiente(); ativo = self._ativo(admin)
        licenca = criar_licenca({
            "nome": "Microsoft 365", "quantidade_contratada": 1, "custo": "62,40",
            "periodicidade": "Mensal", "vencimento_em": (date.today() + timedelta(days=10)).isoformat(),
        }, admin)
        atribuir_licenca(licenca, admin, ativo_id=ativo)
        with self.assertRaises(ValueError):
            atribuir_licenca(licenca, admin, identificador="usuario@empresa.test")
        gerar_alertas_tecnologia(admin); gerar_alertas_tecnologia(admin)
        registro = listar_secao("licencas", admin)[0]
        self.assertEqual((registro["quantidade_utilizada"], registro["quantidade_disponivel"]), (1, 0))
        alertas = [x for x in listar_secao("alertas", admin) if x["recurso_tipo"] == "ti_licencas"]
        self.assertEqual(len(alertas), 1)

    def test_sistemas_monitoramento_e_alerta_critico(self):
        admin, _ = self._ambiente(); ativo = self._ativo(admin)
        sistema = criar_sistema({
            "nome": "ERP Corporativo", "ambiente": "Produção", "criticidade": "Crítica",
            "status": "Operacional", "servidor_ativo_id": ativo, "sla_disponibilidade": "99.9",
        }, admin)
        monitor = criar_monitor({
            "nome": "Disponibilidade ERP", "tipo": "Disponibilidade", "sistema_id": sistema,
            "alvo": "https://erp.interno/health", "intervalo_segundos": 60,
        }, admin)
        registrar_evento_monitoramento(monitor, "Indisponível", admin, valor=0, mensagem="Endpoint não respondeu.")
        self.assertEqual(listar_secao("monitoramento", admin)[0]["status"], "Indisponível")
        self.assertTrue(any(x["recurso_tipo"] == "ti_monitores" for x in listar_secao("alertas", admin)))

    def test_mudanca_integra_aprovacao_central_e_auditoria(self):
        admin, _ = self._ambiente()
        mudanca = criar_mudanca({
            "titulo": "Atualizar banco de produção", "descricao": "Atualização de segurança planejada.",
            "risco": "Alto", "impacto": "ERP indisponível por até 20 minutos.",
            "plano_execucao": "Backup, validação e aplicação da atualização.",
            "plano_rollback": "Restaurar snapshot validado e reabrir o serviço.",
            "responsavel_id": admin["id"],
        }, admin)
        registro = listar_secao("mudancas", admin)[0]
        self.assertEqual(registro["aprovacao_status"], "Pendente")
        decidir_mudanca(mudanca, "Aprovar", admin, "Janela e rollback validados.")
        registro = listar_secao("mudancas", admin)[0]
        self.assertEqual((registro["status"], registro["aprovacao_status"]), ("Aprovada", "Aprovado"))
        self.assertTrue(any(x["recurso_tipo"] == "ti_mudancas" for x in listar_secao("auditoria", admin)))

    def test_acesso_remoto_exige_consentimento_e_mantem_trilha(self):
        admin, _ = self._ambiente(); ativo = self._ativo(admin)
        chamado = criar_chamado({
            "titulo": "Suporte remoto autorizado", "descricao": "Usuário solicitou atendimento remoto.",
            "categoria": "Suporte", "prioridade": "Média", "ativo_id": ativo,
        }, admin)
        with self.assertRaises(PermissionError):
            solicitar_acesso_remoto(ativo, "AnyDesk", "Atendimento autorizado pelo chamado.", admin, chamado_id=chamado, consentimento=False)
        sessao = solicitar_acesso_remoto(ativo, "AnyDesk", "Atendimento autorizado pelo chamado.", admin, chamado_id=chamado, consentimento=True)
        self.assertTrue(sessao["destino"].startswith("anydesk:"))
        encerrar_acesso_remoto(sessao["acesso_id"], "Ajuste concluído e validado pelo usuário.", admin)
        acesso = listar_secao("acessos", admin)[0]
        self.assertEqual((acesso["status"], acesso["consentimento_confirmado"]), ("Encerrada", 1))
        self.assertTrue(any(x["acao"] == "acesso_remoto_iniciado" for x in listar_secao("auditoria", admin)))

    def test_seguranca_analytics_dataframe_e_relatorios(self):
        admin, pasta = self._ambiente(); ativo = self._ativo(admin)
        criar_chamado({"titulo": "VPN não conecta", "descricao": "Falha de autenticação.", "categoria": "Acesso", "prioridade": "Alta", "ativo_id": ativo}, admin)
        criar_incidente_seguranca({
            "titulo": "Tentativa de acesso indevido", "tipo": "Acesso indevido", "severidade": "Alta",
            "descricao": "Múltiplas tentativas bloqueadas.", "contencao": "Conta bloqueada e logs preservados.", "ativo_id": ativo,
        }, admin)
        analise = analisar_tecnologia(admin)
        self.assertTrue(analise["pontos_atencao"])
        dataframe = exportar_dataframe_tecnologia(admin)
        self.assertEqual(len(dataframe), 1)
        for formato in ("csv", "json", "html"):
            destino = pasta / f"relatorio.{formato}"
            gerar_relatorio_tecnologia("chamados", formato, destino, admin)
            self.assertTrue(destino.is_file() and destino.stat().st_size > 10)

    def test_permissoes_granulares_restringem_operacao_sensivel(self):
        admin, _ = self._ambiente()
        usuario = criar_usuario("Técnico", "tecnico", "SenhaTecnico#123", ator=admin, perfil_acesso="ti")
        self.assertTrue(tem_permissao_tecnologia(usuario, "acessar_remotamente"))
        salvar_permissao_acao(usuario["id"], "acessar_remotamente", False, admin)
        self.assertFalse(tem_permissao_tecnologia(usuario, "acessar_remotamente"))
        salvar_permissao_acao(usuario["id"], "acessar_remotamente", True, admin)
        self.assertTrue(tem_permissao_tecnologia(usuario, "acessar_remotamente"))


if __name__ == "__main__":
    unittest.main()
