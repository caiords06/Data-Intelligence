# Data Intelligence V9.5 — Refatoração de Domínios

A V9.5 preserva os contratos públicos e a navegação unificada da V9.4, mas reduz os monólitos dos principais departamentos.

## Estrutura

```text
interface/
  ↓
services/departamentos/
  ↓
enterprise/<departamento>.py        # fachada compatível + núcleo transacional
  ↓
enterprise/domains/<departamento>/ # componentes internos menores
  ↓
enterprise/repositories/
  ├── __init__.py   # contrato público
  └── provider.py   # seleção SQLite/custom
```

## Componentes extraídos

- Financeiro: `base.py`, `conciliacao.py`, `inteligencia.py`.
- Compras: `base.py`, `inteligencia.py`, `relatorios.py`.
- Estoque: `base.py`, `inteligencia.py`, `relatorios.py`.
- Tecnologia: `base.py`, `agentes.py`, `infraestrutura.py`.

Os imports históricos em `enterprise.financeiro`, `enterprise.compras`, `enterprise.estoque` e `enterprise.tecnologia` continuam válidos. A interface permanece consumindo somente `services.departamentos.*`.

## Objetivo arquitetural

A divisão cria fronteiras menores para testes, manutenção e futura troca do provider de persistência. A V9.5 **não altera o schema nem migra o banco para PostgreSQL**; isso evita misturar refatoração estrutural com mudança de banco.

## Navegação e leftbox

O roteador `interface/navegacao_modulos.py` da V9.4 foi preservado. A V9.5 adiciona regressões para impedir que a decomposição de backend volte a alterar caminhos, aliases ou leftboxes.

## Regra de manutenção

Novos blocos de domínio devem preferir componentes internos abaixo de ~500 linhas. Arquivos-fachada podem permanecer maiores temporariamente enquanto o núcleo transacional é extraído de forma incremental e coberta por testes.

## Persistência

A seleção do backend foi isolada em `enterprise/repositories/provider.py`. O modo padrão continua `sqlite`; `provider_temporario()` permite testes e futuras integrações sem alterar imports dos domínios.

## Pipeline de testes

A suíte foi distribuída em seis grupos de CI. Dentro de cada grupo, cada arquivo pytest roda em processo separado para impedir vazamento de threads, sockets, Tk ou estado temporário.
