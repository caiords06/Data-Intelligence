"""Integração mínima e segura com o Firewall do Windows para o laboratório de TI.

A plataforma NUNCA desativa o firewall. Ela pode criar, mediante confirmação do
operador e privilégios administrativos, uma regra ICMPv4 de entrada limitada ao
CIDR privado explicitamente cadastrado. Isso torna a máquina que executa a
plataforma observável no laboratório sem abrir portas de administração remota.
"""

from __future__ import annotations

import base64
import ctypes
import os
import subprocess


class FirewallError(RuntimeError):
    pass


def eh_windows() -> bool:
    return os.name == "nt"


def eh_administrador() -> bool:
    if not eh_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _executar_powershell(script: str, *, ambiente: dict[str, str] | None = None) -> str:
    """Executa PowerShell sem concatenar dados do usuário ao código.

    ``powershell -Command <script> arg1 arg2`` é ambíguo no Windows e foi a
    causa do erro observado em produção: o nome da regra começando por
    ``Data Intelligence ...`` acabou interpretado como código PowerShell.
    O script agora é enviado por ``-EncodedCommand`` (UTF-16LE, formato nativo
    do PowerShell) e os valores variáveis entram somente por variáveis de
    ambiente. Isso também evita corrupção dos acentos na saída de erro.
    """
    codificado = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    comando = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", codificado,
    ]
    env = os.environ.copy()
    if ambiente:
        env.update({str(k): str(v) for k, v in ambiente.items()})
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            shell=False,
            creationflags=flags,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        raise FirewallError(f"Não foi possível executar o PowerShell: {erro}") from erro
    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout or "Falha não detalhada").strip()
        raise FirewallError(detalhe[:1200])
    return (resultado.stdout or "").strip()


def nome_regra(segmento_id: int) -> str:
    return f"Data Intelligence TI - Descoberta {int(segmento_id)}"


def preparar_descoberta_local(segmento_id: int, cidr: str) -> dict:
    """Cria regra ICMP restrita ao CIDR no perfil Private do Windows."""
    if not eh_windows():
        return {"aplicado": False, "status": "Não aplicável", "regra": None, "mensagem": "Firewall automático disponível somente no Windows."}
    if not eh_administrador():
        return {
            "aplicado": False,
            "status": "Requer administrador",
            "regra": nome_regra(segmento_id),
            "mensagem": "Execute a plataforma como Administrador para criar a regra de descoberta local.",
        }
    regra = nome_regra(segmento_id)
    script = r"""
$ErrorActionPreference = 'Stop'
$nome = $env:DI_FIREWALL_RULE_NAME
$cidr = $env:DI_FIREWALL_REMOTE_CIDR
if ([string]::IsNullOrWhiteSpace($nome) -or [string]::IsNullOrWhiteSpace($cidr)) {
    throw 'Parâmetros da regra de firewall ausentes.'
}
Get-NetFirewallRule -DisplayName $nome -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $nome -Direction Inbound -Action Allow -Protocol ICMPv4 -IcmpType 8 -RemoteAddress $cidr -Profile Private | Out-Null
Write-Output 'OK'
"""
    _executar_powershell(
        script,
        ambiente={
            "DI_FIREWALL_RULE_NAME": regra,
            "DI_FIREWALL_REMOTE_CIDR": cidr,
        },
    )
    return {"aplicado": True, "status": "Ativa", "regra": regra, "mensagem": f"Regra ICMP restrita a {cidr} criada no perfil Privado."}


def remover_descoberta_local(segmento_id: int) -> dict:
    if not eh_windows():
        return {"removido": False, "status": "Não aplicável", "regra": None}
    if not eh_administrador():
        raise FirewallError("Execute a plataforma como Administrador para remover a regra do Firewall do Windows.")
    regra = nome_regra(segmento_id)
    script = r"""
$ErrorActionPreference = 'Stop'
$nome = $env:DI_FIREWALL_RULE_NAME
if ([string]::IsNullOrWhiteSpace($nome)) {
    throw 'Nome da regra de firewall ausente.'
}
Get-NetFirewallRule -DisplayName $nome -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
Write-Output 'OK'
"""
    _executar_powershell(
        script,
        ambiente={"DI_FIREWALL_RULE_NAME": regra},
    )
    return {"removido": True, "status": "Removida", "regra": regra}
