# Documentação operacional — Data Intelligence Enterprise Platform

A documentação desta pasta é a referência atual para instalação, operação, administração e integrações. Documentos de versões V9/V10.1 mantidos na raiz são históricos e não devem substituir este conjunto em novas implantações.

## Ordem recomendada de leitura

1. `01_VISAO_GERAL_DA_PLATAFORMA.md`
2. `02_ARQUITETURA.md`
3. `03_INSTALACAO_SERVIDOR.md`
4. `04_INSTALACAO_CENTRAL.md` / `05_INSTALACAO_CLIENTE.md`
5. `06_INSTALACAO_AGENTE_TI.md`
6. `07_POSTGRESQL.md`
7. `08_BACKUP_E_RESTORE.md`
8. `09_SEGURANCA.md`
9. `10_TROUBLESHOOTING_POWERSHELL.md`
10. `11_MANUAL_USUARIO.md` / `12_MANUAL_ADMINISTRADOR.md`
11. `13_API_E_INTEGRACOES.md`
12. `14_ATUALIZACAO_E_ROLLBACK.md`
13. `15_RUNBOOK_PRODUCAO.md`

## Princípio de arquitetura

O Servidor Corporativo é a autoridade transacional. Central e Cliente não possuem banco empresarial local. PostgreSQL é a fonte oficial de dados; `node.json`, logs, temporários e exports não são bancos corporativos.
