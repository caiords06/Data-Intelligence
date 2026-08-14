[Setup]
AppId={{91A58687-A933-450B-9F21-001122334455}
AppName=Data Intelligence Teste
AppVersion=1.0.0
AppPublisher=Data Intelligence
DefaultDirName={autopf}\Data Intelligence Teste
PrivilegesRequired=admin
OutputDir=C:\Temp
OutputBaseFilename=DI_Teste
Compression=lzma2
SolidCompression=yes

[Files]
Source: "C:\Users\caior\OneDrive\Área de Trabalho\Caio - Workplace\Projetos salvar.github\Projeto Automação + Análise de Dados\dist\DataIntelligencePlatform\DataIntelligencePlatform.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Data Intelligence Teste"; Filename: "{app}\DataIntelligencePlatform.exe"