# Relatório de entrega — V9.0.0 integrada

## Resultado

A versão integra as correções de estabilidade identificadas na auditoria e
adiciona a fundação distribuída solicitada. O pacote de distribuição não
contém banco, usuários, hashes, arquivos operacionais, caches, screenshots ou
credenciais.

## Correções concluídas

- isolamento de empresa e filial nas operações sensíveis do RH;
- Central de Aprovações sincronizada com Financeiro, Compras, RH, Estoque e TI;
- alçadas efetivas no Financeiro e etapas reais em Compras;
- backup integral, manifesto SHA-256, verificação e restauração administrativa;
- relatórios sem truncamentos silenciosos e metadados de formato corrigidos;
- sessões revogadas em mudanças de senha, perfil, status e MFA;
- TOTP opcional com segredo armazenado fora do SQLite;
- limite de 500 MB antes de carregar arquivos locais no Pandas;
- callbacks de rede descartados quando a tela de Tecnologia já foi fechada;
- consultas corporativas com tratamento correto de `filial_id NULL`;
- centavos como fonte monetária canônica para aprovações;
- SQLite em WAL, foreign keys ativas e timeout de concorrência;
- divisórias de tabelas recalculadas pela geometria efetivamente renderizada.

## Funcionalidades integradas

- correio corporativo interno com endereço por usuário, Para/Cc/Cco,
  rascunhos, enviadas, arquivo, lixeira, leitura, anexos e auditoria;
- tela administrativa de nós Servidor/Central/Agente;
- receptor HTTP com health check e heartbeat de agentes;
- autenticação HMAC-SHA256, nonce, janela temporal e bloqueio/revogação;
- agente Windows com inventário, telemetria, DPAPI e tarefa agendada;
- scripts de build da aplicação, servidor e agente;
- telas genéricas de Marketing, Administrativo, Jurídico e Comercial com
  painel em cards/fluxos por padrão e tabela de dados sob demanda;
- edição por duplo clique e exportação completa do filtro para XLSX/CSV;
- correio corporativo acessível em todas as sidebars departamentais;
- restauração completa separada da restauração de preferências.

## Validação

| Verificação | Resultado |
|---|---:|
| Arquivos Python | 153 |
| Linhas Python | 47.232 |
| Testes descobertos | 163 |
| Testes aprovados | 153 |
| Testes ignorados | 10 |
| Falhas | 0 |
| Compilação | Aprovada |
| `tabnanny` | Aprovado |

Os dez testes ignorados exigem um desktop gráfico real. A infraestrutura
continua disponível em `scripts/gerar_capturas_interface.py`: ela gera PNGs,
manifesto, folha de contato e relatório, e agora também verifica controles fora
da janela, sobreposições, textos comprimidos e scrollbars desalinhadas.

## Limite operacional consciente

O servidor está implementado e pode ser empacotado, mas não foi publicado em
um provedor externo: isso exige host, domínio, certificado e credenciais da
empresa. A documentação de implantação descreve o caminho seguro sem inserir
segredos de produção no projeto.
