# Data Intelligence Enterprise Platform — V9.0

> **Versão atual:** a documentação de implantação e arquitetura da V9 está em [`README_V9_INSTALACAO_E_ARQUITETURA.md`](README_V9_INSTALACAO_E_ARQUITETURA.md). O restante deste arquivo preserva documentação histórica das versões anteriores.

<div align="center">

# Enterprise Operations & Intelligence Platform

### ERP modular + inteligência operacional + analytics em Python

![Status](https://img.shields.io/badge/status-V8.2.1%20estabilizada-2f8cff)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/testes-140%20validados-22c55e)

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

## Integração funcional V8

- login responsivo com fundo em tela inteira e uma ilustração PNG
  transparente composta por um motor central e exatamente nove nós;
- ações da rightbox reposicionadas dentro da grade de conteúdo, sem botões
  flutuando fora dos limites dos painéis;
- botão de busca alinhado ao título de Acesso rápido na Central;
- CRUD especializado para todas as seções departamentais, com pesquisa,
  filtros, paginação, edição, arquivamento, lixeira, restauração,
  empresa, filial e auditoria antes/depois;
- Central de tarefas com responsável, prioridade, vencimento, conclusão e
  arquivamento;
- Central de documentos com cópia local gerenciada, classificação e
  verificação SHA-256;
- Workflow Builder e Integration Hub com ativação/pausa e segregação por
  empresa e filial;
- Central de relatórios em HTML, CSV e JSON a partir do universo autorizado;
- áreas de Conjuntos, Visualizações, Agendamentos, Modelos e Assistente
  persistidas no backend local do Analytics;
- importação por computador, link público do Google Drive, link
  compartilhado do OneDrive, URL direta e tabela/view de SQLite;
- leitura de XLSX, XLS, CSV, JSON, Parquet e TXT;
- validação de URL contra endereços locais/privados, limite de 100 MB e
  validação do formato retornado;
- divisórias de tabelas recalculadas no primeiro layout, no redimensionamento
  e depois de ajustes manuais de coluna.

## Estabilização V8.1

- telas principais, catálogos, painéis, histórico e áreas administrativas
  responsivos, com rolagem segura e sem ações flutuando fora do conteúdo;
- cabeçalhos usam fábricas de ações, evitando o erro de tentar mover um
  widget Tkinter entre pais diferentes;
- tabelas possuem rolagem horizontal, divisórias recalculadas pela geometria
  renderizada e estado vazio em primeiro plano;
- sidebar contextual única para todo o Analytics, mantendo Dashboard, Nova
  análise, Importações, Conjuntos, Relatórios, Alertas, Modelos e Assistente
  no mesmo domínio de navegação;
- biblioteca persistente de conjuntos de dados com metadados, hash SHA-256,
  reutilização e descarte lógico;
- formulários e tabelas especializados para todas as seções departamentais
  e recursos do Analytics;
- aquisição externa e conversão SQLite executadas fora da thread visual,
  com limite, limpeza de temporários e proteção SSRF em redirecionamentos;
- escopo congelado de empresa e filial para jobs e importações, vínculo
  explícito usuário–empresa e validação do par empresa–filial no banco;
- histórico isolado por empresa, filial e proprietário, com exclusão lógica;
- cancelamento cooperativo do processamento e encerramento controlado das
  threads de trabalho;
- compatibilidade de arquivos também verifica famílias de tipos, estoque usa
  o mínimo configurado por item e documentos são verificados em blocos;
- identidade visual, títulos e auditoria padronizados como V8.1.

## Hotfix de navegação e interface V8.2.1

- o Dashboard processado e todas as páginas do Analytics compartilham uma única
  sidebar canônica; abrir Explorar dados, Relatórios, Visualizações, Modelos ou
  outra seção não troca mais o contexto visual da navegação;
- o rótulo `Explorar dados` é consistente entre menu e página, eliminando a
  alternância visual para `Conjuntos de dados`;
- Central de notificações e Estrutura organizacional destacam a própria opção
  na sidebar, em vez de Visão geral/Configurações; os demais destinos globais
  e menus departamentais também ganharam testes de regressão de contexto;
- `AreaRolavel` e a rolagem da sidebar ignoram eventos tardios depois da
  destruição dos widgets, eliminando o `bad window path name` relatado;
- o Histórico aceita seleção múltipla, mantém Excluir habilitado e desativa/
  escurece ações que exigem um único item; a exclusão múltipla é atômica e
  continua sendo lógica/auditável;
- administradores podem remover com segurança empresas criadas na sessão
  atual, desde que elas não sejam o contexto ativo; empresas anteriores à
  sessão não podem ser removidas por esse comando;
- o Dashboard atualiza corretamente o texto de quantidade de arquivos
  selecionados, evitando mostrar `Nenhum arquivo selecionado` com dados na lista;
- versão visual identificada como V8.2.1.

## Estabilização V8.2.1

- removida a colisão de `criar_estado_vazio()` que derrubava telas vazias;
- corrigida a mistura de `pack` e `grid` na gestão de usuários;
- atividades, notificações e movimentações de estoque passam a preservar a
  filial correta e a validar o par empresa–filial;
- vínculos de usuário, responsáveis de tarefas e permissões são validados no
  contexto empresarial ativo;
- cancelamentos de jobs são estados terminais distintos de falhas;
- migrações antigas deixam de escolher uma filial global para registros de
  empresas diferentes;
- regras de consistência foram reforçadas em Marketing, Comercial, RH, Compras
  e Financeiro, incluindo números inteiros e valores finitos;
- KPI jurídico de contratos a vencer ignora contratos já vencidos;
- componentes roláveis, cabeçalhos, textos e tabelas foram ajustados para
  trabalhar de 1024×680 até Full HD, com 1920×1080 como referência visual;
- no Windows a aplicação abre maximizada na área útil disponível;
- smoke tests reais de Tkinter foram adicionados para detectar telas que
  quebram durante sua construção, além das regressões de backend V8.2.1.

## Workspace Financeiro 2.0

O Financeiro deixou de usar apenas o cadastro departamental genérico e agora
possui um domínio próprio, mantendo compatibilidade com os lançamentos das
versões anteriores. O fluxo implantado é:

```text
registrar → classificar → aprovar → pagar/receber →
conciliar → contabilizar → analisar → auditar
```

Principais capacidades:

- livro financeiro paginado, pesquisável e filtrável por período, natureza,
  conta, categoria, departamento, centro de custo e projeto;
- receitas, despesas, contas a pagar, contas a receber, reembolsos,
  transferências, parcelamentos e recorrências;
- contas bancárias e caixa, saldo consolidado e transferências neutras;
- baixa parcial, juros, multa, desconto e saldo restante;
- alçadas de aprovação por valor e permissões financeiras por ação;
- conciliação por OFX, CSV ou XLSX com sugestão de correspondência;
- orçamento planejado x realizado, alertas de consumo e cenários de caixa;
- plano de contas, categorias, clientes/fornecedores, cartões e anexos;
- DRE baseada em lançamentos contabilizados, relatórios em CSV, Excel,
  HTML e PDF e agenda persistente de relatórios;
- analista financeiro determinístico, alertas de vencimento, risco de caixa,
  orçamento e possíveis duplicidades;
- cancelamento antes da liquidação e estorno auditável depois dela, sem
  exclusão física de registros financeiros;
- valores monetários armazenados como centavos inteiros e escopo obrigatório
  por empresa e filial.

Detalhes funcionais e técnicos estão em
[`RELATORIO_FINANCEIRO_2_0.md`](RELATORIO_FINANCEIRO_2_0.md).

## Workspace Recursos Humanos 2.0

O RH deixou de depender do cadastro departamental genérico e ganhou um
domínio próprio, integrado e auditável. A navegação agora acompanha o ciclo
completo de pessoas:

```text
planejar → recrutar → admitir → integrar → desenvolver →
remunerar → acompanhar → movimentar → desligar → auditar
```

Principais capacidades:

- cadastro mestre e perfil do colaborador com dados pessoais, profissionais,
  dependentes, histórico, benefícios, equipamentos e documentos;
- admissão em oito etapas e geração automática de tarefas para RH, TI,
  Estoque e Administrativo;
- desligamento com tarefas para RH, Financeiro, TI, Estoque e Administrativo,
  impedindo conclusão enquanto houver pendências obrigatórias;
- férias e ausências com saldo, conflito de período e aprovação central;
- ponto e jornada com horas trabalhadas, extras, atrasos e ajustes;
- catálogo de benefícios, vínculos e custos por colaborador;
- folha por competência, eventos, proventos, descontos, encargos,
  fechamento, contracheque em PDF e tarefa de provisão para o Financeiro;
- cargos e faixas salariais, vagas e candidatos, avaliações, PDI,
  treinamentos e inscrições;
- GED de RH com hash SHA-256, validade, classificação, versão e assinatura;
- solicitações, relatórios em PDF/XLSX/CSV, agenda persistente,
  indicadores, análise determinística e auditoria antes/depois;
- perfis de Diretoria de RH, Analista de RH, Gestor de pessoas, Colaborador e
  Auditor, com escopo de equipe/próprio cadastro e proteção de remuneração.

Detalhes funcionais e técnicos estão em
[`RELATORIO_RH_2_0.md`](RELATORIO_RH_2_0.md).

## Workspace Estoque 2.0

O Estoque deixou de alterar diretamente um campo de quantidade e ganhou um
domínio próprio de materiais, produtos, patrimônio, rastreabilidade,
inventário e logística interna. O ciclo implantado é:

```text
cadastrar → receber → conferir → armazenar → reservar →
separar → expedir/consumir → transferir → inventariar →
repor → analisar → auditar
```

Principais capacidades:

- cadastro mestre de itens com SKU, barras, QR, categoria, unidade, custos,
  limites, consumo médio, lead time e controles de lote/série/patrimônio;
- depósitos, almoxarifados e endereçamento por corredor, prateleira, nível
  e posição;
- razão imutável de movimentações: o saldo é consequência das operações
  confirmadas e não pode ser editado ou apagado;
- recebimento, conferência, armazenagem, saída, consumo, devolução,
  perda, avaria e ajuste com usuário, motivo, documento e centro de custo;
- transferências aprovadas com saldo em trânsito até a confirmação do
  depósito de destino;
- reservas que reduzem a disponibilidade sem alterar o saldo físico;
- inventário geral, parcial ou rotativo, contagem cega, recontagem,
  divergência, aprovação e ajuste auditado;
- lotes, validade, bloqueio, quarentena e separação FEFO;
- números de série, patrimônio, garantia, condição, depósito e vínculo
  opcional ao cadastro de colaborador;
- alertas idempotentes de falta, estoque crítico, excesso, validade e falta
  de endereçamento;
- reposição por cobertura, consumo, estoque mínimo/máximo e lead time,
  encaminhando uma solicitação para Compras sem comprar automaticamente;
- tarefas para Financeiro em recebimentos de compra e integração por
  solicitações, aprovações, atividades, notificações e auditoria;
- relatórios em PDF/XLSX/CSV e Analytics sobre o universo autorizado, sem
  truncamento silencioso pela paginação da interface;
- perfis de Operador, Analista, Gestor e Auditor de Estoque, além das
  permissões granulares por ação.

Detalhes funcionais e técnicos estão em
[`RELATORIO_ESTOQUE_2_0.md`](RELATORIO_ESTOQUE_2_0.md).

## Workspace Compras e Suprimentos 2.0

Compras deixou de ser um cadastro genérico de solicitações e passou a
controlar Procurement de ponta a ponta, preservando a decisão humana nas
alçadas e na escolha do fornecedor:

```text
necessidade → solicitação → aprovação → cotação → negociação →
escolha humana → pedido → recebimento → Estoque/Patrimônio →
Financeiro → análise → auditoria
```

Principais capacidades:

- solicitações multi-item, prioridade, prazo, centro de custo, recorrência,
  rascunho e envio para aprovação;
- alçadas configuráveis por valor, prioridade e departamento, ligadas à
  Central de Aprovações;
- cotações com vários fornecedores, propostas por item, frete, impostos,
  desconto, prazo, garantia e condição de pagamento;
- mapa comparativo com scores explicáveis de preço, prazo e qualidade; o
  sistema calcula e recomenda, mas o comprador justifica a escolha;
- rodadas de negociação e saving calculado contra o valor de referência;
- pedido de compra com nova aprovação, etapas de entrega e PDF profissional;
- cadastro compartilhado de fornecedores com Estoque e Financeiro,
  homologação, contatos, documentos, integridade SHA-256 e avaliação;
- recebimento parcial válido, conferência, recusa, lotes, validade,
  divergências e resolução auditada;
- entrada autorizada no Estoque e geração da conta a pagar no Financeiro
  sem duplicar cadastros ou valores;
- contratos, aditivos, vigência, reajuste, renovação e alertas idempotentes;
- relatórios PDF/XLSX/CSV, agenda, Analytics sem truncamento e inteligência
  para concentração, baixa concorrência, atrasos e compras recorrentes;
- 27 tabelas especializadas, valores em centavos, filial obrigatória onde
  aplicável e histórico de Compras imutável;
- perfis de Solicitante, Comprador, Gestor, Recebimento e Auditor com
  permissões granulares por ação.

Detalhes funcionais e técnicos estão em
[`RELATORIO_COMPRAS_2_0.md`](RELATORIO_COMPRAS_2_0.md).

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
comandos do sistema. A interface permite criar workflows de notificação e
ativar ou pausar as regras.

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

### Testes visuais com exportação PNG

No Windows, a aplicação pode abrir todas as interfaces usando um banco
temporário, capturar cada tela em PNG e gerar uma folha de contato com
diagnósticos automáticos:

```powershell
python scripts/gerar_capturas_interface.py --escopo completo
```

Os arquivos são gravados em `artifacts/interface_png`. Consulte
[`TESTES_VISUAIS.md`](TESTES_VISUAIS.md) para execução essencial, resolução
personalizada, uso via `unittest` e Linux/Xvfb.

Validação da entrega: **157 testes coletados**, com **147 executados e
aprovados** e **10 testes gráficos condicionados a display**, incluindo captura
PNG das interfaces, autenticação,
analytics, multiempresa, permissões, módulos, estoque, aprovações, workflows,
Integration Hub, busca, alertas, perfis adaptativos, navegação protegida e
análise direta de dados internos, CRUD departamental V8, Financeiro 2.0,
RH 2.0, Estoque 2.0, Compras 2.0, Tecnologia 3.0, Agente TI 1.0, tarefas, documentos,
relatórios e aquisição de fontes.

## Tecnologia e Serviços 3.0

> **Hotfix 3.0.1:** segmentos de rede arquivados podem ser reativados sem erro de unicidade; o mesmo CIDR privado pode existir em filiais diferentes da mesma empresa.

O módulo de Tecnologia deixou de reutilizar o painel departamental genérico e
passou a funcionar como uma central de operações própria. A experiência é
separada em dois níveis: um **portal de suporte**, acessível a qualquer usuário
autenticado, e uma **operação técnica**, protegida pelas permissões de TI.

Principais capacidades desta versão:

- portal inicial para abrir e acompanhar os próprios chamados sem acesso às
  ferramentas administrativas de TI;
- cockpit com chamados, ativos, segmentos, dispositivos observados e alertas;
- cadastro explícito de segmentos privados: a plataforma não presume ou grava a
  LAN atual como rede padrão;
- CRUD de segmentos, autorização/revogação de descoberta e arquivamento
  auditável de redes cadastradas incorretamente;
- descoberta ativa conservadora somente em CIDRs privados explicitamente
  autorizados, usando ICMP, resolução de hostname e cache ARP, sem varredura de
  portas ou exploração;
- diagnóstico de gateway, DNS do sistema e conectividade com a Internet;
- integração opcional com o Firewall do Windows para criar **somente** uma regra
  ICMPv4 de entrada, no perfil Privado e limitada ao CIDR escolhido. O firewall
  nunca é desativado pela plataforma;
- inventário de dispositivos descobertos, identificação manual, vínculo com
  patrimônio, criação de ativo e arquivamento sem perda da trilha;
- ativos gerenciados com hostname, IP, MAC, usuário, SO, CPU, RAM, disco, saúde,
  telemetria, agente e dados de acesso remoto quando disponíveis;
- Service Desk, manutenção, licenças, sistemas, monitoramento, contratos,
  mudanças, problemas, segurança, alertas, relatórios e auditoria;
- acesso remoto por AnyDesk, TeamViewer ou RustDesk com permissão, consentimento,
  justificativa e registro da sessão.

A descoberta de rede identifica presença e identidade básica. Informações
avançadas de uma estação — usuário de sessão, versão detalhada do SO, CPU/RAM,
disco, uptime e identidade do AnyDesk — vêm do agente gerenciado ou do cadastro
do ativo. Isso evita apresentar inferências de rede como inventário confiável.

### Agente TI 1.0

O projeto inclui o primeiro componente distribuível para computadores Windows.
Ele coleta inventário e telemetria somente da máquina local, identifica a
instalação do AnyDesk, prepara heartbeat HTTPS assinado e pode iniciar com o
Windows pelo Agendador de Tarefas. O token fica fora do JSON e é protegido pelo
DPAPI. Consulte `AGENTE_TI.md` para build, teste e instalação.

Até a API central ser implementada, o agente deve ser validado com `collect` ou
`once --dry-run`; nenhuma comunicação externa ocorre nesses modos.

## Limites deliberados

Ainda não estão implementados:

- cálculo oficial de folha, férias, rescisões, tributos ou eSocial;
- pagamentos, conciliação bancária e emissão fiscal;
- MFA, SSO, LDAP ou Active Directory;
- API central para provisionar agentes e receber os heartbeats assinados;
- captura de pacotes, varredura de portas, exploração ou administração remota própria; a descoberta ativa atual é deliberadamente limitada a presença/identidade em redes privadas autorizadas;
- envio por Gmail, Outlook, SMTP ou WhatsApp;
- sincronização com ERPs, CRMs e bancos externos;
- assinatura digital e gestão processual oficial;
- instalador geral da plataforma e arquitetura cliente-servidor completa; o
  agente possui build próprio e instalação operacional pelo Agendador do Windows.

Esses limites evitam apresentar simulações como funções empresariais reais.
A base V8.2.1 com Tecnologia 3.0 mantém a operação local; integrações externas credenciadas e
processos regulados continuam reservados a etapas próprias de homologação.

## Autor

**Caio Rodrigues**

Projeto desenvolvido para estudo, portfólio e evolução profissional em Python,
automação, backend e inteligência de dados.


## Distribuição Windows · Central + Agente TI

A plataforma possui uma API TI embutida para receber inventário/telemetria de computadores remotos e um Agente TI distribuível como `.exe`. Para compilar e implantar em uma LAN de laboratório, consulte:

- `README_DISTRIBUICAO_WINDOWS.md` — guia completo de build e implantação;
- `README_CENTRAL_TI.md` — instalação do PC central;
- `README_DISPOSITIVO_TI.md` — instalação nos computadores gerenciados;
- `AGENTE_TI.md` — contrato e arquitetura técnica do agente.

Build completo no Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

O build gera `release\DataIntelligence-Deployment-Windows.zip`, contendo a Central e o kit do Agente.
