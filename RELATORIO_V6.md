# Relatório de entrega — V6

## Objetivo

Esta entrega estabiliza a base empresarial antes de ampliar os módulos. O foco
foi eliminar resultados silenciosamente incompletos, reforçar integridade e
criar um ciclo de vida auditável para os registros.

## Implementado

### Banco e integridade

- `PRAGMA foreign_keys = ON` em toda conexão;
- `busy_timeout` para reduzir falhas transitórias de concorrência;
- migração versionada `enterprise_001_v6_estabilizacao`;
- escopo `empresa_id + filial_id` nos registros operacionais;
- índices para filial, estado e paginação;
- dinheiro representado também em centavos inteiros, usado nos resumos e no
  DataFrame enviado ao Analytics;
- histórico com estado anterior, estado posterior, usuário e ID da operação.

### Registros operacionais

- pesquisa textual;
- paginação de 25, 50, 100 ou 200 itens;
- ordenação por coluna;
- edição;
- arquivamento;
- lixeira;
- restauração;
- filtros por estado.

A interface não executa exclusão física. Isso evita apagar movimentações,
aprovações e evidências de auditoria relacionadas.

### Analytics

O limite silencioso de 1.000 linhas foi removido. A consulta empresarial agora
carrega todo o universo autorizado da filial; uma amostra só pode ser usada por
parâmetro explícito.

Foram adicionados motores para:

- Compras;
- Tecnologia;
- Marketing;
- Administrativo;
- Jurídico;
- Comercial.

As categorias também estão disponíveis na Nova análise, nas preferências e nos
dashboards adaptativos.

### Interface

O desenho das divisórias usa coordenadas reais do widget e é refeito após:

- primeiro mapeamento;
- estabilização do layout;
- redimensionamento;
- exposição da janela;
- movimento manual de coluna.

O estado vazio permanece acima das linhas. O comportamento foi aplicado a
módulos, Histórico, Aprovações, Notificações e Usuários.

### Operação

- Job Manager persistente para progresso, conclusão e falha de análises;
- backup administrativo com `sqlite3.backup`, `PRAGMA quick_check` e SHA-256;
- remoção de aprovações da fila sem exclusão da decisão ou auditoria.

## Compatibilidade

A migração é aplicada automaticamente na inicialização e preserva as tabelas
e registros existentes. As colunas `REAL` monetárias foram mantidas nesta fase
para compatibilidade; os novos campos `*_centavos` são a representação exata
usada pelos cálculos V6.

## Validação

```text
50 testes aprovados
compileall sem erros
tabnanny sem erros
foreign_keys = 1 em novas conexões
Analytics validado com mais de 1.000 registros
```

## Mantido no roadmap

Os itens abaixo exigem uma etapa própria de produto e não foram simulados com
telas vazias nesta entrega:

- HCM completo, folha e eSocial;
- Contas a pagar/receber, conciliação e DRE;
- CRM compartilhado entre Marketing e Comercial;
- processos jurídicos;
- portal do colaborador;
- Workflow Builder visual;
- Central de documentos e tarefas completa;
- Gmail API, Microsoft Graph e SMTP com OAuth/cofre;
- relatórios PDF/Excel agendados;
- MFA e SSO;
- migração para PostgreSQL/FastAPI.

Esses recursos precisam de regras de negócio, credenciais, homologação e telas
específicas. A V6 deixa a infraestrutura mais segura para recebê-los.

