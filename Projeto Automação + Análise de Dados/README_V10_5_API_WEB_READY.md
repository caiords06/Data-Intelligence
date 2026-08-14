# V10.5.0 — API e arquitetura Web-Ready

A interface Tkinter passa pela camada `services/`, eliminando importações diretas de `enterprise.*` na UI. Isso reduz o acoplamento do desktop ao domínio e prepara a substituição/adicional de um cliente web sem duplicar regras empresariais.

O Servidor Corporativo mantém o RPC usado pelo desktop e oferece contratos REST explícitos em `/api/v1` para CRM, Comercial, Marketing, Jurídico, Administrativo, Analytics e Orquestrações. A paginação é executada no banco com `LIMIT/OFFSET` e `COUNT(*)`, portanto páginas posteriores continuam acessíveis mesmo quando a tabela ultrapassa milhares de registros.

A autenticação continua centralizada via Bearer token: token ausente/expirado retorna HTTP 401; sessão autenticada sem permissão retorna 403. Respostas REST usam envelope consistente com `ok`, `error` e `request_id`, inclusive em falhas internas.

## Web em outra origem

CORS é desabilitado por padrão (`cors_origins=()`). Para um frontend hospedado em outra origem, configure explicitamente `server_cors_origins` no bootstrap do servidor, por exemplo `["https://app.empresa.local"]`. O servidor responde ao preflight `OPTIONS`, envia `Vary: Origin` e libera a origem somente quando ela estiver na lista. O wildcard `*` é rejeitado em produção.

## Segurança de rede

O servidor nasce em `127.0.0.1`, ambiente `producao`. O Setup recomenda HTTPS para clientes remotos. HTTP em IP privado inicia desmarcado e exige aceite explícito; somente nesse modo o servidor abre `0.0.0.0` e cria regra de firewall restrita a perfil privado/`LocalSubnet`. Em produção, prefira TLS no próprio servidor ou loopback atrás de reverse proxy HTTPS.

## Compatibilidade desktop

O cliente reconhece o envelope REST novo e o formato legado de erro. Ao receber 401, token e bootstrap remoto são removidos da memória para forçar reautenticação. A Central visual é renderizada antes das consultas RPC iniciais, evitando janela branca durante lentidão de rede.

A pasta `enterprise/integrations/` fornece um registro de providers para evoluções futuras com Microsoft, Google, SMTP e HTTP/Webhooks, sem acoplar essas integrações à interface.

Detalhes das correções de auditoria: `RELATORIO_CORRECOES_V10_5_0_AUDITORIA_20260813.md`.
