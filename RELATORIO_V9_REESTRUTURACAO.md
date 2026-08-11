# Relatório técnico — Reestruturação Corporativa V9.0

## Escopo executado

A V9.0 foi construída sobre a base TI Remote 1.1.2 e concentra uma mudança de arquitetura visual, colaboração corporativa, distribuição em rede e correções de estabilidade apontadas na auditoria.

### Front-end

- Criadas experiências departamentais próprias para RH, Financeiro, Estoque, Compras, Marketing, Administrativo, Jurídico e Comercial.
- Tecnologia mantém arquitetura operacional especializada de rede/ativos/service desk.
- Analytics foi preservado, conforme solicitado.
- Criada `TelaOperacaoVisual` para fluxos em que cards/workspaces representam melhor o domínio que uma grade.
- Grades permaneceram nos contextos de comparação massiva e receberam edição direta + exportação CSV/XLSX.
- Removidas divisórias de coluna desenhadas manualmente sobre `Treeview`, eliminando desalinhamento em DPI, resize e scroll horizontal.

### Correio corporativo

- `email_corporativo` incorporado ao usuário.
- Correio interno com entrada, enviados, rascunhos, arquivados, lixeira, anexos e busca.
- Disponível globalmente e a partir dos módulos.
- Em modo servidor, mensagens/anexos são operados pelo Servidor Corporativo.

### Servidor/estações

- Introduzidos papéis `standalone`, `central`, `cliente`, `servidor`.
- Servidor Corporativo instalável com HTTP(S), autenticação, arquivos, backups, correio e usuários.
- Central administrativa conecta ao servidor e pode administrar usuários/arquivos.
- Cliente convencional não executa primeiro acesso e não permite gerenciamento de usuários.
- Agente TI permanece separado para inventário/telemetria de endpoints.
- Build Windows agora produz os quatro pacotes de implantação.

### Correções de auditoria

1. **RH / filial:** operações críticas passaram a validar empresa + filial, inclusive folha, férias, equipamentos, documentos, solicitações, admissão/desligamento e benefícios.
2. **Central de Aprovações:** novos recursos delegam decisão aos motores nativos de Financeiro, Compras, RH, Estoque e TI.
3. **Alçadas Financeiras:** a etapa pendente valida o perfil aprovador exigido.
4. **Compras:** regras de aprovação agora materializam etapas Gestor/Financeiro/Diretoria.
5. **Backup:** substituída cópia isolada do DB por pacote completo com storage, manifesto, hashes e restauração.
6. **Fluxo/Projeções Financeiro:** preenchimento de tabela não exige `id` em linhas calculadas.
7. **Relatórios:** truncamentos PDF passam a ser explícitos e metadados XLSX/PDF foram corrigidos.
8. **Sessões:** `sessao_epoch` invalida sessão após alteração sensível.
9. **Importação local:** arquivos acima de 100 MiB são bloqueados antes de leitura integral pelo Pandas.
10. **Callbacks de Tecnologia:** atualizações tardias verificam se a UI ainda existe.
11. **Filial corporativa NULL:** consultas corporativas relevantes tratam contexto sem filial explicitamente.
12. **Valores monetários:** `valor_centavos` é canônico e triggers mantêm o campo REAL legado sincronizado.
13. **Concorrência SQLite:** conexões tentam WAL + `synchronous=NORMAL` + `busy_timeout` + foreign keys.
14. **Caminhos RH:** novos documentos/contracheques usam caminhos relativos à storage; migração normaliza legados seguros.
15. **Distribuição:** script falha se encontrar `app.db`, `.git`, `__pycache__`, `.pyc`, caches ou artefatos visuais no deployment.
16. **Testes visuais:** analisador ganhou heurísticas adicionais para controles comprimidos/colunas excessivamente estreitas; o build Windows agora executa smoke Tk real obrigatório das telas críticas e das experiências V9. Screenshots extensivos permanecem opt-in.

## Arquivos principais adicionados

- `interface/experiencias_departamentais.py`
- `interface/operacoes_visuais.py`
- `interface/grade_editavel.py`
- `interface/correio.py`
- `interface/servidor_corporativo.py`
- `enterprise/correio.py`
- `enterprise/servidor_cliente.py`
- `core/nodo.py`
- `servidor_corporativo/*`
- `DataIntelligenceServer.spec`
- migrations `014` a `018`
- scripts de configuração Central/Cliente/Servidor
- `scripts/verificar_pacote_limpo.py`
- `tests/test_vnext_estabilizacao.py`

## Limite deliberado da V9.0

Não foi compartilhado o SQLite operacional por rede. Isso seria uma solução frágil para múltiplas estações.

Nesta versão, o Servidor Corporativo é compartilhado para usuários/autenticação, correio, arquivos espelhados e backups. Os CRUDs departamentais ainda são executados localmente no desktop. A fase seguinte, caso seja desejada concorrência transacional real entre várias estações, deve expor os serviços de domínio pelo servidor e migrar a persistência compartilhada para PostgreSQL.
