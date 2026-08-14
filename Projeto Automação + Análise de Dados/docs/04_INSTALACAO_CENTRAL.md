# Instalação da Central

Instale primeiro PostgreSQL + Servidor Corporativo. A Central é uma estação desktop privilegiada, mas não é autoridade de banco.

```powershell
PowerShell -ExecutionPolicy Bypass -File .\Configurar-Estacao-Central.ps1 `
  -ServerUrl "http://IP-DO-SERVIDOR:8770" `
  -AllowPrivateHttp
```

`-AllowPrivateHttp` deve ser usado somente em LAN privada controlada enquanto TLS não estiver configurado. O script testa `/api/v1/health/ready` antes de gravar `%PROGRAMDATA%\DataIntelligence\Platform\node.json` em UTF-8 sem BOM.

Após a configuração, abra `DataIntelligencePlatform.exe`, autentique com usuário criado no Servidor Corporativo e valide módulos, contexto empresa/filial, Analytics e Administração.
