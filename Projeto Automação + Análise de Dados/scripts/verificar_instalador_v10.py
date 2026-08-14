"""Validação estática e multiplataforma do instalador unificado V10.

A compilação real do .iss continua obrigatória no job Windows com ISCC.exe.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

RAIZ = Path(__file__).resolve().parents[1]
ISS = RAIZ / "installer" / "DataIntelligenceSetup.iss"

PERFIS = (
    "PC SERVIDOR + PC CENTRAL",
    "PC CENTRAL",
    "PC SERVIDOR",
    "PC CLIENTE + AGENTE",
    "PC CLIENTE",
    "PC AGENTE",
)


def validar() -> list[str]:
    problemas: list[str] = []
    texto = ISS.read_text(encoding="utf-8")
    for perfil in PERFIS:
        if f"RolePage.Add('{perfil}')" not in texto:
            problemas.append(f"perfil ausente: {perfil}")
    if texto.count("RolePage.Add(") != 6:
        problemas.append("a página de papel deve possuir exatamente seis opções")
    for trecho in (
        "CreateInputOptionPage(wpSelectDir",
        "True, False);",
        "Check: HasRolePlatform",
        "Check: HasRoleServer",
        "Check: HasRoleAgent",
        "DataIntelligence_Setup_V11.1.0",
        "http://127.0.0.1:",
        "https://servidor.empresa.local:8770",
        "AllowPrivateHttpPage.Values[0] := False;",
        "ServerHost := '127.0.0.1';",
        "ServerEnvironment := 'producao';",
        "init-admin --bootstrap-file",
        "configure-file --bootstrap-file",
        "install-task --executable",
        "start-task",
        "wait-ready --timeout 45",
        "{commonappdata}\\DataIntelligence",
    ):
        if trecho not in texto:
            problemas.append(f"contrato ausente: {trecho}")
    if re.search(r"--password\s", texto):
        problemas.append("senha de administrador não pode ser passada por argumento")
    if "AllowPrivateHttpPage.Values[0] := True;" in texto:
        problemas.append("HTTP privado não pode iniciar habilitado")
    if "[Types]" in texto or "[Components]" in texto:
        problemas.append("V10 deve expor a seleção fechada de papel, não componentes editáveis")
    origens_aceitas = (
        (r"..\dist\DataIntelligencePlatform\*", r"{#ProjectRoot}\dist\DataIntelligencePlatform\*"),
        (r"..\dist\DataIntelligenceServer.exe", r"{#ProjectRoot}\dist\DataIntelligenceServer.exe"),
        (r"..\dist\DataIntelligenceTIAgent.exe", r"{#ProjectRoot}\dist\DataIntelligenceTIAgent.exe"),
        (r"..\dist\DataIntelligenceUpdateHelper.exe", r"{#ProjectRoot}\dist\DataIntelligenceUpdateHelper.exe"),
    )
    for alternativas in origens_aceitas:
        if not any(origem in texto for origem in alternativas):
            problemas.append(f"origem de build ausente: {alternativas[-1]}")
    return problemas


def main() -> int:
    problemas = validar()
    if problemas:
        print("Instalador V10 inválido:", file=sys.stderr)
        for problema in problemas:
            print(f" - {problema}", file=sys.stderr)
        return 1
    print("Instalador V11.1.0: validação estática aprovada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
