# Relatório de entrega — V8

## Objetivo

A V8 conecta as áreas que na V7 eram somente representações visuais a um
backend local seguro e reorganiza os elementos que escapavam dos limites das
grades em resoluções menores.

## Interface

- login com fundo independente e ilustração transparente de nove nós;
- composição responsiva entre a marca e o texto institucional;
- busca alinhada ao cabeçalho de Acesso rápido;
- ações dos módulos em coluna interna própria;
- tabelas escuras com divisórias verticais redesenhadas automaticamente;
- estados vazios elevados acima das divisórias;
- identificação visual unificada como V8.

## Backend local

- recursos especializados em todos os departamentos;
- ciclo de vida Ativo, Arquivado e Lixeira;
- pesquisa, filtros, paginação e escopo por empresa/filial;
- auditoria de criação, alteração e mudança de estado;
- tarefas, documentos, workflows, integrações e relatórios;
- aquisição de arquivos externos e importação de SQLite;
- processamento de Excel, CSV, JSON, TXT e Parquet;
- migração idempotente `002_v8_recursos_departamentais`.

## Segurança

- permissões aplicadas em cada serviço;
- segregação por empresa e filial;
- documentos verificados por SHA-256;
- integrações armazenam referência ao cofre, não o segredo;
- URLs privadas, locais e formatos inesperados são recusados;
- automações continuam limitadas a ações declarativas seguras.

## Validação

- `python -m compileall -q .`;
- `python -m tabnanny .`;
- `python -m unittest discover -s tests -v`;
- 62 testes automatizados aprovados.

## Limites intencionais

Conectores Gmail, Microsoft Graph, SMTP, ERPs, IA externa e OAuth exigem
credenciais, consentimento e configuração do ambiente. A V8 fornece o hub e
as referências seguras, mas não simula chamadas externas sem essas condições.
