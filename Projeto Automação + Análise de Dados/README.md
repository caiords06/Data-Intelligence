# Data Intelligence Enterprise Platform — V11.1.0

Plataforma empresarial desktop em Python/Tkinter com **Servidor Corporativo como autoridade transacional**, PostgreSQL como backend corporativo obrigatório e uma camada de serviços preparada para múltiplos clientes. SQLite permanece restrito a migração/teste explicitamente habilitado e não é persistência de produção.

> Estado canônico: **V11.1.0 — governança legal operacional, identidade oficial e correções de homologação**.

## V11.1.0 — resultado desta revisão

- corrige os erros observados nos logs de relatórios de RH, operações de Estoque e expiração de sessão do Desktop;
- bloqueia publicação do Servidor Corporativo em rede sem TLS e exige SSL para PostgreSQL remoto;
- adiciona a Central de Conformidade e Privacidade com inventário de tratamentos, direitos de titulares, incidentes, RIPD versionado, terceiros/transferências, legal hold e catálogo de decisões analíticas;
- cria a base de autorização efêmera do Data Intelligence Remote, vinculada a política, ativo, chamado, consentimento, permissões e trilha encadeada — sem habilitar transmissão de tela ou execução remota nesta versão;
- diferencia assinatura simples, avançada e qualificada e registra hash/evidências; assinatura qualificada interna é recusada;
- aplica a marca fornecida pelo titular do projeto e os tokens tipográficos Manrope/Inter, além de foco visível e navegação rolável;
- mantém o ponto interno explicitamente como integração/consulta, sem alegar homologação como REP-P.

Controles técnicos auxiliam a conformidade, mas **não tornam uma instalação automaticamente conforme**. Bases legais, prazos de retenção, regras trabalhistas/fiscais, contratos, atuação do encarregado, feriados aplicáveis, REP e integrações devem ser validados pela organização e por especialistas competentes. Consulte `docs/16_CONFORMIDADE_E_PRIVACIDADE_V11_1.md` e `docs/18_MATRIZ_IMPLEMENTACAO_REQUISITOS_2026.md`.

## Correções pós-homologação da V11.0.1

- o cliente desktop grava logs e preferências visuais no perfil do usuário e não exige execução como administrador;
- o tema escolhido no login permanece ativo depois da autenticação e nas próximas execuções;
- as barras de rolagem possuem contraste e só aceitam rolagem quando existe conteúdo excedente;
- as navegações laterais receberam cores de seção, ícones destacados e seleção mais evidente;
- o Funcionário 360° exibe a foto à direita do nome, com ação explícita para adicionar ou alterar;
- relatórios de RH em CSV, XLSX e PDF são incluídos e testados no build do Servidor Corporativo;
- Analytics é reservado a perfis de gestão/diretoria e sua navegação termina em Regras analíticas;
- registros operacionais e de RH podem ser removidos logicamente, listados na lixeira e restaurados com auditoria.

Detalhes e evidências dessa etapa histórica: `RELATORIO_CORRECOES_V11_0_1_20260814.md`.

## O que muda nesta linha

A V11 consolida uma camada comum para toda a empresa e preserva as evoluções anteriores:

- **CORE empresarial compartilhado:** organização hierárquica, cadastro mestre de pessoas, permissões contextuais, tarefas, aprovações, colaboração, calendário, documentos, busca, eventos, metadados, dashboards, preferências e transferências de dados.
- **Funcionário 360°:** Pessoa, Colaborador, Usuário, permissões, ativos e acessos são entidades distintas e reunidas em cinco visões controladas pelo serviço.
- **Operações configuráveis:** 108 tipos e 12 fluxos iniciais cobrem Financeiro, RH, Compras, Estoque, CRM, Comercial, Marketing, Administrativo, Jurídico, TI, Analytics, Automação/BPM e GED.
- **Universalidade por configuração:** campos, etiquetas, tipos, workflows, painéis e preferências são parametrizados por empresa e filial, sem exigir uma tabela específica para cada variação de processo.

- **V10.4.0 — Analytics decisório:** a Central Analytics passa a priorizar Visão Executiva, Insights, Alertas e Regras Analíticas usando dados operacionais dos nove módulos especializados. O laboratório de arquivos continua disponível como recurso secundário.
- **V10.4.1 — Inteligência transversal:** Marketing/Comercial, Jurídico/Financeiro, Compras/Estoque e RH/TI/Estoque/Administrativo passam a ter fluxos de orquestração persistentes e rastreáveis.
- **V10.5.0 — Web-ready:** a interface desktop deixa de importar `enterprise.*` diretamente; utiliza `services/`. O Servidor Corporativo mantém RPC para o desktop e expõe contratos REST `/api/v1` explícitos para integrações e futuros clientes web.

## Arquitetura atual

```text
Desktop Tkinter / futuro Web / integrações
                  │
                  ▼
              services/
                  │
                  ▼
       domínios / repositórios enterprise
                  │
                  ▼
       Servidor Corporativo HTTP(S) :8770
                  │
                  ▼
             PostgreSQL
```

A regra arquitetural é: **a interface não é a autoridade do sistema**. Sessão, escopo empresarial, autorização, regras transacionais, workflows, arquivos e persistência pertencem ao servidor/camadas de serviço. O desktop é um cliente da plataforma.

## Módulos especializados

Financeiro, RH, Compras, Estoque, Tecnologia, Marketing, Comercial, Administrativo e Jurídico possuem experiência e serviço departamental próprios. CRM é compartilhado por Marketing e Comercial.

## Funcionário 360° e CORE V11

A nova interface individual do colaborador agrega dados pessoais e profissionais, vínculo, linha do tempo, documentos, jornada, benefícios, folha, equipamentos, sistemas, licenças, treinamentos, desempenho, tarefas, chamados, ocorrências, custos e auditoria. O backend filtra as seções conforme as visões `meu_perfil`, `gestor`, `rh`, `ti` e `auditor`.

Imagens e documentos são tratados por armazenamento gerenciado: validação de tipo/tamanho/resolução, bloqueio de executáveis, hash SHA-256, criptografia AES-GCM, miniaturas, versionamento, controle de acesso e auditoria.

Detalhes: `README_V11_CORE_EMPRESARIAL.md`, `RELATORIO_IMPLEMENTACAO_V11_20260814.md` e `RELATORIO_IMPLEMENTACAO_V11_1_0_20260814.md`.

## Analytics

O menu canônico é dividido em:

**Inteligência:** Visão executiva, Insights, Explorar dados, Alertas, Relatórios, Visualizações e Agendamentos.

**Laboratório:** Análise externa e Importações.

**Administração:** Regras analíticas.

Placeholders antigos de “Modelos”, “IA Assistente” e “Perfis” não são apresentados como funcionalidades prontas. A inteligência atual é baseada em regras explicáveis, dados autorizados e ações navegáveis até o módulo responsável.

## API pública V1

Contratos iniciais incluem:

```text
GET/POST /api/v1/crm/leads
GET/POST /api/v1/comercial/oportunidades
GET/POST /api/v1/marketing/campanhas
GET/POST /api/v1/juridico/processos
GET/POST /api/v1/administrativo/solicitacoes
GET      /api/v1/analytics/insights
GET      /api/v1/analytics/executive
POST     /api/v1/analytics/insights/refresh
POST     /api/v1/crm/leads/to-opportunity
GET      /api/v1/orquestracoes
```

Todos os endpoints protegidos usam a sessão Bearer do Servidor Corporativo e herdam escopo, permissões e auditoria das camadas de serviço/domínio.

## Banco e migrations

PostgreSQL é a autoridade em produção. A série incremental atual termina em:

```text
024_v10_4_analytics_inteligencia
025_v10_4_1_inteligencia_transversal
026_hardening_producao
027_v11_core_empresarial
028_v11_1_conformidade
```

As migrations preservam dados anteriores e são registradas em `migracoes_sistema`.

## Design System

A interface mantém os temas **Escuro tecnológico** e **Claro suave**, preferência corporativa por usuário, componentes responsivos e identidade visual centralizada.

## Qualidade

Antes de gerar uma distribuição execute:

```powershell
python -m compileall -q .
python scripts\auditar_camadas_arquitetura.py
python scripts\auditar_autoridade_servidor.py
python scripts\verificar_instalador_v10.py
python scripts\verificar_instalador_v10_1.py
python scripts\executar_grupo_testes.py --grupo 1 --total 6
```

Repita o runner para os grupos 2 a 6. A integração PostgreSQL real é executada separadamente com `RUN_POSTGRES_INTEGRATION=1`.

## Hardening de produção

A migration 026 adiciona MFA TOTP obrigatório com recuperação, sessões persistentes e revogáveis, rate limit e idempotência compartilhados, fila durável com scheduler/leases/retry/dead-letter/aprovação, auditoria LGPD de leitura, retenção, webhooks HTTPS assinados e backup cifrado `.dibak`. A API expõe OpenAPI 3.1 em `/api/v1/openapi.json` e métricas administrativas em `/api/v1/metrics`.

## Documentação

A documentação operacional está em `docs/`, cobrindo arquitetura, instalação do servidor/central/cliente/agente, PostgreSQL, backup/restore, segurança, troubleshooting PowerShell, usuário, administrador, API/integrações, atualização/rollback e runbook de produção.
