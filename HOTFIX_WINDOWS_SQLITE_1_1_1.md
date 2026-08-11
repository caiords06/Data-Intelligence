# Hotfix TI Remote 1.1.1 — Windows / SQLite

## Problema corrigido

No Windows, `sqlite3.Connection` usada diretamente como context manager (`with sqlite3.connect(...) as conexao:`) confirma/aborta a transação, mas **não fecha o handle do arquivo** ao sair do bloco. Isso é diferente do que muitos códigos assumem e, no Windows, impede que `TemporaryDirectory` remova o `.db` enquanto o processo ainda mantém o arquivo aberto.

O sintoma durante `scripts\\build_distribuicao_windows.ps1` era:

- `PermissionError: [WinError 32] ... legado.db`;
- `PermissionError: [WinError 32] ... enterprise_....db`;
- build cancelado após o primeiro lote de testes.

## Correções aplicadas

1. `enterprise/backups.py`
   - conexões SQLite abertas diretamente para o arquivo de backup agora são envolvidas em `contextlib.closing`, garantindo fechamento real do handle;
   - a verificação de backup também fecha explicitamente a conexão.

2. `dados/fontes.py`
   - importação de bancos SQLite externos em modo somente leitura agora fecha explicitamente a conexão ao terminar.

3. `tests/test_estabilizacao_v5_1.py`
   - o banco legado temporário mantém a semântica de commit do context manager e fecha o arquivo antes da limpeza do `TemporaryDirectory`.

4. `tests/test_v8_backend.py`
   - o banco SQLite externo de teste é confirmado e fechado antes da limpeza da pasta temporária.

## Validação

O mesmo lote que havia falhado foi executado novamente:

```text
51 passed, 19 subtests passed
```

Também foram validados:

```text
Grupo backend complementar: 43 passed
Grupo TI/servidor/agente:     43 passed
Interface V7:                  7 passed, 11 subtests passed
Estabilização V8.1:            5 passed
Smoke Tk opt-in:               9 skipped (esperado sem RUN_TK_SMOKE)
compileall:                    OK
tabnanny:                      OK
```

## Build no Windows

Execute novamente, na raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

O script deve ultrapassar o lote em que antes ocorria o `WinError 32` e continuar para PyInstaller.
