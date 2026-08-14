# Matriz de implementação dos requisitos de 2026

Esta matriz consolida os dois pacotes de requisitos fornecidos para a V11.1.0. “Implementado” significa que há código e teste automatizado no pacote; não equivale a homologação legal ou operacional no ambiente do cliente.

| Área | Estado V11.1.0 | Entrega / limite |
|---|---|---|
| LGPD — inventário, titulares, incidentes, RIPD, terceiros e legal hold | Implementado | Central funcional, versionamento e auditoria. Parametrização jurídica continua obrigatória. |
| Mascaramento, criptografia e auditoria de leitura | Implementado | CPF/conta/e-mail, dados e mídias cifrados, leituras sensíveis auditadas. Revisar chaves e perfis no ambiente real. |
| TLS e PostgreSQL remoto | Implementado | Configuração insegura falha fechado; proxy HTTPS é o padrão do instalador. Certificado/infra são externos ao pacote-fonte. |
| RH/Funcionário 360° | Implementado | Visões meu perfil, gestor, RH, TI e auditor; avatar à direita; ações de edição e registros associados. |
| Ponto eletrônico | Parcial e deliberadamente limitado | Registro interno é integração/consulta; não é declarado REP-P e não substitui solução homologada. |
| Documentos e assinaturas | Implementado como base | mídia gerenciada, versões, hash, OCR e evidência; integração ICP-Brasil/provedor precisa ser contratada e homologada. |
| Financeiro central e segregação | Implementado na base existente | aprovações, origem, auditoria, estorno/estado. Fiscal, bancário e contábil real exigem integrações e homologação. |
| Acesso remoto | Base de governança implementada | política, consentimento, token único, permissões e trilha. Captura de tela, canal e comandos permanecem desabilitados. |
| Analytics e decisões sobre pessoas | Implementado como governança | acesso gerencial existente e catálogo de regra/modelo; revisão humana obrigatória quando há impacto. Não há motor de IA decisória. |
| Identidade visual | Implementado | logos fornecidas aplicadas no login/sidebar; tokens Manrope/Inter. Fontes dependem de instalação/licenciamento no sistema operacional porque os binários não foram fornecidos. |
| Acessibilidade desktop | Parcial | contraste, tema, rolagem, texto além de cor e foco de teclado foram reforçados. Certificação com tecnologia assistiva e matriz completa de DPI ainda é necessária. |
| Licenças e propriedade intelectual | Parcial | provenance dos ativos e inventário de dependências incluídos. Titularidade da marca e contratos/EULA dependem do proprietário. |
| SLA, suporte e contratos | Não automatizado | requer contrato comercial, política de suporte, métricas e responsáveis por cliente. |
| Marco legal geral de IA | Monitoramento | não tratado como lei vigente; LGPD e regras setoriais são aplicadas ao desenho atual. |
| Crianças/adolescentes | Condicional | deve ser desabilitado ou submetido a fluxo específico quando o cliente tratar esse público. Não homologado nesta versão. |

## Referências oficiais complementares

- [MTE — Registro Eletrônico de Ponto](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/fiscalizacao-do-trabalho/rep)
- [Portaria MTP nº 671/2021 compilada](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/legislacao/portarias-1/portarias-vigentes-3/PDFPortarian671de8denovembrode2021compilada13.05.2025.pdf)
- [Lei nº 12.846/2013 — Lei Anticorrupção](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12846.htm)
- [Decreto nº 11.129/2022 — programa de integridade](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/decreto/d11129.htm)
- [Lei nº 13.146/2015 — Lei Brasileira de Inclusão](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm)
- [Governo Digital — eMAG](https://www.gov.br/governodigital/pt-br/acessibilidade-e-usuario/acessibilidade-digital/modelo-de-acessibilidade)
- [Lei nº 9.609/1998 — Lei de Software](https://www.planalto.gov.br/ccivil_03/leis/l9609.htm)

## Portões obrigatórios para produção ampla

- parecer jurídico e trabalhista por escopo de uso;
- homologação contábil/fiscal e das integrações externas;
- pentest, SAST/DAST, teste de carga/concorrência e revisão de privilégios;
- PostgreSQL real, backup cifrado e restauração medida;
- instalador em Windows limpo, atualização e rollback;
- teste de acessibilidade com teclado, DPI, contraste e tecnologia assistiva;
- piloto controlado, treinamento, runbooks, SLA e aceite formal.

