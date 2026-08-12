# Data Intelligence Enterprise Platform — V8.2.1
## Relatório de correções de navegação, interface e histórico

Data da rodada: 10/08/2026

Esta rodada foi feita sobre a V8.2 corrigida e teve como foco exclusivamente os problemas relatados após o teste visual da aplicação. Não foram adicionados novos módulos de negócio.

## 1. Histórico de análises — seleção múltipla

### Problema
A tabela do histórico trabalhava essencialmente com uma seleção individual. Não era possível selecionar várias análises e removê-las em conjunto com um comportamento visual coerente para ações que exigem um único registro.

### Correção
- `Treeview` configurada explicitamente com `selectmode="extended"`.
- `Ctrl+A` seleciona todos os registros visíveis.
- exclusão aceita uma ou várias análises;
- confirmação informa a quantidade selecionada;
- exclusão múltipla é feita em uma única transação;
- antes da transação todos os IDs são validados, evitando exclusão parcial;
- a exclusão continua lógica/auditável (`Lixeira`), não destrói imediatamente o histórico;
- `VER DETALHES` fica desabilitado, escuro e não clicável quando há zero ou mais de um item selecionado;
- `EXCLUIR` fica disponível quando existe pelo menos uma seleção;
- duplo clique só abre detalhes quando existe exatamente um registro selecionado;
- status da seleção é atualizado corretamente ao alternar entre nenhuma, uma ou várias linhas.

Arquivos principais:
- `interface/historico.py`
- `historico/repositorio.py`

## 2. Sidebar do Analytics mudava ao navegar

### Problema
O Dashboard analítico possuía uma sidebar própria. Ao clicar em `Explorar dados`, `Relatórios`, `Visualizações`, `Modelos` e outros destinos, a aplicação abria páginas da Central Analytics que construíam uma sidebar diferente. Isso fazia o contexto visual mudar durante a navegação.

Também havia divergência de nomenclatura: o menu dizia `Explorar dados`, enquanto a tela aberta se chamava `Conjuntos de dados`.

### Correção
Foi criada uma definição canônica única de navegação do Analytics, compartilhada por:
- Dashboard analítico;
- Nova análise;
- Importações;
- Explorar dados;
- Relatórios;
- Visualizações;
- Agendamentos;
- Alertas analíticos;
- Modelos;
- Perfis de análise;
- IA Assistente.

A mesma ordem, os mesmos rótulos e o mesmo contexto são usados nas páginas analíticas. `Explorar dados` também passou a ser o título da página correspondente, eliminando a mudança aparente para `Conjuntos de dados`.

A navegação do Dashboard processado usa wrappers seguros, preservando o tratamento de encerramento/processamento existente antes de trocar de tela.

Arquivos principais:
- `interface/navegacao_analytics.py`
- `interface/app.py`
- `interface/central_analytics.py`
- `interface/componentes.py`

## 3. Revisão de sidebars dos módulos departamentais

Os menus de RH, Financeiro, Estoque, Compras, TI, Marketing, Administrativo, Jurídico e Comercial foram revistos para garantir que o menu permaneça igual ao alternar entre:
- visão geral;
- cadastro principal;
- seções especializadas do departamento.

Foi acrescentado teste gráfico que compara o menu exibido nos dois construtores de tela departamental (`TelaPainelModulo` e `TelaModuloEmpresarial`) em todos os nove módulos.

O item referente à página atual também deixa de ser clicável, evitando navegação redundante sobre a própria tela.

## 4. Erro da scrollbar — `bad window path name`

### Erro relatado
`_tkinter.TclError: bad window path name "...!arearolavel.!scrollbar"`

O erro acontecia quando um evento de roda do mouse era entregue depois que a tela anterior já havia sido destruída. O callback ainda tentava consultar `winfo_ismapped()` em uma scrollbar que já não existia.

### Correção
`AreaRolavel` agora:
- verifica a existência do frame, canvas e scrollbar antes de qualquer operação;
- captura `TclError` em callbacks de rolagem e sincronização;
- remove bindings globais ao destruir a área;
- trata eventos tardios de mouse como eventos inválidos e os descarta;
- protege `MouseWheel`, botões 4/5 do Linux, PageUp e PageDown;
- só exibe a scrollbar quando o conteúdo realmente exige rolagem.

A mesma proteção foi aplicada ao menu rolável da sidebar.

Foi adicionado um teste que destrói intencionalmente a área e chama os callbacks depois da destruição, reproduzindo o cenário do traceback.

Arquivo principal:
- `interface/componentes.py`

## 5. Central de notificações marcava `Visão geral`

### Problema
A tela era aberta corretamente, mas a sidebar recebia `ativo="inicio"`.

### Correção
A Central de notificações agora usa `ativo="notificacoes"` e o texto da navegação global foi padronizado para `Central de notificações`.

Também foi ajustado o atalho correspondente na tela inicial.

Arquivos:
- `interface/notificacoes.py`
- `interface/componentes.py`
- `interface/principal.py`

## 6. Estrutura organizacional marcava `Configurações`

### Problema
A página `Estrutura organizacional` era exibida enquanto a sidebar destacava `Configurações`.

### Correção
A página agora usa `ativo="organizacao"`.

Também foi criado um teste gráfico que valida o item ativo das principais telas globais:
- Visão geral;
- Módulos;
- Histórico analítico;
- Aprovações;
- Central de notificações;
- Configurações;
- Organização;
- Usuários e acessos.

Arquivo:
- `interface/organizacao.py`

## 7. Remoção de empresas criadas na sessão

### Requisito
Somente administradores devem poder remover empresas que foram criadas durante a sessão atual.

### Implementação segura
A sessão mantém em memória o conjunto de IDs de empresas criadas depois do login atual.

Na Estrutura organizacional foi adicionado o botão `REMOVER EMPRESA`.

O botão só é habilitado quando:
- o usuário é administrador (a própria tela já exige administrador);
- a empresa selecionada foi criada na sessão atual;
- a empresa selecionada não é a empresa atualmente ativa.

O backend repete essas verificações, portanto a regra não depende apenas da interface.

A remoção é lógica por segurança: a empresa e suas estruturas organizacionais são desativadas e deixam de aparecer nas listas operacionais, mas o registro permanece disponível para integridade referencial e auditoria. Empresas que já existiam antes da sessão não podem ser removidas por este comando.

Arquivos:
- `auth/sessao.py`
- `enterprise/organizacao.py`
- `interface/organizacao.py`

## 8. Dashboard dizia `Nenhum arquivo selecionado` com arquivo na lista

Na captura enviada, a lista continha `Vendas - Dez.xlsx`, enquanto o texto superior ainda dizia `Nenhum arquivo selecionado`.

A rotina de atualização da lista agora sincroniza imediatamente o rótulo com a quantidade real:
- `Nenhum arquivo selecionado`;
- `1 arquivo selecionado`;
- `N arquivos selecionados`.

Arquivo:
- `interface/app.py`

## 9. Cabeçalho e versão

A versão visual foi atualizada para `V8.2.1` para identificar esta rodada de hotfix.

## 10. Testes de regressão adicionados

Foi criado `tests/test_v8_2_1_hotfix.py` para validar:
- exclusão múltipla e atômica do histórico;
- proteção contra remoção de empresa preexistente;
- remoção segura de empresa criada na sessão;
- bloqueio para usuário não administrador;
- rótulos canônicos do Analytics.

O smoke test real de Tkinter também foi ampliado para validar:
- callback tardio de scrollbar após destruição;
- item ativo das principais sidebars globais;
- seleção múltipla do Histórico;
- botão de remoção de empresa conforme contexto;
- menu idêntico entre Dashboard e Explorar dados;
- menus departamentais idênticos entre visão, seção especializada e cadastro nos nove módulos.

## 11. Validação final

Executado no projeto final:

```text
RUN_TK_SMOKE=1 xvfb-run -a pytest -q
86 passed
73 subtests passed
```

Também foram executados:

```text
python -m compileall -q .      OK
python -m tabnanny .           OK
AST duplicate check            0 duplicações
PRAGMA integrity_check         ok
PRAGMA foreign_key_check       0 violações
```

## 12. Resultado da rodada

Os problemas descritos nas capturas e no traceback desta rodada foram tratados diretamente e ganharam regressões automatizadas nos pontos críticos. A navegação agora possui um contexto estável por área, a seleção múltipla do histórico está funcional, callbacks tardios de scrollbar não operam sobre widgets destruídos e a Organização possui remoção administrativa restrita às empresas criadas na sessão atual.
