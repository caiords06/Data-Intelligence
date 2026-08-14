# V10.2.1 — Auditoria visual e responsividade

A V10.2.1 foi incorporada à V10.3.0. O gerador visual agora pode validar os temas escuro e claro em uma matriz canônica de resoluções.

```powershell
python scripts\gerar_capturas_interface.py --escopo completo --tema ambos --matriz --falhar-em-erro
```

A matriz padrão cobre 1024x680, 1366x768, 1600x900 e 1920x1080. Os artefatos são separados por tema e resolução para evitar mistura entre snapshots.
