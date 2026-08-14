# Auditoria e correções — PostgreSQL obrigatório

Data: 12/08/2026

## Objetivo

Eliminar persistência transacional local das estações Central/Cliente, tornar PostgreSQL a autoridade obrigatória de produção e corrigir falhas encontradas durante a auditoria.

## Correções aplicadas

- PostgreSQL passou a ser o backend padrão e obrigatório em produção.
- SQLite local é recusado em runtime normal e só pode ser habilitado explicitamente para migração/testes legados.
- O Servidor Corporativo não oferece mais SQLite no instalador nem no comando `configure-db`.
- Central/Cliente não inicializam banco, histórico ou schema empresarial local.
- Ausência de `node.json` não transforma mais uma estação em standalone silenciosamente; o modo standalone exige liberação explícita de desenvolvimento.
- Removida a replicação persistente de identidade, empresa e permissões para SQLite no login remoto. O bootstrap remoto fica somente em memória.
- Preferências deixaram de usar `preferencias.json` e passaram para `preferencias_usuarios` no banco central, inclusive via RPC.
- Histórico passou a possuir schema PostgreSQL próprio (`historico_analises`) e RPC centralizado.
- Corrigido o isolamento por empresa/filial do histórico em chamadas RPC do servidor.
- O bootstrap PostgreSQL passa a aplicar as novas tabelas também em bancos V10.1 já inicializados.
- O gerador do baseline PostgreSQL foi atualizado para não apagar as extensões de histórico/preferências em uma regeneração futura.
- Corrigidos blocos incompletos nos scripts PowerShell/Inno Setup após a remoção da opção SQLite.
- Instalador unificado agora apresenta PostgreSQL como obrigatório.
- Documentação operacional atualizada para a arquitetura PostgreSQL-only.
- Adicionados testes de regressão que comprovam que senha contendo `!` satisfaz a exigência de símbolo.

## Validação

- Compilação Python: 271 arquivos Python sem erro de sintaxe na auditoria inicial; compilação final dos fontes também aprovada.
- Testes automatizados executados em blocos: **290 aprovados**.
- **16 ignorados** por dependerem de recursos indisponíveis neste ambiente: desktop gráfico/Tk real ou instância PostgreSQL real de integração.
- Validador estático do instalador V10.1.1: aprovado.
- Testes específicos das correções PostgreSQL-only, preferências, histórico e senha: aprovados.

## Persistência local permitida

A proibição de persistência local foi aplicada aos **dados corporativos/transacionais das estações**. Permanecem apenas arquivos técnicos que não podem ser substituídos pelo próprio PostgreSQL: configuração de endereço/papel da estação (`node.json`), configuração do serviço (`server.json`), segredo necessário para o servidor conseguir autenticar no PostgreSQL, logs, arquivos temporários e exportações explicitamente solicitadas pelo usuário. Arquivos corporativos binários são mantidos no armazenamento gerenciado do **Servidor Corporativo**, com metadados e controle de acesso no PostgreSQL; não são mantidos como banco/cópia de autoridade nas estações Cliente/Central.

## Compatibilidade SQLite

O código de leitura/migração SQLite permanece exclusivamente para importar bases antigas e para testes unitários isolados. Produção não possui fallback para SQLite.
