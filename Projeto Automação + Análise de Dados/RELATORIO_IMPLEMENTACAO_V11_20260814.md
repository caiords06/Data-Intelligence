# Relatório de implementação — V11.0.0

Data de consolidação: 14/08/2026

## Escopo entregue

1. Migration 027 para SQLite e schema complementar PostgreSQL com o CORE empresarial, Funcionário 360°, metadados, registros operacionais e BPM.
2. Provisionamento idempotente de 108 tipos de registro e 12 fluxos transversais.
3. Serviços de pessoas, organização, segurança contextual, colaboração, metadados, documentos, busca, eventos, registros, Funcionário 360°, transferências e credenciais.
4. Fachadas em `services/` para que Desktop, API, RPC e integrações usem os mesmos casos de uso.
5. API V11 com busca, inbox, calendário, dashboards, pessoas, operações, transições, Funcionário 360° e transferências; documentação OpenAPI ampliada.
6. Janela Desktop do Funcionário 360° com troca de visão e avatar gerenciado.
7. RPC Server First ampliado para os serviços V11 e canal dedicado para operações com arquivos.
8. Eventos corporativos publicados pelo ciclo do worker para webhooks assinados.

## Segurança incorporada

- dados sensíveis de pessoas e campos personalizados cifrados com AES-GCM;
- documento de identificação indexado por hash e apresentado de forma mascarada;
- imagens e documentos cifrados fora do banco, com hash, versão e miniatura;
- validação de formato, tamanho e resolução; extensões executáveis bloqueadas;
- separação das visões do Funcionário 360° no backend;
- auditoria de alterações e leituras sensíveis;
- referências de credenciais apontam para cofre, keyring ou variável, sem armazenar o segredo;
- concorrência otimista nos registros, dashboards e unidades.

## Validação e limites de homologação

Na consolidação desta entrega, 383 testes `unittest` foram executados com sucesso — incluindo os seis testes específicos da V11 — e 15 cenários dependentes do ambiente foram ignorados. Também passaram a compilação integral e as auditorias de arquitetura, autoridade Server First e exceções silenciosas. O pacote-fonte é validado depois de extraído e inclui hashes individuais no `SOURCE_MANIFEST.json`.

A homologação real de PostgreSQL, TLS, instalador Windows, carga, recuperação de desastre, provedores de assinatura/OCR e integrações externas depende da infraestrutura e das credenciais da empresa destinatária. Esses itens não devem ser declarados homologados até a execução no ambiente final.

Funcionalidades regulatórias profundas — por exemplo cálculo fiscal, folha legal completa, remessa bancária e assinatura qualificada — exigem parametrização por país, regime, banco e provedor. A V11 fornece o CORE, os fluxos e os pontos de extensão, sem assumir regras jurídicas universais inexistentes.
