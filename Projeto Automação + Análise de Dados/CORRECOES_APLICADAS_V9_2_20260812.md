# V9.2 — Estabilização e Consolidação

Data da revisão: 12/08/2026

Esta revisão foi produzida a partir da auditoria integral do projeto. O objetivo foi corrigir defeitos reproduzíveis de instalação, integração, segurança, armazenamento, sessão, rede, correio, interface e validação sem reescrever o produto nem quebrar compatibilidade com bancos existentes.

## Correções críticas

- Numeração de migrations normalizada: não existem mais migrations concorrentes com prefixos `013` e `014`.
- Migration `019_compatibilidade_v9_legada` adicionada para atualizar instalações antigas sem perder registros e garantir tabelas ainda consumidas por adapters legados.
- Upgrade validado sobre cópia do banco operacional original.
- `Sessao.validar()` centraliza a validação de usuário ativo e `sessao_epoch`; o watchdog principal também revoga sessões alteradas no servidor.
- Perfil `financeiro_analista` adicionado ao catálogo oficial com permissões financeiras coerentes e sem alçada de aprovação.
- Configuração do servidor passa a falhar de forma fechada quando o arquivo existe mas é inválido ou quando produção tenta expor wildcard sem TLS.
- Configuração de nó rejeita URL inválida, credenciais embutidas e HTTP público; HTTP sem TLS fica restrito a localhost/rede privada explicitamente permitida.

## Segurança e isolamento de dados

- Armazenamento corporativo exige autorização de administrador no backend, não apenas na interface.
- Listagem, download, exclusão e upload de arquivos/backups respeitam empresa e filial da sessão.
- Erros de autorização administrativa retornam 403; ausência/revogação de sessão retorna 401.
- Upload corporativo usa arquivo temporário, hash por streaming, transação e `os.replace`, removendo resíduos em caso de falha.
- Cliente envia arquivos e backups em blocos de 1 MiB, sem carregar arquivos grandes inteiros na RAM.
- Correio remoto valida o limite efetivo do JSON/Base64 antes do envio e orienta usar armazenamento corporativo quando o anexo excede o transporte seguro.
- Anexos do correio são revertidos quando a transação falha e nomes duplicados não colidem.
- Segredo do adapter legado de nós usa DPAPI no Windows e migra o segredo plaintext antigo quando possível.

## Interface

- Campo reutilizável de pesquisa com placeholder visual real, limpeza no foco, Escape e debounce.
- Estoque, Compras e Tecnologia deixam de tratar o texto do placeholder como consulta real.
- Estados vazios cobrem a grade por completo, eliminando as linhas verticais de uma "planilha vazia" atrás da mensagem.
- Tabela operacional de Tecnologia ganhou rolagem horizontal.
- RH usa colunas explícitas e estáveis em vez de inferir colunas do primeiro registro retornado pelo backend; também ganhou rolagem horizontal e estado vazio consistente.
- Manifesto de screenshots deixa de vazar caminhos absolutos da estação de desenvolvimento.
- Gerador visual remove capturas geradas obsoletas antes de criar o novo conjunto.

## Arquitetura e compatibilidade

A arquitetura canônica está documentada em `docs/ARQUITETURA_CANONICA_V9_2.md`. `servidor_corporativo`, `enterprise.correio` e a arquitetura atual de agentes TI são as implementações oficiais. Componentes antigos permanecem apenas como adapters de compatibilidade para não destruir dados/instalações existentes.

## Qualidade e CI

- `pytest.ini` impede coleta em build/dist/release/storage/artifacts.
- Novos testes de regressão cobrem migrations, banco limpo, produção/TLS, configuração fail-closed, escopo empresa/filial, autorização de arquivos, empacotamento e caminhos do manifesto visual.
- Testes de servidor passaram a encerrar `shutdown()` antes de `server_close()`.
- CI divide a suíte em três processos independentes para eliminar vazamento de estado global/sockets entre grupos.
- CI gráfico usa Xvfb e valida screenshots essenciais em 1366×768 e 1600×900.
- Resultado local da revisão: 180 testes aprovados, 14 testes gráficos ignorados por ausência de display e 30 subtestes aprovados; zero falhas nos três grupos.

## Distribuição

`scripts/empacotar_fonte_limpa.py` gera um ZIP por allowlist. O pacote exclui `.git`, `storage`, bancos, logs, caches, `build`, `dist`, `release`, artefatos visuais e arquivos de credenciais. A única planilha binária permitida é a fixture fictícia `dados_exemplo/Vendas - Dez.xlsx`, necessária aos testes.

## Limites deliberados desta revisão

Esta versão corrige os defeitos reproduzíveis encontrados na auditoria, mas não transforma decisões de arquitetura de longo prazo em mudanças destrutivas. A migração de SQLite para PostgreSQL, a decomposição dos módulos Python muito grandes e uma reformulação visual completa de todos os departamentos são evoluções de produto e devem ocorrer em versões separadas, com migração e testes próprios.
