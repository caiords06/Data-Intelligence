# Instalação de estação Cliente

```powershell
PowerShell -ExecutionPolicy Bypass -File .\Configurar-Estacao-Cliente.ps1 `
  -ServerUrl "http://IP-DO-SERVIDOR:8770" `
  -AllowPrivateHttp
```

O cliente valida a prontidão do servidor antes de salvar `node.json`. Criação local de administrador/usuário fica desativada. O cliente não cria `app.db`, histórico local ou preferências corporativas locais.

Teste de conectividade antes de abrir a aplicação:

```powershell
Test-NetConnection IP-DO-SERVIDOR -Port 8770
Invoke-RestMethod http://IP-DO-SERVIDOR:8770/api/v1/health/ready
```
