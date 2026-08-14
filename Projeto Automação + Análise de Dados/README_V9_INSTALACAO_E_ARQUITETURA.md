> **DOCUMENTO HISTÓRICO.** Esta documentação descreve arquitetura anterior à linha final Server First. Para novas instalações, use `docs/README.md`.

# Data Intelligence Enterprise Platform V9.0

## Reestruturação corporativa, módulos por objetivo, correio interno e servidor corporativo

Esta versão reorganiza a plataforma em três tipos de instalação e abandona a ideia de que todos os departamentos precisam parecer uma planilha.

## 1. Componentes da distribuição

Depois do build Windows, o arquivo `release\DataIntelligence-Deployment-Windows.zip` contém quatro pastas:

- **Servidor** — serviço corporativo sem interface gráfica. Centraliza identidade/usuários, correio interno, arquivos espelhados e backups completos.
- **Central** — aplicativo desktop para administradores e operadores autorizados. Conecta-se ao Servidor Corporativo e pode administrar usuários e arquivos do servidor.
- **Cliente** — o mesmo aplicativo desktop em papel convencional. Autentica no Servidor Corporativo e não permite criar usuários.
- **Agente-TI** — processo separado e leve para inventário/telemetria dos computadores gerenciados pelo módulo de Tecnologia. Não substitui a estação Cliente.

> **Importante:** não compartilhe `app.db` por SMB/pasta de rede. O servidor e os clientes se comunicam por HTTP(S), e cada processo mantém seu próprio armazenamento conforme a função.

## 2. Ordem correta de implantação

### 2.1 Servidor Corporativo

No computador que ficará disponível para a rede:

1. Extraia `Servidor`.
2. Abra PowerShell **como Administrador** na pasta.
3. Execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\Instalar-Servidor-Corporativo.ps1
```

4. O instalador solicitará o primeiro administrador: nome, login, e-mail corporativo e senha.
5. Descubra o IPv4 do servidor com `ipconfig`.
6. Em uma rede privada de laboratório, teste, por exemplo:

```powershell
.\Testar-Servidor-Corporativo.ps1 -ServerUrl "http://192.168.1.10:8770"
```

A instalação cria:

- executável em `C:\Program Files\DataIntelligence\Server\DataIntelligenceServer.exe`;
- dados persistentes em `C:\ProgramData\DataIntelligence\Server`;
- regra de firewall TCP/8770 limitada ao perfil **Private** e `LocalSubnet`;
- tarefa do Windows para iniciar o servidor como `SYSTEM` na inicialização.

Em produção, use **HTTPS com certificado**. O modo HTTP privado existe apenas para laboratório/LAN controlada.

### 2.2 Estação Central

No computador administrativo:

1. Extraia `Central`.
2. Abra PowerShell como Administrador.
3. Em laboratório privado:

```powershell
powershell -ExecutionPolicy Bypass -File .\Configurar-Estacao-Central.ps1 `
  -ServerUrl "http://192.168.1.10:8770" `
  -AllowPrivateHttp
```

4. Se o mesmo computador também receber heartbeats dos Agentes TI, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\Preparar-Central-TI.ps1
```

5. Abra:

```text
DataIntelligencePlatform\DataIntelligencePlatform.exe
```

A Central não faz primeiro acesso local quando está configurada para servidor remoto. Entre com a conta criada no servidor.

### 2.3 Estação Cliente

Nos computadores dos usuários convencionais:

```powershell
powershell -ExecutionPolicy Bypass -File .\Configurar-Estacao-Cliente.ps1 `
  -ServerUrl "http://192.168.1.10:8770" `
  -AllowPrivateHttp
```

Depois abra `DataIntelligencePlatform.exe`.

A estação Cliente:

- usa login corporativo do servidor;
- não executa bootstrap/primeiro administrador;
- não oferece gerenciamento de usuários na navegação;
- não permite abrir a tela de usuários mesmo se uma credencial administrativa for usada por engano;
- usa o correio corporativo interno;
- pode espelhar exportações para o servidor conforme a configuração do nó.

### 2.4 Agente TI

O `Agente-TI` é opcional e serve para monitoramento técnico de máquinas. Instale-o em computadores que devem enviar inventário/telemetria para a Central TI.

Ele é independente da estação Cliente. Um computador pode ter:

- apenas Cliente;
- apenas Agente-TI;
- Cliente + Agente-TI.

Consulte `README_DISPOSITIVO_TI.md` para provisionamento do Agent ID/token e heartbeat.

## 3. Correio corporativo interno

Cada usuário possui `email_corporativo`. Se não for informado explicitamente, o sistema gera um endereço interno no domínio local da plataforma.

O Correio Corporativo possui:

- Caixa de entrada;
- Enviados;
- Rascunhos;
- Arquivados;
- Lixeira;
- busca;
- nova mensagem/resposta;
- anexos;
- marcação de leitura/destaque;
- origem do módulo.

O correio aparece globalmente e dentro dos módulos. Em estações conectadas ao Servidor Corporativo, mensagens e anexos ficam no servidor, não em um arquivo compartilhado de rede.

## 4. Nova lógica visual dos módulos

**Analytics foi preservado** como área analítica própria. Os outros módulos passaram a usar metáforas de trabalho específicas:

- RH — `People Operations`: jornada da pessoa, admissões, ausências, desempenho e offboarding.
- Financeiro — `Financial Command Center`: liquidez, entradas/saídas, aprovações, conciliação e projeção.
- Estoque — `Warehouse Control`: recebimento, disponibilidade, reservas, movimentação e inventário.
- Compras — `Procurement Desk`: solicitação, alçada, cotação, pedido e recebimento.
- Tecnologia — centro operacional de rede, ativos, telemetria, service desk e acesso remoto.
- Marketing — `Growth Studio`: campanhas, conteúdo, calendário, aquisição e aprendizado.
- Administrativo — `Workplace Operations`: serviços internos, facilities, salas, viagens e reembolsos.
- Jurídico — `Legal Operations`: prazos, contratos, processos, audiências e risco.
- Comercial — `Revenue Workspace`: leads, qualificação, propostas, negociação e clientes.

Grades são mantidas apenas onde comparação massiva faz sentido. Nessas grades, a V9 inclui edição direta por célula e exportação CSV/XLSX nos fluxos implementados. As divisórias artificiais que ficavam desalinhadas em DPI/redimensionamento foram removidas; as colunas passam a usar a renderização nativa do `Treeview`.

## 5. Arquivos e backups

### Exportações

Quando um usuário escolhe um caminho para exportar CSV/XLSX/relatório:

1. o arquivo continua no caminho escolhido;
2. se o nó estiver conectado e o espelhamento estiver ativo, uma cópia é enviada ao servidor.

Documentos corporativos, anexos financeiros, documentos/contracheques de RH e datasets importados também possuem espelhamento best-effort quando a sessão remota está ativa.

### Backup completo

A Central pode gerar um ZIP de backup contendo:

- snapshot consistente do SQLite local;
- arquivos persistentes da pasta de dados;
- manifesto;
- SHA-256 de cada arquivo.

O servidor recebe cópias dos backups da Central conforme o intervalo configurado. A rotina de verificação confere hashes, `quick_check` e foreign keys. Existe restauração completa do banco + storage, com backup de segurança antes da restauração.

## 6. Administração do servidor

Na estação Central, administradores possuem acesso a **Configurações → Arquivos do Servidor Corporativo**.

A tela permite:

- consultar saúde do servidor;
- listar materiais espelhados;
- listar backups;
- excluir um item específico do servidor.

Exclusão de arquivos/backups no servidor é protegida por autenticação e privilégio administrativo.

## 7. Segurança de sessão

A V9 usa `sessao_epoch` para revogação. Alterações sensíveis como senha/status/perfil invalidam sessões antigas. No modo remoto, o servidor também valida o epoch do usuário a cada requisição autenticada.

A mudança da própria senha encerra a sessão remota atual e exige novo login.

## 8. Isolamento empresarial e aprovações

Foram adicionadas regressões para:

- operações de RH não atravessarem filiais;
- consultas corporativas tratarem corretamente `filial_id IS NULL`;
- alçadas financeiras exigirem o perfil da etapa;
- Compras criar etapas reais de Gestor/Financeiro/Diretoria conforme a regra;
- Central de Aprovações delegar a decisão ao motor nativo do módulo e manter os estados sincronizados.

## 9. Limite arquitetural atual

O Servidor Corporativo da V9 é a autoridade compartilhada para **identidade/autenticação, correio, repositório de materiais e backups**.

Os motores transacionais departamentais ainda executam no aplicativo desktop e mantêm um banco local por estação. Seus snapshots completos podem ser enviados ao servidor, mas **esta versão ainda não transforma todo CRUD departamental em uma única base transacional multiusuário em tempo real**.

Para essa próxima fase, a arquitetura correta é mover os serviços de domínio para APIs do servidor e, conforme a concorrência crescer, migrar a base compartilhada para PostgreSQL. Não use SQLite compartilhado diretamente por SMB.

## 10. Build Windows

Na raiz do código-fonte, no Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

O script:

1. instala dependências;
2. compila e executa regressões;
3. gera o Desktop;
4. gera o Agente TI;
5. gera o Servidor Corporativo;
6. monta Central/Cliente/Agente-TI/Servidor;
7. verifica que não há banco, `.git`, caches ou screenshots na distribuição;
8. gera `release\DataIntelligence-Deployment-Windows.zip`.

Não distribua o ZIP do código-fonte como instalador. Distribua o ZIP gerado em `release`.
