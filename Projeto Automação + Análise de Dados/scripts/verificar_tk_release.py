"""Pré-flight do Tcl/Tk usado pelo build Windows.

Falha antes da suíte gráfica quando o interpretador não consegue carregar
Tcl/Tk. Também imprime caminhos úteis para diferenciar instalação quebrada
de uma regressão da interface.
"""
from __future__ import annotations

import sys
from pathlib import Path

def main() -> int:
    try:
        import tkinter as tk
    except Exception as exc:
        print(f"ERRO: tkinter não pôde ser importado: {exc!r}")
        print(f"Python: {sys.executable}")
        print(f"Base: {sys.base_prefix}")
        return 2

    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()

        tcl_library = Path(str(root.tk.eval("info library")))
        tcl_patch = str(root.tk.call("info", "patchlevel"))
        tk_patch = str(root.tk.call("package", "require", "Tk"))

        print(f"Python: {sys.version.split()[0]}")
        print(f"Executável: {sys.executable}")
        print(f"Base Python: {sys.base_prefix}")
        print(f"Tcl: {tcl_patch}")
        print(f"Tk: {tk_patch}")
        print(f"Tcl library: {tcl_library}")
        print(f"init.tcl: {tcl_library / 'init.tcl'}")
        print(f"init.tcl existe: {(tcl_library / 'init.tcl').is_file()}")

        # Pequeno ciclo de janelas filhas sem criar novos interpretadores.
        for _ in range(3):
            child = tk.Toplevel(root)
            child.geometry("320x180+0+0")
            child.update_idletasks()
            child.destroy()

        root.destroy()
        print("Tcl/Tk de release: OK")
        return 0
    except Exception as exc:
        print(f"ERRO: Tcl/Tk não conseguiu inicializar: {exc!r}")
        print(f"Python: {sys.executable}")
        print(f"Base Python: {sys.base_prefix}")
        tcl_root = Path(sys.base_prefix) / "tcl"
        print(f"Pasta Tcl esperada: {tcl_root}")
        if tcl_root.exists():
            print("Conteúdo da pasta Tcl:")
            for item in sorted(tcl_root.iterdir()):
                print(f"  - {item}")
        else:
            print("A pasta Tcl esperada não existe.")
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
