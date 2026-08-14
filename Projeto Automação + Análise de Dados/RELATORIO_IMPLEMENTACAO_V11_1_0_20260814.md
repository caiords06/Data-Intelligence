# Relatório de implementação — Data Intelligence V11.1.0

Data: 14/08/2026  
Escopo: logs de homologação, pacote legal/centralização e melhorias por módulo fornecidos pelo titular.

## Diagnóstico dos logs

| Ocorrência | Quantidade observada | Causa | Correção |
|---|---:|---|---|
| `session_preferences_unavailable` | 101 | watchdog consultava preferências após a sessão remota deixar de ser válida | detecção de sessão inválida, encerramento local, retorno único ao login e limitação de avisos |
| falha em operações de Estoque | 6 | alias `do`, palavra reservada no PostgreSQL | aliases alterados para `dep_origem` e `dep_destino` |
| falha em relatórios de RH | 5 | `pandas.read_sql_query` esperava `.cursor()` ausente no adaptador corporativo | execução pela interface comum do repositório e criação explícita do DataFrame |
| configuração de rede insegura | 1 configuração | bind `0.0.0.0`, `tls=false`, ambiente LAN e PostgreSQL remoto com `sslmode=prefer` | falha fechada; servidor local em loopback e publicação por proxy HTTPS; SSL obrigatório no PostgreSQL remoto |

## Entregas funcionais

- Central de Conformidade e Privacidade com RoPA, titulares, incidentes, RIPD, terceiros, legal hold e decisões analíticas;
- migração SQLite 028 e schema PostgreSQL correspondente;
- autorização remota governada por política, chamado, consentimento, permissões, token efêmero e trilha hash-encadeada;
- classificação de assinaturas e evidência hash; bloqueio de falsa assinatura qualificada interna;
- avatar e menu de ações no Funcionário 360°, leitura sensível por campo e armazenamento de mídia governado;
- logos fornecidas aplicadas ao login e à navegação, Manrope para marca/títulos e Inter para interface;
- foco visível, scrollbar contextual e cores de navegação reforçadas;
- menu de RH consolidado e ponto identificado como integração/consulta, não REP-P;
- Analytics mantido para perfis gerenciais/diretoria e governança de impacto humano.

## Evidências automatizadas

- regressão final `unittest`: **396 testes, 380 aprovados, 16 ignorados e zero falhas**; as saídas de exceção controlada pertencem a cenários negativos que validam logging e recuperação.
- testes direcionados: CORE V11, RH 2.0, Estoque 2.0, instalador, PostgreSQL-only, hardening e V11.1 aprovados.
- o teste PostgreSQL real continua condicionado a `RUN_POSTGRES_INTEGRATION=1`, PostgreSQL 17 e ambiente Python 3.14 do CI; não foi simulado como se fosse execução real.

Os totais finais e os hashes do pacote são registrados no `SOURCE_MANIFEST.json` do ZIP canônico.

## Limites deliberados

- nenhuma alegação de certificação legal, fiscal, trabalhista, REP-P, ICP-Brasil ou acessibilidade foi feita;
- o transporte de tela/comandos do Data Intelligence Remote não foi implementado nem habilitado;
- certificado TLS, proxy, PostgreSQL real, backup/restauração e instalador Windows exigem homologação no ambiente-alvo;
- fontes Manrope/Inter foram configuradas, mas os binários de fonte não foram fornecidos e não foram redistribuídos;
- prazos sugeridos não incorporam feriados locais;
- integrações bancárias, fiscais, governamentais e provedores de assinatura dependem de contrato e homologação próprios.

Consulte `docs/18_MATRIZ_IMPLEMENTACAO_REQUISITOS_2026.md` para o estado completo por requisito.
