# Relatório da implementação · Compras e Suprimentos 2.0

## Objetivo

O módulo foi reconstruído para que o departamento de Compras possa operar o
ciclo completo de aquisição dentro da plataforma. O sistema não compra nem
escolhe fornecedores sozinho: ele organiza evidências, calcula comparações,
aplica alçadas e exige decisões humanas nas etapas sensíveis.

## Fluxo implantado

```text
Necessidade
    ↓
Solicitação multi-item
    ↓
Aprovação por alçada
    ↓
Cotação e propostas
    ↓
Negociação e escolha humana
    ↓
Pedido de compra aprovado
    ↓
Entrega e recebimento parcial/total
    ↓
Estoque ou Patrimônio
    ↓
Conta a pagar no Financeiro
    ↓
Analytics e auditoria
```

## Interface departamental

A sidebar de Compras está agrupada por processo:

| Grupo | Seções |
|---|---|
| Demandas | Minhas solicitações, Todas, Aprovações, Catálogo |
| Sourcing | Cotações, Mapa comparativo, Negociações |
| Pedidos | Pedidos de compra, Acompanhamento |
| Fornecedores | Cadastro, Homologação, Avaliações, Documentos |
| Recebimento | Recebimentos, Divergências |
| Contratos | Contratos, Aditivos |
| Gestão | Alertas, Relatórios, Auditoria, Configurações |

A Visão geral apresenta oito indicadores, atalhos operacionais, ciclo
clicável de suprimentos e fila de trabalho. As tabelas usam rolagem vertical e
horizontal, divisórias persistentes, busca local e estado vazio sobreposto.

## Demandas e aprovações

- Uma solicitação pode conter vários produtos e serviços.
- Cada item guarda especificação, quantidade, unidade, estimativa e eventual
  vínculo ao cadastro mestre do Estoque.
- A demanda possui justificativa, prioridade, data necessária, departamento,
  centro de custo e recorrência.
- Rascunhos podem ser salvos antes do envio.
- O envio escolhe uma regra de alçada por faixa monetária, prioridade e
  departamento e cria uma aprovação central.
- Aprovar, rejeitar ou solicitar alteração registra usuário, justificativa,
  data, estado anterior e estado posterior.

## Sourcing, cotação e negociação

- Uma cotação aceita um ou mais fornecedores ativos.
- Cada fornecedor responde por item, com preço, frete, impostos, desconto,
  prazo, validade, pagamento, garantia e condições comerciais.
- O mapa comparativo calcula scores separados de preço, prazo e qualidade.
- A ponderação atual é determinística e visível: 50% preço, 25% prazo e
  25% qualidade histórica.
- O score não toma a decisão. O comprador escolhe e precisa justificar.
- Rodadas de negociação preservam proposta anterior, contraproposta,
  economia, prazo, condições e responsável.
- O saving é a diferença entre a referência aprovada e o valor escolhido.

## Pedidos e entregas

- A proposta escolhida gera um pedido sem copiar informação manualmente.
- O pedido passa por aprovação humana antes do envio.
- Estados: aguardando aprovação, aprovado, enviado, confirmado, em produção,
  em transporte, parcialmente recebido, recebido, cancelado e encerrado.
- Um PDF profissional lista empresa, filial, fornecedor, endereço, itens,
  quantidades, valores, condição e aprovação.
- Atrasos geram alertas e aparecem no Analytics de Compras.

## Recebimento e integrações

- Recebimentos podem ser parciais sem serem classificados como divergência.
- Cada conferência registra quantidade recebida, aceita e recusada, lote,
  validade, números de série, nota fiscal e responsável.
- Recusa ou divergência manual pode representar quantidade, preço, produto,
  avaria, documento, atraso ou outro problema.
- Divergências permanecem abertas até uma resolução humana auditada.
- Itens aceitos vinculados ao cadastro de Estoque geram entrada confirmada no
  depósito autorizado.
- O recebimento cria uma tarefa para o Financeiro. A ação autorizada gera uma
  conta a pagar ligada ao pedido, nota fiscal, fornecedor e centro de custo.
- Se uma integração não puder ser executada por permissão ou dados ausentes,
  o sistema cria tarefa e notificação em vez de perder a operação.

## Fornecedores, documentos e contratos

- O cadastro de fornecedor é sincronizado com Estoque e Financeiro.
- Homologação possui estados Em análise, Homologado, Com restrições,
  Bloqueado e Inativo.
- Avaliações calculam média de preço, prazo, qualidade, atendimento e
  conformidade e atualizam o score compartilhado.
- Documentos são copiados para o repositório corporativo, classificados,
  ligados ao fornecedor e verificados por SHA-256.
- Validades documentais e contratuais alimentam a Central de Alertas.
- Contratos registram fornecedor, objeto, vigência, valor, periodicidade,
  índice, percentual, renovação e prazo de cancelamento.
- Aditivos preservam valores e datas anteriores antes da atualização.

## Analytics e relatórios

O motor de Compras avalia:

- valores e saving;
- concentração por fornecedor;
- pedidos atrasados;
- baixa concorrência;
- solicitações recorrentes;
- possível fracionamento de demandas;
- divergências e contratos vencendo.

O DataFrame analítico recebe o universo autorizado, sem o limite visual da
tabela. Relatórios de solicitações, cotações, pedidos, fornecedores,
recebimentos, divergências, contratos e auditoria podem ser gerados em PDF,
XLSX ou CSV. A agenda de relatórios é persistente.

## Segurança e dados

- 24 ações granulares são controladas pelo perfil e por exceções individuais.
- Perfis: Solicitante, Comprador, Gestor, Recebimento e Auditor de Compras.
- Todos os valores monetários especializados usam centavos inteiros.
- O contexto de empresa e filial é aplicado a solicitações, cotações,
  pedidos, recebimentos, contratos, alertas e histórico.
- A trilha `cmp_historico` possui gatilhos que bloqueiam UPDATE e DELETE.
- A migração é idempotente e preserva solicitações legadas.

## Validação

- 27 tabelas especializadas de Compras;
- quatro alçadas iniciais e configuração adicional suportada;
- 10 testes novos do módulo;
- 119 testes aprovados no projeto completo;
- `compileall`, `tabnanny` e validação AST sem erros;
- `PRAGMA foreign_keys = 1` e `PRAGMA integrity_check = ok`.

Os sete smoke tests gráficos existentes ficam condicionados a um display Tk
real e não representam falha do código.
