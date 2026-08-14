# Manual do administrador

O administrador gerencia usuários, empresa/filiais, permissões, integrações, servidor, backups e observabilidade.

## Rotina

- confirme `/health/ready`;
- monitore tarefas/jobs e agentes;
- revise usuários inativos e permissões;
- valide backup recente;
- consulte auditoria quando houver divergência;
- mantenha servidor e estações na mesma versão compatível.

## Integrações

Cadastre apenas referências a segredos. Um provedor no catálogo não significa que esteja ativo: somente integrações configuradas/habilitadas são reportadas como disponíveis.

## Mudanças

Antes de update, gere backup, preserve o pacote anterior, execute validações e planeje rollback. Nunca copie um banco SQLite local para substituir o PostgreSQL produtivo.
