"""Audita a arquitetura em camadas da V11.1.0.

Falha quando a UI volta a importar ``enterprise.*`` diretamente ou quando os
contratos centrais (services, API pública, migrations e Analytics decisório)
ficam incompletos. É intencionalmente estático para ser rápido no CI/build.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

DEPARTAMENTOS = (
    "financeiro", "rh", "estoque", "compras", "tecnologia",
    "marketing", "comercial", "administrativo", "juridico",
)
ANALYTICS_OBRIGATORIOS = {
    "visao", "insights", "conjuntos", "alertas", "relatorios",
    "visualizacoes", "agendamentos", "nova", "importacoes", "regras",
}
ANALYTICS_PLACEHOLDERS = {"modelos", "assistente", "perfis"}


def _imports_enterprise(caminho: Path) -> list[tuple[int, str]]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8-sig"), filename=str(caminho))
    achados: list[tuple[int, str]] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                if alias.name == "enterprise" or alias.name.startswith("enterprise."):
                    achados.append((no.lineno, alias.name))
        elif isinstance(no, ast.ImportFrom):
            modulo = no.module or ""
            if modulo == "enterprise" or modulo.startswith("enterprise."):
                achados.append((no.lineno, modulo))
    return achados


def auditar() -> list[str]:
    problemas: list[str] = []

    for arquivo in sorted((RAIZ / "interface").rglob("*.py")):
        for linha, modulo in _imports_enterprise(arquivo):
            problemas.append(f"UI contorna services: {arquivo.relative_to(RAIZ)}:{linha} -> {modulo}")

    for modulo in DEPARTAMENTOS:
        caminho = RAIZ / "services" / "departamentos" / f"{modulo}.py"
        if not caminho.is_file():
            problemas.append(f"service departamental ausente: {caminho.relative_to(RAIZ)}")

    for caminho in (
        RAIZ / "services" / "analytics.py",
        RAIZ / "services" / "crm.py",
        RAIZ / "services" / "orquestracao.py",
        RAIZ / "servidor_corporativo" / "api_v1.py",
        RAIZ / "enterprise" / "analytics_inteligencia.py",
        RAIZ / "enterprise" / "orquestracao.py",
        RAIZ / "services" / "core_empresarial.py",
        RAIZ / "services" / "funcionario_360.py",
        RAIZ / "services" / "operacoes_v11.py",
        RAIZ / "enterprise" / "core_v11" / "registros.py",
        RAIZ / "enterprise" / "core_v11" / "funcionarios.py",
    ):
        if not caminho.is_file():
            problemas.append(f"contrato arquitetural ausente: {caminho.relative_to(RAIZ)}")

    try:
        from interface.navegacao_analytics import MENU_ANALYTICS
        chaves = {item[0] for item in MENU_ANALYTICS}
        faltantes = sorted(ANALYTICS_OBRIGATORIOS - chaves)
        indevidos = sorted(ANALYTICS_PLACEHOLDERS & chaves)
        if faltantes:
            problemas.append("Analytics sem destinos canônicos: " + ", ".join(faltantes))
        if indevidos:
            problemas.append("Analytics expõe placeholders como produto pronto: " + ", ".join(indevidos))
    except Exception as exc:
        problemas.append(f"falha ao carregar navegação Analytics: {exc}")

    try:
        from enterprise.migrations import MIGRACOES, validar_registry
        validar_registry()
        if not MIGRACOES[-5:] == (
            "024_v10_4_analytics_inteligencia", "025_v10_4_1_inteligencia_transversal",
            "026_hardening_producao", "027_v11_core_empresarial", "028_v11_1_conformidade",
        ):
            problemas.append("registry final não contém Analytics + orquestração + hardening + CORE V11 + conformidade")
    except Exception as exc:
        problemas.append(f"migrations inválidas: {exc}")

    return problemas


def main() -> int:
    problemas = auditar()
    if problemas:
        print("AUDITORIA DE CAMADAS: REPROVADA", file=sys.stderr)
        for problema in problemas:
            print(f" - {problema}", file=sys.stderr)
        return 1
    print("AUDITORIA DE CAMADAS: APROVADA")
    print("UI -> services -> domínio/repositório -> autoridade Server First")
    print(f"Services departamentais: {len(DEPARTAMENTOS)}/9")
    print("Analytics decisório + API v1 + orquestração: presentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
