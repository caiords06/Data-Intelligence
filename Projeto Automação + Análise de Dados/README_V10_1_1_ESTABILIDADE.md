# V10.1.1 — Estabilidade e correção Server First

A V10.1.1 é uma release de estabilização sobre a V10.1.0, criada a partir da homologação real no Windows e de uma nova auditoria integral do código-fonte. O princípio desta entrega é explícito: **Servidor Corporativo é a autoridade transacional; Central e Cliente não podem virar autoridades locais por falha de instalação, configuração ou rede.** SQLite foi removido da persistência de produção e permanece somente em migração/testes explicitamente habilitados.

## Correções de instalação e `node.json`

- `node.json` aceita UTF-8 puro e UTF-8 com BOM (`utf-8-sig`).
- executável distribuído sem `node.json` falha fechado; não cai silenciosamente em `standalone`;
- o Setup grava o papel da estação antes de configurar Servidor/Agente, evitando uma Central parcialmente instalada tentar operar sem a autoridade PostgreSQL;
- todos os JSONs/bootstraps gerados pelo Setup são gravados em UTF-8 sem BOM;
- scripts alternativos de Central/Cliente também gravam UTF-8 sem BOM e validam `/api/v1/health/ready`;
- build oficial limpa `build`, `dist` e `release` automaticamente.

## Tarefas Windows sem intervenção manual

- removido o caminho frágil `cmd.exe /C schtasks /Create ... /TR ...`;
- Servidor e Agente registram suas tarefas por `New-ScheduledTaskAction`, separando executável de argumentos e aceitando corretamente `C:\Program Files\Data Intelligence\...`;
- Setup encerra tarefas antigas antes de substituir executáveis em upgrades;
- Setup inicia o Servidor, aguarda `/health/ready` e só conclui após confirmar prontidão;
- falha após registro de tarefa executa rollback best-effort para não deixar tarefa parcial;
- Agente executa um heartbeat real antes de instalar a tarefa automática;
- scripts alternativos de instalação/desinstalação usam os mesmos caminhos do Setup unificado.

## Server First reforçado

- criação/listagem/alteração de usuários usa o Servidor em Central/Cliente;
- permissões e aplicação de perfis são RPC do Servidor Corporativo;
- empresas, filiais, departamentos e centros de custo são RPC do Servidor;
- adapter legado de nós da plataforma não grava no cache de estações conectadas;
- `arquivar_documento` foi incluído no RPC corporativo;
- fachadas departamentais possuem regressão que impede novas operações transacionais de escaparem da política RPC;
- UI/Services não acessam `auth.banco`/SQLite diretamente para CRUD empresarial;
- sessão remota é revalidada no Servidor e atualiza apenas o cache mínimo de identidade/contexto;
- indisponibilidade de rede vira erro operacional tratável, não traceback de callback Tk;
- backup agendado da Central solicita um único backup autoritativo no Servidor; foi removido o antigo fluxo de upload duplo/inválido do cache.

## PostgreSQL

- schema gerado não contém `IFNULL`; usa `COALESCE`;
- verificações `sqlite_master` são traduzidas para `information_schema`;
- bootstrap preserva a exceção SQL original e restaura transação/autocommit corretamente;
- pool Psycopg é fechado em comandos CLI curtos;
- `LIKE` legado é traduzido para `ILIKE`, preservando buscas case-insensitive esperadas da UI;
- offsets `date('now', ...)` / `datetime('now', ...)` possuem tradução genérica adicional;
- `lastrowid` usa a sequence da tabela inserida (`pg_get_serial_sequence` + `currval`), não `LASTVAL()` global;
- Estoque deixou de usar `MAX(0, expressão)` como função escalar SQLite e passou a SQL portátil com `CASE`;
- segredo PostgreSQL continua fora do `server.json`, protegido por DPAPI de máquina e ACL para SYSTEM/Administradores no Windows.

## Consistência de release/documentação

- versão canônica: `10.1.1` / `V10.1.1`;
- auditoria deixou de registrar a versão fixa antiga `V8.2` e usa a versão canônica;
- documentação de deployment ativa foi atualizada para V10.1.1/porta 8770/PostgreSQL;
- o pacote de distribuição não inclui mais READMEs V9.1 contraditórios como documentação principal;
- `servidor/` permanece somente como legado histórico/testado; o build oficial usa `servidor_corporativo/`;
- `servidor_ti/` conserva componentes de autenticação/heartbeat e o receptor 8765 apenas para standalone; em Server First o Agente usa `:8770`.

## Operações de arquivo

As funções que dependem de arquivos da estação continuam fora do RPC JSON genérico, mas agora possuem **fluxo dedicado de upload/download em streaming**. Importações enviam somente o arquivo necessário ao Servidor Corporativo; relatórios e documentos gerados no servidor retornam por um canal binário controlado; datasets são baixados para cópia transitória apenas quando o usuário escolhe utilizá-los. Nenhuma dessas operações usa banco corporativo local na Central ou no Cliente.

## Build oficial no Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

Não apague manualmente `build`, `dist` ou `release`: o script faz a limpeza antes do build.
