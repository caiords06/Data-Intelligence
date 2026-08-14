# Relatório de correções pós-homologação — V11.0.1

Data de consolidação: 14/08/2026.

## Escopo

Esta revisão trata os problemas observados na homologação visual e funcional da V11: execução sem elevação, persistência de tema, navegação e rolagem, foto do colaborador, relatórios de RH, acesso ao Analytics e ciclo de vida dos dados.

## Correções implementadas

### Execução desktop sem administrador

- Logs do cliente são gravados no diretório de estado do usuário (`LOCALAPPDATA` no Windows), e não em uma pasta protegida do `ProgramData`.
- A inicialização possui fallback seguro para diretório temporário e, em último caso, saída de erro padrão.
- A falha de criação do arquivo de log deixa de encerrar o aplicativo.

### Tema claro e escuro

- A escolha feita no login é salva atomicamente em preferência visual local não sensível.
- Após autenticar, o tema escolhido é reconciliado com a sessão e permanece aplicado na próxima tela.
- A preferência é recuperada antes de construir a tela de login nas execuções seguintes.

### Navegação, cores e rolagem

- Sidebars usam faixas, cabeçalhos de grupo e ícones com cores distintas, além de contraste maior no item ativo.
- Scrollbars receberam largura e contraste explícitos nos dois temas.
- O contêiner responsivo calcula se há conteúdo excedente antes de exibir e habilitar a rolagem.
- A sidebar do Analytics contém somente Inteligência, Laboratório e Administração, terminando em Regras analíticas.

### Funcionário 360°

- A foto governada aparece à direita do nome e do resumo profissional.
- O estado sem foto possui avatar por iniciais e ação explícita `ADICIONAR FOTO`.
- O estado com foto oferece `ALTERAR FOTO` e usa a miniatura produzida pelo armazenamento gerenciado.
- Upload, validação, hash, versionamento, autorização e auditoria continuam no serviço central.

### Relatórios de RH

- O build do Servidor Corporativo coleta explicitamente os motores de CSV, XLSX e PDF.
- O cliente exibe erros funcionais e de transporte de forma consistente.
- Há teste de regressão que gera o relatório de colaboradores nos três formatos e valida o conteúdo recebido.

### Analytics restrito à gestão

- O contexto empresarial impede acesso ao domínio Analytics para perfis não gerenciais, mesmo quando existir permissão genérica antiga.
- Administradores, diretoria e perfis gerenciais contextuais permanecem autorizados.
- A mesma regra protege interface, serviços e operações do domínio.

### Adicionar, editar, remover e restaurar

- Registros configuráveis do CORE aceitam remoção lógica e restauração com concorrência otimista, histórico, auditoria e atualização do índice de busca.
- A API V1 aceita `PATCH` e `DELETE` por registro, exige `If-Match` e expõe os contratos no OpenAPI.
- Seções operacionais de RH aceitam remoção lógica, filtro Ativos/Lixeira e restauração.
- Movimentações profissionais permanecem imutáveis por representarem evidência histórica.
- Relatórios e indicadores de RH excluem registros removidos por padrão.

## Validações da revisão

Foram adicionados testes específicos para preferência de tema, fallback de logs, classificação gerencial do Analytics, estrutura da sidebar, dependências de relatórios, remoção/restauração do CORE, OpenAPI, geração de relatórios de RH e remoção/restauração no RH.

A validação final da distribuição deve incluir a suíte automatizada completa, auditorias arquiteturais, verificação do instalador, empacotamento determinístico e homologação do executável em Windows limpo. O instalador Windows é produzido no próprio Windows pelo script `scripts/build_setup_windows.ps1`.

## Próxima etapa recomendada

Após instalar a V11.0.1, homologar módulo por módulo com perfis de administrador, gestor e operador. Cada fluxo deve comprovar criação, leitura, edição, remoção, restauração, permissões, auditoria, relatório e comportamento após reiniciar cliente e servidor.
