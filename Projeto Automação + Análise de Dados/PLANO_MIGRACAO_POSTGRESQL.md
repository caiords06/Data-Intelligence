# PostgreSQL — próxima migração server-side

A V9.1 remove a dependência dos clientes em relação ao banco operacional: Central e
Cliente falam com o Servidor Corporativo por API. Isso permite migrar o banco do
servidor sem reinstalar ou reescrever as estações.

A conversão para PostgreSQL deve ser feita como uma migração de persistência do
servidor, não com acesso direto dos clientes ao banco. O caminho seguro é:

1. criar repositories server-side por domínio;
2. portar migrations/triggers SQLite para PostgreSQL;
3. executar migração de dados com contagem e hash lógico por tabela;
4. rodar testes de equivalência de RH, Financeiro, Compras, Estoque e Tecnologia;
5. executar teste de concorrência e transações;
6. ativar PostgreSQL no servidor somente depois de equivalência 100%;
7. manter API/RPC inalterada para Central, Cliente e Agente TI.

Não se recomenda expor credenciais PostgreSQL às estações, compartilhar SQLite por
SMB nem traduzir SQL SQLite para PostgreSQL por regex em produção.
