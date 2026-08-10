# Relatório de entrega — V7 Front-end

## Objetivo

A V7 remodela a experiência visual completa sem expandir regras de negócio.
O backend estabilizado na V6 foi preservado. As novas áreas que ainda não
possuem serviço real são exibidas como **prévia funcional**, sem gravar,
excluir ou alterar dados.

## Arquitetura de navegação

```text
Central da aplicação
└── Módulos
    ├── Analytics
    │   ├── Dashboard
    │   ├── Nova análise
    │   ├── Importações
    │   ├── Conjuntos de dados
    │   ├── Relatórios
    │   ├── Agendamentos
    │   ├── Modelos
    │   └── IA Assistente
    ├── Recursos Humanos
    ├── Financeiro
    ├── Estoque
    ├── Compras
    ├── Tecnologia
    ├── Marketing
    ├── Administrativo
    ├── Jurídico
    └── Comercial
```

## Design system

O arquivo `interface/tema.py` passou a concentrar a paleta, tipografia,
espaçamento e estilos ttk. `interface/componentes.py` oferece navegação,
cards, métricas, chips, cabeçalhos, botões e estados vazios reutilizáveis.

## Painéis departamentais

Cada departamento possui:

- menu interno específico;
- indicadores derivados do backend V6;
- atalhos contextuais;
- representação do fluxo operacional;
- lista das integrações planejadas;
- seção funcional de registros preservada;
- telas vazias seguras para funcionalidades futuras.

As definições ficam em `interface/configuracao_modulos_ui.py` e a renderização
adaptativa em `interface/painel_modulo.py`.

## O que continua funcional

- autenticação, sessão e perfis;
- multiempresa e multifilial;
- permissões por módulo;
- cadastros, edição, arquivamento, lixeira e restauração;
- paginação, pesquisa, filtros e ordenação;
- aprovações, notificações e auditoria;
- análise de arquivos locais;
- análise direta dos módulos internos;
- dashboards, qualidade, histórico, jobs e backup.

## Prévias sem backend nesta etapa

- Google Drive, OneDrive, bancos de dados e URL;
- Central de relatórios e agendamentos;
- IA Assistente;
- Workflow Builder visual;
- subseções profundas de cada departamento;
- integrações externas e serviços regulados.

Todo comando de prévia informa ao usuário que a integração está pendente.

## Validação

- compilação Python concluída;
- `tabnanny` sem problemas;
- testes de backend preservados;
- novos testes estruturais para a interface V7;
- validação visual final recomendada no Windows, ambiente nativo do projeto.
