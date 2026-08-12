# Implantação do servidor, central e agentes

## 1. Desenvolvimento local

```powershell
python -m servidor --host 127.0.0.1 --port 8765
```

Validação:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

HTTP sem TLS é aceito apenas em `localhost`. Em rede ou nuvem, use HTTPS.

## 2. Provisionar um agente

Na aplicação central, acesse **Infraestrutura → Novo nó**, selecione
**Agente** e copie o identificador e o token exibidos uma única vez.

```powershell
$env:DATA_TI_AGENT_TOKEN = "TOKEN_EXIBIDO_PELA_CENTRAL"
DataIntelligenceTIAgent.exe configure `
  --server-url https://dados.empresa.com `
  --agent-id "IDENTIFICADOR_EXIBIDO_PELA_CENTRAL" `
  --patrimonio TI-PC-001

DataIntelligenceTIAgent.exe once
DataIntelligenceTIAgent.exe install
DataIntelligenceTIAgent.exe task-status
```

No Windows, o token é armazenado separadamente e protegido por DPAPI. Remova
a variável de ambiente depois da configuração.

## 3. Gerar os executáveis

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_aplicacao.ps1
powershell -ExecutionPolicy Bypass -File scripts/build_servidor.ps1
powershell -ExecutionPolicy Bypass -File scripts/build_agente_ti.ps1
```

## 4. Produção

- publique o servidor atrás de HTTPS com certificado válido;
- restrinja a porta no firewall e nunca exponha o SQLite por compartilhamento;
- execute o servidor com conta de serviço sem privilégios administrativos;
- proteja `storage/`, certificados e backups;
- monitore `/health`, espaço em disco, logs e expiração do certificado;
- faça teste periódico de restauração.

O receptor do agente aceita no máximo 2 MB por heartbeat, não segue
redirecionamentos, não registra tokens e exige TLS 1.2 ou superior quando
configurado com certificado.
