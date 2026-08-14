# V9.6 — Refatoração da camada visual

A V9.6 reduz a concentração de responsabilidades nas quatro maiores interfaces sem alterar os contratos públicos, o roteador departamental ou as leftboxes estabilizadas na V9.4.

## Estrutura

- `interface/app.py`: fachada da aplicação analítica; layout em `interface/app_layout.py`.
- `interface/financeiro.py`: fachada do Financeiro; views em `financeiro_views.py` e diálogos/formulários em `financeiro_dialogos.py`.
- `interface/compras.py`: fachada de Compras; views em `compras_views.py` e ações/formulários em `compras_acoes.py`.
- `interface/tecnologia.py`: fachada de Tecnologia; operações interativas em `tecnologia_operacoes.py` e ações/formulários em `tecnologia_acoes.py`.

As classes `AplicacaoAutomacao`, `TelaFinanceiro`, `TelaCompras` e `TelaTecnologia` permanecem com os mesmos nomes e métodos públicos, por meio de mixins. Chamadores existentes não precisam mudar.

## Regra de crescimento

A suíte V9.6 impede que as fachadas voltem ao tamanho monolítico anterior. Novas funcionalidades devem preferir componentes especializados em vez de adicionar centenas de linhas diretamente às classes-fachada.
