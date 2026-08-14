# V9.7 — RH, Estoque e componentes departamentais

A V9.7 conclui a segunda etapa da refatoração visual iniciada na V9.6. O roteador e as leftboxes da V9.4 continuam canônicos; esta versão muda a organização interna das telas, não os caminhos vistos pelo usuário.

## Estrutura

- `interface/rh.py` é uma fachada pequena e compatível.
- `interface/rh_views.py` concentra renderização e tabelas.
- `interface/rh_acoes.py` concentra formulários, comandos e diálogos.
- `interface/rh_shared.py` concentra catálogo, dependências e formatadores do módulo.
- `interface/estoque.py`, `estoque_views.py`, `estoque_acoes.py` e `estoque_shared.py` seguem o mesmo contrato.
- `interface/componentes_departamentais.py` centraliza padrões reutilizáveis de KPIs e atalhos.

## Regra arquitetural

Novas funcionalidades de RH e Estoque não devem voltar a crescer diretamente nas classes-fachada. Componentes de apresentação ficam em `*_views.py`; comandos e formulários ficam em `*_acoes.py`; elementos visuais repetidos devem ir para `componentes_departamentais.py` ou `componentes.py` quando forem realmente globais.

## Compatibilidade

Os imports públicos `from interface.rh import TelaRH` e `from interface.estoque import TelaEstoque` continuam válidos. Os métodos usados por navegação, testes e integrações são fornecidos pelos mixins e mantêm os nomes anteriores.
