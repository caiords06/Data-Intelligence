"""Gera o pacote-fonte canônico, limpo, determinístico e verificável da V11.1.0.

Uso:
    python scripts/empacotar_fonte_limpa.py
    python scripts/empacotar_fonte_limpa.py caminho/saida.zip
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.versao import PYTHON_RELEASE_TEXTO, VERSAO_INTERFACE, VERSAO_PLATAFORMA
from enterprise.migrations import validar_registry

SAIDA_PADRAO = RAIZ / "release" / f"DataIntelligence-Source-V{VERSAO_PLATAFORMA}.zip"
MANIFESTO_NOME = "SOURCE_MANIFEST.json"
ARQUIVO_VERSAO = f"VERSAO_{VERSAO_INTERFACE.replace('.', '_')}.txt"
DATA_ZIP_DETERMINISTICA = (2026, 8, 14, 0, 0, 0)

DIRETORIOS_PERMITIDOS = {
    ".github", "agente_ti", "analysis", "analytics", "assets", "auth", "automacao",
    "configuracoes", "core", "dados", "docs", "enterprise", "historico", "interface",
    "scripts", "services", "servidor", "servidor_corporativo", "servidor_ti",
    "sistema", "tests", "installer",
}
ARQUIVOS_RAIZ_PERMITIDOS = {
    ".gitignore", ".gitattributes", ".python-version", "app.py", "main.py", "pytest.ini",
    "pyproject.toml", "SECURITY.md",
    "requirements.txt", "requirements.lock.txt", "requirements-agent.txt",
    "requirements-agent.lock.txt", "requirements-agent-build.txt",
    "requirements-build.txt", "requirements-build.lock.txt",
    "DataIntelligencePlatform.spec", "DataIntelligenceServer.spec", "DataIntelligenceUpdateHelper.spec", "agente_ti.spec",
}
EXTENSOES_DOC = {".md", ".txt"}
DIRETORIOS_PROIBIDOS = {
    ".git", ".pytest_cache", "__pycache__", "build", "dist", "release",
    "storage", "artifacts", ".venv", "venv", "env", ".idea", ".vscode",
}
EXTENSOES_PROIBIDAS = {
    ".db", ".sqlite", ".sqlite3", ".log", ".pyc", ".pyo", ".xlsx", ".xls", ".csv",
}
NOMES_PROIBIDOS = {
    ".env", "credentials.json", "token.json", "secrets.json", ".coverage",
}
AMOSTRAS_PUBLICAS = {"dados_exemplo/Vendas - Dez.xlsx"}
ARQUIVOS_OBRIGATORIOS = {
    ".gitattributes",
    ".python-version",
    "main.py",
    "pytest.ini",
    "requirements.txt",
    "requirements.lock.txt",
    "requirements-build.lock.txt",
    "requirements-agent.lock.txt",
    "DataIntelligencePlatform.spec",
    "DataIntelligenceServer.spec",
    "DataIntelligenceUpdateHelper.spec",
    "agente_ti.spec",
    "pyproject.toml",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "DEPENDENCY_INVENTORY.md",
    "scripts/build_distribuicao_windows.ps1",
    "scripts/build_setup_windows.ps1",
    "scripts/verificar_instalador_v10.py",
    "scripts/verificar_instalador_v10_1.py",
    "tests/test_v10_1_postgresql_integration.py",
    "tests/test_v10_5_api_http_regressoes.py",
    "tests/test_v10_5_seguranca_release.py",
    "RELATORIO_CORRECOES_V10_5_0_AUDITORIA_20260813.md",
    "RELATORIO_HARDENING_PRODUCAO_V10_5_0_20260813.md",
    "installer/DataIntelligenceSetup.iss",
    "README_V10_INSTALADOR_UNIFICADO.md",
    "scripts/verificar_fonte_reproduzivel.py",
    "enterprise/migrations/__init__.py",
    "enterprise/repositories/__init__.py",
    "enterprise/repositories/provider.py",
    "enterprise/domains/financeiro/base.py",
    "enterprise/domains/financeiro/conciliacao.py",
    "enterprise/domains/financeiro/inteligencia.py",
    "enterprise/domains/compras/base.py",
    "enterprise/domains/compras/inteligencia.py",
    "enterprise/domains/compras/relatorios.py",
    "enterprise/domains/estoque/base.py",
    "enterprise/domains/estoque/inteligencia.py",
    "enterprise/domains/estoque/relatorios.py",
    "enterprise/domains/tecnologia/base.py",
    "enterprise/domains/tecnologia/agentes.py",
    "enterprise/domains/tecnologia/infraestrutura.py",
    "core/versao.py",
    "core/ciclo_vida.py",
    "core/observabilidade.py",
    "core/criptografia.py",
    "core/atualizacoes.py",
    "README_V9_9_ROBUSTEZ_OPERACIONAL.md",
    "interface/navegacao_modulos.py",
    "services/departamentos/financeiro.py",
    "services/departamentos/rh.py",
    "services/departamentos/estoque.py",
    "services/departamentos/compras.py",
    "services/departamentos/tecnologia.py",
    "README_V9_5_ARQUITETURA_DOMINIOS.md",
    "README_V10_4_ANALYTICS_INTELIGENCIA.md",
    "README_V10_4_1_INTELIGENCIA_TRANSVERSAL.md",
    "README_V10_5_API_WEB_READY.md",
    "enterprise/analytics_inteligencia.py",
    "enterprise/orquestracao.py",
    "enterprise/migrations/024_v10_4_analytics_inteligencia.py",
    "enterprise/migrations/025_v10_4_1_inteligencia_transversal.py",
    "enterprise/migrations/026_hardening_producao.py",
    "enterprise/postgresql/schema_hardening.sql",
    "enterprise/postgresql/schema_v11.sql",
    "enterprise/postgresql/schema_v11_1.sql",
    "enterprise/migrations/027_v11_core_empresarial.py",
    "enterprise/migrations/028_v11_1_conformidade.py",
    "enterprise/compliance.py",
    "enterprise/remote_governanca.py",
    "enterprise/core_v11/__init__.py",
    "enterprise/core_v11/common.py",
    "enterprise/core_v11/catalogo.py",
    "enterprise/core_v11/provisionamento.py",
    "enterprise/core_v11/pessoas.py",
    "enterprise/core_v11/organizacao.py",
    "enterprise/core_v11/seguranca.py",
    "enterprise/core_v11/colaboracao.py",
    "enterprise/core_v11/metadados.py",
    "enterprise/core_v11/documentos.py",
    "enterprise/core_v11/busca.py",
    "enterprise/core_v11/eventos.py",
    "enterprise/core_v11/registros.py",
    "enterprise/core_v11/funcionarios.py",
    "enterprise/core_v11/transferencias.py",
    "enterprise/core_v11/integracoes.py",
    "services/core_empresarial.py",
    "services/compliance.py",
    "services/remote_governanca.py",
    "services/funcionario_360.py",
    "services/operacoes_v11.py",
    "interface/funcionario_360.py",
    "interface/compliance.py",
    "README_V11_CORE_EMPRESARIAL.md",
    "RELATORIO_IMPLEMENTACAO_V11_20260814.md",
    "RELATORIO_CORRECOES_V11_0_1_20260814.md",
    "RELATORIO_IMPLEMENTACAO_V11_1_0_20260814.md",
    "docs/16_CONFORMIDADE_E_PRIVACIDADE_V11_1.md",
    "docs/17_MIGRACAO_TLS_V11_1.md",
    "docs/18_MATRIZ_IMPLEMENTACAO_REQUISITOS_2026.md",
    "assets/brand/logo_empresa.png",
    "assets/brand/login_data_center.png",
    "assets/brand/acesso_corporativo.png",
    "assets/brand/ASSET_PROVENANCE.md",
    "tests/test_v11_core_empresarial.py",
    "tests/test_v11_0_1_correcoes.py",
    "tests/test_v11_1_conformidade.py",
    "enterprise/automacao_motor.py",
    "enterprise/privacidade.py",
    "enterprise/webhooks.py",
    "services/analytics.py",
    "services/crm.py",
    "services/orquestracao.py",
    "servidor_corporativo/api_v1.py",
    "servidor_corporativo/controles_api.py",
    "servidor_corporativo/dto.py",
    "servidor_corporativo/openapi.py",
    "servidor_corporativo/sessoes.py",
    "scripts/auditar_camadas_arquitetura.py",
    "scripts/auditar_excecoes_silenciosas.py",
    "scripts/teste_carga_api.py",
    "scripts/update_helper.py",
    "tests/test_hardening_producao.py",
    "README_V9_6_INTERFACE_COMPONENTES.md",
    "interface/app_layout.py",
    "interface/financeiro_views.py",
    "interface/financeiro_dialogos.py",
    "interface/compras_views.py",
    "interface/compras_acoes.py",
    "interface/tecnologia_operacoes.py",
    "interface/tecnologia_acoes.py",
    "interface/rh_shared.py",
    "interface/rh_views.py",
    "interface/rh_acoes.py",
    "interface/estoque_shared.py",
    "interface/estoque_views.py",
    "interface/estoque_acoes.py",
    "interface/componentes_departamentais.py",
    "README_V9_7_COMPONENTES_DEPARTAMENTAIS.md",
    "README_V9_8_INFRAESTRUTURA_VISUAL.md",
    "interface/componentes_navegacao.py",
    "interface/componentes_acoes.py",
    "interface/componentes_basicos.py",
    "interface/componentes_responsivos.py",
    "interface/painel_modulo_shared.py",
    "interface/painel_modulo_visao.py",
    "interface/painel_modulo_operacoes.py",
    "interface/central_analytics_shared.py",
    "interface/central_analytics_dashboard.py",
    "interface/central_analytics_datasets.py",
    "interface/central_analytics_recursos.py",
    "interface/modulo_empresarial_shared.py",
    "interface/modulo_empresarial_tabela.py",
    "interface/modulo_empresarial_formularios.py",
    "README_V10_1_POSTGRESQL_SERVER_FIRST.md",
    "core/segredos.py",
    "core/windows_tasks.py",
    "enterprise/postgresql/__init__.py",
    "enterprise/postgresql/adapter.py",
    "enterprise/postgresql/bootstrap.py",
    "enterprise/postgresql/migracao.py",
    "enterprise/postgresql/schema_v10_1.sql",
    "scripts/gerar_schema_postgresql.py",
    "servidor_corporativo/windows.py",
    "tests/test_v10_1_1_estabilidade.py",
    "tests/test_v10_2_design_system.py",
    "interface/gerenciador_tema.py",
    "interface/icones.py",
    "README_V10_2_DESIGN_SYSTEM.md",
    "VERSAO_V10_1_1.txt",
    "README_V10_1_1_ESTABILIDADE.md",
    "RELATORIO_V10_1_1_ESTABILIDADE_20260812.md",
    ARQUIVO_VERSAO,
}


def permitido(caminho: Path) -> bool:
    if caminho.is_symlink():
        return False
    relativo = caminho.relative_to(RAIZ)
    relativo_posix = relativo.as_posix()
    if relativo_posix in AMOSTRAS_PUBLICAS:
        return True
    if any(parte in DIRETORIOS_PROIBIDOS for parte in relativo.parts):
        return False
    if caminho.name in NOMES_PROIBIDOS or caminho.suffix.lower() in EXTENSOES_PROIBIDAS:
        return False
    if len(relativo.parts) == 1:
        return caminho.name in ARQUIVOS_RAIZ_PERMITIDOS or caminho.suffix.lower() in EXTENSOES_DOC
    return relativo.parts[0] in DIRETORIOS_PERMITIDOS


def _info_zip(nome: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(nome, DATA_ZIP_DETERMINISTICA)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _manifesto(arquivos: list[Path]) -> bytes:
    itens = []
    for arquivo in sorted(arquivos, key=lambda p: p.relative_to(RAIZ).as_posix()):
        dados = arquivo.read_bytes()
        itens.append({
            "caminho": arquivo.relative_to(RAIZ).as_posix(),
            "tamanho": len(dados),
            "sha256": sha256(dados).hexdigest(),
        })
    payload = {
        "formato": 1,
        "produto": "Data Intelligence Enterprise Platform",
        "versao": VERSAO_PLATAFORMA,
        "python_release": PYTHON_RELEASE_TEXTO,
        "arquivos": itens,
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def validar_zip(caminho_zip: Path) -> None:
    problemas: list[str] = []
    with zipfile.ZipFile(caminho_zip) as zf:
        nomes = zf.namelist()
        if len(nomes) != len(set(nomes)):
            problemas.append("nomes duplicados no ZIP")
        for nome in nomes:
            partes = Path(nome).parts
            base = Path(nome).name
            sufixo = Path(nome).suffix.lower()
            if Path(nome).is_absolute() or ".." in partes:
                problemas.append(f"caminho inseguro:{nome}")
            if any(p in DIRETORIOS_PROIBIDOS for p in partes):
                problemas.append(nome)
            if base in NOMES_PROIBIDOS or (
                sufixo in EXTENSOES_PROIBIDAS and nome not in AMOSTRAS_PUBLICAS
            ):
                problemas.append(nome)
        ausentes = sorted(ARQUIVOS_OBRIGATORIOS - set(nomes))
        if ausentes:
            problemas.append("obrigatórios ausentes:" + ",".join(ausentes))
        if MANIFESTO_NOME not in nomes:
            problemas.append("manifesto ausente")
        else:
            try:
                manifesto = json.loads(zf.read(MANIFESTO_NOME).decode("utf-8"))
                if manifesto.get("versao") != VERSAO_PLATAFORMA:
                    problemas.append("versão incorreta no manifesto")
                registrados = {x["caminho"]: x for x in manifesto.get("arquivos", [])}
                esperados = set(nomes) - {MANIFESTO_NOME}
                if set(registrados) != esperados:
                    problemas.append("manifesto não corresponde ao conteúdo do ZIP")
                else:
                    for nome, item in registrados.items():
                        dados = zf.read(nome)
                        if len(dados) != item.get("tamanho") or sha256(dados).hexdigest() != item.get("sha256"):
                            problemas.append(f"hash/tamanho inválido:{nome}")
                            break
            except Exception as exc:
                problemas.append(f"manifesto inválido:{exc}")
    if problemas:
        raise RuntimeError("Pacote-fonte inválido: " + "; ".join(sorted(set(problemas))[:30]))


def empacotar(destino: str | Path = SAIDA_PADRAO) -> tuple[Path, int]:
    validar_registry()
    saida = Path(destino).expanduser().resolve()
    saida.parent.mkdir(parents=True, exist_ok=True)
    temporario = saida.with_suffix(saida.suffix + ".tmp")
    temporario.unlink(missing_ok=True)
    arquivos = [
        p for p in RAIZ.rglob("*")
        if p.is_file() and permitido(p) and p.resolve() not in {saida, temporario}
    ]
    relativos = {p.relative_to(RAIZ).as_posix() for p in arquivos}
    ausentes = sorted(ARQUIVOS_OBRIGATORIOS - relativos)
    if ausentes:
        raise RuntimeError("Fonte incompleta; arquivos obrigatórios ausentes: " + ", ".join(ausentes))

    try:
        with zipfile.ZipFile(temporario, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for arquivo in sorted(arquivos, key=lambda p: p.relative_to(RAIZ).as_posix()):
                nome = arquivo.relative_to(RAIZ).as_posix()
                zf.writestr(_info_zip(nome), arquivo.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            zf.writestr(_info_zip(MANIFESTO_NOME), _manifesto(arquivos), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        temporario.replace(saida)
        validar_zip(saida)
    except Exception:
        temporario.unlink(missing_ok=True)
        saida.unlink(missing_ok=True)
        raise
    return saida, len(arquivos)


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)
    if len(argumentos) > 1:
        raise SystemExit("Uso: empacotar_fonte_limpa.py [saida.zip]")
    saida, quantidade = empacotar(argumentos[0] if argumentos else SAIDA_PADRAO)
    print(f"Pacote-fonte V{VERSAO_PLATAFORMA} criado: {saida}")
    print(f"Arquivos incluídos: {quantidade} + {MANIFESTO_NOME}")
    print(f"Tamanho: {saida.stat().st_size / 1024 / 1024:.2f} MiB")
    print(f"SHA-256: {sha256(saida.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
