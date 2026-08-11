"""Regressões da remodelação Tecnologia 3.0: suporte público, rede e inventário."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import obter_contexto
from enterprise.organizacao import criar_filial, definir_contexto_empresa
from enterprise.rede_ti import descobrir_hosts
from enterprise.tecnologia import (
    atualizar_dispositivo_rede,
    atualizar_segmento_rede,
    autorizar_segmento_rede,
    criar_ativo,
    criar_chamado,
    criar_segmento_rede,
    descobrir_segmento_rede,
    listar_secao,
    obter_segmento_rede,
    preparar_firewall_segmento,
    registrar_dispositivo_descoberto,
    registrar_snapshot_agente,
    remover_dispositivo_rede,
    remover_segmento_rede,
    revogar_autorizacao_segmento_rede,
    vincular_dispositivo_ativo,
)


class Tecnologia30Tests(unittest.TestCase):
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
        SESSAO.iniciar(admin)
        inicializar_enterprise(); obter_contexto()
        return admin, pasta

    @staticmethod
    def _congelar(ator):
        contexto = obter_contexto()
        return {
            **dict(ator),
            "_empresa_id": contexto["empresa_id"],
            "_filial_id": contexto["filial_id"],
        }

    def test_migracao_011_adiciona_campos_operacionais(self):
        self._ambiente()
        with banco.conectar() as conexao:
            seg = {x["name"] for x in conexao.execute("PRAGMA table_info(ti_segmentos_rede)")}
            dev = {x["name"] for x in conexao.execute("PRAGMA table_info(ti_dispositivos_rede)")}
            ativos = {x["name"] for x in conexao.execute("PRAGMA table_info(ti_ativos)")}
            self.assertTrue({"firewall_status", "firewall_regra", "ultima_varredura_em"} <= seg)
            self.assertTrue({"ativo", "ultimo_ping_ms", "observacao"} <= dev)
            self.assertTrue({"agent_id", "fqdn", "usuario_sessao", "remote_alias", "remote_status"} <= ativos)
            self.assertIsNotNone(conexao.execute(
                "SELECT 1 FROM migracoes_sistema WHERE chave='enterprise_011_tecnologia_operacoes_rede'"
            ).fetchone())

    def test_usuario_sem_ti_abre_e_consulta_somente_os_proprios_chamados(self):
        admin, _ = self._ambiente()
        usuario = criar_usuario("Analista", "analista.portal", "SenhaPortal#123", ator=admin, perfil_acesso="analista")
        outro = criar_usuario("Outro", "outro.portal", "SenhaPortal#123", ator=admin, perfil_acesso="analista")

        # Chamado de outro usuário criado pelo administrador.
        criar_chamado({
            "titulo": "Chamado do outro",
            "descricao": "Registro usado para validar o isolamento do portal.",
            "solicitante_id": outro["id"],
        }, admin)

        SESSAO.iniciar(usuario); obter_contexto()
        ator = self._congelar(usuario)
        chamado_id = criar_chamado({
            "titulo": "Preciso de suporte",
            "descricao": "O usuário autenticado consegue abrir chamado sem permissão operacional de TI.",
            # Tentativas de forjar campos administrativos precisam ser ignoradas.
            "solicitante_id": outro["id"],
            "tecnico_id": admin["id"],
        }, ator)
        meus = listar_secao("meus_chamados", ator)
        self.assertEqual([x["id"] for x in meus], [chamado_id])
        self.assertEqual(meus[0]["solicitante_id"], usuario["id"])
        self.assertIsNone(meus[0]["tecnico_id"])
        with self.assertRaises(PermissionError):
            listar_secao("ativos", ator)

    def test_segmento_tem_crud_autorizacao_e_descoberta_controlada(self):
        admin, _ = self._ambiente()
        segmento = criar_segmento_rede({
            "nome": "Laboratório",
            "cidr": "192.168.77.0/30",
            "gateway": "192.168.77.1",
        }, admin)
        atualizar_segmento_rede(segmento, {
            "nome": "Laboratório TI",
            "cidr": "192.168.77.0/30",
            "gateway": "192.168.77.1",
            "dns": "192.168.77.1",
        }, admin)
        self.assertEqual(obter_segmento_rede(segmento, admin)["nome"], "Laboratório TI")

        with self.assertRaises(PermissionError):
            descobrir_segmento_rede(segmento, admin)
        autorizar_segmento_rede(segmento, "Rede privada do laboratório autorizada para inventário.", admin)

        falso = {
            "cidr": "192.168.77.0/30",
            "total_testados": 2,
            "online": 1,
            "duracao_segundos": 0.01,
            "dispositivos": [{
                "endereco_ip": "192.168.77.1",
                "hostname": "LAB-PC",
                "endereco_mac": "AA:BB:CC:DD:EE:FF",
                "ultimo_ping_ms": 1.2,
                "status": "Online",
                "origem": "Descoberta ICMP",
            }],
        }
        with patch("enterprise.rede_ti.descobrir_hosts", return_value=falso):
            resultado = descobrir_segmento_rede(segmento, admin)
        self.assertEqual(resultado["online"], 1)
        encontrados = listar_secao("rede", admin)
        self.assertEqual(encontrados[0]["hostname"], "LAB-PC")
        self.assertAlmostEqual(encontrados[0]["ultimo_ping_ms"], 1.2)

        revogar_autorizacao_segmento_rede(segmento, admin, "Encerramento do teste")
        self.assertFalse(obter_segmento_rede(segmento, admin)["autorizado"])
        remover_segmento_rede(segmento, admin)
        self.assertEqual(listar_secao("segmentos", admin), [])
        self.assertEqual(listar_secao("rede", admin), [])


    def test_segmento_removido_pode_ser_reativado_sem_erro_unique(self):
        admin, _ = self._ambiente()
        segmento = criar_segmento_rede({
            "nome": "Rede temporária",
            "cidr": "192.168.188.0/24",
            "gateway": "192.168.188.1",
        }, admin)
        autorizar_segmento_rede(
            segmento,
            "Rede temporária autorizada exclusivamente para o teste de reativação.",
            admin,
        )
        remover_segmento_rede(segmento, admin)

        reativado = criar_segmento_rede({
            "nome": "Rede corrigida",
            "cidr": "192.168.188.0/24",
            "gateway": "192.168.188.1",
            "dns": "192.168.188.1",
        }, admin)
        self.assertEqual(reativado, segmento)
        salvo = obter_segmento_rede(reativado, admin)
        self.assertEqual(salvo["nome"], "Rede corrigida")
        self.assertTrue(salvo["ativo"])
        self.assertFalse(salvo["autorizado"])
        self.assertIsNone(salvo["firewall_regra"])

        with self.assertRaisesRegex(ValueError, "já está cadastrado"):
            criar_segmento_rede({
                "nome": "Duplicado",
                "cidr": "192.168.188.0/24",
            }, admin)

    def test_mesmo_cidr_pode_existir_em_filiais_diferentes(self):
        admin, _ = self._ambiente()
        contexto = obter_contexto()
        empresa_id = int(contexto["empresa_id"])
        primeira_filial = int(contexto["filial_id"])

        primeiro = criar_segmento_rede({
            "nome": "LAN Matriz",
            "cidr": "10.222.10.0/24",
        }, admin)
        segunda_filial = criar_filial(
            "Filial laboratório", "LAB2", cidade="Teste", estado="DF", ator=admin
        )
        definir_contexto_empresa(empresa_id, segunda_filial)
        segundo = criar_segmento_rede({
            "nome": "LAN Filial",
            "cidr": "10.222.10.0/24",
        }, admin)
        self.assertNotEqual(primeiro, segundo)

        with banco.conectar() as conexao:
            linhas = conexao.execute(
                "SELECT filial_id,cidr FROM ti_segmentos_rede WHERE empresa_id=? AND cidr=? ORDER BY filial_id",
                (empresa_id, "10.222.10.0/24"),
            ).fetchall()
        self.assertEqual(len(linhas), 2)
        self.assertEqual({int(x["filial_id"]) for x in linhas}, {primeira_filial, segunda_filial})

        definir_contexto_empresa(empresa_id, primeira_filial)

    def test_firewall_e_opcional_e_persiste_estado_sem_desativar_firewall(self):
        admin, _ = self._ambiente()
        segmento = criar_segmento_rede({"nome": "LAN", "cidr": "10.90.0.0/30"}, admin)
        autorizar_segmento_rede(segmento, "Rede de laboratório autorizada pelo administrador.", admin)
        retorno = {
            "aplicado": True,
            "status": "Ativa",
            "regra": "Data Intelligence TI - Descoberta 1",
            "mensagem": "Regra ICMP restrita criada.",
        }
        with patch("enterprise.firewall_ti.preparar_descoberta_local", return_value=retorno):
            recebido = preparar_firewall_segmento(segmento, admin)
        self.assertTrue(recebido["aplicado"])
        salvo = obter_segmento_rede(segmento, admin)
        self.assertEqual(salvo["firewall_status"], "Ativa")
        self.assertTrue(salvo["firewall_regra"])

    def test_dispositivo_pode_ser_identificado_vinculado_e_arquivado(self):
        admin, _ = self._ambiente()
        segmento = criar_segmento_rede({"nome": "LAN", "cidr": "10.91.0.0/24"}, admin)
        autorizar_segmento_rede(segmento, "Segmento de laboratório autorizado para descoberta.", admin)
        dispositivo = registrar_dispositivo_descoberto(segmento, {
            "endereco_ip": "10.91.0.10", "hostname": "DESCONHECIDO", "status": "Online"
        }, admin)
        atualizar_dispositivo_rede(dispositivo, {
            "hostname": "FIN-PC-01", "fabricante": "Dell", "tipo_estimado": "Desktop", "observacao": "Financeiro"
        }, admin)
        ativo = criar_ativo({
            "patrimonio": "TI-FIN-001", "nome": "Desktop Financeiro", "tipo": "Desktop",
            "status": "Em uso", "criticidade": "Alta"
        }, admin)
        vincular_dispositivo_ativo(dispositivo, ativo, admin)
        registro = listar_secao("rede", admin)[0]
        self.assertEqual(registro["ativo_id"], ativo)
        self.assertEqual(registro["patrimonio"], "TI-FIN-001")
        remover_dispositivo_rede(dispositivo, admin)
        self.assertEqual(listar_secao("rede", admin), [])

    def test_snapshot_do_agente_atualiza_inventario_telemetria_e_anydesk(self):
        admin, _ = self._ambiente()
        ativo = criar_ativo({
            "patrimonio": "TI-AG-001", "nome": "Notebook gerenciado", "tipo": "Notebook",
            "status": "Em uso", "criticidade": "Alta"
        }, admin)
        payload = {
            "agent_id": "agent-uuid-001",
            "agente_versao": "3.0.0",
            "patrimonio": "TI-AG-001",
            "dispositivo": {
                "hostname": "NOTE-FIN-01", "fqdn": "NOTE-FIN-01.empresa.local",
                "sistema_operacional": "Windows", "versao_sistema": "Windows 11 Pro 24H2",
                "arquitetura": "AMD64", "processador": "CPU Teste", "executado_como": "maria",
                "enderecos_ip": ["10.0.0.44"], "enderecos_mac": ["00:11:22:33:44:55"],
                "memoria_total_gb": 16, "armazenamento_total_gb": 512,
            },
            "metricas": {
                "cpu_percentual": 22, "memoria_percentual": 58, "disco_percentual": 61,
                "espaco_livre_gb": 180, "uptime_segundos": 3600, "latencia_ms": 5,
            },
            "acesso_remoto": {
                "provedor": "AnyDesk", "identificador": "123456789", "alias": "note-fin@ad",
                "status": "online", "versao": "9.0",
            },
        }
        self.assertEqual(registrar_snapshot_agente(payload, admin), ativo)
        registro = listar_secao("ativos", admin)[0]
        self.assertEqual(registro["agent_id"], "agent-uuid-001")
        self.assertEqual(registro["usuario_sessao"], "maria")
        self.assertEqual(registro["remote_provider"], "AnyDesk")
        self.assertEqual(registro["remote_id"], "123456789")
        self.assertEqual(registro["estado_conectividade"], "Online")
        with banco.conectar() as conexao:
            self.assertEqual(conexao.execute("SELECT COUNT(*) FROM ti_telemetria WHERE ativo_id=?", (ativo,)).fetchone()[0], 1)

    def test_scanner_recusa_redes_publicas_e_segmentos_grandes(self):
        with self.assertRaises(ValueError):
            descobrir_hosts("8.8.8.0/30")
        with self.assertRaises(ValueError):
            descobrir_hosts("10.0.0.0/16")


if __name__ == "__main__":
    unittest.main()
