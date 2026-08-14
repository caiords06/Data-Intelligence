# Backup e restore

Backups produtivos pertencem ao Servidor Corporativo. Não copie `app.db` de estações: ele não é banco produtivo.

O administrador pode criar backup pelos recursos do servidor. Antes de restaurar, valide disponibilidade das ferramentas PostgreSQL e faça uma cópia adicional do estado atual.

Em PostgreSQL, o formato padrão é `.dibak`, cifrado e autenticado com AES-256-GCM. Defina `DATA_INTELLIGENCE_BACKUP_MASTER_KEY` em um cofre de segredos para permitir recuperação em outra máquina. O fallback DPAPI do Windows protege a chave localmente, mas não substitui uma estratégia de disaster recovery.

A API de restauração exige administrador, cabeçalho `X-Confirm-Restore: RESTORE-<id>` e ainda cria uma automação em estado **Aguardando aprovação**. A restauração só começa após a aprovação humana do job.

Checklist de restore:

1. anunciar janela de manutenção;
2. impedir novas operações;
3. validar arquivo e SHA-256;
4. validar versão do PostgreSQL/ferramentas;
5. restaurar em banco de staging quando possível;
6. executar health/schema checks;
7. iniciar servidor e smoke de login/módulos;
8. liberar estações;
9. registrar auditoria da intervenção.

O exercício de restore deve ser feito periodicamente em ambiente isolado com PostgreSQL real; verificar o ZIP/dump não comprova, sozinho, que RTO e RPO serão atendidos.
