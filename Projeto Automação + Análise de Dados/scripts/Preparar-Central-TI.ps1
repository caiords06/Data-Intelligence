# LEGADO/STANDALONE: porta 8765 pertence ao receptor TI embutido. Em V10.2.0 Server First use o Servidor Corporativo :8770.
param(
    [int]$Porta = 8765
)

$ErrorActionPreference = "Stop"

$identidade = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]$identidade
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Abra o PowerShell como Administrador para preparar a Central TI."
}

if ($Porta -lt 1024 -or $Porta -gt 65535) {
    throw "Porta inválida. Use uma porta entre 1024 e 65535."
}

$Regra = "Data Intelligence - TI Agent API"
$DataDir = Join-Path $env:PROGRAMDATA "DataIntelligence\Platform"
$UsuarioAplicacao = $identidade.Name

New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

# O banco da Central não é liberado para todos os usuários locais. Apenas
# SYSTEM, Administradores e o usuário que executou esta preparação recebem acesso.
icacls.exe $DataDir /inheritance:r /grant:r `
    "*S-1-5-18:(OI)(CI)F" `
    "*S-1-5-32-544:(OI)(CI)F" `
    "${UsuarioAplicacao}:(OI)(CI)M" | Out-Null

Get-NetFirewallRule -DisplayName $Regra -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule -ErrorAction SilentlyContinue

New-NetFirewallRule `
    -DisplayName $Regra `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $Porta `
    -Profile Private `
    -RemoteAddress LocalSubnet | Out-Null

$Perfis = Get-NetConnectionProfile -ErrorAction SilentlyContinue |
    Where-Object { $_.IPv4Connectivity -ne "Disconnected" }
$Ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -ExpandProperty IPAddress -Unique

Write-Host ""
Write-Host "Central TI preparada com sucesso." -ForegroundColor Green
Write-Host "Porta TCP........: $Porta"
Write-Host "Firewall.........: perfil Private / origem LocalSubnet"
Write-Host "Pasta de dados...: $DataDir"
Write-Host "Usuário do app...: $UsuarioAplicacao"
if ($Ips) {
    Write-Host "IPv4 encontrado(s): $($Ips -join ', ')"
    Write-Host "URL provável......: http://$(@($Ips)[0]):$Porta"
}
if ($Perfis -and ($Perfis.NetworkCategory -contains "Public")) {
    Write-Warning "Há uma conexão de rede ativa marcada como PUBLIC. A regra criada vale somente para rede PRIVATE. Confirme o perfil da LAN antes de testar os agentes."
}
Write-Host ""
Write-Host "A regra NÃO desativa o Windows Firewall; libera somente TCP/$Porta para a sub-rede local privada."
