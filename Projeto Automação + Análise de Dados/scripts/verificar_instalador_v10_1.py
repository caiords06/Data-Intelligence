"""Validação estática do instalador V10.1 PostgreSQL + Server First."""
from __future__ import annotations
from pathlib import Path
import re, sys
RAIZ=Path(__file__).resolve().parents[1]
ISS=RAIZ/'installer'/'DataIntelligenceSetup.iss'
PERFIS=("PC SERVIDOR + PC CENTRAL","PC CENTRAL","PC SERVIDOR","PC CLIENTE + AGENTE","PC CLIENTE","PC AGENTE")
def validar()->list[str]:
    t=ISS.read_text(encoding='utf-8'); p=[]
    for perfil in PERFIS:
        if f"RolePage.Add('{perfil}')" not in t: p.append('perfil ausente: '+perfil)
    if t.count('RolePage.Add(')!=6: p.append('devem existir exatamente seis perfis')
    for trecho in (
        'DataIntelligence_Setup_V11.1.0','PostgreSQL (obrigatório)',
        'configure-db --bootstrap-file','migrate-sqlite --source','postgresql_migrated_v10_1.marker',
        'init-admin --bootstrap-file','install-task --executable','start-task','wait-ready --timeout 45',
        '{commonappdata}\\DataIntelligence','http://127.0.0.1:'
    ):
        if trecho not in t: p.append('contrato ausente: '+trecho)
    for trecho in ("SaveStringsToUTF8FileWithoutBOM", "WriteNodeConfig();", "ConfigureServer();"):
        if trecho not in t: p.append('contrato de estabilidade ausente: '+trecho)
    if re.search(r'SaveUtf8NoBom\([^;]*,\s*False\)', t):
        p.append('SaveUtf8NoBom deve receber somente arquivo e conteúdo')
    if re.search(r'--password\s',t): p.append('senha não pode ser passada por argumento')
    if 'LoadStringFromFile(ErrorPath, ErrorDetails)' in t:
        p.append('LoadStringFromFile exige AnsiString; use LoadStringsFromFile para log UTF-8')
    if 'LoadStringsFromFile' not in t:
        p.append('leitura UTF-8 do log de erro do PostgreSQL ausente')
    if 'SQLite (compatibilidade/standalone)' in t or 'configure-db --backend sqlite' in t: p.append('SQLite de produção não pode ser oferecido')
    if '[Types]' in t or '[Components]' in t: p.append('perfis devem continuar fechados')
    return p
def main()->int:
    p=validar()
    if p:
        print('Instalador V10.1 inválido:',file=sys.stderr)
        for x in p: print(' - '+x,file=sys.stderr)
        return 1
    print('Instalador V11.1.0: validação estática aprovada.')
    return 0
if __name__=='__main__': raise SystemExit(main())
