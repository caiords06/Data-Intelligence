# Migração segura de rede e TLS — V11.1.0

## Mudança incompatível intencional

O Servidor Corporativo não inicia com `host` externo e `tls=false` em produção ou LAN. O modo recomendado é:

1. serviço Data Intelligence ligado apenas a `127.0.0.1:8770`;
2. proxy reverso na mesma máquina;
3. certificado válido e HTTPS no proxy;
4. firewall liberando somente a porta HTTPS;
5. clientes configurados para a URL HTTPS corporativa;
6. PostgreSQL remoto com `sslmode=require`, `verify-ca` ou, preferencialmente, `verify-full`.

Não reabra a porta 8770 no firewall. O parâmetro histórico `-PermitirHttpLan` foi desativado e gera erro.

## Exceção de laboratório

HTTP fora de loopback só é aceito quando `ambiente=desenvolvimento` e `DATA_INTELLIGENCE_ALLOW_INSECURE_LAB=1`. Essa exceção é exclusiva de rede isolada, sem dados reais, e não deve ser usada para contornar certificado em homologação ou produção.

## Validação

- confirmar certificado, cadeia, nome DNS e renovação;
- testar redirecionamento HTTP → HTTPS no proxy;
- verificar que `/api/v1/health` funciona pela URL HTTPS;
- confirmar que a porta 8770 não responde de outra máquina;
- executar teste de login, MFA, upload, download, RPC e revogação de sessão;
- registrar evidência da configuração e data da revisão.

