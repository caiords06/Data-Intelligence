# Relatório de entrega — Tecnologia e Serviços 2.0

## Resultado

Tecnologia deixou de utilizar o painel departamental genérico e passou a ter
um workspace funcional, persistente e auditável. A nova arquitetura conecta o
atendimento ao inventário, os ativos à telemetria, a infraestrutura aos
alertas e as mudanças à aprovação humana.

## Fluxo operacional

1. o usuário abre um chamado e informa impacto, urgência, prioridade, ativo e
   sistema relacionados;
2. a plataforma aplica o SLA, registra comentários e mantém o histórico de
   cada transição;
3. o ativo pode enviar heartbeat com CPU, memória, disco, espaço livre,
   latência e uptime;
4. limites críticos geram alertas e o ativo pode seguir para manutenção;
5. sistemas e monitores registram eventos de disponibilidade;
6. problemas recorrentes viram registros de causa raiz e mudanças relevantes
   entram na Central de Aprovações;
7. relatórios e o motor analítico usam o universo autorizado sem o limite
   silencioso da tabela visual.

## Funcionalidades

### Service Desk

- chamados e chamados do usuário;
- SLA por prioridade;
- triagem, atendimento, espera, resolução, reabertura e cancelamento;
- comentários internos ou visíveis;
- ativo, sistema, solicitante e técnico relacionados;
- base de conhecimento.

### Ativos e CMDB

- patrimônio, série, hostname, IP, MAC, hardware e sistema operacional;
- responsável, departamento, centro de custo, local, compra e garantia;
- conectividade e saúde separadas do status de ciclo de vida;
- telemetria, manutenções e equipamento substituto preparado no modelo;
- vínculos opcionais com Estoque e fornecedores de Compras.

### Rede e monitoramento

- segmentos CIDR privados de até 4096 endereços;
- autorização formal com justificativa e usuário responsável;
- registro de dispositivos somente dentro do segmento autorizado;
- origem do dado identificada: agente, SNMP, importação ou conector;
- monitores de CPU, memória, disco, latência, disponibilidade, serviço,
  backup e API;
- alertas idempotentes para evitar duplicação.

### Software e governança

- licenças, capacidade, atribuições, custo e renovação;
- sistemas, ambientes, criticidade, servidor e responsáveis;
- contratos de TI;
- problemas e causa raiz;
- mudanças com plano de execução, rollback e aprovação;
- incidentes de segurança e contenção;
- relatórios CSV, JSON e HTML;
- auditoria imutável.

## Segurança

- perfis: Solicitante de TI, Suporte N1, Suporte N2, Gestor e Auditor;
- permissões granulares por ação e possibilidade de exceção por usuário;
- somente redes privadas previamente autorizadas aceitam descobertas;
- a plataforma não captura pacotes e não executa varredura silenciosa;
- o acesso remoto exige perfil autorizado, consentimento, justificativa e
  abertura deliberada do cliente externo;
- cada sessão registra ativo, técnico, provedor, chamado, início, término,
  duração e resultado;
- segredos não são armazenados no cadastro do ativo.

## Persistência

A migração `010_tecnologia_departamental` adiciona 24 tabelas `ti_*`,
chaves estrangeiras, índices e bloqueio de alteração/exclusão do histórico.
Valores monetários são armazenados em centavos.

## Validação

- 129 testes aprovados;
- 10 testes específicos de Tecnologia 2.0;
- 7 smoke tests gráficos condicionados a display;
- `compileall`, AST e `tabnanny` sem erro;
- `PRAGMA foreign_keys = 1`;
- `PRAGMA integrity_check = ok`;
- regressões de Financeiro 2.0, RH 2.0, Estoque 2.0 e Compras 2.0 preservadas.

## Limites conscientes

O projeto ainda não distribui um agente corporativo, não faz varredura ativa,
não captura pacotes e não implementa um protocolo próprio de acesso remoto.
Essas responsabilidades ficam para agentes e provedores homologados. O módulo
atual oferece o domínio, as validações, os fluxos, a auditoria e a interface
necessários para integrá-los com segurança.
