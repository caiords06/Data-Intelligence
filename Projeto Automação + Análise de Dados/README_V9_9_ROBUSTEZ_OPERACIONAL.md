# V9.9 — Robustez operacional e observabilidade

A V9.9 mantém a arquitetura visual e de domínio das V9.4–V9.8 e concentra as mudanças no ciclo de vida dos processos.

## Mudanças principais

- ciclo de vida centralizado em `core/ciclo_vida.py` para iniciar, encerrar e aguardar servidores/threads;
- servidor TI embutido agora aguarda a thread HTTP e o monitor antes de concluir o shutdown;
- monitor do Servidor Corporativo é encerrado e `join`ado explicitamente;
- runner pytest usa grupos de processo e mata a árvore inteira em timeout, evitando processos filhos órfãos;
- `core/observabilidade.py` adiciona métricas thread-safe, request IDs e logs JSON Lines rotativos;
- Servidor Corporativo e Servidor TI expõem liveness/readiness separados;
- Servidor Corporativo oferece health detalhado apenas para administrador autenticado;
- status do Agente TI passa a ser incremental e preserva PID, versão, início, último envio e falhas;
- logs de servidor/agente ficam estruturados para futura ingestão por observabilidade externa.

## Endpoints de saúde

Servidor Corporativo:

- `GET /api/v1/health/live` — processo HTTP vivo;
- `GET /api/v1/health/ready` — dependências mínimas prontas;
- `GET /api/v1/health/details` — métricas operacionais, exige administrador autenticado.

Servidor TI:

- `GET /api/v1/ti/health/live`;
- `GET /api/v1/ti/health/ready`.

Liveness não executa dependências; readiness consulta o banco. Assim balanceadores/orquestradores conseguem distinguir processo vivo de processo temporariamente incapaz de servir tráfego.
