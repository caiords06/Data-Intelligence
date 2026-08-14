"""Auditoria estática de autoridade Server First da distribuição V11.1.0.

Falha com exit code 1 se uma regressão permitir que Central/Cliente volte a
abrir persistência corporativa local ou se o pacote do servidor deixar de
cobrir a superfície RPC dinâmica.
"""
from __future__ import annotations

import ast
import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
IGNORAR_PARTES = {"tests", "scripts", "build", "dist", "release", ".pytest_cache", "__pycache__"}
SQLITE_PERMITIDO = {
    "auth/banco.py",                    # compatibilidade explícita migração/testes
    "enterprise/backups.py",           # leitura/restauração de backups legados
    "enterprise/postgresql/migracao.py", # origem SQLite somente leitura
    "dados/fontes.py",                  # arquivo SQLite escolhido como fonte de análise
}


def _arquivos_producao() -> list[Path]:
    saida = []
    for caminho in ROOT.rglob("*.py"):
        relativo = caminho.relative_to(ROOT)
        if any(parte in IGNORAR_PARTES for parte in relativo.parts):
            continue
        saida.append(caminho)
    return sorted(saida)


def main() -> int:
    problemas: list[str] = []
    arquivos = _arquivos_producao()
    linhas = 0
    for caminho in arquivos:
        texto = caminho.read_text(encoding="utf-8", errors="ignore")
        linhas += len(texto.splitlines())
        relativo = caminho.relative_to(ROOT).as_posix()
        if "sqlite3.connect" in texto and relativo not in SQLITE_PERMITIDO:
            problemas.append(f"SQLite operacional inesperado: {relativo}")
        if "preferencias.json" in texto.lower():
            problemas.append(f"Preferência persistente local reapareceu: {relativo}")

    # UI e fachadas não podem conhecer o banco diretamente.
    for pasta in (ROOT / "interface", ROOT / "services"):
        for caminho in pasta.rglob("*.py"):
            texto = caminho.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"(?:from\s+auth\.banco\s+import|import\s+auth\.banco)", texto):
                problemas.append(f"Camada de apresentação acessa auth.banco: {caminho.relative_to(ROOT)}")

    # Nenhuma tela de produção pode criar um destino persistente local por
    # conta própria. Os únicos seletores de saída permitidos vivem no helper
    # que desvia Central/Cliente para server:// e no editor de grade, cujo ramo
    # remoto retorna antes do Save As standalone. Capturas visuais são tooling.
    save_as_permitido = {
        "interface/armazenamento_servidor.py",
        "interface/grade_editavel.py",
    }
    for caminho in (ROOT / "interface").rglob("*.py"):
        relativo = caminho.relative_to(ROOT).as_posix()
        texto = caminho.read_text(encoding="utf-8", errors="ignore")
        if "asksaveasfilename" in texto and relativo not in save_as_permitido:
            problemas.append(f"Tela ainda abre destino persistente local: {relativo}")

    # Exercita a tradução PostgreSQL sobre todos os literais SQL operacionais.
    # Migrations SQLite e rotinas de restauração legada são deliberadamente
    # excluídas porque não executam no backend PostgreSQL de produção.
    from enterprise.postgresql.adapter import traduzir_sql
    sql_auditados = 0
    residuos_sqlite = (
        (r"\bCOLLATE\s+NOCASE\b", "COLLATE NOCASE"),
        (r"\bIS\s+%s", "IS %s"),
        (r"date\('now'", "date('now')"),
        (r"datetime\('now'", "datetime('now')"),
        (r"\bjulianday\s*\(", "julianday"),
        (r"\bstrftime\s*\(", "strftime"),
        (r"\bprintf\s*\(", "printf"),
        (r"\bsqlite_master\b", "sqlite_master"),
    )
    for caminho in arquivos:
        relativo = caminho.relative_to(ROOT).as_posix()
        if (
            "/migrations/" in relativo or "/postgresql/" in relativo
            or relativo in {
                "auth/banco.py", "enterprise/banco.py", "enterprise/backups.py",
                "dados/fontes.py",
            }
        ):
            continue
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as erro:
            problemas.append(f"Python inválido durante auditoria SQL: {relativo}:{erro.lineno}")
            continue
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Constant) or not isinstance(no.value, str):
                continue
            sql = no.value
            if not re.search(r"\b(?:SELECT|INSERT|UPDATE|DELETE)\b", sql, re.I):
                continue
            sql_auditados += 1
            try:
                traduzido = traduzir_sql(sql)
            except Exception as erro:
                problemas.append(f"Falha ao traduzir SQL: {relativo}:{no.lineno}: {erro}")
                continue
            for padrao, rotulo in residuos_sqlite:
                if re.search(padrao, traduzido, re.I):
                    problemas.append(
                        f"SQL operacional ainda contém sintaxe SQLite ({rotulo}): {relativo}:{no.lineno}"
                    )

    banco = (ROOT / "auth/banco.py").read_text(encoding="utf-8")
    if 'get("DATA_INTELLIGENCE_DB_BACKEND", "postgresql")' not in banco:
        problemas.append("PostgreSQL deixou de ser o backend padrão obrigatório.")
    if 'papel in {"central", "cliente"}' not in banco or "não pode abrir banco" not in banco:
        problemas.append("Barreira de banco direto Central/Cliente ausente.")

    spec = (ROOT / "DataIntelligenceServer.spec").read_text(encoding="utf-8")
    for trecho in ("from core.rpc_central import RPC_ALLOWLIST", "hiddenimports = list(_rpc_modulos)", "collect_submodules(_package)"):
        if trecho not in spec:
            problemas.append(f"Spec do servidor não deriva superfície RPC: {trecho}")

    from core.rpc_central import RPC_ALLOWLIST
    for modulo, funcoes in RPC_ALLOWLIST.items():
        try:
            obj = importlib.import_module(modulo)
        except Exception as erro:
            problemas.append(f"Módulo RPC não importável: {modulo}: {erro}")
            continue
        for nome in sorted(funcoes):
            alvo = getattr(obj, nome, None)
            if not callable(alvo):
                problemas.append(f"Alvo RPC ausente: {modulo}.{nome}")
            elif not getattr(alvo, "__di_rpc_wrapper__", False):
                problemas.append(f"Alvo RPC sem wrapper Server First: {modulo}.{nome}")

    config = (ROOT / "servidor_corporativo/config.py").read_text(encoding="utf-8")
    if 'db_backend != "postgresql"' not in config:
        problemas.append("ConfigServidor ainda permite backend diferente de PostgreSQL.")

    firewall = (ROOT / "enterprise/firewall_ti.py").read_text(encoding="utf-8")
    if '"-EncodedCommand", codificado' not in firewall or "DI_FIREWALL_RULE_NAME" not in firewall:
        problemas.append("Firewall não usa PowerShell codificado + variáveis de ambiente.")

    tecnologia_ui = (ROOT / "interface/tecnologia_operacoes.py").read_text(encoding="utf-8")
    if "SALVAR ARQUIVO TEMPORÁRIO" in tecnologia_ui:
        problemas.append("Provisionamento do agente ainda permite persistir token localmente.")

    grade = (ROOT / "interface/grade_editavel.py").read_text(encoding="utf-8")
    if "enviar_bytes_servidor" not in grade or "io.StringIO" not in grade or "io.BytesIO" not in grade:
        problemas.append("Exportação de grade remota não é Server First em memória.")

    compras = (ROOT / "enterprise/domains/compras/inteligencia.py").read_text(encoding="utf-8")
    if "SELECT si.descricao,COUNT(DISTINCT s.id)" in compras:
        problemas.append("Consulta Compras mantém GROUP BY incompatível com PostgreSQL.")

    # Saídas geradas por RH/Estoque/Compras/TI devem ficar no servidor em modo remoto.
    for relativo in (
        "interface/rh_acoes.py", "interface/estoque_acoes.py",
        "interface/compras_acoes.py", "interface/tecnologia_acoes.py",
    ):
        texto = (ROOT / relativo).read_text(encoding="utf-8")
        if "escolher_destino_gerado" not in texto:
            problemas.append(f"Relatório departamental sem destino Server First: {relativo}")
        if "asksaveasfilename" in texto:
            problemas.append(f"Saída departamental ainda abre Save As local: {relativo}")

    cliente = (ROOT / "enterprise/servidor_cliente.py").read_text(encoding="utf-8")
    servidor_app = (ROOT / "servidor_corporativo/app.py").read_text(encoding="utf-8")
    if 'startswith("server://")' not in cliente or "/api/v1/rpc/file-store" not in cliente:
        problemas.append("Cliente não possui fluxo de relatório gerado diretamente no servidor.")
    if 'path == "/api/v1/rpc/file-store"' not in servidor_app or "_rpc_armazenar_arquivo" not in servidor_app:
        problemas.append("Servidor não possui endpoint para persistir resultado RPC sem download.")

    mfa = (ROOT / "auth/mfa.py").read_text(encoding="utf-8")
    if "_garantir_execucao_servidor()" not in mfa or "MFA deve ser configurado no Servidor Corporativo" not in mfa:
        problemas.append("MFA ainda pode iniciar persistência de segredo numa estação remota.")

    rpc_arquivos = (ROOT / "core/rpc_arquivos.py").read_text(encoding="utf-8")
    for alvo in (
        '("enterprise.rh", "gerar_contracheque")',
        '("enterprise.financeiro", "gerar_relatorio_financeiro")',
        '("enterprise.ferramentas", "gerar_relatorio")',
    ):
        if alvo not in rpc_arquivos or "RPC_ARQUIVO_PERSISTE_SERVIDOR" not in rpc_arquivos:
            problemas.append(f"Artefato sensível ainda pode baixar automaticamente: {alvo}")

    print(f"Arquivos Python de produção auditados: {len(arquivos)}")
    print(f"Linhas Python de produção auditadas: {linhas}")
    print(f"Módulos RPC auditados: {len(RPC_ALLOWLIST)}")
    print(f"Operações RPC auditadas: {sum(len(v) for v in RPC_ALLOWLIST.values())}")
    print(f"Literais SQL operacionais traduzidos/auditados: {sql_auditados}")
    if problemas:
        print("AUDITORIA SERVER FIRST: FALHOU")
        for problema in problemas:
            print(f"- {problema}")
        return 1
    print("AUDITORIA SERVER FIRST: APROVADA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
