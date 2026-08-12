# V9.3 — Histórico de migrations legadas removidas

A V9.3 remove do diretório executável `enterprise/migrations/` duas migrations de prévia interna que possuíam números já usados pelo registry canônico.

| Arquivo legado | SHA-256 original | Substituição canônica |
|---|---|---|
| `013_plataforma_distribuida.py` | `258d7df32d89ed31c2e39ca41682b82d713d132eec5901ad81057ced4c0c2e2f` | funcionalidades compatíveis consolidadas em `014_colaboracao_email_sessoes.py` e `019_compatibilidade_v9_legada.py` |
| `014_consistencia_monetaria.py` | `6c0d7f58f55ddc87c4d516f553411d98641373c11088394bd461a2b819e9a3ea` | lógica corrigida e idempotente em `017_consistencia_monetaria_aprovacoes.py` |

Esses arquivos não devem ser recolocados na pasta de migrations. O registry V9.3 é validado por teste e pelo empacotador de release; qualquer arquivo numerado não registrado ou número duplicado cancela a entrega.

A remoção não apaga dados nem desfaz instalações antigas. `019_compatibilidade_v9_legada.py` existe justamente para reconhecer e normalizar estruturas criadas por previews anteriores.
