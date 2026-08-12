# Relatório · Integração TI Central + Agente 1.1

## Objetivo

Fechar a lacuna entre o módulo Tecnologia da aplicação desktop e os computadores remotos da LAN, deixando o projeto preparado para distribuição Windows em dois componentes:

1. **DataIntelligencePlatform.exe** — Central de TI;
2. **DataIntelligenceTIAgent.exe** — agente dos computadores gerenciados.

## Implementado

### API central do agente

Foi criado o pacote `servidor_ti/` com um servidor HTTP(S) embutido, iniciado junto com a aplicação desktop.

Rotas:

```text
GET  /health
GET  /api/v1/ti/health
POST /api/v1/ti/agentes/heartbeat
```

A API recebe o contrato do agente, valida a identidade e chama o domínio existente `registrar_snapshot_agente()` para atualizar ativo e telemetria.

### Provisionamento por ativo

Foram adicionadas ao domínio de Tecnologia:

- criação/rotação da credencial de agente;
- consulta de estado;
- revogação;
- listagem por empresa/filial.

A interface **Ativos gerenciados** ganhou:

- `GERAR / ROTACIONAR AGENTE`;
- `REVOGAR AGENTE`;
- estado do agente;
- versão;
- último heartbeat;
- janela com Server URL, patrimônio, Agent ID, token e comando de instalação.

### Segurança do heartbeat

O transporte usa:

- Agent ID;
- HMAC-SHA256;
- hash SHA-256 do corpo;
- timestamp;
- nonce;
- comparação de assinatura em tempo constante;
- recusa de replay;
- validação de Agent ID/patrimônio;
- escopo empresa/filial derivado da credencial da Central.

O token não é enviado dentro do JSON. No endpoint Windows ele é protegido por DPAPI e separado do `agent.json`.

### Estado Online/Degradado

A Central monitora o último heartbeat. Após o limite operacional, o agente passa para `Degradado` e o ativo deixa de ser considerado online pelo heartbeat.

### Caminhos seguros para PyInstaller

Foi criado `core/caminhos.py`.

No desenvolvimento:

```text
storage/app.db
```

No EXE Windows:

```text
C:\ProgramData\DataIntelligence\Platform\app.db
```

Recursos visuais são lidos do bundle PyInstaller, enquanto banco, preferências e logs permanecem fora da pasta temporária do empacotador.

### Agente 1.1

O agente foi atualizado para aceitar o Agent ID emitido pela Central e para falar com a API implementada.

Para laboratório, HTTP em IP privado é permitido **somente quando explicitamente habilitado**. HTTPS continua sendo a orientação para ambiente real.

### Build Windows

Foram adicionados/atualizados:

```text
DataIntelligencePlatform.spec
agente_ti.spec
requirements-build.txt
requirements-agent.txt
requirements-agent-build.txt
scripts/build_distribuicao_windows.ps1
scripts/build_agente_ti.ps1
```

O build completo gera:

```text
release\DataIntelligence-Deployment-Windows.zip
```

com Central e Agente separados.

### Scripts de implantação

Central:

```text
Preparar-Central-TI.ps1
Testar-Central-TI.ps1
Remover-Regra-Servidor-TI.ps1
```

Endpoint:

```text
Instalar-Agente-TI.ps1
Testar-Agente-TI.ps1
Diagnosticar-Conexao-TI.ps1
Desinstalar-Agente-TI.ps1
```

A preparação da Central não desliga o firewall. Cria somente uma regra TCP limitada ao perfil Private e à `LocalSubnet`.

### Documentação

Criados:

```text
README_DISTRIBUICAO_WINDOWS.md
README_CENTRAL_TI.md
README_DISPOSITIVO_TI.md
AGENTE_TI.md
```

O README principal também aponta para esses guias.

## Banco

Nova migração:

```text
enterprise/migrations/013_agentes_ti_api.py
```

Novas tabelas:

```text
ti_agentes
ti_agente_nonces
```

A migração foi aplicada na cópia de validação sem violação de chave estrangeira.

## Validação executada

- `compileall`: aprovado;
- `tabnanny`: aprovado;
- 24 arquivos de testes executados em lotes;
- 158 testes aprovados;
- 1 teste não gráfico ignorado pelo ambiente;
- 82 subtests aprovados nos grupos que os utilizam;
- smoke Tk real com Xvfb: 9 testes + 52 subtests aprovados;
- teste end-to-end do agente enviando heartbeat para um `TIServer` real em localhost: HTTP 202;
- token incorreto: recusado;
- SQLite `integrity_check`: `ok`;
- SQLite `foreign_key_check`: 0 violações;
- migração 013 detectada e tabelas novas presentes.

## Limite desta entrega

O ambiente usado para a correção é Linux. Por isso, os **binários Windows `.exe` não foram fabricados aqui**. PyInstaller gera executáveis para o sistema em que o build é executado; o projeto foi deixado com specs e script PowerShell para que o build Windows seja realizado no seu computador com um comando.

O que foi validado aqui é o código Python, a API, o contrato agente-servidor, o banco, a interface via Tk/Xvfb e a estrutura de distribuição.

## Escopo multi-PC atual

A API implementada é dedicada ao **Agente TI**. Ela permite que endpoints remotos sejam inventariados e monitorados pela Central.

Ela **não transforma ainda todos os módulos desktop em clientes remotos do mesmo banco SQLite**. Se futuramente todos os funcionários precisarem abrir a aplicação completa a partir de suas máquinas com dados centrais compartilhados, a etapa correta será criar o backend multiusuário da plataforma e migrar a persistência empresarial para um banco servidor, como PostgreSQL.
