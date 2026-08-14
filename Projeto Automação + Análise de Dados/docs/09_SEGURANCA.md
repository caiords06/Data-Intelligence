# Segurança

- Autenticação e sessões são centralizadas no Servidor Corporativo; tokens são persistidos somente como SHA-256 e podem ser encerrados remotamente.
- MFA TOTP é confirmado antes de ser ativado, impede replay na mesma janela e oferece códigos de recuperação de uso único protegidos com scrypt.
- Política de força de senha é aplicada em criação/alteração/redefinição, não durante login.
- Permissões são avaliadas por módulo, ação e contexto empresa/filial.
- Central/Cliente falham fechados se tentarem abrir banco diretamente.
- Segredos de integrações não devem ser colocados em JSON de configuração; use referências `cofre://`, `keyring://` ou `env://`.
- Acesso remoto de TI exige provedor permitido, justificativa e consentimento conforme a regra do domínio.
- API pública v1 usa bearer e retorna `X-Request-ID` para rastreabilidade.
- Em produção, qualquer bind fora de loopback exige TLS. PostgreSQL remoto exige `sslmode=require`, `verify-ca` ou `verify-full`.
- Leituras de CPF, remuneração, dados bancários, dependentes e documentos geram trilha específica de privacidade. Retenção executa em modo de simulação por padrão.
- Webhooks usam HTTPS, bloqueio de SSRF, segredo cifrado e assinatura HMAC SHA-256 com timestamp.
