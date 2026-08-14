# Hotfix V10.1.1 — estabilidade do smoke Tcl/Tk no Windows

## Sintoma reproduzido
Durante `scripts\build_distribuicao_windows.ps1`, vários testes gráficos
eram aprovados e, depois de muitas criações/destruições de `tk.Tk()`, um
teste podia falhar com:

`TclError: Can't find a usable init.tcl`

O traceback podia sugerir instalação incorreta do Tcl, mesmo depois de
dezenas de telas já terem sido construídas no mesmo processo.

## Correções
1. `test_interface_smoke_v8_2.py`
   - um `tk.Tk()` mestre por método;
   - telas de cada cenário usam `tk.Toplevel`;
   - preserva construção real dos widgets e dos menus;
   - reduz drasticamente criação/destruição de interpretadores Tcl.

2. `scripts/verificar_tk_release.py`
   - inicializa Tcl/Tk antes do smoke;
   - mostra Python, base, versões Tcl/Tk e caminho de `init.tcl`;
   - falha cedo se a instalação realmente estiver quebrada.

3. `scripts/build_distribuicao_windows.ps1`
   - smoke V8.2 e V9 rodam em processos Python diferentes;
   - `RUN_TK_SMOKE` é sempre removida por `finally`;
   - mensagem de falha passa a distinguir runtime Tcl/Tk de regressão da UI.

## Validação neste pacote
Em ambiente gráfico Xvfb:
- `test_interface_smoke_v8_2.py`: 10 passed, 52 subtests;
- `test_v9_interface_smoke.py`: 3 passed, 18 subtests.

## Aplicação
Extraia este patch sobre a raiz da V10.1.1, substituindo os arquivos, e rode:

powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
