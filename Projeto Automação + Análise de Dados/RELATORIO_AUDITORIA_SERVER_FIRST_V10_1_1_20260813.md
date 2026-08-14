# Relatório de Auditoria Server First — Data Intelligence V10.1.1

Data da auditoria: 13/08/2026

## Objetivo

Eliminar persistência corporativa e autoridade transacional das estações Central/Cliente. Em produção, a estação deve atuar apenas como interface/cliente do Servidor Corporativo. O Servidor Corporativo é a única camada autorizada a executar operações de domínio, persistir dados e acessar PostgreSQL.

Arquitetura alvo:

```text
Central / Cliente
      |
      | HTTP(S) / RPC autenticado
      v
Servidor Corporativo :8770
      |
      | conexão PostgreSQL
      v
PostgreSQL :5432
```

Arquivos técnicos inevitáveis da estação (executável, `node.json`, logs e temporários estritamente necessários para um upload/abertura explícita) não são fonte de verdade corporativa. Não há banco corporativo local, preferências em JSON local nem fallback de produção para SQLite.

## Falhas confirmadas pelos logs enviados

O `server(1).log` mostrou 204 registros: 160 respostas HTTP 200, 21 HTTP 500 e 2 HTTP 400. Os 21 erros 500 se dividiram em quatro causas independentes:

- 17 ocorrências: `ModuleNotFoundError: No module named 'configuracoes'`.
- 1 ocorrência: `ModuleNotFoundError: No module named 'historico'`.
- 2 ocorrências: erro de parser PowerShell ao preparar regra de Firewall (`MissingStatementBlockForDataSection`).
- 1 ocorrência: `pg_dump` não localizado pelo serviço do Servidor Corporativo.

O `desktop(1).jsonl` mostrou ainda que Histórico e Configurações recebiam a falha RPC do servidor e que a preferência de sessão era repetidamente degradada para 30 minutos por indisponibilidade do módulo de configurações.

## Correções aplicadas

### 1. Empacotamento do Servidor Corporativo

`DataIntelligenceServer.spec` deixou de depender de uma lista manual de hidden imports. A superfície de empacotamento agora é derivada de `RPC_ALLOWLIST`, incluindo automaticamente módulos como:

- `configuracoes.preferencias`;
- `historico.repositorio`;
- todos os módulos `enterprise.*` autorizados pelo RPC.

Também são coletados os submódulos necessários de `enterprise`, `servidor_corporativo`, `servidor_ti`, `psycopg` e `psycopg_pool`.

### 2. Preflight completo do RPC no startup

Foi criado `validar_rpc_runtime()` e o Servidor Corporativo executa essa validação antes de ficar disponível. Todos os módulos e todas as funções autorizadas pelo RPC são importados e verificados.

Resultado: uma futura dependência esquecida no PyInstaller impede o servidor de iniciar/ficar ready, em vez de explodir somente quando o usuário clicar em uma tela específica.

### 3. PostgreSQL obrigatório

- `ConfigServidor` rejeita qualquer backend diferente de PostgreSQL.
- `auth.banco` usa PostgreSQL como padrão.
- Central/Cliente recebem bloqueio explícito caso qualquer código tente chamar `conectar()` ou `inicializar_banco()` diretamente.
- SQLite permanece somente em caminhos declarados de migração/teste ou como arquivo-fonte escolhido pelo usuário para importação.
- O servidor não aceita `--backend sqlite`.

### 4. Schema PostgreSQL validado no runtime

O bootstrap PostgreSQL passa a validar as tabelas esperadas no `information_schema`, inclusive extensões posteriores como:

- `historico_analises`;
- `preferencias_usuarios`.

### 5. Histórico e preferências somente no servidor

- Preferências são persistidas em `preferencias_usuarios` no banco corporativo.
- Histórico é persistido em `historico_analises`.
- Ambos passam pelo RPC na Central/Cliente.
- Nenhum `preferencias.json` é permitido pela auditoria.

### 6. Firewall TI corrigido

O PowerShell deixou de receber script + argumentos de texto ambíguos por `-Command`. Agora:

- o script é enviado por `-EncodedCommand` em UTF-16LE;
- nome da regra e CIDR entram exclusivamente por variáveis de ambiente;
- `shell=False`;
- falhas esperadas de Firewall são convertidas em erro operacional legível (HTTP 400), em vez de `Falha interna do servidor` genérica.

### 7. Backup PostgreSQL

A descoberta de `pg_dump`/`pg_restore` agora procura:

- PATH do serviço;
- `DATA_INTELLIGENCE_PG_BIN`;
- instalações padrão do PostgreSQL em `Program Files`, `ProgramW6432` e `Program Files (x86)` no Windows;
- diretórios usuais no Linux.

A ausência das ferramentas não derruba o servidor nem invalida o banco. O endpoint de backup retorna diagnóstico específico. O health detalhado também informa a disponibilidade das ferramentas.

### 8. Request ID e logs operacionais

- Respostas de erro incluem `X-Request-ID`.
- O cliente acrescenta o ID da requisição na mensagem de exceção.
- Logs JSON passaram a preservar `erro_operacional`, `modulo` e `funcao`.
- Erros de POST/GET no servidor registram request ID, método e caminho.

### 9. Relatórios e exportações Server First

Em Central/Cliente, relatórios gerados por RH, Estoque, Compras e Tecnologia não abrem mais `Salvar como`. É usado o destino lógico `server://...`; o Servidor Corporativo gera e persiste o arquivo diretamente no repositório corporativo e registra metadados no banco.

Também passam a permanecer no servidor, sem download automático:

- contracheques;
- relatórios financeiros;
- relatórios da Central de Ferramentas.

Uma cópia transitória só é permitida em operações explicitamente de abertura/uso (por exemplo, abrir um relatório já armazenado ou usar um dataset). A fonte de verdade permanece no servidor e os temporários são registrados para limpeza ao finalizar a sessão.

### 10. Exportação de grades

CSV/XLSX de grades são construídos em memória (`StringIO`/`BytesIO`) em modo remoto e enviados diretamente ao endpoint corporativo de exportações. A estação não precisa criar um arquivo persistente antes do upload.

### 11. Provisionamento do Agente TI

Foi removida a opção que gravava token de provisionamento em arquivo temporário local. Permanecem cópia para clipboard e fechamento da janela.

### 12. MFA

Foi adicionado bloqueio fail-closed antes da criação de qualquer segredo MFA na estação remota. Até existir uma tela dedicada via RPC, Central/Cliente não podem iniciar essa persistência local.

### 13. SQL PostgreSQL

Além das correções de `GROUP BY` que causaram a falha do cockpit, foi corrigida outra consulta em Compras que selecionava coluna não agrupada.

A auditoria automática percorreu e traduziu 930 literais SQL operacionais, verificando resíduos incompatíveis de SQLite como:

- `COLLATE NOCASE`;
- `IS ?`;
- `date('now', ...)` / `datetime('now', ...)`;
- `julianday`;
- `strftime`;
- `printf`;
- `sqlite_master`.

Nenhum resíduo proibido permaneceu nos caminhos operacionais PostgreSQL auditados.

## Barreira automática de arquitetura

Foi criado `scripts/auditar_autoridade_servidor.py` e ele é chamado automaticamente por:

- `scripts/build_setup_windows.ps1`;
- `scripts/build_distribuicao_windows.ps1`.

O build agora falha se detectar regressões como:

- SQLite operacional inesperado;
- `preferencias.json`;
- UI/serviços importando `auth.banco`;
- Central/Cliente sem bloqueio de conexão direta;
- módulo/função RPC ausente;
- módulo RPC fora do pacote do servidor;
- backend do servidor diferente de PostgreSQL;
- Firewall voltando ao PowerShell inseguro;
- token do Agente sendo salvo localmente;
- exportação remota voltando a usar arquivo local;
- relatório departamental voltando a abrir `Save As` local;
- MFA escrevendo segredo antes de chegar ao servidor;
- sintaxe SQLite residual nos SQLs operacionais.

Resultado final da barreira:

```text
Arquivos Python de produção auditados: 222
Linhas Python de produção auditadas: 51363
Módulos RPC auditados: 18
Operações RPC auditadas: 299
Literais SQL operacionais traduzidos/auditados: 930
AUDITORIA SERVER FIRST: APROVADA
```

## Testes

Suíte padrão dividida por arquivos/processos:

- 330 testes aprovados;
- 16 ignorados por dependerem de recursos externos/gráficos;
- 0 falhas nos grupos concluídos após as correções.

Validação gráfica real em Xvfb:

```text
36 passed, 90 subtests passed
```

Também passaram:

```text
python -m compileall -q .
python scripts/auditar_autoridade_servidor.py
python scripts/verificar_instalador_v10.py
python scripts/verificar_instalador_v10_1.py
```

## Limitações do ambiente de auditoria

O ambiente desta auditoria é Linux/Python 3.13.5 e não possui:

- servidor PostgreSQL (`postgres`/`initdb`);
- `psycopg`;
- `pg_dump`/`pg_restore`;
- PowerShell do Windows;
- Inno Setup (`ISCC.exe`).

Por isso não é correto afirmar que a integração física com o seu PostgreSQL Windows ou a compilação Inno/PyInstaller Windows foram executadas aqui. O teste `test_v10_1_postgresql_integration.py` permanece condicionado a um PostgreSQL real.

A suíte completa de screenshots também excedeu o limite de execução deste ambiente; os smokes Tk reais acima foram concluídos com sucesso.

## Procedimento no Windows

1. Substituir o código-fonte pela versão desta auditoria.
2. Gerar a distribuição completa:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

3. O build executará automaticamente a barreira Server First e os validadores antes de gerar a distribuição.
4. Instalar o novo `DataIntelligence_Setup_V10.1.1.exe`.
5. No PC servidor, confirmar:
   - Servidor Corporativo na porta 8770;
   - PostgreSQL na porta configurada (normalmente 5432);
   - `/api/v1/health/ready` respondendo 200;
   - `server.log` sem ERROR no startup.
6. Só então testar Central/Cliente.

## Resultado arquitetural

A estação deixou de ser uma autoridade paralela. O projeto fica protegido por código + testes + build contra retorno acidental de banco corporativo local. Dados transacionais, preferências, histórico, relatórios gerados e artefatos corporativos são dirigidos ao Servidor Corporativo/PostgreSQL; operações locais restantes são apenas bootstrap técnico, diagnóstico ou trânsito explícito necessário para importar/abrir um arquivo solicitado pelo usuário.
