# Servidor Corporativo · V9.1

O `DataIntelligenceServer.exe` é a autoridade única das estações Central e Cliente.
Ele mantém autenticação, sessões, correio, arquivos, backups, operações transacionais dos módulos e heartbeats do Agente TI.

## Instalação no Windows

1. Extraia a pasta `Servidor` do pacote de distribuição.
2. Abra PowerShell **como Administrador** nessa pasta.
3. Execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\Instalar-Servidor-Corporativo.ps1
```

4. Crie o primeiro administrador quando solicitado.
5. Descubra o IPv4 do servidor com `ipconfig`.
6. Teste, por exemplo:

```powershell
.\Testar-Servidor-Corporativo.ps1 -ServerUrl "http://192.168.1.4:8770"
```

O health deve informar `autoridade_transacional: true` e `agentes_ti: true`.

## Firewall

O instalador não desliga o Windows Firewall. Ele cria uma regra de entrada TCP/8770 limitada ao perfil `Private` e `LocalSubnet`.

## Central

Na estação administrativa:

```powershell
.\Configurar-Estacao-Central.ps1 -ServerUrl "http://192.168.1.4:8770" -AllowPrivateHttp
```

Use `-AllowPrivateHttp` apenas em laboratório/LAN privada. Em produção configure HTTPS.

## Cliente

Na estação convencional:

```powershell
.\Configurar-Estacao-Cliente.ps1 -ServerUrl "http://192.168.1.4:8770" -AllowPrivateHttp
```

O Cliente não cria administrador inicial nem usuários locais.

## Agente TI

O Agente TI usa a **mesma URL do Servidor Corporativo**:

```text
http://192.168.1.4:8770
```

O endpoint de heartbeat é:

```text
POST /api/v1/ti/agentes/heartbeat
```

Não é necessário abrir a porta 8765 na Central quando ela está conectada ao servidor V9.1.

## Persistência

Dados do servidor no Windows:

```text
C:\ProgramData\DataIntelligence\Server
```

Central/Cliente possuem apenas cache local de identidade/navegação em:

```text
C:\ProgramData\DataIntelligence\Platform
```

O cache da estação não é fonte de verdade dos módulos.
