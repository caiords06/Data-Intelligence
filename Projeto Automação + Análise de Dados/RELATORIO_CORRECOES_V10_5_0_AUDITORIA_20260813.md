# Correções pós-auditoria — V10.5.0 — 13/08/2026

Este pacote incorpora as correções encontradas na auditoria profunda da V10.5.0, sem alterar o número público da versão.

## 1. Paginação real da API

CRM, Comercial, Marketing, Administrativo, Jurídico, Analytics e Orquestrações passaram a paginar no SQL com `LIMIT/OFFSET` e a calcular o total com `COUNT(*)`. A API não fatia mais listas previamente truncadas. O teste de regressão usa 2.105 leads e valida páginas acima do antigo limite de 2.000 registros.

## 2. Instalação e rede em modo seguro por padrão

O Servidor Corporativo passa a usar `127.0.0.1` e ambiente `producao` por padrão. O Setup sugere HTTPS para estações remotas e a opção de HTTP privado inicia desmarcada. Exposição em `0.0.0.0`, ambiente `lan` e regra de firewall `LocalSubnet` só são ativados após aceite explícito de HTTP sem TLS. O script PowerShell do servidor segue a mesma regra pelo switch `-PermitirHttpLan`.

## 3. Tela principal não bloqueia na RPC inicial

A Central renderiza primeiro o shell visual e inicia `resumo_cockpit()`/`obter_contexto()` em worker daemon. O resultado volta à thread Tk por `after()`. Erros remotos deixam a interface utilizável e oferecem nova tentativa, em vez de produzir uma janela branca durante timeout de rede.

## 4. Semântica HTTP de autenticação

Sessão Bearer ausente, expirada ou revogada retorna `401 Unauthorized`. Usuário autenticado sem autorização retorna `403 Forbidden`. Os endpoints REST V10.5 mantêm envelope estruturado com `ok`, `error.code`, `error.message` e `request_id`.

## 5. Erros 500 consistentes

Falhas inesperadas nos endpoints REST públicos retornam `internal_error` no mesmo envelope da API. Rotas legadas mantêm compatibilidade com o formato anterior.

## 6. Cliente compatível com os dois envelopes

O cliente desktop interpreta tanto `{"erro":"..."}` quanto `{"error":{"message":"..."}}`. Ao receber 401 ele elimina token e bootstrap em memória para impedir reutilização de sessão inválida. Timeout e indisponibilidade continuam convertidos em erro operacional exibível pela UI.

## 7. Marcador correto no build

`scripts/build_distribuicao_windows.ps1` copia `VERSAO_V10_5_0.txt`, eliminando o identificador V10.1.1 que ainda era levado para o deployment legado.

## 8. CORS controlado

O Servidor Corporativo suporta preflight `OPTIONS` e origens explícitas configuradas por `cors_origins`/`server_cors_origins`. Produção rejeita `*`; ambiente de desenvolvimento pode optar por wildcard. Respostas incluem `Vary: Origin` e só liberam `Access-Control-Allow-Origin` para origem autorizada.

## 9. Cobertura V10.5 ampliada

Foram adicionadas regressões para volume/paginação, Bearer ausente, Bearer expirado, distinção 401/403, CORS permitido/bloqueado, envelope 500, parser do cliente e timeout de rede.

## 10. PostgreSQL real ampliado

O job PostgreSQL 17 agora possui cenário adicional que exercita autenticação/contexto e fluxos atuais de CRM, Comercial, Marketing, Administrativo, Jurídico, Analytics e Financeiro, incluindo as novas consultas de paginação/contagem. O teste permanece condicionado a `RUN_POSTGRES_INTEGRATION=1`.

## 11. Isolamento da suíte

O runner oficial mantém um processo por arquivo, força `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, aplica timeout por arquivo e encerra árvores de processos. A saída de cada pytest passou a usar arquivo temporário em vez de `PIPE`, evitando bloqueio de `communicate()` quando processos netos herdam stdout. O `conftest.py` também limpa sessão, token/bootstrap, temporários e pool PostgreSQL entre testes.
