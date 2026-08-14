# Hotfix PostgreSQL do instalador — 12/08/2026

## Sintoma

O Setup V10.1.1 interrompia a instalação com:

`Falha ao conectar/configurar o PostgreSQL. Confira host, banco, usuário, senha e SSL mode.`

## Causa raiz

O instalador gravava `C:\ProgramData\DataIntelligence\Server\server.json` com
`db_backend=postgresql` **antes** de o comando `configure-db` proteger a senha e
gravar `postgres_segredo`.

Na sequência, `configure-db` chamava `carregar_config()`. Como a configuração
PostgreSQL já estava marcada como ativa, a validação exigia `postgres_segredo` e
rejeitava o próprio arquivo parcial criado pelo Setup. Portanto a instalação podia
falhar antes mesmo de testar host, porta, usuário ou senha do PostgreSQL.

## Correção

- O Setup não grava mais `server.json` parcial.
- `configure-db` recebe também porta/configuração do Servidor Corporativo e grava
  a configuração completa somente depois de preparar o segredo e validar a conexão.
- `configure-db` consegue recuperar automaticamente o `server.json` parcial deixado
  por uma tentativa V10.1.1 anterior.
- O instalador e o script PowerShell exibem agora o erro PostgreSQL real através de
  `install-db-error.log` quando a conexão efetivamente falhar.
- O instalador PowerShell alternativo recebeu a mesma correção.

## Validação

- 273 arquivos Python compilados sem erro.
- 33 testes direcionados de PostgreSQL/Setup aprovados.
- Regressão adicionada reproduzindo o `server.json` parcial da V10.1.1.
- Validadores estáticos V10 e V10.1 aprovados.

## Reinstalação

A nova versão pode ser executada diretamente sobre a tentativa que falhou. Não é
necessário apagar manualmente `C:\ProgramData\DataIntelligence\Server\server.json`.
O bootstrap recupera esse estado e substitui a configuração parcial por uma válida.
