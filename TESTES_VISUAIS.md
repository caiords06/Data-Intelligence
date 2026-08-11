# Testes visuais das interfaces

O projeto possui uma rotina dedicada a abrir as janelas Tkinter, exportar cada
estado de interface para PNG e reunir as evidências em um relatório visual.
O banco utilizado durante a captura é temporário: os dados reais da aplicação
não são alterados.

O catálogo atual cobre **166 estados de interface** no escopo completo e **37**
no escopo essencial. As seções são descobertas a partir dos menus reais do
projeto, evitando uma lista visual paralela que fique desatualizada.

## Execução recomendada no Windows

Feche ou minimize outras janelas, mantenha a área de trabalho desbloqueada e
execute no terminal aberto na raiz do projeto:

```powershell
python scripts/gerar_capturas_interface.py --escopo completo
```

Para uma verificação mais curta, com as telas principais de cada família:

```powershell
python scripts/gerar_capturas_interface.py --escopo essencial
```

Para escolher resolução e pasta de saída:

```powershell
python scripts/gerar_capturas_interface.py `
    --escopo completo `
    --largura 1600 `
    --altura 900 `
    --destino artifacts/interface_png
```

## Arquivos gerados

| Arquivo | Finalidade |
| --- | --- |
| `*.png` | Uma evidência visual por tela/seção |
| `FOLHA_CONTATO.png` | Todas as telas reunidas para revisão rápida |
| `RELATORIO_VISUAL.md` | Resultado, dimensões e diagnósticos por interface |
| `MANIFESTO_VISUAL.json` | Métricas estruturadas para CI ou comparação futura |

Cada PNG é verificado quanto a dimensão mínima, imagem vazia, contraste,
variedade visual e controles visíveis posicionados fora da janela. A folha de
contato ainda deve ser revisada por uma pessoa, pois alinhamento, clareza e
hierarquia visual dependem do contexto do design.

## Execução como teste automatizado

No Prompt de Comando:

```bat
set RUN_TK_SCREENSHOTS=1
python -m unittest tests.test_interface_screenshots -v
```

No PowerShell:

```powershell
$env:RUN_TK_SCREENSHOTS = "1"
python -m unittest tests.test_interface_screenshots -v
```

O teste visual é opt-in para não quebrar execuções headless. Os testes do
analisador de PNG continuam rodando normalmente em qualquer ambiente.

## Linux/CI

O Tkinter exige um display. Em um runner Linux com Tk e Xvfb instalados:

```bash
RUN_TK_SCREENSHOTS=1 xvfb-run -a \
    python -m unittest tests.test_interface_screenshots -v
```

Sem um display, o teste real é ignorado e apenas o analisador de imagens é
validado.
