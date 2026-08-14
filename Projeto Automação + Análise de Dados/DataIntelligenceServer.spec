# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

# O dispatcher RPC importa operações de domínio por string em runtime. Essas
# dependências não aparecem no grafo estático do PyInstaller. Derivamos a lista
# diretamente da allowlist para que a próxima adição de módulo RPC não dependa
# de alguém lembrar de editar manualmente este spec.
from core.rpc_central import RPC_ALLOWLIST

_rpc_modulos = sorted(RPC_ALLOWLIST)
_rpc_packages = sorted({modulo.split(".", 1)[0] for modulo in _rpc_modulos})

hiddenimports = list(_rpc_modulos)
for _package in _rpc_packages:
    hiddenimports += collect_submodules(_package)
# O processo servidor usa módulos enterprise importados estaticamente e o
# cliente PostgreSQL carrega backends internos dinamicamente.
hiddenimports += collect_submodules("enterprise")
hiddenimports += collect_submodules("servidor_corporativo")
hiddenimports += collect_submodules("servidor_ti")
hiddenimports += collect_submodules("psycopg")
hiddenimports += collect_submodules("psycopg_pool")
hiddenimports += collect_submodules("cryptography")
# Relatórios de RH são gerados no processo servidor. Pandas carrega os engines
# XLSX e o ReportLab possui submódulos dinâmicos que o grafo estático pode não
# detectar quando a importação ocorre dentro do caso de uso.
hiddenimports += collect_submodules("pandas")
hiddenimports += collect_submodules("openpyxl")
hiddenimports += collect_submodules("reportlab")
hiddenimports = sorted(set(hiddenimports))

a = Analysis(
    ["servidor_corporativo/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("enterprise/postgresql/schema_v10_1.sql", "enterprise/postgresql"),
        ("enterprise/postgresql/schema_hardening.sql", "enterprise/postgresql"),
        ("enterprise/postgresql/schema_v11.sql", "enterprise/postgresql"),
        ("enterprise/postgresql/schema_v11_1.sql", "enterprise/postgresql"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # O servidor é headless. Interface gráfica e automação de navegador não
    # pertencem ao processo autoritativo.
    excludes=["tests", "tkinter", "selenium", "PIL"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="DataIntelligenceServer", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=True, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
