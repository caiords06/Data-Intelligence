# Financeiro 2.0 — Relatório de implementação

## Objetivo

O módulo Financeiro foi convertido em um workspace departamental próprio. A
interface, os serviços e o banco seguem o ciclo:

```text
registrar → classificar → aprovar → pagar/receber →
conciliar → contabilizar → analisar → auditar
```

As telas dos demais departamentos não foram remodeladas nesta entrega.

## Interface especializada

A sidebar financeira está organizada em grupos recolhíveis:

- **Operações:** Lançamentos, Contas a pagar, Contas a receber,
  Reembolsos, Transferências e Recorrências;
- **Tesouraria:** Fluxo de caixa, Bancos e contas, Conciliação e Cartões;
- **Planejamento:** Orçamento, Projeções e Centros de custo;
- **Gestão:** DRE, Relatórios, Aprovações e Auditoria;
- **Cadastros:** Plano de contas, Categorias e Clientes/Fornecedores.

A Visão geral apresenta recebido, pago, saldo consolidado, resultado,
pendências, vencimentos e caixa projetado. O período pode ser alternado entre
Hoje, Mês, Trimestre e Ano.

O livro financeiro possui pesquisa, paginação e filtros por status, natureza,
competência, conta, categoria, centro de custo, departamento e projeto. Os
filtros são executados no SQLite; a interface não recorta apenas os primeiros
registros carregados.

## Operações financeiras

### Lançamentos

O formulário registra:

- receita, despesa, transferência, ajuste, conta a pagar, conta a receber ou
  reembolso;
- descrição, valor, competência e vencimento;
- cliente/fornecedor, categoria e conta do plano contábil;
- departamento, centro de custo e projeto;
- conta de origem/liquidação e conta de destino;
- forma de pagamento, documento, nota fiscal, tags e observações;
- quantidade de parcelas e recorrência.

Parcelamentos dividem o total em centavos sem perder resíduos de arredondamento.
Recorrências podem ser semanais, mensais, trimestrais ou anuais e são
materializadas sem duplicar competências já geradas.

### Aprovação

As alçadas iniciais são semeadas pela migração e podem produzir uma ou mais
etapas conforme o valor. As etapas precisam ser decididas na ordem. Aprovar,
rejeitar ou solicitar alteração atualiza o título, a central corporativa de
aprovações e a auditoria.

### Pagamento e recebimento

Uma baixa pode ser parcial e registrar principal, juros, multa, desconto,
forma de pagamento e referência. O saldo remanescente e o status são
recalculados automaticamente.

Transferências geram saída e entrada entre as contas indicadas, mas não são
tratadas como receita ou despesa.

### Cancelamento e estorno

Não existe exclusão física do livro financeiro:

- um título ainda não liquidado pode ser cancelado com motivo;
- um título liquidado deve ser estornado;
- o estorno preserva o lançamento e as baixas, marca as baixas como estornadas
  e reverte o efeito no saldo;
- anexos e eventos continuam disponíveis para auditoria.

## Tesouraria e conciliação

As contas financeiras armazenam o saldo inicial em centavos e calculam o saldo
atual a partir de baixas não estornadas e transferências válidas.

A importação de extrato aceita OFX, CSV, XLSX e XLS. Antes de escolher o
arquivo, o usuário seleciona explicitamente a conta. O conciliador procura
lançamentos com valor compatível, proximidade de data e semelhança textual,
gerando um score. A confirmação continua sendo humana.

O fluxo de caixa projeta de 7 a 365 dias pela interface e suporta cenários
Realista, Otimista e Pessimista. Recebíveis e obrigações são ponderados de
forma diferente em cada cenário.

## Planejamento e gestão

Orçamentos podem ser definidos por mês, categoria e centro de custo, com
limite percentual de alerta. A tela compara planejado, realizado, disponível e
percentual utilizado.

A DRE utiliza somente lançamentos contabilizados, evitando misturar previsão
de caixa com resultado contábil. Ela calcula Receita bruta, Deduções, Receita
líquida, Custos, Lucro bruto, Despesas operacionais, EBITDA, Resultado
financeiro e Resultado.

O analista interno é determinístico e verifica:

- contas vencidas e vencimentos nos próximos sete dias;
- risco de caixa negativo;
- consumo do limite orçamentário;
- possíveis pagamentos duplicados;
- classificação incompleta para a DRE.

Ele apenas explica, alerta e recomenda. Pagamento, aprovação, conciliação e
estorno permanecem decisões humanas.

## Relatórios

A Central gera conjuntos específicos para Contas a pagar, Contas a receber,
Fluxo de caixa, DRE, Orçamento x realizado e Auditoria financeira. As saídas
disponíveis são CSV, Excel, HTML e PDF.

Agendamentos armazenam relatório, formato, frequência, próxima execução e
destinatários. A entrega externa por Gmail ou Microsoft depende de um provedor
OAuth configurado no Integration Hub; credenciais não são simuladas nem
gravadas em texto aberto por esta entrega.

## Segurança e integridade

- valores monetários são persistidos em centavos inteiros;
- datas aceitam `DD/MM/AAAA` ou ISO e extratos brasileiros usam dia primeiro;
- toda consulta exige empresa e filial do contexto autorizado;
- referências são verificadas no contexto antes da gravação;
- permissões podem ser configuradas por ação financeira;
- botões incompatíveis com o perfil ficam desativados;
- toda conexão SQLite mantém `foreign_keys=ON`;
- alterações geram atividade e histórico antes/depois.

## Arquivos principais

| Arquivo | Responsabilidade |
|---|---|
| `enterprise/financeiro.py` | regras, consultas, relatórios, conciliação e auditoria |
| `enterprise/migrations/005_financeiro_departamental.py` | esquema especializado e migração do legado |
| `interface/financeiro.py` | workspace e formulários financeiros |
| `enterprise/modulos.py` | ponte do novo livro com o Analytics central |
| `main.py` | roteamento exclusivo para o workspace Financeiro |
| `tests/test_financeiro_departamental.py` | contratos funcionais do novo domínio |

## Compatibilidade

Lançamentos criados pela API genérica das versões anteriores são
sincronizados incrementalmente para o novo livro, com IDs negativos para não
colidir com os registros nativos. Assim, dashboards e históricos existentes
continuam visíveis enquanto os novos fluxos usam o domínio especializado.

## Validação desta entrega

- `compileall`: aprovado;
- `tabnanny`: aprovado;
- 91 testes automatizados: aprovados;
- 7 smoke tests Tkinter permanecem condicionados a um display gráfico real.

