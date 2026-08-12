# Data Intelligence Enterprise Platform — V9.3.0

## Objetivo da versão

A V9.3 é uma versão de **Release Engineering + Zero Defects**. O objetivo principal é estabilizar a base atual antes de novas expansões funcionais, removendo ambiguidades de migrations, tornando o pacote-fonte reproduzível e criando uma cadeia de validação coerente entre desenvolvimento, CI e build Windows.

## Correções e endurecimentos

- Remoção dos arquivos históricos de migration `013_plataforma_distribuida.py` e `014_consistencia_monetaria.py` da pasta canônica de migrations.
- Registry de migrations validado contra os arquivos físicos e bloqueio de prefixos numéricos duplicados.
- Compatibilidade histórica preservada pelas migrations posteriores já canônicas e documentada em `docs/MIGRATIONS_LEGADAS_V9_3.md`.
- Versão centralizada em `core/versao.py`: plataforma `9.3.0`, interface `V9.3` e Python oficial de release `3.14`.
- `.python-version` e `.gitattributes` adicionados para padronização do ambiente e dos finais de linha.
- Dependências diretas de release travadas em `requirements.lock.txt`, `requirements-agent.lock.txt` e `requirements-build.lock.txt`.
- Build Windows bloqueia versão de Python incompatível antes de instalar dependências ou gerar executáveis.
- Build oficial usa exclusivamente os specs reais: `DataIntelligencePlatform.spec`, `DataIntelligenceServer.spec` e `agente_ti.spec`.
- Pacote-fonte gerado por allowlist; banco, logs, Git, caches, builds, releases e dados operacionais são recusados.
- Pacote-fonte contém `SOURCE_MANIFEST.json` com tamanho e SHA-256 de cada arquivo.
- ZIP-fonte é determinístico: ordenação, timestamp e permissões das entradas são controlados.
- Verificador de fonte extrai o ZIP em diretório limpo, valida conteúdo, compila o Python e permite executar cada grupo de testes em processo independente.
- Workflow de CI dividido em grupos independentes, testes do pacote-fonte, smoke visual com Xvfb em 1366×768 e 1600×900 e build PyInstaller em Windows/Python 3.14.
- O build de distribuição Windows agora gera tanto o deployment quanto o pacote-fonte limpo e os valida no mesmo fluxo.

## Validação funcional nesta revisão

Na validação local desta V9.3, a suíte foi separada nos mesmos três grupos usados pelo CI para impedir contaminação de estado entre testes de rede/servidor:

- Grupo 1: 81 testes aprovados; 19 subtestes aprovados.
- Grupo 2: 51 testes aprovados; 11 testes gráficos ignorados no ambiente sem display; 11 subtestes aprovados.
- Grupo 3: 55 testes aprovados; 3 testes gráficos ignorados no ambiente sem display.
- Total: **187 testes aprovados, 14 testes gráficos ignorados, 30 subtestes aprovados e zero falhas**.

Os testes gráficos ignorados localmente são executados no CI com Xvfb. O workflow também possui job Windows/Python 3.14 para compilar os três artefatos PyInstaller.

## Limitação do ambiente desta auditoria

O ambiente usado para esta implementação executa Linux com Python 3.13.5. Por isso, o build Windows/Python 3.14 não pode ser homologado localmente nesta sessão. A V9.3 trata isso explicitamente: `scripts/verificar_python_release.py` recusa a versão local para release oficial e o GitHub Actions executa o build final no ambiente Windows/Python 3.14 correspondente.

## Regra de release daqui para frente

Não compacte manualmente a pasta do projeto. O pacote-fonte oficial deve ser criado por:

```bash
python scripts/empacotar_fonte_limpa.py
```

E validado por:

```bash
python scripts/verificar_fonte_reproduzivel.py release/DataIntelligence-Source-V9.3.0.zip
python scripts/verificar_fonte_reproduzivel.py release/DataIntelligence-Source-V9.3.0.zip --grupo 1
python scripts/verificar_fonte_reproduzivel.py release/DataIntelligence-Source-V9.3.0.zip --grupo 2
python scripts/verificar_fonte_reproduzivel.py release/DataIntelligence-Source-V9.3.0.zip --grupo 3
```

No Windows, `scripts/build_distribuicao_windows.ps1` executa o fluxo oficial completo.
