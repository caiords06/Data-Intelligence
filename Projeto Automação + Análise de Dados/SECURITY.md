# Política de segurança

## Relato responsável

Não publique credenciais, dados pessoais, evidências de clientes ou detalhes exploráveis em issues públicas. Envie o relato ao responsável de segurança definido pela organização que opera a instalação, contendo versão, impacto, reprodução mínima e mitigação sugerida.

## Requisitos de produção

- PostgreSQL é a autoridade transacional; SQLite é exclusivo de migração/testes.
- Bind de produção fora de loopback exige TLS; PostgreSQL remoto exige SSL.
- O instalador publica o serviço em `127.0.0.1`; exposição corporativa deve ocorrer por proxy reverso HTTPS com certificado válido. HTTP em LAN falha fechado.
- Defina chaves mestras de MFA, backup, webhook e atualização em cofre de segredos. No Windows isolado, o fallback usa DPAPI da conta da máquina.
- MFA deve ser confirmado antes da ativação; códigos de recuperação são mostrados uma vez e armazenados com scrypt.
- Backups PostgreSQL usam o formato `.dibak` cifrado e devem participar de exercícios reais de restauração.
- Restrinja `/api/v1/metrics`, trilhas LGPD, backups, webhooks e retenção a administradores autorizados.
- Configure controlador, operador, encarregado, bases legais, retenção e responsáveis na Central de Conformidade antes de tratar dados reais.
- O acesso remoto operacional não está habilitado: a V11.1.0 fornece política, consentimento, token efêmero e evidência, mas não transporte de tela/comandos.
- Incidentes devem ser avaliados pelo encarregado. O prazo sugerido pelo sistema conta três dias úteis sem calendário local de feriados e precisa de confirmação operacional.

## Controles automatizados

O CI executa compilação, testes, lint, tipagem incremental, cobertura do hardening, SAST, auditoria de dependências, SBOM, integração PostgreSQL e build Windows. Uma aprovação de implantação ainda deve considerar pentest, carga, restauração e homologação no ambiente-alvo.
