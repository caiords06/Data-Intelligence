> **DOCUMENTO HISTÓRICO.** Esta documentação descreve arquitetura anterior à linha final Server First. Para novas instalações, use `docs/README.md`.

# Distribuição Windows · Data Intelligence V10.1.1

O build produz quatro papéis separados:

```text
DataIntelligence-Deployment
├── Servidor
├── Central
├── Cliente
└── Agente-TI
```

## 1. Servidor

Instale primeiro o `Servidor`. Ele é a autoridade de autenticação, módulos, correio, arquivos, backups e telemetria TI. PostgreSQL é o backend recomendado para uso multiusuário; SQLite permanece para compatibilidade/standalone.

```powershell
powershell -ExecutionPolicy Bypass -File .\Instalar-Servidor-Corporativo.ps1
```

Porta padrão: `8770`.

## 2. Central administrativa

```powershell
.\Configurar-Estacao-Central.ps1 -ServerUrl "http://IP-DO-SERVIDOR:8770" -AllowPrivateHttp
```

Depois abra `DataIntelligencePlatform.exe` e faça login com uma conta criada no servidor.

## 3. Cliente convencional

```powershell
.\Configurar-Estacao-Cliente.ps1 -ServerUrl "http://IP-DO-SERVIDOR:8770" -AllowPrivateHttp
```

O Cliente não oferece bootstrap administrativo local.

## 4. Agente TI

Crie a credencial no módulo Tecnologia e instale o Agente usando a mesma URL `:8770` do servidor.

Consulte `README_DISPOSITIVO_TI.md`.

## Build

Na raiz do código-fonte, em Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

Resultado:

```text
release\DataIntelligence-Deployment-Windows.zip
```

O verificador do pacote impede distribuição de `app.db`, `.git`, `__pycache__`, `.pyc`, caches e artefatos de testes.
