<div align="center">

# Enterprise Operations & Intelligence Platform

### ERP modular + inteligência operacional + analytics em Python

![Status](https://img.shields.io/badge/status-V7%20front--end-2f8cff)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/testes-56%20aprovados-22c55e)

</div>

## Visão

A V5 transforma a antiga Data Intelligence Platform em uma fundação
empresarial modular. A análise de dados não foi descartada: ela passou a ser o
motor transversal que recebe tanto arquivos externos quanto dados produzidos
pelos setores da própria plataforma.

```text
                ENTERPRISE PLATFORM
                        │
       ┌────────────────┼────────────────┐
       │                │                │
  Enterprise Core  Módulos          Segurança
       │                │                │
       └────────────────┼────────────────┘
                        ▼
                Analytics central
                        │
          Alertas · Histórico · Workflows
```

Esta versão é uma fundação empresarial funcional, não uma tentativa de simular
um ERP fiscal ou uma folha oficial. Processos regulados e integrações externas
somente serão ativados quando houver APIs, credenciais, regras e homologações
adequadas.

## Estabilização V5.1

- navegação hierárquica: `Módulos → Central analítica → Nova análise`;
- remoção dos atalhos Central analítica e Nova análise da sidebar;
- catálogo mostra todos os módulos e sinaliza acessos indisponíveis;
- perfis departamentais base e perfis `+` com áreas complementares;
- alteração de perfil e permissões personalizadas na gestão de usuários;
- separadores verticais nas tabelas operacionais dos módulos;
- validações de autorização adicionadas aos caminhos indiretos do Analytics;
- textos de retorno corrigidos conforme a origem real da navegação.

## Estabilização V6

- chaves estrangeiras ativas em toda conexão SQLite;
- migrações empresariais versionadas e idempotentes;
- Analytics interno sem limite silencioso de 1.000 registros;
- escopo operacional por empresa e filial;
- valores monetários espelhados em centavos inteiros e usados nos cálculos;
- paginação, pesquisa, ordenação e filtro de estado nos módulos;
- edição, arquivamento, lixeira, restauração e histórico antes/depois;
- aprovações removíveis da fila sem apagar a auditoria;
- divisórias de tabelas recalculadas no primeiro layout e em redimensionamentos;
- motores e dashboards específicos para Compras, TI, Marketing,
  Administrativo, Jurídico e Comercial;
- Job Manager persistente para acompanhar análises;
- backup administrativo com hash SHA-256 e verificação SQLite.

## Remodelação de front-end V7

- novo design system escuro centralizado, com tipografia, cores, espaçamentos,
  estados, cards, botões, chips e tabelas padronizados;
- nova Central da aplicação inspirada em dashboards corporativos modernos;
- navegação global reorganizada em Operacional e Gestão;
- hierarquia preservada: `Módulos → Analytics → Nova análise`;
- catálogo de módulos com estados visualmente distintos para acesso autorizado
  e restrito;
- painel, menu interno, atalhos, pipeline e mapa funcional exclusivos para RH,
  Financeiro, Estoque, Compras, TI, Marketing, Administrativo, Jurídico e
  Comercial;
- cadastros e tabelas V6 preservados como a seção operacional funcional de
  cada departamento;
- Central Analytics remodelada com análises recentes, saúde do motor e novas
  áreas de Importações, Conjuntos, Relatórios, Agendamentos, Modelos e IA;
- Nova análise remodelada com seletores visuais para Computador, Google Drive,
  OneDrive, banco de dados e URL, resumo dinâmico e configuração modular;
- Dashboard de resultados alinhado à nova paleta e com acessos preparados para
  Explorar dados, Relatórios, Visualizações e Modelos;
- funcionalidades ainda sem backend identificadas como **prévia funcional**;
  elas não alteram dados e informam claramente que a integração ocorrerá na
  próxima etapa.

## Correções visuais da V5 e V5.1

- tema TTK escuro aplicado antes da criação das tabelas;
- Histórico vazio não apresenta mais uma área branca;
- estado vazio com mensagem orientando o primeiro processamento;
- ações de detalhe e exclusão desabilitadas sem seleção;
- sidebar, cores, dimensões, cards, botões, tabelas e comboboxes padronizados;
- campos e textos mantêm recuo consistente em relação às bordas;
- tela de resultados analíticos alinhada à identidade visual empresarial.
- divisórias verticais discretas entre as colunas dos módulos operacionais.

## Enterprise Core

O núcleo compartilhado possui persistência própria para:

- empresas e filiais;
- departamentos e centros de custo;
- usuários e permissões por empresa e módulo;
- atividades empresariais;
- notificações;
- aprovações humanas;
- tarefas;
- documentos;
- metadados de integrações;
- workflows seguros;
- auditoria administrativa.

Ao iniciar uma base nova, o sistema cria uma Empresa principal, uma Matriz,
departamentos corporativos e centros de custo iniciais. Administradores podem
criar empresas, filiais, departamentos e centros de custo em Configurações.

## Módulos operacionais

| Módulo | Cadastro funcional | Indicadores principais |
|---|---|---|
| Recursos Humanos | colaboradores, cargo, setor, salário base e situação | quadro, ativos, departamentos e folha base |
| Financeiro | receitas, despesas, categorias, vencimentos e status | receitas, despesas, saldo e pendências |
| Estoque | código, item, quantidade, mínimo, custo e localização | itens, unidades, críticos e valor |
| Compras | item, quantidade, fornecedor, estimativa e status | solicitações, pendências, aprovações e valor |
| Tecnologia | chamados, categoria, prioridade e responsável | chamados, abertos, críticos e ativos de TI |
| Marketing | campanhas, canais, investimento, leads e conversões | investimento, leads, conversões e receita |
| Administrativo | solicitações, facilities, viagens e reembolsos | volume, pendências, aprovações e valor |
| Jurídico | contratos, partes, riscos, valores e vencimentos | contratos, ativos, vencimentos e risco financeiro |
| Comercial | clientes, etapas, oportunidades e responsáveis | oportunidades, abertas, ganhas e pipeline |

Cada tela possui cadastro, tabela operacional, estado vazio e quatro cards
adaptados. O Estoque também permite Entrada, Saída e Ajuste, impedindo saldo
negativo.

Todos os cards permanecem visíveis no catálogo. Quando o perfil não possui
acesso, o botão é substituído por uma mensagem educada, em vermelho discreto,
sem criar um caminho clicável para o módulo protegido.

## Analytics como cérebro da plataforma

O botão **Analisar módulo** envia uma cópia autorizada dos dados internos ao
mesmo orquestrador usado para planilhas. Não é criado arquivo temporário.
Esse botão só aparece quando o perfil também possui permissão de escrita no
Analytics.

```text
Dados do módulo
      ↓
Cópia autorizada
      ↓
Tratamento e validação
      ↓
Classificação
      ↓
Indicadores + qualidade + temporal
      ↓
Dashboard adaptativo
      ↓
Histórico + atividade empresarial
```

O motor possui indicadores universais e dashboards específicos para Vendas,
Financeiro, Estoque, Cadastro, Recursos Humanos, Compras, TI, Marketing,
Administrativo, Jurídico e Comercial.

## Cockpit executivo

A tela inicial passou a apresentar:

- saldo financeiro;
- colaboradores ativos;
- itens críticos de estoque;
- aprovações pendentes;
- atividades recentes;
- alertas dos módulos autorizados;
- acesso à busca universal com `Ctrl + K`.

Os valores respeitam a empresa ativa e as permissões do usuário.

## Permissões e segurança

Administradores possuem acesso integral. Usuários comuns recebem permissões
por empresa e módulo:

- leitura: permite visualizar o módulo;
- escrita: permite criar registros e movimentações;
- aprovação: permite decidir solicitações pendentes.

A escrita e a aprovação dependem da leitura. A interface apresenta o catálogo
completo, mas os módulos sem autorização não possuem ação de abertura.

Perfis disponíveis: Analista, RH/RH+, Financeiro/Financeiro+, Estoque/Estoque+,
Compras/Compras+, TI/TI+, Marketing/Marketing+, Administrativo/Administrativo+,
Jurídico/Jurídico+ e Comercial/Comercial+. O sufixo `+` adiciona somente áreas
relacionadas. Aprovações nunca são concedidas automaticamente por esses perfis.

Continuam funcionais:

- hash `scrypt` com salt individual;
- senha forte;
- bloqueio após cinco tentativas inválidas;
- expiração de sessão;
- proteção do último administrador;
- alteração segura de senha;
- auditoria de operações sensíveis.

## Aprovações humanas

Solicitações de Compras e Administrativo entram automaticamente na fila de
aprovações. Um usuário autorizado pode:

- aprovar;
- rejeitar;
- solicitar alteração;
- registrar uma justificativa.

A decisão atualiza o registro original, cria atividade, notifica o solicitante
e entra na auditoria. A plataforma não autoriza IA ou workflow a realizar
pagamentos, demissões, alterações salariais ou decisões jurídicas.

## Alertas e atividades

Regras internas já geram alertas para:

- estoque igual ou inferior ao mínimo;
- chamado de TI crítico;
- contrato próximo do vencimento;
- decisão de aprovação.

Uma admissão ativa cria tarefas relacionadas para RH, TI e Estoque. A Central
de notificações permite consultar alertas e marcá-los como lidos.

## Workflow Engine

O backend possui um motor de workflows declarativo. Ele aceita somente três
ações seguras:

- criar notificação;
- criar tarefa;
- solicitar aprovação.

As condições usam operadores controlados, sem `eval`, execução de Python ou
comandos do sistema. A interface visual do Workflow Builder fica reservada para
a fase de front-end.

## Integration Hub

O backend registra metadados para conectores Google, Microsoft, SMTP, Slack,
Teams, GitHub, ERPs, bancos de dados e APIs HTTP. Segredos não podem ser salvos
na configuração: deve ser usada uma referência a um cofre de credenciais.

Os conectores ainda não enviam e-mails nem sincronizam dados. Gmail API,
Microsoft Graph, OAuth, SMTP e Playwright/Selenium serão implementados somente
com credenciais e critérios de segurança definidos.

## Estrutura principal

```text
analysis/           análise temporal
auth/               autenticação, sessão, usuários e auditoria
automacao/          validação web e WebDriver
configuracoes/      preferências e perfis analíticos
core/               orquestrador de analytics
dados/              tratamento, classificação, qualidade e indicadores
enterprise/         core, módulos, permissões, organização e workflows
historico/          resumos das análises
interface/          cockpit e telas Tkinter
sistema/            SO, usuário e navegador
tests/              testes automatizados
main.py             inicialização e navegação
```

## Execução

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

No primeiro uso será criado o administrador inicial. O banco e as preferências
locais permanecem fora do Git.

## Testes

```bash
python -m unittest discover -v
python -m compileall -q .
python -m tabnanny .
```

Validação da entrega: **50 testes aprovados**, incluindo autenticação,
analytics, multiempresa, permissões, módulos, estoque, aprovações, workflows,
Integration Hub, busca, alertas, perfis adaptativos, navegação protegida e
análise direta de dados internos.

## Limites deliberados

Ainda não estão implementados:

- cálculo oficial de folha, férias, rescisões, tributos ou eSocial;
- pagamentos, conciliação bancária e emissão fiscal;
- MFA, SSO, LDAP ou Active Directory;
- descoberta de rede, captura de pacotes ou telemetria remota;
- envio por Gmail, Outlook, SMTP ou WhatsApp;
- sincronização com ERPs, CRMs e bancos externos;
- assinatura digital e gestão processual oficial;
- interface visual do Workflow Builder, documentos e tarefas;
- instalador e arquitetura cliente-servidor.

Esses limites evitam apresentar simulações como funções empresariais reais. A
próxima fase prevista é conectar, um a um, os painéis departamentais da V7 a
serviços de backend específicos, mantendo testes, permissões e auditoria.

## Autor

**Caio Rodrigues**

Projeto desenvolvido para estudo, portfólio e evolução profissional em Python,
automação, backend e inteligência de dados.
