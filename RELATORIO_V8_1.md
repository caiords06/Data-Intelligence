# Relatório de entrega — V8.1

## Objetivo

A V8.1 é a versão de estabilização da plataforma empresarial. Ela corrige
os problemas visuais e funcionais identificados na V8, reforça a integridade
multiempresa e fecha os fluxos locais que ainda estavam apenas representados na
interface.

## Interface estabilizada

- cabeçalhos, ações e conteúdo passam a compartilhar o mesmo contêiner;
- grades de cards se reorganizam conforme a largura disponível;
- sidebars e páginas extensas possuem rolagem;
- a barra vertical permanece na extremidade direita da janela, enquanto o
  recuo visual é aplicado somente aos cards e textos;
- tabelas possuem rolagem vertical e horizontal;
- divisórias das colunas são redesenhadas automaticamente;
- estados vazios cobrem a área completa, mantendo linhas atrás da mensagem;
- formulários, catálogos, histórico, organização, usuários e configurações
  usam os mesmos componentes responsivos;
- versão visual e títulos foram padronizados como V8.1.

## Analytics

- navegação analítica unificada;
- Nova análise e Importações possuem fluxos distintos;
- fontes locais, URL, Google Drive e SQLite permanecem disponíveis;
- a biblioteca de conjuntos de dados é persistente;
- metadados podem ser editados;
- arquivos podem ser substituídos com incremento de versão e auditoria;
- conjuntos podem ser reutilizados em novas análises ou removidos;
- Relatórios, Visualizações, Agendamentos, Alertas, Modelos e Assistente
  possuem configuração e linguagem próprias;
- os dez motores analíticos especializados continuam disponíveis.

## Backend e integridade

- toda conexão SQLite ativa `PRAGMA foreign_keys = ON`;
- migração idempotente `003_v8_1_integridade` protege relações entre
  empresa, filial, usuários e conjuntos de dados;
- novos usuários são vinculados ao contexto empresarial ativo;
- consultas operacionais respeitam empresa e filial;
- histórico usa escopo, dono e exclusão lógica;
- jobs congelam o ator no início e podem ser cancelados;
- tarefas, alertas e atividades aplicam autorização antes da limitação;
- download por URL revalida redirecionamentos e remove arquivos incompletos;
- temporários gerenciados antigos são limpos sem atingir arquivos externos;
- importação SQLite é feita em blocos;
- segredos aninhados continuam proibidos no Integration Hub;
- formulários especializados cobrem todas as seções departamentais;
- arquivos internos dos módulos chegam ao Analytics sem o limite silencioso de
  mil registros.

## Ciclo de vida da interface

- callbacks assíncronos verificam se a tela ainda existe;
- aquisições canceladas limpam seus temporários;
- o fechamento sinaliza cancelamento, aguarda a thread e encerra o navegador;
- somente o controlador principal define a geometria da janela;
- as preferências de interface podem ser restauradas.

## Validação

Executado na raiz do projeto:

```bash
python -m compileall -q .
python -m tabnanny .
python -m unittest discover -s tests -v
```

Resultado: **68 testes aprovados**, sem falhas de compilação ou indentação.

## Limites intencionais

Serviços externos continuam dependendo das credenciais e do consentimento do
ambiente em que a aplicação for instalada. A V8.1 entrega os fluxos locais, a
persistência, a validação e os pontos de integração; não inclui credenciais de
Gmail, Microsoft Graph, provedores de IA ou bancos externos.
