# Entrega — Workspace Estoque 2.0

## Resultado

O módulo de Estoque foi reconstruído como um workspace departamental
especializado. A tabela `itens_estoque` foi preservada como origem legada,
enquanto o novo ciclo operacional utiliza um domínio `est_*` multiempresa,
multifilial, rastreável e auditável.

Financeiro 2.0, RH 2.0 e os demais departamentos não foram substituídos. A
integração ocorre por aprovações, tarefas, notificações, atividades,
solicitações de compra e pelo Analytics central.

## Interface

A sidebar especializada possui grupos recolhíveis:

- Cadastros: itens, categorias, patrimônio e fornecedores;
- Operações: movimentações, recebimentos, saídas, reservas,
  transferências e devoluções;
- Controle: inventários, depósitos, endereços, lotes, avarias e perdas;
- Planejamento: reposição, cobertura, alertas e solicitações;
- Gestão: relatórios, auditoria e configurações.

As ações do cabeçalho mudam de acordo com a seção. Tabelas possuem
pesquisa, rolagem horizontal e vertical, divisórias recalculadas e estado vazio
em primeiro plano. A Visão geral apresenta indicadores, atalhos, o fluxo
Recebimento–Conferência–Armazenagem–Reserva–Expedição e os alertas atuais.

## Cadastro e endereçamento

O cadastro mestre armazena código, SKU, barras, QR, nome, descrição,
categoria, marca, fabricante, modelo, unidade, peso, dimensões, imagem,
fornecedor, custos, limites, consumo, lead time e regras de rastreabilidade.

Depósitos pertencem à empresa e filial. Localizações podem representar
corredor, prateleira, nível e posição, permitindo endereços como
`DEP01-A-03-02`.

## Razão, saldos e custos

`est_movimentacoes` é imutável por triggers de banco: `UPDATE` e `DELETE`
são rejeitados. Cada linha registra item, depósito, localização, lote,
quantidade assinada, saldo anterior, saldo posterior, custo, usuário, motivo,
documento, departamento e centro de custo.

O saldo físico é atualizado somente dentro da mesma transação que grava o
razão. Estoque negativo é bloqueado por padrão. Entradas recalculam custo
médio ponderado e preservam o histórico de custos.

## Operações

Entradas e recebimentos passam por recebimento, conferência e armazenagem.
Saídas registram separação, expedição ou consumo interno. Ajustes, perdas,
avarias, vencimentos e transferências exigem aprovação humana autorizada.

Transferências debitam a origem ao iniciar o trânsito. O destino somente é
creditado quando o recebimento é confirmado, evitando saldo simultâneo nos
dois locais.

Cancelamento é permitido antes da confirmação e permanece auditado.
Operações concluídas não são apagadas; correções devem usar operações
compensatórias.

## Reservas e solicitações

Reservas reduzem a disponibilidade sem alterar o físico. Podem indicar
solicitante, departamento, centro de custo, finalidade, origem e expiração.
Liberação e atendimento mantêm histórico.

Solicitações internas entram na Central de Aprovações e ficam preparadas
para reserva, separação e entrega.

## Inventário

O inventário suporta escopo geral, parcial, rotativo, por categoria,
localização ou lote. A contagem cega oculta o saldo esperado de perfis sem
alçada. Primeira contagem, recontagem, divergência, contador e horário ficam
persistidos. Divergências geram aprovação; o ajuste final é lançado no razão.

## Lotes, validade, séries e patrimônio

Itens controlados por lote exigem o número no recebimento. Itens com validade
exigem data válida e saídas utilizam FEFO. Alertas identificam lotes vencidos
ou a vencer em 30 dias.

Itens serializados exigem um número por unidade. Patrimônios podem manter
garantia, condição, localização e vínculo com colaborador do RH.

## Reposição e integrações

A sugestão de reposição considera saldo disponível, estoque mínimo/máximo,
ponto de pedido, estoque de segurança, consumo médio e lead time. O sistema
não compra automaticamente: um usuário autorizado encaminha a sugestão,
criando solicitação e tarefa no módulo Compras.

Recebimentos de compra criam uma tarefa para o Financeiro conferir o documento
e o possível contas a pagar. O cadastro de patrimônio referencia colaboradores
do RH e pode alimentar os fluxos de TI.

## Inteligência, relatórios e alertas

O analista de Estoque explica faltas, criticidade, validade, capital parado,
perdas e itens mais movimentados. Relatórios de posição, razão, inventários,
lotes, alertas e rastreabilidade podem ser gerados em PDF, XLSX e CSV.

O Analytics recebe o universo autorizado do novo cadastro sem usar o limite
da tabela visual. Custos são removidos quando o ator não possui permissão.

## Segurança e limites

Foram adicionados perfis de Operador, Analista, Gestor e Auditor de Estoque,
além de 17 permissões granulares por ação. O módulo não executa compras,
baixas patrimoniais sensíveis ou ajustes divergentes sem ação humana.

Leitura por webcam, coletores físicos, etiquetas impressas, integração fiscal,
WMS externo, transportadoras e APIs bancárias exigem hardware, credenciais e
homologação; a interface atual aceita o código lido por scanner que opere como
teclado.

## Validação

- 109 testes automatizados aprovados;
- 7 smoke tests de Tkinter mantidos com execução condicionada a display;
- compilação, AST e `tabnanny` aprovados;
- 10 regressões dedicadas ao Estoque 2.0;
- regressão integral do Financeiro 2.0, RH 2.0 e demais módulos aprovada.
