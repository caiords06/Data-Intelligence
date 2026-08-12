# Data Intelligence V9.3 — Release Engineering + Zero Defects

A V9.3 é uma versão de estabilização. Ela não cria um novo módulo empresarial; fecha a cadeia de migrations, testes, build e distribuição para que o mesmo código validado seja o código entregue.

## Fonte oficial

Não compacte manualmente a pasta do projeto. O único pacote-fonte oficial é gerado por:

```powershell
python scripts\empacotar_fonte_limpa.py
```

O ZIP resultante exclui `.git`, `build`, `dist`, `release`, `storage`, banco, logs, caches e artefatos visuais. Ele contém `SOURCE_MANIFEST.json` com tamanho e SHA-256 de cada arquivo.

Para verificar uma entrega já criada:

```powershell
python scripts\verificar_fonte_reproduzivel.py release\DataIntelligence-Source-V9.3.0.zip
python scripts\verificar_fonte_reproduzivel.py release\DataIntelligence-Source-V9.3.0.zip --grupo 1
python scripts\verificar_fonte_reproduzivel.py release\DataIntelligence-Source-V9.3.0.zip --grupo 2
python scripts\verificar_fonte_reproduzivel.py release\DataIntelligence-Source-V9.3.0.zip --grupo 3
```

## Python e dependências

O release oficial usa Python 3.14. O script de build cancela a execução se outro Python estiver ativo.

- `requirements.txt`: faixas aceitas para desenvolvimento.
- `requirements.lock.txt`: versões diretas homologadas para o release.
- `requirements-build.lock.txt`: PyInstaller e pytest do release.
- `requirements-agent.lock.txt`: runtime travado do agente.

## Migrations

`enterprise/migrations/` contém exatamente uma migration por número e o conteúdo físico precisa corresponder ao tuple `MIGRACOES`. O CI e o empacotador executam essa validação.

As previews antigas `013_plataforma_distribuida.py` e `014_consistencia_monetaria.py` foram removidas da pasta executável; sua origem e hashes estão em `docs/MIGRATIONS_LEGADAS_V9_3.md`.

## Build Windows

O build oficial é:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

Ele valida Python, instala locks, executa regressões e smoke Tk, compila os três `.spec`, monta a distribuição e verifica que o pacote final não contém dados operacionais.
