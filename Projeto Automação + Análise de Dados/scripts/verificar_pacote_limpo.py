"""Falha o build se a distribuição contiver dados operacionais ou resíduos de desenvolvimento."""
from __future__ import annotations
from pathlib import Path
import sys

raiz=Path(sys.argv[1] if len(sys.argv)>1 else "release/DataIntelligence-Deployment").resolve()
proibidos={".git",".pytest_cache","__pycache__","app.db",".coverage"}
extensoes={".pyc",".pyo",".db-wal",".db-shm"}
problemas=[]
for p in raiz.rglob("*") if raiz.exists() else []:
    partes=set(p.parts)
    if any(x in partes for x in {".git",".pytest_cache","__pycache__"}) or p.name in proibidos or p.suffix.lower() in extensoes:
        problemas.append(str(p.relative_to(raiz)))
    # screenshots/test artifacts are never deployment content
    if p.is_file() and (p.name.lower().startswith(("screenshot_","sheet_")) or "manifesto_visual" in p.name.lower()):
        problemas.append(str(p.relative_to(raiz)))
if problemas:
    print("Pacote contém conteúdo proibido:")
    print("\n".join(sorted(set(problemas))[:100]))
    raise SystemExit(2)
print("Pacote sanitizado: nenhum banco operacional, .git, cache ou bytecode encontrado.")
