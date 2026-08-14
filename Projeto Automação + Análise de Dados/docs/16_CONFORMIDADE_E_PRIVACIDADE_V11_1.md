# Conformidade e privacidade — V11.1.0

Data de verificação normativa: 14/08/2026.

## Limite do produto

A plataforma fornece controles, evidências e pontos de configuração. Ela não substitui o controlador, o encarregado, assessoria jurídica, contabilidade, departamento pessoal, medicina do trabalho ou auditoria. A conformidade depende da finalidade real, setor, localidade, contratos, dados usados, configuração e operação de cada organização.

## Controles entregues

| Tema | Controle funcional | Evidência |
|---|---|---|
| Inventário de tratamento | código, controlador, operador, encarregado, finalidade, base legal, titulares, dados, compartilhamento, transferência, retenção e segurança | `compliance_tratamentos`, histórico e evento corporativo |
| Direitos do titular | protocolo, prova de identidade, tipo, escopo, responsável, prazo, resposta e fundamento de recusa | `compliance_solicitacoes_titulares` |
| Incidentes | detecção, confirmação, dados/titulares, risco, contenção, decisão justificada, comunicação e encerramento | `compliance_incidentes` |
| RIPD | necessidade/proporcionalidade, riscos, salvaguardas, risco residual, aprovação e versões imutáveis | `compliance_ripd` |
| Terceiros | papel, dados, finalidade, DPA, transferência, salvaguarda, segurança e revisão | `compliance_terceiros` |
| Retenção | política por classe, simulação, anonimização auditada e bloqueio legal | `politicas_retencao`, `compliance_bloqueios_retencao` |
| Leitura sensível | finalidade, campos, usuário, recurso, momento e request ID | `auditoria_leituras_sensiveis` |
| Analytics/IA | catálogo de regra/modelo, dados de entrada, lógica, versão, impacto e revisão humana | `analytics_catalogo_decisoes` |
| Documentos | classificação, armazenamento cifrado, hash, versão, OCR e evidência de assinatura | `core_documentos_v11`, `core_midias`, `core_documento_assinaturas` |

## Regras operacionais importantes

- O prazo de solicitações de titulares é inicialmente sugerido em 15 dias corridos. A organização deve validar o prazo e o procedimento aplicável ao pedido concreto.
- Para incidentes comunicáveis, o sistema sugere três dias úteis após confirmação. O cálculo ignora feriados nacionais, estaduais e municipais; o encarregado deve confirmar o vencimento e eventual norma setorial.
- A comunicação à ANPD ou aos titulares não é automática. A decisão exige justificativa e o envio deve ser realizado por responsável autorizado nos canais aplicáveis.
- Legal hold prevalece sobre expurgo enquanto ativo e dentro da validade registrada.
- Um RIPD aprovado exige riscos e salvaguardas. Uma revisão cria nova versão e marca a anterior como substituída.
- Regra/modelo que impacte pessoas exige revisão humana. O catálogo não executa modelos e não constitui, por si, validação de viés, qualidade ou legalidade.
- Assinatura qualificada exige provedor/certificado ICP-Brasil homologado; o provedor interno é rejeitado para essa classificação.

## Referências oficiais verificadas

- [Lei nº 13.709/2018 — LGPD, texto compilado](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/L13709compilado.htm)
- [ANPD — Regulamentações vigentes, incluindo Resolução CD/ANPD nº 15/2024](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd)
- [ANPD — Comunicação de incidente de segurança](https://www.gov.br/anpd/pt-br/assuntos/comunicacao-de-incidentes-de-seguranca-cis)
- [Lei nº 12.965/2014 — Marco Civil da Internet](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm)
- [Lei nº 14.063/2020 — assinaturas eletrônicas](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/l14063.htm)
- [Lei nº 12.682/2012 — documentos digitalizados](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12682.htm)
- [Decreto nº 10.278/2020 — digitalização e preservação](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/decreto/D10278.htm)

## Pendências de implantação

Antes de dados reais: designar encarregado e responsáveis; aprovar RoPA e tabela de retenção; classificar dados; validar contratos/DPA; configurar cofre de segredos; executar RIPD onde aplicável; homologar backup/restauração, TLS, PostgreSQL, controles de acesso e resposta a incidentes; realizar treinamento e teste de mesa.

