#define MyAppName "Data Intelligence"
#define MyAppVersion "11.1.0"
#define MyPublisher "Data Intelligence"
#define MyExeName "DataIntelligencePlatform.exe"

[Setup]
AppId={{D8E17B0A-1B6A-4A8F-90F4-3F99837D1010}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyPublisher}
DefaultDirName={autopf}\Data Intelligence
DefaultGroupName=Data Intelligence
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=DataIntelligence_Setup_V11.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Files]
Source: "..\dist\DataIntelligencePlatform\*"; DestDir: "{app}\Platform"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: HasRolePlatform
Source: "..\dist\DataIntelligenceServer.exe"; DestDir: "{app}\Server"; Flags: ignoreversion; Check: HasRoleServer
Source: "..\dist\DataIntelligenceTIAgent.exe"; DestDir: "{app}\TIAgent"; Flags: ignoreversion; Check: HasRoleAgent
Source: "..\dist\DataIntelligenceUpdateHelper.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Data Intelligence"; Filename: "{app}\Platform\DataIntelligencePlatform.exe"; Check: HasRolePlatform
Name: "{autodesktop}\Data Intelligence"; Filename: "{app}\Platform\DataIntelligencePlatform.exe"; Tasks: desktopicon; Check: HasRolePlatform

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Check: HasRolePlatform

[Run]
Filename: "{app}\Platform\DataIntelligencePlatform.exe"; Description: "Abrir Data Intelligence"; Flags: nowait postinstall skipifsilent; Check: HasRolePlatform

[Code]
var
  RolePage: TInputOptionWizardPage;
  ServerPage: TInputQueryWizardPage;
  ServerConfigPage: TInputQueryWizardPage;
  DbBackendPage: TInputOptionWizardPage;
  PostgresPage: TInputQueryWizardPage;
  PostgresPasswordPage: TInputQueryWizardPage;
  AdminPage: TInputQueryWizardPage;
  AdminPasswordPage: TInputQueryWizardPage;
  AgentPage: TInputQueryWizardPage;
  AgentTokenPage: TInputQueryWizardPage;
  AllowPrivateHttpPage: TInputOptionWizardPage;

function Role(): String;
begin
  case RolePage.SelectedValueIndex of
    0: Result := 'servercentral';
    1: Result := 'central';
    2: Result := 'server';
    3: Result := 'clientagent';
    4: Result := 'client';
    5: Result := 'agent';
  else
    Result := 'servercentral';
  end;
end;

function HasRoleServer(): Boolean;
begin
  Result := (Role() = 'servercentral') or (Role() = 'server');
end;

function HasRolePlatform(): Boolean;
begin
  Result := (Role() = 'servercentral') or (Role() = 'central') or
            (Role() = 'clientagent') or (Role() = 'client');
end;

function HasRoleAgent(): Boolean;
begin
  Result := (Role() = 'clientagent') or (Role() = 'agent');
end;

function IsCentral(): Boolean;
begin
  Result := (Role() = 'servercentral') or (Role() = 'central');
end;

function NeedsRemoteServer(): Boolean;
begin
  Result := (Role() = 'central') or (Role() = 'clientagent') or
            (Role() = 'client') or (Role() = 'agent');
end;

function JsonBool(Value: Boolean): String;
begin
  if Value then Result := 'true' else Result := 'false';
end;

function BoolText(Value: Boolean; const TrueText, FalseText: String): String;
begin
  if Value then Result := TrueText else Result := FalseText;
end;

function JsonQuote(const S: String): String;
var
  T: String;
begin
  T := S;
  StringChangeEx(T, '\', '\\', True);
  StringChangeEx(T, '"', '\"', True);
  Result := '"' + T + '"';
end;

function CmdQuote(const S: String): String;
begin
  Result := '"' + S + '"';
end;

procedure SaveUtf8NoBom(const FileName, Content: String);
var
  Lines: TArrayOfString;
begin
  SetArrayLength(Lines, 1);
  Lines[0] := Content;
  if not SaveStringsToUTF8FileWithoutBOM(FileName, Lines, False) then
    RaiseException('Falha ao gravar configuração em ' + FileName + '.');
end;

function LoadTextFile(const FileName: String; var Content: String): Boolean;
var
  Lines: TArrayOfString;
  I: Integer;
begin
  Content := '';
  Result := LoadStringsFromFile(FileName, Lines);
  if not Result then
    exit;

  for I := 0 to GetArrayLength(Lines) - 1 do begin
    if I > 0 then
      Content := Content + #13#10;
    Content := Content + Lines[I];
  end;
end;

procedure InitializeWizard();
begin
  RolePage := CreateInputOptionPage(wpSelectDir,
    'Tipo de instalação', 'Selecione o papel deste computador',
    'Escolha uma das seis instalações homologadas e clique em Avançar.', True, False);
  RolePage.Add('PC SERVIDOR + PC CENTRAL');
  RolePage.Add('PC CENTRAL');
  RolePage.Add('PC SERVIDOR');
  RolePage.Add('PC CLIENTE + AGENTE');
  RolePage.Add('PC CLIENTE');
  RolePage.Add('PC AGENTE');
  RolePage.SelectedValueIndex := 0;

  ServerPage := CreateInputQueryPage(RolePage.ID,
    'Servidor corporativo', 'Conexão com o Servidor Corporativo',
    'Informe o endereço HTTPS publicado para esta estação. HTTP é aceito somente em loopback.');
  ServerPage.Add('URL do servidor:', False);
  ServerPage.Values[0] := 'https://servidor.empresa.local:8770';

  AllowPrivateHttpPage := CreateInputOptionPage(ServerPage.ID,
    'Segurança da conexão', 'Transporte corporativo protegido',
    'A V11.1 exige HTTPS fora do próprio computador. O servidor local permanece em loopback para publicação por proxy reverso HTTPS.', False, False);
  AllowPrivateHttpPage.Add('Usar HTTP apenas em 127.0.0.1/localhost');
  AllowPrivateHttpPage.Values[0] := False;

  ServerConfigPage := CreateInputQueryPage(AllowPrivateHttpPage.ID,
    'Configuração do servidor', 'Servidor Corporativo',
    'Defina a porta de escuta. Dados persistentes ficam em ProgramData e são preservados em upgrades.');
  ServerConfigPage.Add('Porta:', False);
  ServerConfigPage.Values[0] := '8770';

  DbBackendPage := CreateInputOptionPage(ServerConfigPage.ID,
    'Banco de dados corporativo', 'Selecione o backend transacional do servidor',
    'PostgreSQL é obrigatório para o modo Server First. Não existe banco local de produção.', True, False);
  DbBackendPage.Add('PostgreSQL (obrigatório)');
  DbBackendPage.SelectedValueIndex := 0;

  PostgresPage := CreateInputQueryPage(DbBackendPage.ID,
    'PostgreSQL', 'Conexão com o banco corporativo',
    'O banco e o usuário devem existir e estar acessíveis por esta máquina. A senha não será gravada no server.json.');
  PostgresPage.Add('Host:', False);
  PostgresPage.Add('Porta:', False);
  PostgresPage.Add('Banco:', False);
  PostgresPage.Add('Usuário:', False);
  PostgresPage.Add('SSL mode:', False);
  PostgresPage.Values[0] := '127.0.0.1';
  PostgresPage.Values[1] := '5432';
  PostgresPage.Values[2] := 'dataintelligence';
  PostgresPage.Values[3] := 'dataintelligence';
  PostgresPage.Values[4] := 'prefer';

  PostgresPasswordPage := CreateInputQueryPage(PostgresPage.ID,
    'Credencial PostgreSQL', 'Senha do usuário do banco',
    'No Windows, a senha será protegida com DPAPI em ProgramData e não ficará em texto puro na configuração.');
  PostgresPasswordPage.Add('Senha:', True);
  PostgresPasswordPage.Add('Confirmar senha:', True);

  AdminPage := CreateInputQueryPage(PostgresPasswordPage.ID,
    'Administrador inicial', 'Criação segura do primeiro administrador',
    'Esta conta será criada apenas se o servidor ainda não possuir usuários.');
  AdminPage.Add('Nome:', False);
  AdminPage.Add('Login:', False);
  AdminPage.Add('E-mail:', False);
  AdminPage.Values[0] := 'Administrador';
  AdminPage.Values[1] := 'admin';

  AdminPasswordPage := CreateInputQueryPage(AdminPage.ID,
    'Senha do administrador', 'Defina a senha inicial',
    'A senha será usada somente durante o bootstrap e não será gravada pelo instalador.');
  AdminPasswordPage.Add('Senha:', True);
  AdminPasswordPage.Add('Confirmar senha:', True);

  AgentPage := CreateInputQueryPage(AdminPasswordPage.ID,
    'Agente TI', 'Provisionamento do agente',
    'Use os dados gerados em Tecnologia > Ativos gerenciados > GERAR / ROTACIONAR AGENTE.');
  AgentPage.Add('Patrimônio:', False);
  AgentPage.Add('Agent ID fornecido pela Central:', False);
  AgentPage.Add('Provedor remoto (AnyDesk/TeamViewer/RustDesk):', False);
  AgentPage.Values[2] := 'AnyDesk';

  AgentTokenPage := CreateInputQueryPage(AgentPage.ID,
    'Token do Agente TI', 'Token de provisionamento',
    'Cole o token gerado pela Central de Tecnologia.');
  AgentTokenPage.Add('Token:', True);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = ServerPage.ID then
    Result := not NeedsRemoteServer()
  else if PageID = AllowPrivateHttpPage.ID then
    Result := not (NeedsRemoteServer() or HasRoleServer())
  else if (PageID = ServerConfigPage.ID) or (PageID = DbBackendPage.ID) or
          (PageID = AdminPage.ID) or (PageID = AdminPasswordPage.ID) then
    Result := not HasRoleServer()
  else if (PageID = PostgresPage.ID) or (PageID = PostgresPasswordPage.ID) then
    Result := not HasRoleServer()
  else if (PageID = AgentPage.ID) or (PageID = AgentTokenPage.ID) then
    Result := not HasRoleAgent();
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  P, V: Integer;
  Provider: String;
begin
  Result := True;
  if CurPageID = ServerPage.ID then begin
    if Pos('http://', Lowercase(ServerPage.Values[0])) <> 1 then
      if Pos('https://', Lowercase(ServerPage.Values[0])) <> 1 then begin
        MsgBox('Informe uma URL HTTP(S) válida.', mbError, MB_OK); Result := False; exit;
      end;
  end;
  if CurPageID = AllowPrivateHttpPage.ID then begin
    if NeedsRemoteServer() and (Pos('http://', Lowercase(Trim(ServerPage.Values[0]))) = 1) and
       (Pos('http://127.0.0.1', Lowercase(Trim(ServerPage.Values[0]))) <> 1) and
       (Pos('http://localhost', Lowercase(Trim(ServerPage.Values[0]))) <> 1) then begin
      MsgBox('HTTP fora de loopback não é permitido. Use HTTPS ou 127.0.0.1/localhost no mesmo computador.', mbError, MB_OK);
      Result := False; exit;
    end;
  end;
  if CurPageID = ServerConfigPage.ID then begin
    P := StrToIntDef(ServerConfigPage.Values[0], -1);
    if (P < 1024) or (P > 65535) then begin
      MsgBox('Use uma porta entre 1024 e 65535.', mbError, MB_OK); Result := False; exit;
    end;
  end;
  if CurPageID = PostgresPage.ID then begin
    P := StrToIntDef(PostgresPage.Values[1], -1);
    if (Trim(PostgresPage.Values[0]) = '') or (Trim(PostgresPage.Values[2]) = '') or
       (Trim(PostgresPage.Values[3]) = '') or (P < 1) or (P > 65535) then begin
      MsgBox('Host, porta, banco e usuário PostgreSQL são obrigatórios.', mbError, MB_OK); Result := False; exit;
    end;
    Provider := Lowercase(Trim(PostgresPage.Values[4]));
    if (Provider <> 'disable') and (Provider <> 'allow') and (Provider <> 'prefer') and
       (Provider <> 'require') and (Provider <> 'verify-ca') and (Provider <> 'verify-full') then begin
      MsgBox('SSL mode PostgreSQL inválido.', mbError, MB_OK); Result := False; exit;
    end;
  end;
  if CurPageID = PostgresPasswordPage.ID then begin
    if Length(PostgresPasswordPage.Values[0]) < 1 then begin
      MsgBox('Informe a senha do PostgreSQL.', mbError, MB_OK); Result := False; exit;
    end;
    if PostgresPasswordPage.Values[0] <> PostgresPasswordPage.Values[1] then begin
      MsgBox('As senhas PostgreSQL não coincidem.', mbError, MB_OK); Result := False; exit;
    end;
  end;
  if CurPageID = AdminPage.ID then begin
    if Length(Trim(AdminPage.Values[0])) < 2 then begin
      MsgBox('Informe o nome do administrador.', mbError, MB_OK); Result := False; exit;
    end;
    if Length(Trim(AdminPage.Values[1])) < 3 then begin
      MsgBox('O login do administrador deve possuir pelo menos 3 caracteres.', mbError, MB_OK); Result := False; exit;
    end;
    if (Trim(AdminPage.Values[2]) <> '') and
       ((Pos('@', AdminPage.Values[2]) = 0) or (Pos('.', AdminPage.Values[2]) = 0)) then begin
      MsgBox('Informe um e-mail válido ou deixe o campo vazio.', mbError, MB_OK); Result := False; exit;
    end;
  end;
  if CurPageID = AdminPasswordPage.ID then begin
    if Length(AdminPasswordPage.Values[0]) < 10 then begin
      MsgBox('Use uma senha com pelo menos 10 caracteres.', mbError, MB_OK); Result := False; exit;
    end;
    if AdminPasswordPage.Values[0] <> AdminPasswordPage.Values[1] then begin
      MsgBox('As senhas não coincidem.', mbError, MB_OK); Result := False; exit;
    end;
  end;
  if CurPageID = AgentPage.ID then begin
    Provider := AgentPage.Values[2];
    if (Provider <> 'AnyDesk') and (Provider <> 'TeamViewer') and (Provider <> 'RustDesk') then begin
      MsgBox('Provedor remoto inválido.', mbError, MB_OK); Result := False; exit;
    end;
    if (Trim(AgentPage.Values[0]) = '') or (Trim(AgentPage.Values[1]) = '') then begin
      MsgBox('Patrimônio e Agent ID são obrigatórios.', mbError, MB_OK); Result := False; exit;
    end;
  end;
  if CurPageID = AgentTokenPage.ID then begin
    V := Length(AgentTokenPage.Values[0]);
    if V < 24 then begin
      MsgBox('O token precisa possuir pelo menos 24 caracteres.', mbError, MB_OK); Result := False; exit;
    end;
  end;
end;

function EffectiveServerUrl(): String;
begin
  if Role() = 'servercentral' then
    Result := 'http://127.0.0.1:' + ServerConfigPage.Values[0]
  else
    Result := ServerPage.Values[0];
end;

procedure WriteNodeConfig();
var
  Dir, Path, Papel, Payload: String;
  AllowHttp: Boolean;
begin
  if not HasRolePlatform() then exit;
  Dir := ExpandConstant('{commonappdata}\DataIntelligence\Platform');
  ForceDirectories(Dir);
  Path := Dir + '\node.json';
  if IsCentral() then Papel := 'central' else Papel := 'cliente';
  AllowHttp := (Role() = 'servercentral') or AllowPrivateHttpPage.Values[0];
  Payload := '{' + #13#10 +
    '  "papel": ' + JsonQuote(Papel) + ',' + #13#10 +
    '  "servidor_url": ' + JsonQuote(EffectiveServerUrl()) + ',' + #13#10 +
    '  "permitir_http_privado": ' + JsonBool(AllowHttp) + ',' + #13#10 +
    '  "sincronizar_backups": ' + JsonBool(IsCentral()) + ',' + #13#10 +
    '  "sincronizar_exportacoes": true,' + #13#10 +
    '  "intervalo_backup_minutos": ' + BoolText(IsCentral(), '15', '30') + #13#10 + '}';
  SaveUtf8NoBom(Path, Payload);
end;

procedure RemoveServerTaskBestEffort(const Exe: String);
var
  ResultCode: Integer;
begin
  if FileExists(Exe) then
    Exec(Exe, 'uninstall-task', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure RemoveAgentTaskBestEffort(const Exe: String);
var
  ResultCode: Integer;
begin
  if FileExists(Exe) then
    Exec(Exe, 'uninstall', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure ConfigureServer();
var
  DataDir, Exe, Params, ErrorPath, ErrorDetails: String;
  PasswordPath, BootstrapPath, Bootstrap: String;
  PgPasswordPath, PgBootstrapPath, PgBootstrap, LegacyDb, MigrationMarker: String;
  ServerHost, ServerEnvironment: String;
  ResultCode: Integer;
begin
  if not HasRoleServer() then exit;
  DataDir := ExpandConstant('{commonappdata}\DataIntelligence\Server');
  ForceDirectories(DataDir);
  { Não grave server.json parcial aqui. O configure-db deve criar a configuração
    completa de forma atômica, já com a referência segura do segredo PostgreSQL.
    Isso também permite recuperar instalações V11.1.0 que falharam no bootstrap. }
  Exe := ExpandConstant('{app}\Server\DataIntelligenceServer.exe');
  ServerHost := '127.0.0.1';
  ServerEnvironment := 'producao';

    PgPasswordPath := ExpandConstant('{tmp}\di-postgres-password.txt');
    PgBootstrapPath := ExpandConstant('{tmp}\di-postgres-bootstrap.json');
    SaveUtf8NoBom(PgPasswordPath, PostgresPasswordPage.Values[0]);
    PgBootstrap := '{' +
      '"backend":"postgresql",' +
      '"server_host":' + JsonQuote(ServerHost) + ',' +
      '"server_porta":' + ServerConfigPage.Values[0] + ',' +
      '"server_tls":false,' +
      '"server_max_upload_mb":1024,' +
      '"server_ambiente":' + JsonQuote(ServerEnvironment) + ',' +
      '"host":' + JsonQuote(PostgresPage.Values[0]) + ',' +
      '"porta":' + PostgresPage.Values[1] + ',' +
      '"banco":' + JsonQuote(PostgresPage.Values[2]) + ',' +
      '"usuario":' + JsonQuote(PostgresPage.Values[3]) + ',' +
      '"sslmode":' + JsonQuote(Lowercase(Trim(PostgresPage.Values[4]))) + ',' +
      '"pool_min":2,"pool_max":12,' +
      '"password_file":' + JsonQuote(PgPasswordPath) + '}';
    SaveUtf8NoBom(PgBootstrapPath, PgBootstrap);
    Params := 'configure-db --bootstrap-file ' + CmdQuote(PgBootstrapPath);
    if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then begin
      DeleteFile(PgPasswordPath); DeleteFile(PgBootstrapPath);
      ErrorPath := DataDir + '\install-db-error.log';
      ErrorDetails := '';
      if LoadTextFile(ErrorPath, ErrorDetails) and (Trim(ErrorDetails) <> '') then
        RaiseException('Falha ao conectar/configurar o PostgreSQL.' + #13#10 + #13#10 + Trim(ErrorDetails))
      else
        RaiseException('Falha ao conectar/configurar o PostgreSQL. Confira host, banco, usuário, senha e SSL mode.');
    end;
    DeleteFile(PgPasswordPath); DeleteFile(PgBootstrapPath);

    { Upgrade V10.0 -> V10.1: migra o app.db legado apenas uma vez. }
    LegacyDb := DataDir + '\app.db';
    MigrationMarker := DataDir + '\postgresql_migrated_v10_1.marker';
    if FileExists(LegacyDb) and (not FileExists(MigrationMarker)) then begin
      Params := 'migrate-sqlite --source ' + CmdQuote(LegacyDb);
      if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
        RaiseException('Falha ao migrar os dados SQLite existentes para PostgreSQL. O app.db original foi preservado.');
      SaveUtf8NoBom(MigrationMarker, 'V10.1 PostgreSQL migration completed');
    end;

  PasswordPath := ExpandConstant('{tmp}\di-admin-password.txt');
  BootstrapPath := ExpandConstant('{tmp}\di-admin-bootstrap.json');
  SaveUtf8NoBom(PasswordPath, AdminPasswordPage.Values[0]);
  Bootstrap := '{' +
    '"nome":' + JsonQuote(AdminPage.Values[0]) + ',' +
    '"usuario":' + JsonQuote(AdminPage.Values[1]) + ',' +
    '"email":' + JsonQuote(AdminPage.Values[2]) + ',' +
    '"password_file":' + JsonQuote(PasswordPath) + '}';
  SaveUtf8NoBom(BootstrapPath, Bootstrap);
  Params := 'init-admin --bootstrap-file ' + CmdQuote(BootstrapPath);
  if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then begin
    DeleteFile(PasswordPath); DeleteFile(BootstrapPath);
    RaiseException('Falha ao criar/verificar o administrador inicial do servidor.');
  end;
  DeleteFile(PasswordPath); DeleteFile(BootstrapPath);

  { O próprio servidor registra a tarefa via subprocess sem cmd.exe.
    Isso preserva corretamente caminhos com espaços em Program Files. }
  Params := 'install-task --executable ' + CmdQuote(Exe);
  if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    RaiseException('Falha ao registrar o Servidor Corporativo para iniciar com o Windows.');

  if not Exec(Exe, 'start-task', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then begin
    RemoveServerTaskBestEffort(Exe);
    RaiseException('O Servidor Corporativo foi instalado, mas não pôde ser iniciado. A tarefa parcial foi removida.');
  end;

  { O processo pode levar alguns segundos para abrir o pool PostgreSQL.
    O Setup só conclui quando /health/ready confirmar prontidão. }
  if not Exec(Exe, 'wait-ready --timeout 45', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then begin
    RemoveServerTaskBestEffort(Exe);
    RaiseException('O Servidor Corporativo não ficou pronto na porta configurada. A tarefa parcial foi removida; consulte ProgramData\DataIntelligence\Server.');
  end;

  { O servidor fica em loopback. A exposição corporativa deve ocorrer por proxy
    reverso HTTPS com certificado e regras próprias de firewall. }
  Exec(ExpandConstant('{sys}\netsh.exe'), 'advfirewall firewall delete rule name="Data Intelligence - Corporate Server"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure ConfigureAgent();
var
  Exe, Params, ServerUrl, TokenPath, BootstrapPath, Bootstrap: String;
  ResultCode: Integer;
begin
  if not HasRoleAgent() then exit;
  Exe := ExpandConstant('{app}\TIAgent\DataIntelligenceTIAgent.exe');
  ServerUrl := EffectiveServerUrl();
  TokenPath := ExpandConstant('{tmp}\di-agent-token.txt');
  BootstrapPath := ExpandConstant('{tmp}\di-agent-bootstrap.json');
  SaveUtf8NoBom(TokenPath, AgentTokenPage.Values[0]);
  Bootstrap := '{' +
    '"server_url":' + JsonQuote(ServerUrl) + ',' +
    '"patrimonio":' + JsonQuote(AgentPage.Values[0]) + ',' +
    '"agent_id":' + JsonQuote(AgentPage.Values[1]) + ',' +
    '"provider":' + JsonQuote(AgentPage.Values[2]) + ',' +
    '"allow_private_http":' + JsonBool(AllowPrivateHttpPage.Values[0]) + ',' +
    '"token_file":' + JsonQuote(TokenPath) + '}';
  SaveUtf8NoBom(BootstrapPath, Bootstrap);
  Params := 'configure-file --bootstrap-file ' + CmdQuote(BootstrapPath);
  if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then begin
    DeleteFile(TokenPath); DeleteFile(BootstrapPath);
    RaiseException('Falha ao provisionar o Agente TI.');
  end;
  DeleteFile(TokenPath); DeleteFile(BootstrapPath);

  { Valida URL + Agent ID + token antes de persistir uma tarefa quebrada. }
  if not Exec(Exe, 'once', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    RaiseException('O Agente TI foi configurado, mas o primeiro heartbeat falhou. Confira Servidor, Agent ID, token e firewall.');

  Params := 'install --executable ' + CmdQuote(Exe);
  if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    RaiseException('Falha ao instalar a inicialização automática do Agente TI.');
  if not Exec(Exe, 'start-task', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then begin
    RemoveAgentTaskBestEffort(Exe);
    RaiseException('Agente TI instalado, mas a tarefa não pôde ser iniciada. A tarefa parcial foi removida.');
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  { Em upgrade, encerra tarefas antigas antes de substituir EXEs em Program Files.
    /End usa apenas o nome da tarefa e não sofre com as aspas do /TR. }
  Exec(ExpandConstant('{sys}\schtasks.exe'), '/End /TN DataIntelligenceCorporateServer', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\schtasks.exe'), '/End /TN DataIntelligence-TIAgent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(800);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    { O papel da estação é persistido primeiro. Se qualquer etapa posterior
      falhar, a Plataforma falha fechado em vez de virar standalone. }
    WriteNodeConfig();
    ConfigureServer();
    ConfigureAgent();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then begin
    if FileExists(ExpandConstant('{app}\Server\DataIntelligenceServer.exe')) then
      Exec(ExpandConstant('{app}\Server\DataIntelligenceServer.exe'), 'uninstall-task', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    if FileExists(ExpandConstant('{app}\TIAgent\DataIntelligenceTIAgent.exe')) then
      Exec(ExpandConstant('{app}\TIAgent\DataIntelligenceTIAgent.exe'), 'uninstall', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec(ExpandConstant('{sys}\netsh.exe'), 'advfirewall firewall delete rule name="Data Intelligence - Corporate Server"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
  if CurUninstallStep = usPostUninstall then begin
    // Intencionalmente NÃO removemos {commonappdata}\DataIntelligence.
    // Banco, configuração, logs, certificados e backups são dados persistentes.
  end;
end;
