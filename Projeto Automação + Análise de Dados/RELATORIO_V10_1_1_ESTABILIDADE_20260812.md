# Relatório técnico — Data Intelligence V10.1.1 · Estabilidade e Correção Server First

Data da revisão: 12/08/2026

## 1. Escopo

A revisão foi executada sobre o pacote-fonte fornecido para homologação da V10.1.0. Foram inspecionados código Python, autenticação, sessões, persistência SQLite/PostgreSQL, RPC, Servidor Corporativo, Central, Cliente, Agente TI, instalador Inno Setup, tarefas do Windows, scripts de deployment, build/release, documentação ativa e suíte automatizada.

O objetivo da V10.1.1 é eliminar os defeitos reproduzidos durante a instalação real e impedir que uma falha de configuração faça Central/Cliente se tornarem uma segunda fonte de verdade.

## 2. Defeitos reproduzidos durante a homologação

### 2.1 Registro do Servidor no Task Scheduler

A V10.1.0 montava `schtasks /Create` através de `cmd.exe` com aspas aninhadas para um executável em `C:\Program Files\Data Intelligence\...`. No Windows isso foi reproduzido como quebra do argumento em `Files\Data` e obrigou a criação manual da tarefa.

**Correção:** Servidor e Agente agora usam uma infraestrutura comum (`core/windows_tasks.py`) baseada em `New-ScheduledTaskAction`, passando caminho e argumentos separadamente por variáveis de ambiente. O Setup não usa mais `/TR` para registrar os executáveis.

### 2.2 Instalação parcial deixava a Central sem configuração

O pós-install anterior executava `ConfigureServer()` antes de `WriteNodeConfig()`. Se a tarefa do servidor falhasse, a instalação era interrompida antes de gravar o papel da estação. Uma Central podia então iniciar com comportamento local/standalone e criar registros fora da autoridade PostgreSQL.

**Correção:** `WriteNodeConfig()` é executado primeiro. Além disso, um executável empacotado sem `node.json` agora falha fechado, com mensagem de reparo/reinstalação, em vez de adotar `standalone` silenciosamente.

### 2.3 `node.json` com UTF-8 BOM derrubava a aplicação

Um `node.json` criado pelo PowerShell com BOM produziu `JSONDecodeError: Unexpected UTF-8 BOM`.

**Correção:** leitura com `utf-8-sig` em `core/nodo.py` e nos demais JSONs operacionais. O Setup e scripts de configuração gravam explicitamente UTF-8 sem BOM.

### 2.4 Bootstrap do administrador no PostgreSQL

Foi reproduzida uma consulta `sqlite_master` durante `init-admin`, inválida no PostgreSQL.

**Correção:** consultas parametrizadas/literais são traduzidas para `information_schema.tables`; os caminhos conhecidos foram normalizados e há regressão específica.

### 2.5 Schema PostgreSQL e encerramento do pool

Foram reproduzidos `IFNULL(...)` no schema PostgreSQL, mascaramento de erro de SQL por alteração de `autocommit` em conexão abortada e `PythonFinalizationError` do `psycopg_pool` em comandos curtos.

**Correção:** `COALESCE`, rollback antes de restaurar autocommit, preservação da exceção original e fechamento explícito do pool em CLI.

## 3. Correções adicionais encontradas na auditoria integral

### 3.1 Server First / split-brain

Foram revisadas as fachadas consumidas por UI/Services. Gestão de permissões, perfis, empresas, filiais, departamentos, centros de custo, nós legados e arquivamento de documentos agora estão cobertos pela política RPC quando a estação usa Servidor Corporativo.

Foi adicionado um teste estrutural que compara as fachadas departamentais com a allowlist/bloqueios RPC. Uma nova função transacional adicionada ao Service sem política remota passa a falhar no teste.

### 3.2 Backup agendado da Central

A rotina podia solicitar um backup remoto e, em seguida, tentar reenviar `resultado["arquivo"]`, chave que não existe na resposta server-side. A exceção era silenciosa.

**Correção:** Central conectada apenas solicita `criar_backup(ator)` ao Servidor. Não existe fallback para backup do cache local.

### 3.3 SQL SQLite ainda vazando para PostgreSQL

A liberação de reserva do Estoque usava `MAX(0, quantidade_reservada-?)` como função escalar. SQLite aceita essa forma; PostgreSQL trata `MAX` como agregação e rejeitaria a expressão.

**Correção:** SQL portátil com `CASE`. A auditoria também reforçou tradução de `LIKE`→`ILIKE`, offsets genéricos de data/hora e `lastrowid` por sequence da tabela.

### 3.4 Caminhos divergentes entre Setup e scripts fallback

O Setup instalava em `C:\Program Files\Data Intelligence\...`, mas scripts do Agente e desinstalador do Servidor ainda procuravam `C:\Program Files\DataIntelligence\...`.

**Correção:** todos os scripts ativos usam os mesmos caminhos do Setup. Os instaladores fallback encerram tarefas antigas antes de substituir binários. O fallback do Servidor também ganhou migração SQLite→PostgreSQL e rollback de tarefa em falha.

### 3.5 Upgrade com processos ainda ativos

Uma atualização poderia tentar substituir `DataIntelligenceServer.exe`/Agente enquanto a tarefa antiga continuava executando.

**Correção:** o Setup usa `PrepareToInstall` para encerrar as tarefas antigas antes da etapa de cópia; scripts fallback fazem o mesmo.

### 3.6 Provisionamento do Agente

O Setup configurava e registrava o Agente sem confirmar que Server URL, Agent ID e token realmente funcionavam.

**Correção:** um heartbeat real (`once`) é exigido antes da instalação da tarefa. Se o início da tarefa falhar, a tarefa parcial é removida.

### 3.7 Auditoria com versão antiga

`auth/banco.py` ainda registrava `V8.2` de forma fixa em eventos de auditoria.

**Correção:** usa `VERSAO_INTERFACE` de `core/versao.py`.

### 3.8 Documentação contraditória no deployment

O build ainda copiava documentação V9.1 que dizia que o banco operacional era SQLite, contradizendo a V10.1 Server First.

**Correção:** deployment passa a incluir documentação V10.1.1/Server First atual. Relatórios antigos continuam apenas como histórico da evolução do projeto.

## 4. Segurança e persistência

- senha PostgreSQL não é gravada em `server.json`;
- segredo Windows usa DPAPI com escopo de máquina;
- diretório/arquivo de segredo recebe ACL para SYSTEM e Administradores;
- token do Agente não é gravado em `agent.json`;
- senhas de usuários não são persistidas no cache remoto; o cache recebe hash aleatório inutilizável para autenticação;
- upload corporativo permanece streaming e valida SHA-256;
- Central/Cliente não fazem fallback transacional para SQLite quando o Servidor fica indisponível.

## 5. Operações de arquivo ainda deliberadamente separadas

As operações que dependem de um arquivo físico da estação e ainda não possuem contrato dedicado de upload/download permanecem em `RPC_BLOQUEADAS_REMOTO`. Exemplos: determinadas importações, anexos e geração/abertura local de relatórios.

Nesta release de estabilidade elas **não** são redirecionadas de forma improvisada nem executadas no cache local. O sistema falha explicitamente informando que o fluxo de arquivo precisa de transporte específico. Isso evita split-brain e perda silenciosa de documentos. A implementação de um file-RPC genérico foi deliberadamente evitada nesta versão porque aumentaria a superfície de segurança e regressão.

## 6. Validação executada

- `compileall`: aprovado;
- `tabnanny`: aprovado;
- validadores estáticos do instalador V10/V10.1: aprovados;
- regressões V10.1.1: 20 aprovadas;
- fluxo end-to-end de usuário remoto: administrador entra no Servidor, cria usuário, aplica perfil, novo usuário autentica por `/api/v1/auth/login` e recebe contexto/permissões: aprovado;
- grupos 1, 2, 3, 4 e 6 da matriz oficial: aprovados;
- grupo 5 inicialmente acusou apenas a ausência deste próprio relatório obrigatório; após sua inclusão, foi reexecutado antes do empacotamento final.

A matriz completa final foi reexecutada após a inclusão deste relatório e ficou integralmente verde nas verificações executáveis deste ambiente.

## 7. Limitações de homologação deste ambiente

Este ambiente não é Windows. Portanto ele não compila nem executa o `Setup.exe`, não cria tarefas reais do Windows e não reproduz DPAPI/Firewall localmente. O código usa exatamente o mecanismo `ScheduledTasks` que foi validado manualmente na máquina Windows durante a homologação, e os validadores estáticos estão verdes.

O teste PostgreSQL real também depende de `RUN_POSTGRES_INTEGRATION=1` e de um servidor PostgreSQL disponível. Neste ambiente ele permanece ignorado; o workflow de CI deve manter PostgreSQL real como gate, e a instalação Windows deve ser homologada novamente com o PostgreSQL 18 usado no laboratório.

## 8. Procedimento de build Windows

Na raiz da fonte V10.1.1:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

O script limpa `build`, `dist` e `release`, executa regressões, smoke Tk real no Windows, gera os três binários, deployment, pacote-fonte e `DataIntelligence_Setup_V10.1.1.exe`.

## 9. Resultado final da matriz

Matriz oficial completa, executada em processos isolados por arquivo:

- Grupo 1: 56 aprovados + 4 subtestes;
- Grupo 2: 40 aprovados + 1 gráfico ignorado + 15 subtestes;
- Grupo 3: 41 aprovados + 10 gráficos ignorados + 11 subtestes;
- Grupo 4: 59 aprovados + 1 integração PostgreSQL real ignorada neste ambiente;
- Grupo 5: 53 aprovados + 1 gráfico ignorado + 87 subtestes;
- Grupo 6: 33 aprovados + 3 gráficos ignorados + 47 subtestes.

**Total: 282 testes aprovados, 16 ignorados condicionais/headless, 164 subtestes aprovados e zero falhas nos testes executáveis deste ambiente.**

Além da matriz, `compileall`, `tabnanny` e os dois validadores estáticos do instalador foram aprovados. A varredura de código/scripts cobriu 230 arquivos Python/PowerShell/Inno/SQL, aproximadamente 54,9 mil linhas, além da documentação e configuração de release. Não foram encontrados segredos estáticos óbvios nos diretórios operacionais auditados.

## 10. Artefato

O pacote-fonte final desta release é gerado pelo empacotador determinístico `scripts/empacotar_fonte_limpa.py`, com `SOURCE_MANIFEST.json`, hashes por arquivo, bloqueio de banco/log/cache/build/dist/release e validação de arquivos obrigatórios.

Nome canônico de entrega:

`Projeto_Automacao_Analise_Dados_V10_1_1_ESTABILIDADE_20260812.zip`

O SHA-256 externo do ZIP é calculado após o empacotamento final e registrado no relatório de entrega que acompanha o artefato, evitando circularidade de hash dentro do próprio pacote.
