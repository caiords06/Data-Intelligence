# V10 — Instalador Windows Unificado

O build V10 produz um único `DataIntelligence_Setup_V10.0.0.exe`.

Perfis disponíveis no assistente:

1. **PC SERVIDOR + PC CENTRAL** — instala Servidor Corporativo e aplicação desktop em modo Central. A Central aponta automaticamente para o servidor local.
2. **PC CENTRAL** — instala a aplicação desktop em modo Central e solicita a URL do Servidor Corporativo.
3. **PC SERVIDOR** — instala somente o Servidor Corporativo.
4. **PC CLIENTE + AGENTE** — instala a aplicação em modo Cliente e o Agente TI.
5. **PC CLIENTE** — instala somente a aplicação em modo Cliente.
6. **PC AGENTE** — instala somente o Agente TI.

## Persistência

Executáveis ficam em `C:\Program Files\Data Intelligence` e dados mutáveis em `C:\ProgramData\DataIntelligence`. Upgrades e desinstalações não removem automaticamente banco, configuração, logs, certificados ou backups.

## Build

Requisitos no Windows: Python 3.14, dependências travadas, PyInstaller e Inno Setup 6.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_distribuicao_windows.ps1
```

Ao final, o arquivo principal para distribuição é:

```text
release\DataIntelligence_Setup_V10.0.0.exe
```
