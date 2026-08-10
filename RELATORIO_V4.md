# Relatório de evolução — V4

## Objetivo

A V4 torna o dashboard adaptativo e separa claramente as responsabilidades de
navegação, preferências, perfis e configuração do motor analítico.

## Implementações

### Indicadores e dashboards

- indicadores universais para qualquer DataFrame;
- motores específicos de Vendas, Financeiro, Estoque, Cadastro e RH;
- ampliação do mapeamento semântico do classificador;
- cards, títulos, formatação e destaques escolhidos pela categoria;
- fallback universal quando não há motor ou campos suficientes.

### Interface

- texto e cursor dos campos de login recuados da borda;
- foco azul aplicado à moldura do campo;
- sidebar compartilhada e com textos mais internos;
- navegação completa também na tela Nova análise;
- retorno ao início movido para o rodapé;
- tela funcional de histórico;
- tela funcional de configurações globais;
- card da Central convertido em Perfis de análise, com função distinta;
- quatro perfis prontos: completa, executiva, qualidade e rápida;
- progresso mínimo padrão de cinco segundos executado fora da thread da UI.

### Segurança

- senha forte com dez caracteres e quatro classes obrigatórias;
- bloqueio de cinco minutos após cinco falhas de autenticação;
- expiração de sessão por inatividade;
- autorização administrativa aplicada também no backend;
- confirmação dupla no cadastro e na redefinição de senhas;
- proteção contra autodesativação e contra remoção do último admin;
- auditoria de login, usuários, senhas e histórico;
- migração automática do banco das versões anteriores.

### Histórico e preferências

- armazenamento somente do resumo, sem o conteúdo bruto da planilha;
- nomes de arquivos sem caminhos completos;
- usuário comum acessa somente o próprio histórico;
- administrador pode consultar e administrar todos os resumos;
- persistência JSON atômica das preferências;
- categoria, período, pasta, atraso, sessão e confirmação de exclusão
  configuráveis.

## Validação

- 28 testes automatizados aprovados;
- `compileall` sem erros;
- `tabnanny` sem problemas de indentação;
- todos os módulos importados sem disparar a aplicação;
- execução ponta a ponta preservada para a planilha de vendas da V3.2;
- testes sintéticos dos quatro novos motores e dos indicadores universais.

## Compatibilidade

O banco antigo é migrado ao iniciar. A política nova é aplicada a senhas
criadas ou redefinidas na V4; hashes existentes continuam verificáveis porque os
parâmetros `scrypt` foram mantidos.
