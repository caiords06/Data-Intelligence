# -*- mode: python ; coding: utf-8 -*-
a = Analysis(["scripts/update_helper.py"], pathex=["."], binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=["tkinter"], noarchive=False, optimize=1)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="DataIntelligenceUpdateHelper", debug=False, strip=False, upx=False, console=True)
