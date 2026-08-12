# Segurança e recuperação na V9

## Controles ativos

- senhas com `scrypt`, salt individual e comparação segura;
- bloqueio progressivo de autenticação;
- MFA TOTP opcional, com segredo fora do SQLite;
- revogação de sessão ao alterar senha, perfil, status ou MFA;
- RBAC por módulo, ação, empresa e filial;
- auditoria de criações, alterações, decisões e restaurações;
- exclusão lógica para registros empresariais;
- HMAC, nonce e janela temporal nos agentes;
- foreign keys ativas e valores monetários canônicos em centavos.

## Backup completo

O administrador pode criar e restaurar backups em **Configurações**. Cada
pacote ZIP contém:

- snapshot transacional do banco;
- documentos, anexos, relatórios e segredos gerenciados;
- manifesto com tamanho e SHA-256 de cada arquivo;
- verificação `PRAGMA quick_check` do banco.

Antes de restaurar, a aplicação cria automaticamente um backup de segurança.
Depois da restauração, reinicie o aplicativo para descartar o contexto antigo.

## Recomendações operacionais

Mantenha pelo menos três cópias, em dois meios diferentes e uma fora do
computador principal. Criptografe o armazenamento, limite o acesso aos
administradores e valide a restauração em ambiente isolado.
