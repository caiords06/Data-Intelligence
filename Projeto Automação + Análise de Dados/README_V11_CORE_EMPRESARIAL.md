# Data Intelligence V11 — CORE empresarial e operações configuráveis

A V11 transforma a plataforma em um ecossistema empresarial configurável. As áreas continuam possuindo serviços especializados, mas passam a compartilhar identidade, estrutura organizacional, colaboração, documentos, busca, segurança, eventos, workflows e metadados.

## Princípio de arquitetura

A universalidade nasce da configuração. Cada empresa pode definir tipos de registro, campos, etiquetas, dashboards, preferências, funções contextuais e regras sem criar uma nova tabela ou tela para cada variação do processo. O Servidor Corporativo permanece como autoridade transacional e o PostgreSQL é obrigatório em produção.

## CORE compartilhado

- empresas, filiais, unidades, departamentos e centros de custo;
- cadastro mestre de pessoas e seus papéis como colaborador, cliente, fornecedor ou contato;
- grupos, funções e permissões contextuais;
- tarefas, aprovações, comentários, notificações e caixa de entrada;
- calendário, eventos corporativos e outbox para webhooks assinados;
- documentos, imagens, versões, miniaturas, hashes, ACL e assinaturas;
- busca universal, histórico e auditoria de leitura;
- campos personalizados e etiquetas;
- dashboards e preferências por usuário, empresa e filial;
- importação e exportação CSV, JSON e XLSX;
- referências para credenciais em cofres externos, sem gravar o segredo no banco.

## Funcionário 360°

O cadastro diferencia Pessoa, Colaborador, Usuário, Permissões, Ativos e Acessos. A interface compõe dados pessoais, vínculo profissional, histórico, documentos, jornada, benefícios, folha, equipamentos, acessos, treinamentos, desempenho, tarefas, chamados, ocorrências, custos e auditoria.

As visões disponíveis são filtradas no serviço, antes de chegar à interface:

- `meu_perfil`: autoatendimento do colaborador;
- `gestor`: equipe, jornada, desempenho e pendências;
- `rh`: dados pessoais, vínculo, benefícios e remuneração;
- `ti`: identidade corporativa, equipamentos, sistemas, acessos e chamados;
- `auditor`: evidências e trilhas em modo somente leitura.

Fotos e anexos usam armazenamento gerenciado com validação de MIME e resolução, bloqueio de executáveis, AES-GCM, miniaturas, SHA-256, versão e auditoria.

## Operações departamentais

O provisionamento cria 108 tipos configuráveis e 12 modelos de fluxo para Financeiro, RH, Compras, Estoque, CRM, Comercial, Marketing, Administrativo, Jurídico, TI, Analytics, Automação/BPM e GED. Ao criar um registro, a plataforma instancia o workflow, cria tarefas e aprovações e publica eventos corporativos.

Os módulos especializados anteriores continuam disponíveis. A camada V11 é complementar: oferece uma linguagem operacional comum para processos que atravessam departamentos.

## Execução e produção

Consulte os guias de instalação e hardening existentes. Para produção, configure TLS, PostgreSQL, chaves mestras e cofre de credenciais; execute os testes de integração, backup/restauração, carga e o build do instalador em ambiente Windows limpo. Não use o modo SQLite legado fora de testes ou migração controlada.
