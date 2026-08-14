"""Regressões V10.2.0 — estabilidade, Server First e instalação Windows."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]


class EstabilidadeV1011Tests(unittest.TestCase):
    def test_node_json_aceita_utf8_bom(self):
        from core.nodo import carregar_config_nodo
        with tempfile.TemporaryDirectory() as tmp:
            caminho=Path(tmp)/"node.json"
            caminho.write_bytes(
                b"\xef\xbb\xbf" + json.dumps({
                    "papel":"central",
                    "servidor_url":"http://127.0.0.1:8770",
                    "permitir_http_privado":True,
                }).encode("utf-8")
            )
            with patch.dict(os.environ, {"DATA_INTELLIGENCE_NODE_CONFIG":str(caminho)}, clear=False):
                cfg=carregar_config_nodo()
            self.assertEqual(cfg.papel,"central")
            self.assertEqual(cfg.servidor_url,"http://127.0.0.1:8770")

    def test_executavel_sem_node_json_falha_fechado(self):
        from core.nodo import carregar_config_nodo
        with tempfile.TemporaryDirectory() as tmp:
            caminho=Path(tmp)/"node.json"
            env={
                "DATA_INTELLIGENCE_NODE_CONFIG":str(caminho),
                "DATA_INTELLIGENCE_NODE_ROLE":"",
                "DATA_INTELLIGENCE_SERVER_URL":"",
                "DATA_INTELLIGENCE_ALLOW_STANDALONE":"",
            }
            with patch.dict(os.environ,env,clear=False), patch("core.nodo.executando_empacotado",return_value=True):
                with self.assertRaisesRegex(ValueError,"Configuração do nó ausente"):
                    carregar_config_nodo()

    def test_tarefa_servidor_preserva_caminho_com_espacos(self):
        from servidor_corporativo.windows import _comando_tarefa
        with tempfile.TemporaryDirectory(prefix="Program Files ") as tmp:
            exe=Path(tmp)/"Data Intelligence"/"Server"/"DataIntelligenceServer.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"x")
            comando=_comando_tarefa(exe)
            self.assertEqual(comando,f'"{exe.resolve()}" run')

    def test_registro_de_tarefas_separa_executavel_dos_argumentos(self):
        texto=(RAIZ/"core/windows_tasks.py").read_text(encoding="utf-8")
        self.assertIn("New-ScheduledTaskAction",texto)
        self.assertIn("$env:DI_TASK_EXE",texto)
        self.assertIn("$env:DI_TASK_ARGS",texto)
        self.assertNotIn('"/TR"',texto)
        servidor=(RAIZ/"servidor_corporativo/windows.py").read_text(encoding="utf-8")
        agente=(RAIZ/"agente_ti/windows.py").read_text(encoding="utf-8")
        self.assertIn("registrar_tarefa_boot_system",servidor)
        self.assertIn("registrar_tarefa_boot_system",agente)

    def test_instalador_nao_usa_cmd_para_registrar_servidor(self):
        texto=(RAIZ/"installer/DataIntelligenceSetup.iss").read_text(encoding="utf-8-sig")
        self.assertIn("install-task --executable",texto)
        self.assertIn("wait-ready --timeout 45",texto)
        self.assertNotIn("schtasks /Create /TN DataIntelligenceCorporateServer",texto)
        self.assertNotIn("ExpandConstant('{cmd}')",texto)
        self.assertIn("{sys}\\netsh.exe",texto)
        pos_bloco=texto.index("if CurStep = ssPostInstall")
        trecho=texto[pos_bloco:pos_bloco+600]
        self.assertLess(trecho.index("WriteNodeConfig();"),trecho.index("ConfigureServer();"))
        self.assertIn("SaveStringsToUTF8FileWithoutBOM",texto)
        self.assertIn("function PrepareToInstall",texto)
        self.assertIn("/End /TN DataIntelligenceCorporateServer",texto)
        self.assertIn("RemoveServerTaskBestEffort",texto)
        self.assertIn("RemoveAgentTaskBestEffort",texto)
        self.assertIn("o primeiro heartbeat falhou",texto)

    def test_backup_agendado_da_central_nao_faz_upload_duplo_do_cache(self):
        texto=(RAIZ/"main.py").read_text(encoding="utf-8")
        inicio=texto.index("def sincronizar_backup_servidor")
        trecho=texto[inicio:inicio+1800]
        self.assertIn("criar_backup(ator)",trecho)
        self.assertNotIn("enviar_backup",trecho)
        self.assertNotIn('resultado["arquivo"]',trecho)

    def test_build_limpa_artefatos_automaticamente(self):
        texto=(RAIZ/"scripts/build_distribuicao_windows.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('@("build", "dist", "release")',texto)
        self.assertIn('Remove-Item -LiteralPath $Alvo -Recurse -Force',texto)

    def test_crud_organizacao_e_permissoes_estao_no_rpc(self):
        from core.rpc_central import RPC_ALLOWLIST
        self.assertTrue({
            "listar_empresas","listar_filiais","listar_departamentos","listar_centros_custo",
            "criar_empresa","criar_filial","criar_departamento","criar_centro_custo",
        }.issubset(RPC_ALLOWLIST["enterprise.organizacao"]))
        self.assertTrue({
            "obter_permissoes_usuario","salvar_permissoes_usuario","aplicar_perfil_padrao_usuario",
        }.issubset(RPC_ALLOWLIST["enterprise.contexto"]))
        self.assertIn("arquivar_documento", RPC_ALLOWLIST["enterprise.ferramentas"])

    def test_fachadas_departamentais_nao_escapam_da_politica_rpc(self):
        import ast
        from core.rpc_central import RPC_ALLOWLIST, RPC_BLOQUEADAS_REMOTO
        problemas=[]
        for caminho in (RAIZ/"services/departamentos").glob("*.py"):
            arvore=ast.parse(caminho.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                if not isinstance(no,ast.ImportFrom) or not no.module or not no.module.startswith("enterprise."):
                    continue
                cobertas=RPC_ALLOWLIST.get(no.module,set()) | RPC_BLOQUEADAS_REMOTO.get(no.module,set())
                for alias in no.names:
                    # Catálogos/constantes são somente leitura e não fazem I/O.
                    if alias.name.isupper():
                        continue
                    if alias.name not in cobertas:
                        problemas.append(f"{caminho.name}:{no.module}.{alias.name}")
        self.assertEqual(problemas,[])

    def test_interface_nao_importa_auth_banco_diretamente(self):
        problemas=[]
        for p in (RAIZ/"interface").rglob("*.py"):
            texto=p.read_text(encoding="utf-8")
            if "from auth.banco" in texto or "import auth.banco" in texto:
                problemas.append(p.relative_to(RAIZ).as_posix())
        self.assertEqual(problemas,[])

    def test_segredo_postgresql_tem_acl_de_maquina(self):
        texto=(RAIZ/"core/segredos.py").read_text(encoding="utf-8")
        self.assertIn("CRYPTPROTECT_LOCAL_MACHINE",texto)
        self.assertIn("icacls.exe",texto)
        self.assertIn("*S-1-5-18",texto)
        self.assertIn("*S-1-5-32-544",texto)

    def test_json_operacional_tolerante_a_bom(self):
        arquivos=[
            "core/nodo.py","agente_ti/config.py",
            "agente_ti/cli.py","agente_ti/runtime.py","servidor_ti/config.py",
            "servidor_corporativo/config.py","servidor_corporativo/__main__.py",
        ]
        for relativo in arquivos:
            texto=(RAIZ/relativo).read_text(encoding="utf-8")
            self.assertIn("utf-8-sig",texto,relativo)

    def test_adapter_postgresql_cobre_busca_like_e_offsets_de_data_genericos(self):
        from enterprise.postgresql.adapter import traduzir_sql
        busca=traduzir_sql("SELECT * FROM itens WHERE nome LIKE ?")
        self.assertIn("ILIKE %s",busca)
        data=traduzir_sql("SELECT date('now','-17 day') limite")
        self.assertNotIn("date('now'",data.lower())
        self.assertIn("-17 days",data)
        instante=traduzir_sql("SELECT datetime('now','-15 minute') limite")
        self.assertNotIn("datetime('now'",instante.lower())
        self.assertIn("-15 minutes",instante)

    def test_lastrowid_postgresql_nao_depende_de_lastval(self):
        texto=(RAIZ/"enterprise/postgresql/adapter.py").read_text(encoding="utf-8")
        bloco=texto[texto.index("class CursorCompat"):texto.index("class ConexaoCompat")]
        self.assertNotIn('"SELECT LASTVAL()"',bloco)
        self.assertIn("pg_get_serial_sequence",bloco)
        self.assertIn("currval",bloco)

    def test_usuario_criado_no_servidor_consegue_login_remoto_e_recebe_permissoes(self):
        """Reproduz o fluxo real Central -> Servidor -> novo Cliente."""
        from auth import banco
        from auth.autenticacao import criar_admin_inicial
        from auth.sessao import SESSAO
        from enterprise.banco import inicializar_enterprise
        from enterprise.contexto import obter_contexto
        from servidor_corporativo.app import CorporateRequestHandler, CorporateServer
        from servidor_corporativo.config import ConfigServidor
        from servidor_corporativo import sessoes as sessoes_servidor

        def requisitar(base, path, *, metodo="GET", dados=None, token=None):
            corpo=None
            headers={"Accept":"application/json"}
            if dados is not None:
                corpo=json.dumps(dados).encode("utf-8")
                headers["Content-Type"]="application/json"
            if token:
                headers["Authorization"]=f"Bearer {token}"
            req=urllib.request.Request(base+path,data=corpo,headers=headers,method=metodo)
            with urllib.request.urlopen(req,timeout=5) as resp:
                return resp.status,json.loads(resp.read().decode("utf-8-sig"))

        with tempfile.TemporaryDirectory() as tmp:
            pasta=Path(tmp)
            with patch.object(banco,"DB_PATH",pasta/"server.db"), patch.object(banco,"STORAGE_DIR",pasta/"storage"):
                SESSAO.encerrar(); sessoes_servidor._SESSOES.clear()
                banco.inicializar_banco()
                admin=criar_admin_inicial("Administrador","admin","SenhaAdmin#123",email_corporativo="admin@empresa.local")
                SESSAO.iniciar(admin)
                inicializar_enterprise(); obter_contexto()
                servidor=CorporateServer(("127.0.0.1",0),CorporateRequestHandler,ConfigServidor(host="127.0.0.1",porta=8770))
                thread=threading.Thread(target=servidor.serve_forever,daemon=True); thread.start()
                try:
                    base=f"http://127.0.0.1:{servidor.server_address[1]}"
                    status,login_admin=requisitar(base,"/api/v1/auth/login",metodo="POST",dados={"usuario":"admin","senha":"SenhaAdmin#123"})
                    self.assertEqual(status,200)
                    token=login_admin["token"]
                    status,criado=requisitar(base,"/api/v1/users",metodo="POST",token=token,dados={
                        "nome":"Cliente V1011","usuario":"cliente.v1011","senha":"Cliente#12345",
                        "perfil":"usuario","perfil_acesso":"analista","email_corporativo":"cliente.v1011@empresa.local",
                    })
                    self.assertEqual(status,201)
                    uid=int(criado["id"])

                    # Aplica perfil pelo mesmo RPC usado pela Central conectada.
                    status,_=requisitar(base,"/api/v1/rpc",metodo="POST",token=token,dados={
                        "modulo":"enterprise.contexto","funcao":"aplicar_perfil_padrao_usuario",
                        "args":[uid,"analista",admin],"kwargs":{},
                    })
                    self.assertEqual(status,200)

                    status,login_cliente=requisitar(base,"/api/v1/auth/login",metodo="POST",dados={
                        "usuario":"cliente.v1011","senha":"Cliente#12345",
                    })
                    self.assertEqual(status,200)
                    self.assertEqual(login_cliente["usuario"]["usuario"],"cliente.v1011")
                    self.assertEqual(login_cliente["usuario"]["perfil_acesso"],"analista")
                    self.assertTrue(login_cliente.get("empresa"))
                    self.assertTrue(login_cliente.get("permissoes"))

                    with banco.conectar() as con:
                        row=con.execute("SELECT usuario,ativo FROM usuarios WHERE id=?",(uid,)).fetchone()
                        vinculo=con.execute("SELECT empresa_id FROM usuarios_empresas WHERE usuario_id=? AND ativo=1",(uid,)).fetchone()
                    self.assertEqual(row["usuario"],"cliente.v1011")
                    self.assertTrue(bool(row["ativo"]))
                    self.assertIsNotNone(vinculo)
                finally:
                    servidor.shutdown(); servidor.server_close(); thread.join(timeout=3)
                    SESSAO.encerrar(); sessoes_servidor._SESSOES.clear()

    def test_scripts_de_estacao_gravam_sem_bom_e_validam_ready(self):
        for relativo in ("scripts/Configurar-Estacao-Central.ps1","scripts/Configurar-Estacao-Cliente.ps1"):
            texto=(RAIZ/relativo).read_text(encoding="utf-8-sig")
            self.assertIn("UTF8Encoding($false)",texto,relativo)
            self.assertIn("/api/v1/health/ready",texto,relativo)
            self.assertNotIn("Set-Content",texto,relativo)
        servidor=(RAIZ/"scripts/Instalar-Servidor-Corporativo.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("install-task",servidor)
        self.assertIn("start-task",servidor)
        self.assertIn("wait-ready",servidor)
        self.assertIn('backend="postgresql"',servidor)
        self.assertIn("migrate-sqlite --source",servidor)
        self.assertIn('Stop-ScheduledTask -TaskName "DataIntelligenceCorporateServer"',servidor)
        self.assertIn("uninstall-task",servidor)
        self.assertNotIn("Register-ScheduledTask",servidor)
        agente=(RAIZ/"scripts/Instalar-Agente-TI.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('Stop-ScheduledTask -TaskName "DataIntelligence-TIAgent"',agente)
        self.assertIn("once",agente)

    def test_scripts_fallback_usam_mesmos_caminhos_do_setup(self):
        instalar_agente=(RAIZ/"scripts/Instalar-Agente-TI.ps1").read_text(encoding="utf-8-sig")
        testar_agente=(RAIZ/"scripts/Testar-Agente-TI.ps1").read_text(encoding="utf-8-sig")
        remover_agente=(RAIZ/"scripts/Desinstalar-Agente-TI.ps1").read_text(encoding="utf-8-sig")
        remover_servidor=(RAIZ/"scripts/Desinstalar-Servidor-Corporativo.ps1").read_text(encoding="utf-8-sig")
        for texto in (instalar_agente,testar_agente,remover_agente):
            self.assertIn('"Data Intelligence\\TIAgent',texto)
            self.assertNotIn('"DataIntelligence\\TIAgent',texto)
        self.assertIn('"Data Intelligence\\Server',remover_servidor)
        build=(RAIZ/"scripts/build_distribuicao_windows.ps1").read_text(encoding="utf-8-sig")
        self.assertNotIn("README_V9_1_AUTORIDADE_CENTRAL.md",build)
        self.assertIn("README_V10_1_1_ESTABILIDADE.md",build)

    def test_estoque_nao_usa_max_escalar_exclusivo_do_sqlite(self):
        texto=(RAIZ/"enterprise/estoque.py").read_text(encoding="utf-8")
        self.assertNotIn("quantidade_reservada=MAX(0", texto)
        self.assertIn("CASE", texto)
        self.assertIn("quantidade_reservada - ? < 0", texto)

    def test_auditoria_usa_versao_canonica_atual(self):
        texto=(RAIZ/"auth/banco.py").read_text(encoding="utf-8")
        self.assertIn("from core.versao import VERSAO_INTERFACE",texto)
        self.assertIn("VERSAO_INTERFACE,",texto)
        self.assertNotIn('"V8.2",',texto)

    def test_versao_estabilidade(self):
        from core.versao import VERSAO_INTERFACE,VERSAO_PLATAFORMA
        self.assertEqual(VERSAO_PLATAFORMA,"11.1.0")
        self.assertEqual(VERSAO_INTERFACE,"V11.1.0")


if __name__ == "__main__":
    unittest.main()
