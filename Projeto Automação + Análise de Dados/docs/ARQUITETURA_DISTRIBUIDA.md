# Arquitetura distribuída da V9

## Papéis

| Componente | Responsabilidade | Pode administrar usuários? |
|---|---|---:|
| Servidor central | Receber agentes, manter banco, arquivos, backups e integrações | Não pela API do agente |
| Aplicação central | Interface completa para administradores, governança, nós e restauração | Sim |
| Aplicação de usuário | Acesso aos módulos liberados pelo perfil e correio corporativo | Não |
| Agente de TI | Inventário e telemetria autorizada do computador | Não |

## Fluxo operacional

1. O administrador cadastra um nó do tipo **Agente** em **Infraestrutura**.
2. A aplicação mostra uma vez o identificador e o token de provisionamento.
3. O agente é configurado com o mesmo identificador, URL HTTPS e token.
4. Cada heartbeat leva timestamp, nonce e assinatura HMAC-SHA256.
5. O servidor rejeita agentes bloqueados, assinaturas inválidas, mensagens antigas e replay.
6. O snapshot aceito atualiza o inventário de Tecnologia no escopo da empresa/filial.

## Persistência e arquivos

O SQLite continua adequado à edição desktop atual e opera com `WAL`,
`busy_timeout` e foreign keys ativas. Arquivos são mantidos fora do banco,
com caminho relativo e SHA-256. O backup completo inclui o snapshot consistente
do SQLite e todo o armazenamento gerenciado.

O pacote de backup contém documentos e segredos operacionais. Ele deve ser
armazenado em local criptografado, com acesso administrativo e retenção
controlada. A V9 não envia o arquivo para um provedor de nuvem sem que o
administrador configure uma infraestrutura e credenciais reais.

## Limites da entrega

O projeto inclui o servidor executável e os componentes de central/agente. A
publicação em nuvem exige um host, domínio, certificado TLS, firewall, rotina
de atualização e política de backup definidos pela empresa. Nenhuma credencial
de produção é criada ou embutida no código.
