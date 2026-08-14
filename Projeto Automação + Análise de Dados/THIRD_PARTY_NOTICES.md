# Avisos de terceiros

Este produto usa bibliotecas Python declaradas em `requirements.lock.txt`, `requirements-build.lock.txt` e `requirements-agent.lock.txt`. `DEPENDENCY_INVENTORY.md` consolida as versões diretas fixadas; o CI gera o artefato completo `artifacts/sbom.cdx.json` a partir do ambiente resolvido.

Antes de distribuição comercial, o responsável pelo release deve executar a auditoria de licenças e vulnerabilidades no ambiente Python 3.14 do build, revisar licenças transitivas e anexar os textos exigidos por cada licença. Este arquivo não substitui os avisos originais dos projetos.

Ativos gráficos de marca fornecidos pelo titular estão documentados em `assets/brand/ASSET_PROVENANCE.md`.
