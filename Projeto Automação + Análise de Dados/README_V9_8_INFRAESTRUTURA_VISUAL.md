# V9.8 — Infraestrutura Visual Compartilhada

A V9.8 reduz os monólitos visuais compartilhados sem alterar os contratos públicos da interface.

## Componentes

- `interface/componentes.py` tornou-se uma fachada compatível.
- Navegação/cabeçalhos: `componentes_navegacao.py`.
- Controles básicos: `componentes_basicos.py`.
- Containers responsivos: `componentes_responsivos.py`.
- `TelaPainelModulo` foi dividida em visão e operações.
- `TelaCentralAnalytics` foi dividida em dashboard, datasets e recursos.
- `TelaModuloEmpresarial` foi dividida em tabela/paginação e formulários.

## Compatibilidade

Os imports existentes continuam válidos:

```python
from interface.componentes import criar_sidebar, AreaRolavel
from interface.painel_modulo import TelaPainelModulo
from interface.central_analytics import TelaCentralAnalytics
from interface.modulo_empresarial import TelaModuloEmpresarial
```

Roteador, aliases de navegação e leftboxes permanecem sob a arquitetura estabilizada na V9.4.

## Regra de manutenção

Arquivos-fachada não devem voltar a concentrar implementação. Novas responsabilidades devem ser adicionadas aos componentes especializados e cobertas por testes.
