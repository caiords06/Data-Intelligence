# Implantação atual — Servidor Corporativo, Central, Cliente e Agente TI

> Documento atualizado para V10.1.1. O antigo servidor `servidor/` em 8765 é legado; a implantação corporativa usa `servidor_corporativo/` em 8770.

## Servidor

Use preferencialmente o Setup unificado e selecione **PC SERVIDOR** ou **PC SERVIDOR + PC CENTRAL**. PostgreSQL é o backend recomendado.

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8770/api/v1/health/live
Invoke-RestMethod http://127.0.0.1:8770/api/v1/health/ready
```

## Central/Cliente

A estação recebe `node.json` com papel `central` ou `cliente` e a URL do servidor. Não conecte estações diretamente ao PostgreSQL.

## Agente TI

Gere a credencial em **Tecnologia → Ativos gerenciados** e configure o agente usando a mesma URL do Servidor Corporativo, normalmente `http://IP_DO_SERVIDOR:8770` em laboratório privado.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```
