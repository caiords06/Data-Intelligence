# Central de TI · Instalação Windows

Este diretório é destinado ao computador que atuará como **Central de Tecnologia**.

## Conteúdo

```text
Central\
├── DataIntelligencePlatform\
│   └── DataIntelligencePlatform.exe
├── Preparar-Central-TI.ps1
├── Testar-Central-TI.ps1
├── Remover-Regra-Servidor-TI.ps1
└── README_CENTRAL_TI.md
```

## Instalação

1. Extraia a pasta em um local fixo.
2. Abra PowerShell como Administrador.
3. Execute:

```powershell
.\Preparar-Central-TI.ps1
```

4. Abra:

```text
DataIntelligencePlatform\DataIntelligencePlatform.exe
```

A aplicação inicia a API do Agente TI automaticamente na porta padrão `8765`.

## Teste local

Com a Central aberta:

```powershell
.\Testar-Central-TI.ps1
```

Saída esperada: TCP OK e JSON com `"ok": true`.

Para testar usando o próprio IP da LAN:

```powershell
.\Testar-Central-TI.ps1 -HostCentral "192.168.0.10"
```

## Firewall

A preparação cria a regra:

```text
Data Intelligence - TI Agent API
```

Configuração:

```text
Direção:       entrada
Protocolo:     TCP
Porta:         8765
Perfil:        Private
Origem:        LocalSubnet
```

O Windows Firewall permanece ativo.

Se quiser remover somente essa regra:

```powershell
.\Remover-Regra-Servidor-TI.ps1
```

## Onde ficam o banco e os logs

```text
C:\ProgramData\DataIntelligence\Platform\
├── app.db
├── ti_server.json
└── ti-server.log
```

Esse diretório deve entrar na rotina de backup da Central.

## Cadastrar um computador remoto

Na aplicação:

```text
Tecnologia
→ Ativos gerenciados
→ cadastrar/selecionar ativo
→ GERAR / ROTACIONAR AGENTE
```

Anote/transfira:

- URL da Central;
- patrimônio;
- Agent ID;
- token temporário.

O token é exibido para o provisionamento e não deve ficar guardado em TXT depois da instalação.

## Rede do laboratório

O computador remoto precisa alcançar o IP da Central na porta 8765. No PC remoto:

```powershell
Test-NetConnection 192.168.0.10 -Port 8765
```

Se `TcpTestSucceeded` for `False`, verifique se:

- a Central está aberta;
- o perfil da LAN no Windows é Private;
- o endereço IP está correto;
- roteador/AP não está usando isolamento de clientes;
- firewall de terceiros não está bloqueando a porta.

## HTTP no laboratório

A configuração padrão da Central usa HTTP. Isso é adequado apenas para laboratório controlado na LAN, com o agente exigindo a autorização explícita `AllowPrivateHttp`.

Para ambiente real, configure HTTPS e não exponha a porta diretamente à Internet.

## Observação sobre o aplicativo em outros PCs

Nesta versão, o **servidor distribuído implementado é o servidor do Agente TI**. Ele permite inventário/telemetria dos endpoints. Ele não transforma o SQLite da aplicação em um banco multiusuário remoto. Portanto, para monitoramento de computadores, instale **Agente TI** nos endpoints e mantenha uma Central.
