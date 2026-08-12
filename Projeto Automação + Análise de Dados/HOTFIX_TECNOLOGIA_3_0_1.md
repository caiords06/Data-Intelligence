# Tecnologia 3.0.1 — correção do CRUD de segmentos

Correção aplicada ao erro `sqlite3.IntegrityError: UNIQUE constraint failed: ti_segmentos_rede.empresa_id, ti_segmentos_rede.cidr`.

## O que foi corrigido

- Segmento removido/arquivado com o mesmo CIDR agora é **reativado**, preservando o mesmo ID e a auditoria.
- Segmento já ativo com o mesmo CIDR retorna **mensagem amigável**, sem traceback do SQLite.
- Ao reativar, autorização de descoberta, regra de firewall e estatísticas da última varredura são reiniciadas para evitar estado antigo indevido.
- Edição de segmento valida conflito de CIDR antes de atualizar.
- Nova migração `012_segmentos_rede_multifilial` substitui a unicidade antiga `(empresa_id, cidr)` por unicidade de escopo `(empresa_id, filial_id, cidr)`.
- Duas filiais da mesma empresa podem usar o mesmo CIDR privado, situação comum em redes corporativas.
- A migração preserva IDs, vínculos com dispositivos e integridade referencial.

## Validação

- `tests/test_tecnologia_3_0.py`: 9 aprovados.
- Regressões relacionadas a Tecnologia/V8.2: 30 aprovados.
- Smoke Tkinter de Tecnologia: 2 aprovados + 6 subtests.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: 0 violações.
