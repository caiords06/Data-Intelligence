"""Gera o pacote-fonte canônico, limpo, determinístico e verificável da V9.3.

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

from core.versao import PYTHON_RELEASE_TEXTO, VERSAO_PLATAFORMA
from enterprise.migrations import validar_registry

SAIDA_PADRAO = RAIZ / "release" / f"DataIntelligence-Source-V{VERSAO_PLATAFORMA}.zip"
MANIFESTO_NOME = "SOURCE_MANIFEST.json"
DATA_ZIP_DETERMINISTICA = (2026, 8, 12, 0, 0, 0)

DIRETORIOS_PERMITIDOS = {
    ".github", "agente_ti", "analysis", "analytics", "assets", "auth", "automacao",
    "configuracoes", "core", "dados", "docs", "enterprise", "historico", "interface",
    "scripts", "services", "servidor", "servidor_corporativo", "servidor_ti",
    "sistema", "tests",
}
ARQUIVOS_RAIZ_PERMITIDOS = {
    ".gitignore", ".gitattributes", ".python-version", "app.py", "main.py", "pytest.ini",
    "requirements.txt", "requirements.lock.txt", "requirements-agent.txt",
    "requirements-agent.lock.txt", "requirements-agent-build.txt",
    "requirements-build.txt", "requirements-build.lock.txt",
    "DataIntelligencePlatform.spec", "DataIntelligenceServer.spec", "agente_ti.spec",
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
    "agente_ti.spec",
    "scripts/build_distribuicao_windows.ps1",
    "scripts/verificar_fonte_reproduzivel.py",
    "enterprise/migrations/__init__.py",
    "core/versao.py",
    "VERSAO_V9_3.txt",
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
