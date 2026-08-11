# Hotfix TI Remote 1.1.2 — janela de provisionamento do agente

## Problema
Ao clicar em **GERAR / ROTACIONAR AGENTE**, a credencial era criada no backend, mas a janela visual ficava branca/vazia.

## Causa
`interface/tecnologia.py` chamava `preparar_janela_secundaria` usando a assinatura antiga:

```python
preparar_janela_secundaria(janela, "Provisionamento do agente TI", largura=760, altura=600)
```

O segundo argumento da função atual é o **widget pai**, não o título. A string era tratada como `parent`, causando exceção depois que o `Toplevel` já havia sido criado; por isso sobrava uma janela branca.

## Correção
- título definido com `janela.title(...)`;
- `self.root` passado como parent real;
- dimensões passadas segundo a assinatura atual;
- modalidade e tamanho mínimo definidos explicitamente;
- teste gráfico de regressão adicionado para garantir que a janela abre, tem tema escuro e contém servidor, patrimônio e Agent ID.
