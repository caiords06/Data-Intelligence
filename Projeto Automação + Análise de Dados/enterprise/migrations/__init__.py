"""Migrações versionadas e idempotentes do banco empresarial."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import re


MIGRACOES = (
    "001_v6_estabilizacao",
    "002_v8_recursos_departamentais",
    "003_v8_1_integridade",
    "004_v8_2_estabilizacao",
    "005_financeiro_departamental",
    "006_rh_departamental",
    "007_rh_2_0_complementos",
    "008_estoque_departamental",
    "009_compras_departamental",
    "010_tecnologia_departamental",
    "011_tecnologia_operacoes_rede",
    "012_segmentos_rede_multifilial",
    "013_agentes_ti_api",
    "014_colaboracao_email_sessoes",
    "015_aprovacoes_compras",
    "016_relatorios_formatos",
    "017_consistencia_monetaria_aprovacoes",
    "018_caminhos_rh_portaveis",
    "019_compatibilidade_v9_legada",
)


def validar_registry(pasta: str | Path | None = None) -> tuple[str, ...]:
    """Falha se os arquivos de migration divergirem do registry canônico.

    Esta validação é executada no CI/empacotamento, e não automaticamente no
    runtime congelado do PyInstaller, onde os módulos podem não existir como
    arquivos físicos no mesmo diretório.
    """
    raiz = Path(pasta) if pasta is not None else Path(__file__).resolve().parent
    arquivos = tuple(p.stem for p in sorted(raiz.glob("[0-9][0-9][0-9]_*.py")))
    if arquivos != MIGRACOES:
        ausentes = [x for x in MIGRACOES if x not in arquivos]
        extras = [x for x in arquivos if x not in MIGRACOES]
        raise RuntimeError(
            "Registry de migrations divergente. "
            f"Ausentes={ausentes or 'nenhuma'}; extras={extras or 'nenhuma'}."
        )
    numeros = [re.match(r"^(\d{3})_", nome).group(1) for nome in arquivos]
    duplicados = sorted({n for n in numeros if numeros.count(n) > 1})
    if duplicados:
        raise RuntimeError("Números de migration duplicados: " + ", ".join(duplicados))
    return arquivos


def aplicar_migracoes(conexao) -> None:
    """Aplica, em ordem, somente migrações ainda não registradas."""
    for nome in MIGRACOES:
        chave = f"enterprise_{nome}"
        aplicada = conexao.execute(
            "SELECT 1 FROM migracoes_sistema WHERE chave = ?",
            (chave,),
        ).fetchone()
        if aplicada is not None:
            continue

        modulo = import_module(f"enterprise.migrations.{nome}")
        modulo.upgrade(conexao)
        conexao.execute(
            "INSERT INTO migracoes_sistema (chave) VALUES (?)",
            (chave,),
        )
