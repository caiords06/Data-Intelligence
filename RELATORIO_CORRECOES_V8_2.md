# Relatório de Correções — V8.2

## Escopo

Esta rodada foi dedicada **exclusivamente a correções, estabilização e prevenção de regressões**. Não foram adicionados novos módulos de negócio. O objetivo foi atacar os erros reproduzidos na V8.1, principalmente interface Tkinter, isolamento multiempresa/multifilial, integridade do SQLite, jobs, validações e uso de contexto em operações assíncronas.

A versão resultante foi identificada como **V8.2 — Correção e Estabilização**.

---

## 1. Correções críticas de interface

### 1.1 Colisão de `criar_estado_vazio()`

**Problema:** `interface/componentes.py` possuía duas funções globais com o mesmo nome e assinaturas diferentes. Em Python, a segunda definição substituía a primeira. Telas que usavam a assinatura antiga podiam falhar com `TypeError` ao tentar exibir estado vazio.

**Correção:** mantida uma única implementação compatível com as telas do projeto e removida a definição conflitante.

**Cobertura de regressão:** as telas que dependem do componente agora são instanciadas em smoke tests gráficos reais.

### 1.2 Tela de Usuários: mistura de `pack` e `grid`

**Problema:** a `Treeview` era criada com `painel` como pai, enquanto um frame intermediário era gerenciado por `pack`; depois a própria tabela era gerenciada por `grid` no pai errado. Isso provocava `TclError`.

**Correção:** a tabela passou a nascer dentro de `area_tabela`, onde tabela e scrollbars usam somente `grid`. O painel externo continua usando `pack`, sem misturar gerenciadores no mesmo container.

### 1.3 Rolagem e responsividade

Foram corrigidos e consolidados comportamentos de layout:

- scrollbar principal aparece apenas quando o conteúdo excede o viewport;
- sidebar rolável suporta `MouseWheel`, rolagem Linux (`Button-4`/`Button-5`) e `PageUp`/`PageDown`;
- subtítulos dos cabeçalhos recalculam `wraplength` pela largura real do container;
- textos pequenos de 7 pt foram elevados para um mínimo operacional mais legível;
- tabelas críticas mantêm rolagem horizontal quando a soma das colunas excede a largura disponível;
- o layout continua funcional em janelas menores por meio de scroll, sem depender de dimensões fixas.

### 1.4 Full HD como resolução de referência

A aplicação agora usa **1920×1080 como referência visual**, sem tornar essa resolução obrigatória.

No Windows, a janela é aberta em estado maximizado (`zoomed`) para utilizar a área útil real do monitor sem cobrir a barra de tarefas. O mínimo responsivo permanece em `1024×680`.

Isso evita dois problemas anteriores: desperdício de espaço em Full HD e quebra total quando a janela é menor.

### 1.5 Identificação visual da versão

Títulos, badges e versão do design system foram atualizados de V8.1 para **V8.2**. A versão registrada em auditoria também foi atualizada.

---

## 2. Isolamento multiempresa e multifilial

### 2.1 Vínculo usuário → empresa/filial

**Problema:** em alguns caminhos, um usuário podia manter ou selecionar contexto empresarial sem uma validação suficientemente forte do vínculo em `usuarios_empresas`.

**Correção:** `enterprise/contexto.py` passou a validar:

- empresa ativa;
- vínculo ativo do usuário;
- filial vinculada quando o vínculo é restrito;
- filial pertencente à empresa;
- contexto congelado informado por workers.

Vínculo com `filial_id` nulo continua representando acesso corporativo à empresa; vínculo com filial preenchida restringe o usuário àquela unidade.

### 2.2 Permissões de usuário fora da empresa atual

**Problema:** um administrador podia consultar/alterar permissões de um usuário existente sem confirmar que esse usuário estava vinculado à empresa selecionada.

**Correção:** consulta e gravação de permissões agora exigem vínculo ativo entre o usuário-alvo e a empresa atual.

### 2.3 Responsável de tarefa fora do escopo

**Problema:** `responsavel_id` podia apontar para um usuário existente de outra empresa/filial.

**Correção:** tarefas validam se o responsável está ativo e autorizado no mesmo escopo empresarial da tarefa antes da gravação.

### 2.4 Consultas organizacionais

Departamentos, centros de custo e filiais passaram a respeitar o vínculo do ator. A criação de centro de custo também valida se o departamento selecionado pertence à empresa ativa.

---

## 3. Vazamento de atividades e notificações entre filiais

**Problema reproduzido:** eventos operacionais eram gravados com `filial_id = NULL` em diversos caminhos. Como `NULL` era tratado como evento corporativo, uma ação da Filial A podia aparecer na Filial B.

**Correção:** os writers de atividades/notificações em módulos, central, ferramentas, workflows e recursos passam a persistir `filial_id` do contexto da operação.

Registros legados sem filial são normalizados pela migração V8.2 para uma filial válida **da própria empresa**, nunca para uma filial global de outra organização.

Eventos corporativos com filial nula continuam possíveis apenas quando forem explicitamente tratados como corporativos; as operações locais normais não dependem mais de omissão do campo.

---

## 4. Estoque multifilial

### 4.1 `movimentos_estoque` sem filial

**Problema:** movimentações sabiam a empresa e o item, mas não a filial onde ocorreram.

**Correção:** `filial_id` foi adicionado ao schema e às gravações de movimentação. Registros antigos recebem a filial do próprio item quando possível e, como fallback, uma filial ativa da mesma empresa.

### 4.2 Integridade item × empresa × filial

Foram criados triggers que impedem inserir ou alterar uma movimentação para apontar a um item que pertença a outra empresa/filial.

Assim, o banco não aceita apenas “empresa existe” + “filial existe” + “item existe”; ele exige que o **item pertença ao mesmo escopo da movimentação**.

### 4.3 SKU duplicado em filiais diferentes

**Problema de compatibilidade de banco legado:** bases atualizadas de versões antigas ainda conservavam `UNIQUE(empresa_id, codigo)`, apesar do item já ser tratado como recurso de filial. Isso impedia o mesmo SKU em duas filiais da mesma empresa.

**Correção:** a migração V8.2 detecta a restrição antiga e reconstrói `itens_estoque` preservando IDs e dados, substituindo-a por:

```text
UNIQUE (empresa_id, filial_id, codigo)
```

A reconstrução preserva referências das movimentações e recria índices/triggers de escopo. O procedimento foi testado em uma cópia do `storage/app.db` enviado.

---

## 5. Migrações multifiliais antigas

**Problema:** migrações anteriores podiam preencher `filial_id` usando a primeira filial ativa global do banco.

**Correção:** V6 e V8 foram ajustadas para inferir filial pela `empresa_id` de cada registro.

A nova migração `004_v8_2_estabilizacao.py` também normaliza registros antigos inconsistentes e cria índices/triggers adicionais.

Não há mais backfill operacional baseado em “primeira filial do banco inteiro”.

---

## 6. Job Manager e cancelamento

### 6.1 Cancelamento não é falha

**Problema:** `ProcessamentoCancelado` podia chegar ao caminho de `falhar_job()`, registrando uma ação voluntária do usuário como erro.

**Correção:** foi criado `cancelar_job()` como transição terminal explícita. A interface chama `_cancelar_job_analise()` nos fluxos de cancelamento e reserva `_falhar_job_analise()` para erros reais.

### 6.2 Encerramento da aplicação durante processamento

O fechamento da aplicação sinaliza o `cancel_event`, registra o job como cancelado quando necessário e aguarda brevemente o worker antes de destruir a janela/driver.

### 6.3 Contexto imutável para workers

Operações assíncronas utilizam `ator_execucao` com `_empresa_id` e `_filial_id` congelados. Serviços críticos passam a resolver o escopo a partir desse ator, não a partir de uma sessão global que pode mudar durante o processamento.

---

## 7. Autorização antes do `LIMIT`

Listagens centrais foram endurecidas para aplicar escopo/permissões no SQL **antes** da paginação/limite.

Isso evita o caso em que os 20 registros mais recentes pertencem a módulos não autorizados, são removidos em Python e a tela aparece vazia embora existam registros autorizados mais antigos.

A correção abrange principalmente atividades, notificações, aprovações, tarefas, documentos e relatórios.

---

## 8. Validações de negócio e numéricas

Foram corrigidas validações que permitiam estados logicamente impossíveis ou números perigosos:

- rejeição de `NaN` e infinito;
- rejeição de número decimal em campo que exige inteiro, sem truncamento silencioso;
- Marketing: conversões não podem superar leads;
- Comercial: combinações incoerentes entre etapa `Ganho`/`Perdido` e status são rejeitadas;
- Compras: quantidade precisa ser positiva;
- Financeiro: combinações contraditórias de tipo/status são rejeitadas;
- relações organizacionais de departamento e centro de custo são verificadas;
- valores monetários passam por conversão finita antes do armazenamento em centavos.

---

## 9. KPI Jurídico

**Problema:** contratos já vencidos e ainda marcados como ativos podiam entrar no indicador “Vencem em 30 dias”.

**Correção:** o intervalo agora exige vencimento entre a data atual e a data atual + 30 dias. Contratos vencidos não entram nesse KPI.

---

## 10. Segurança e consistência de integrações

Nesta revisão também foi confirmado que proteções implementadas na V8.1 continuam operantes:

- redirects de fontes externas são validados antes de seguir para destinos locais/privados;
- segredos aninhados em configurações de integrações são detectados;
- referências de credencial usam esquemas controlados;
- importações externas rodam fora da thread visual;
- SQLite externo é processado em blocos;
- arquivos temporários possuem limpeza;
- hashes de documentos são processados em blocos.

Além disso, serviços de integrações/recursos/backups foram alinhados ao contexto congelado do ator quando aplicável.

---

## 11. Auditoria

A versão da aplicação gravada pela auditoria foi atualizada para V8.2 e chamadas empresariais relevantes foram alinhadas para enviar metadados estruturados de empresa, filial, módulo, entidade e operação quando disponíveis.

---

## 12. Testes adicionados

### Regressões de backend V8.2

Arquivo:

```text
tests/test_v8_2_correcoes.py
```

Cobre, entre outros:

- isolamento de atividades/notificações por filial;
- movimentação de estoque com filial correta;
- bloqueio de movimento apontando item de outra filial;
- mesmo SKU permitido em filiais diferentes;
- usuário restrito impedido de trocar para outra filial;
- responsável de tarefa de outra empresa rejeitado;
- permissões de usuário fora da empresa atual bloqueadas;
- cancelamento terminal de job;
- validações Marketing/Comercial/inteiros;
- KPI Jurídico de vencimento.

### Smoke tests gráficos reais

Arquivo:

```text
tests/test_interface_smoke_v8_2.py
```

Os testes instanciam Tkinter de verdade e cobrem **35 cenários de tela**, incluindo:

- Central da aplicação;
- Catálogo de módulos;
- Central Analytics;
- Nova análise;
- Histórico;
- Aprovações;
- Notificações;
- Configurações;
- Organização;
- Perfis;
- Usuários;
- painel e cadastro dos nove departamentos;
- Tarefas;
- Documentos;
- Workflows;
- Integrações;
- Relatórios;
- Auditoria.

Em Linux/CI são executados por opt-in com Xvfb:

```bash
RUN_TK_SMOKE=1 xvfb-run -a python -m pytest -q tests/test_interface_smoke_v8_2.py
```

O opt-in explícito evita que uma variável `DISPLAY` inválida faça a suíte comum falhar em ambientes sem servidor gráfico real.

---

## 13. Validação final executada

### Código

```text
python -m compileall -q .     OK
python -m tabnanny .          OK
AST duplicate/default scan    0 problemas
```

### Testes comuns

```text
75 passed
1 skipped (smoke gráfico opt-in)
30 subtests passed
```

### Smoke gráfico

```text
1 test passed
35 subtests passed
```

### Banco enviado pelo usuário

A migração foi testada sobre uma cópia e depois aplicada ao banco incluído no pacote final:

```text
PRAGMA integrity_check        ok
PRAGMA foreign_key_check      0 violações
Migração V8.2                 aplicada
Triggers de estoque           presentes
```

### Coverage da suíte comum

Excluindo os próprios arquivos de teste:

```text
Cobertura do código-fonte: ~62%
```

O smoke gráfico é executado separadamente e, portanto, não está somado a essa medição.

---

## 14. Arquivos principais alterados

```text
main.py
README.md
auth/banco.py
dados/fontes.py

enterprise/banco.py
enterprise/contexto.py
enterprise/central.py
enterprise/organizacao.py
enterprise/modulos.py
enterprise/ferramentas.py
enterprise/workflows.py
enterprise/recursos.py
enterprise/integracoes.py
enterprise/backups.py
enterprise/jobs.py
enterprise/migrations/001_v6_estabilizacao.py
enterprise/migrations/002_v8_recursos_departamentais.py
enterprise/migrations/004_v8_2_estabilizacao.py
enterprise/migrations/__init__.py

interface/componentes.py
interface/usuarios.py
interface/app.py
interface/tema.py
interface/central_analytics.py
interface/nova_analise.py
interface/painel_modulo.py
interface/modulo_empresarial.py
interface/principal.py
interface/login.py
interface/historico.py
interface/organizacao.py
interface/configuracoes_app.py
interface/ferramentas.py
interface/primeiro_acesso.py

tests/test_v8_2_correcoes.py
tests/test_interface_smoke_v8_2.py
tests/test_interface_v7.py
```

---

## Resultado

Todos os **problemas reproduzidos e identificados nesta rodada de revisão** receberam correção e teste de regressão quando tecnicamente verificável. A aplicação compila, a suíte automatizada está verde, as telas críticas constroem sob Tkinter real e o SQLite enviado passa em integridade e foreign keys após a migração.

Isso não equivale a afirmar que um software com mais de vinte mil linhas nunca poderá conter outro defeito ainda não exercitado. A diferença da V8.2 é que os erros encontrados nesta rodada deixaram de depender apenas de teste manual: os principais agora possuem regressões automatizadas para evitar retorno silencioso.
