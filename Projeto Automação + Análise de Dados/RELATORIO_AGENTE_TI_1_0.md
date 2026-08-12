# Entrega — Agente TI 1.0

Foi criado o primeiro agente distribuível do módulo Tecnologia. A implementação
é isolada do processo gráfico principal e pode ser empacotada como executável
para computadores Windows administrados pela empresa.

## Componentes entregues

- configuração validada, com HTTPS obrigatório;
- credencial separada e protegida pelo Windows DPAPI;
- coletor local de inventário e telemetria;
- consulta controlada de ID, alias, versão e status do AnyDesk;
- transporte JSON autenticado por HMAC-SHA256;
- execução contínua, backoff, status, logs rotativos e trava de instância;
- comandos `configure`, `collect`, `once`, `run`, `install`, `uninstall` e
  `task-status`;
- build PyInstaller e instalação pelo Agendador do Windows;
- documentação operacional e configuração de laboratório;
- onze testes próprios integrados à regressão completa.

## Decisões de segurança

O agente segue coleta mínima. Não há descoberta de rede, execução remota,
captura de tela, leitura de documentos, keylogging ou coleta de histórico de
navegação. O token não é enviado no payload e o transporte recusa
redirecionamentos. A API futura deverá validar timestamp, nonce, assinatura,
patrimônio e escopo antes de chamar o domínio de Tecnologia.

## Próxima etapa

Criar a API central de agentes, com provisionamento, revogação, proteção contra
replay, persistência de último contato e integração com `registrar_heartbeat()`.
