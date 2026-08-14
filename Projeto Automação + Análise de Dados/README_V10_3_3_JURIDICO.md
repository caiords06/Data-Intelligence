# V10.3.3 — Jurídico especializado

O Jurídico passa a usar o **Legal Operations**, orientado por agenda, exposição e risco.

Entregas: contratos especializados, processos, prazos, audiências, riscos, provisões, indicadores, alertas e exportação para Analytics; RPC Server First e migration `023_v10_3_3_juridico`.

`contratos_juridicos` permanece como origem legada. A migration copia os dados para `juridico_contratos` sem apagar a tabela anterior e controla idempotência por `legacy_contrato_id`.
