# Instalação do Servidor Corporativo

## Pré-requisitos

Windows suportado, PowerShell como Administrador, PostgreSQL acessível, banco/usuário previamente criados e pacote oficial contendo `DataIntelligenceServer.exe` ao lado de `Instalar-Servidor-Corporativo.ps1`.

## Instalação

Execute a partir da pasta `Servidor` do deployment:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\Instalar-Servidor-Corporativo.ps1 `
  -Porta 8770 `
  -PostgresHost "127.0.0.1" `
  -PostgresPorta 5432 `
  -PostgresBanco "dataintelligence" `
  -PostgresUsuario "dataintelligence" `
  -PostgresSslMode "prefer"
```

O script solicita a senha PostgreSQL como `SecureString`, usa arquivo temporário UTF-8 sem BOM, valida/configura o banco, inicializa o administrador, registra a tarefa do servidor, espera `/health/ready` e cria firewall somente em perfil **Private**, `LocalSubnet`, TCP/8770.

`ExecutionPolicy Bypass` aqui permite executar o script local de deployment ainda que ele não esteja assinado por uma CA. Use apenas o script obtido do pacote oficial; isso não deve ser usado como política genérica de segurança da máquina.

## Verificação

```powershell
PowerShell -ExecutionPolicy Bypass -File .\Testar-Servidor-Corporativo.ps1 -ServerUrl "http://127.0.0.1:8770"
Invoke-RestMethod http://127.0.0.1:8770/api/v1/health/ready
```

Dados persistentes do servidor ficam em `%PROGRAMDATA%\DataIntelligence\Server`.
