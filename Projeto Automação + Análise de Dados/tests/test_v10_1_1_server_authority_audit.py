from __future__ import annotations

import importlib
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def test_superficie_rpc_inteira_importa_no_codigo_fonte():
    from servidor_corporativo.rpc import validar_rpc_runtime

    resultado = validar_rpc_runtime()
    assert "configuracoes.preferencias" in resultado
    assert "historico.repositorio" in resultado
    assert resultado["configuracoes.preferencias"]
    assert resultado["historico.repositorio"]


def test_todos_os_modulos_rpc_estao_cobertos_pelo_spec_do_servidor():
    spec = (ROOT / "DataIntelligenceServer.spec").read_text(encoding="utf-8")
    assert "from core.rpc_central import RPC_ALLOWLIST" in spec
    assert "_rpc_modulos = sorted(RPC_ALLOWLIST)" in spec
    assert "hiddenimports = list(_rpc_modulos)" in spec


def test_configuracoes_e_historico_sao_derivados_da_allowlist_no_servidor():
    from core.rpc_central import RPC_ALLOWLIST
    assert "configuracoes.preferencias" in RPC_ALLOWLIST
    assert "historico.repositorio" in RPC_ALLOWLIST
    spec = (ROOT / "DataIntelligenceServer.spec").read_text(encoding="utf-8")
    assert "collect_submodules(_package)" in spec


def test_firewall_usa_encoded_command_e_ambiente_em_vez_de_argumentos_de_codigo(monkeypatch):
    from enterprise import firewall_ti

    capturado = {}

    class Resultado:
        returncode = 0
        stdout = "OK\n"
        stderr = ""

    def fake_run(comando, **kwargs):
        capturado["comando"] = list(comando)
        capturado["kwargs"] = kwargs
        return Resultado()

    monkeypatch.setattr(firewall_ti.subprocess, "run", fake_run)
    retorno = firewall_ti._executar_powershell(
        "Write-Output $env:DI_TESTE",
        ambiente={"DI_TESTE": "Data Intelligence TI - Descoberta 1 192.168.1.0/24"},
    )
    assert retorno == "OK"
    comando = capturado["comando"]
    assert "-EncodedCommand" in comando
    assert "-Command" not in comando
    assert "Data Intelligence TI - Descoberta" not in " ".join(comando)
    assert capturado["kwargs"]["env"]["DI_TESTE"].startswith("Data Intelligence TI")
    assert capturado["kwargs"]["shell"] is False


def test_backup_encontra_pg_dump_na_instalacao_padrao_windows(tmp_path, monkeypatch):
    from enterprise import backups

    pg_dump = tmp_path / "PostgreSQL" / "17" / "bin" / "pg_dump.exe"
    pg_dump.parent.mkdir(parents=True)
    pg_dump.write_bytes(b"fake")
    monkeypatch.setattr(backups.shutil, "which", lambda _nome: None)
    monkeypatch.setattr(backups, "_eh_windows", lambda: True)
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.delenv("ProgramW6432", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    monkeypatch.delenv("DATA_INTELLIGENCE_PG_BIN", raising=False)

    assert Path(backups._comando_postgres("pg_dump")) == pg_dump.resolve()


def test_allowlist_alvos_instalam_wrapper_server_first():
    from core.rpc_central import RPC_ALLOWLIST

    faltando = []
    for modulo, funcoes in RPC_ALLOWLIST.items():
        mod = importlib.import_module(modulo)
        for nome in funcoes:
            alvo = getattr(mod, nome, None)
            if not callable(alvo) or not getattr(alvo, "__di_rpc_wrapper__", False):
                faltando.append(f"{modulo}.{nome}")
    assert not faltando, "Operações sem proxy Server First: " + ", ".join(faltando)


def test_central_cliente_jamais_abrem_banco_diretamente(tmp_path, monkeypatch):
    import json
    from auth import banco

    node = tmp_path / "node.json"
    node.write_text(json.dumps({"papel": "central", "servidor_url": "http://127.0.0.1:8770"}), encoding="utf-8")
    monkeypatch.setenv("DATA_INTELLIGENCE_NODE_CONFIG", str(node))
    monkeypatch.delenv("DATA_INTELLIGENCE_NODE_ROLE", raising=False)

    try:
        with banco.conectar():
            raise AssertionError("a conexão não deveria ser aberta")
    except RuntimeError as erro:
        assert "não pode abrir banco" in str(erro)


def test_erro_http_exibe_request_id(monkeypatch):
    import io
    import urllib.error
    from enterprise import servidor_cliente

    class Cfg:
        servidor_url = "http://127.0.0.1:8770"
        permitir_http_privado = False

    monkeypatch.setattr(servidor_cliente, "_cfg", lambda: Cfg())
    monkeypatch.setattr(servidor_cliente, "_TOKEN", "token")

    def falhar(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "http://127.0.0.1:8770/api/v1/rpc", 500, "erro",
            {"X-Request-ID": "abc123"}, io.BytesIO(b'{"erro":"Falha interna do servidor."}')
        )

    monkeypatch.setattr(servidor_cliente.urllib.request, "urlopen", falhar)
    try:
        servidor_cliente._request("/api/v1/rpc")
    except ValueError as erro:
        assert "abc123" in str(erro)
    else:
        raise AssertionError("erro HTTP deveria ser propagado")


def test_preflight_backup_exige_dump_e_restore(monkeypatch):
    from enterprise import backups
    vistos = []
    monkeypatch.setattr(backups, "backend_banco", lambda: "postgresql")
    monkeypatch.setattr(backups, "_comando_postgres", lambda nome: vistos.append(nome) or f"/fake/{nome}")
    resultado = backups.validar_dependencias_backup()
    assert resultado["ok"] is True
    assert vistos == ["pg_dump", "pg_restore"]



def test_logger_json_preserva_detalhe_operacional():
    import json
    import logging
    from core.observabilidade import JsonLineFormatter
    registro = logging.LogRecord("teste", logging.WARNING, __file__, 1, "falha", (), None)
    registro.erro_operacional = "detalhe real"
    payload = json.loads(JsonLineFormatter().format(registro))
    assert payload["erro_operacional"] == "detalhe real"



def test_exportacao_grade_remota_vai_direto_para_servidor_sem_save_dialog():
    texto = (ROOT / "interface/grade_editavel.py").read_text(encoding="utf-8")
    assert "enviar_bytes_servidor" in texto
    trecho_remoto = texto.split("if usa_servidor_remoto():", 1)[1]
    assert "io.StringIO" in trecho_remoto
    assert "io.BytesIO" in texto
    # O caminho local existe apenas no ramo standalone, depois do retorno remoto.
    assert texto.index("if usa_servidor_remoto():") < texto.index("filedialog.asksaveasfilename")


def test_cliente_pode_enviar_artefato_em_memoria_ao_endpoint_de_exportacao(monkeypatch):
    from enterprise import servidor_cliente
    capturado = {}

    def fake_request(path, **kwargs):
        capturado["path"] = path
        capturado.update(kwargs)
        return {"id": 9, "nome": "grade.csv"}

    monkeypatch.setattr(servidor_cliente, "_request", fake_request)
    resultado = servidor_cliente.enviar_bytes_servidor(b"abc", "grade.csv", modulo="grade", categoria="exportacao")
    assert resultado["id"] == 9
    assert capturado["path"] == "/api/v1/exports"
    assert capturado["corpo"] == b"abc"
    assert capturado["headers"]["X-SHA256"]


def test_provisionamento_agente_nao_oferece_persistencia_local_do_token():
    texto = (ROOT / "interface/tecnologia_operacoes.py").read_text(encoding="utf-8")
    assert "SALVAR ARQUIVO TEMPORÁRIO" not in texto
    assert "Salvar provisionamento temporário" not in texto


def test_config_servidor_rejeita_sqlite_mesmo_com_flag_legada(monkeypatch):
    from servidor_corporativo.config import ConfigServidor
    monkeypatch.setenv("DATA_INTELLIGENCE_ENABLE_LEGACY_SQLITE", "1")
    try:
        ConfigServidor(db_backend="sqlite").validar()
    except ValueError as erro:
        assert "somente PostgreSQL" in str(erro)
    else:
        raise AssertionError("Servidor Corporativo não pode aceitar SQLite")


def test_relatorio_remoto_com_server_uri_nao_baixa_arquivo(monkeypatch):
    from enterprise import servidor_cliente

    capturado = {}

    def fake_store(payload):
        capturado.update(payload)
        return {"id": 44, "nome": payload["nome_destino"], "armazenamento": "servidor_corporativo"}

    monkeypatch.setattr(servidor_cliente, "_request_armazenar_resultado_arquivo", fake_store)
    resultado = servidor_cliente.executar_operacao_arquivo_remota(
        "enterprise.rh",
        "gerar_relatorio_rh",
        args=("Colaboradores", "CSV", "server://rh_colaboradores.csv", {"id": 1}),
    )
    assert resultado["id"] == 44
    assert resultado["armazenamento"] == "servidor_corporativo"
    assert capturado["nome_destino"] == "rh_colaboradores.csv"


def test_helper_de_destino_remoto_nao_abre_save_as(tmp_path, monkeypatch):
    import json
    from interface import armazenamento_servidor

    node = tmp_path / "node.json"
    node.write_text(json.dumps({"papel": "central", "servidor_url": "http://127.0.0.1:8770"}), encoding="utf-8")
    monkeypatch.setenv("DATA_INTELLIGENCE_NODE_CONFIG", str(node))
    monkeypatch.delenv("DATA_INTELLIGENCE_NODE_ROLE", raising=False)
    monkeypatch.setattr(
        armazenamento_servidor.filedialog,
        "asksaveasfilename",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("Save As local não deve abrir em Central/Cliente")),
    )
    destino, remoto = armazenamento_servidor.escolher_destino_gerado(
        parent=None, nome_sugerido="relatório.xlsx", defaultextension=".xlsx"
    )
    assert remoto is True
    assert destino.startswith("server://")


def test_endpoint_server_store_existe_e_persiste_arquivo_corporativo():
    texto = (ROOT / "servidor_corporativo/app.py").read_text(encoding="utf-8")
    assert 'path == "/api/v1/rpc/file-store"' in texto
    assert "_rpc_armazenar_arquivo" in texto
    assert "'gerado_servidor'" in texto


def test_relatorios_departamentais_usam_destino_server_first():
    for relativo in (
        "interface/rh_acoes.py",
        "interface/estoque_acoes.py",
        "interface/compras_acoes.py",
        "interface/tecnologia_acoes.py",
    ):
        texto = (ROOT / relativo).read_text(encoding="utf-8")
        assert "escolher_destino_gerado" in texto, relativo
    assert "asksaveasfilename" not in (ROOT / "interface/rh_acoes.py").read_text(encoding="utf-8")
    assert "asksaveasfilename" not in (ROOT / "interface/estoque_acoes.py").read_text(encoding="utf-8")
    # Compras ainda possui askopenfilename para importar documento; apenas saída foi removida.
    compras = (ROOT / "interface/compras_acoes.py").read_text(encoding="utf-8")
    assert "asksaveasfilename" not in compras
    tecnologia = (ROOT / "interface/tecnologia_acoes.py").read_text(encoding="utf-8")
    assert "asksaveasfilename" not in tecnologia


def test_mfa_falha_fechado_em_estacao_remota_antes_de_persistir(tmp_path, monkeypatch):
    import json
    from auth import mfa

    node = tmp_path / "node.json"
    node.write_text(json.dumps({"papel": "cliente", "servidor_url": "http://127.0.0.1:8770"}), encoding="utf-8")
    monkeypatch.setenv("DATA_INTELLIGENCE_NODE_CONFIG", str(node))
    monkeypatch.delenv("DATA_INTELLIGENCE_NODE_ROLE", raising=False)
    try:
        mfa.habilitar_mfa(1, {"id": 1, "perfil": "usuario"})
    except RuntimeError as erro:
        assert "Servidor Corporativo" in str(erro)
    else:
        raise AssertionError("MFA remoto não pode iniciar persistência local")


def test_artefatos_gerados_sensiveis_nao_fazem_download_automatico(monkeypatch):
    from enterprise import servidor_cliente

    capturado = []
    monkeypatch.setattr(
        servidor_cliente,
        "_request_armazenar_resultado_arquivo",
        lambda payload: capturado.append(payload) or {"id": 5, "nome": "artefato.pdf", "armazenamento": "servidor_corporativo"},
    )
    # Se o fluxo tentar baixar bytes, o teste deve falhar.
    monkeypatch.setattr(
        servidor_cliente,
        "_request_resultado_arquivo",
        lambda _payload: (_ for _ in ()).throw(AssertionError("download automático indevido")),
    )
    resultado = servidor_cliente.executar_operacao_arquivo_remota(
        "enterprise.financeiro", "gerar_relatorio_financeiro",
        args=("DRE", "PDF", {"id": 1}),
    )
    assert resultado["armazenamento"] == "servidor_corporativo"
    assert capturado[0]["funcao"] == "gerar_relatorio_financeiro"


def test_contracheque_financeiro_e_relatorio_ferramentas_mostram_armazenamento_servidor():
    from core.rpc_arquivos import RPC_ARQUIVO_PERSISTE_SERVIDOR
    assert ("enterprise.rh", "gerar_contracheque") in RPC_ARQUIVO_PERSISTE_SERVIDOR
    assert ("enterprise.financeiro", "gerar_relatorio_financeiro") in RPC_ARQUIVO_PERSISTE_SERVIDOR
    assert ("enterprise.ferramentas", "gerar_relatorio") in RPC_ARQUIVO_PERSISTE_SERVIDOR
    for relativo in ("interface/rh_acoes.py", "interface/financeiro_dialogos.py", "interface/ferramentas.py"):
        texto = (ROOT / relativo).read_text(encoding="utf-8")
        assert "armazenamento" in texto and "servidor_corporativo" in texto, relativo
