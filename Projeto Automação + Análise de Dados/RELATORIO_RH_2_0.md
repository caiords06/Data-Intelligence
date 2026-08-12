# Entrega — Workspace Recursos Humanos 2.0

## Resultado

O módulo de Recursos Humanos foi reconstruído como um workspace
departamental especializado. O cadastro simples das versões anteriores foi
preservado como origem legada, enquanto as novas operações passaram a usar um
domínio `rh_*` próprio, multiempresa, multifilial, auditável e protegido por
permissões por ação.

O Financeiro 2.0 e os demais departamentos não foram substituídos. A integração
ocorre por tarefas, aprovações, notificações, documentos, atividades e pelo
motor analítico central.

## Interface

A sidebar especializada foi reorganizada em grupos recolhíveis:

- Recursos Humanos: Visão geral;
- Pessoas: Colaboradores, Admissões, Desligamentos e Movimentações;
- Jornada: Ponto e jornada, Férias e ausências;
- Remuneração: Benefícios, Folha e custos, Cargos e salários;
- Talentos: Recrutamento, Desempenho, Treinamentos, Carreira e PDI;
- Gestão: Documentos, Solicitações, Relatórios, Auditoria e Configurações RH.

A Visão geral apresenta headcount, ativos, departamentos, folha base,
pré-admissões, desligamentos, férias e tarefas pendentes. Também exibe
atalhos operacionais, jornada do colaborador e pontos de atenção.

As tabelas possuem pesquisa, divisórias recalculadas, estado vazio em primeiro
plano e ações contextuais. O perfil do colaborador separa dados profissionais,
pessoais, remuneração, dependentes, histórico, benefícios, equipamentos e
documentos.

## Cadastro mestre

O cadastro especializado armazena:

- matrícula, nome completo e nome social;
- CPF, RG, nascimento e dados de contato;
- empresa, filial, departamento e centro de custo;
- cargo, gestor, contrato, modalidade e jornada;
- admissão, experiência, status e etapa da jornada;
- remuneração em centavos inteiros e dados bancários;
- dependentes, benefícios, equipamentos, documentos e histórico profissional.

Alterações relevantes geram registro antes/depois no histórico profissional
e na auditoria empresarial.

## Admissão

O processo possui oito etapas persistidas, checklist, benefícios, onboarding,
assinatura e responsável. Ao iniciar uma admissão, o sistema cria tarefas para:

- RH: documentos, contrato e benefícios;
- TI: conta, e-mail e acessos;
- Estoque: equipamentos e termos de entrega;
- Administrativo: crachá e estrutura.

Na conclusão, o colaborador passa para Ativo e a jornada é atualizada.

## Desligamento

O desligamento registra tipo, motivo, data prevista, checklist e entrevista de
saída. São criadas tarefas para RH, Financeiro, TI, Estoque e Administrativo.
O processo não pode ser concluído enquanto tarefas obrigatórias estiverem
pendentes, evitando revogações ou devoluções incompletas.

## Jornada, férias e ausências

O ponto calcula minutos trabalhados, extras e atrasos a partir das marcações.
Férias e ausências mantêm período, dias, saldo, abono, motivo, anexo e status.
Períodos conflitantes para o mesmo colaborador são bloqueados. Toda solicitação
gera uma aprovação central e pode ser aprovada ou rejeitada pelo RH autorizado.

## Remuneração e folha

Benefícios possuem fornecedor, elegibilidade, custo da empresa e desconto do
colaborador. A folha é aberta por competência e recebe eventos de provento,
desconto e encargo. Os totais são recalculados em centavos inteiros.

Ao fechar uma folha:

- o status torna-se Fechada;
- usuário e horário ficam registrados;
- uma tarefa é criada para a provisão no Financeiro;
- contracheques individuais podem ser gerados em PDF;
- caminho e hash SHA-256 do contracheque ficam persistidos.

O cálculo implementado é operacional, baseado em eventos informados. Ele não
substitui folha legal, motor fiscal, eSocial ou validação de especialista.

## Talentos

O workspace inclui:

- cargos, níveis, responsabilidades, competências e faixas salariais;
- vagas com aprovação central, quantidade, motivo e responsável;
- candidatos e etapas do funil seletivo;
- ciclos de avaliação, notas, competências e feedback;
- PDI com objetivo, ações, prazo e progresso;
- catálogo de treinamentos, obrigatoriedade, validade, custo e inscrições.

## Documentos e patrimônio

O GED de RH copia documentos para o armazenamento gerenciado e registra
categoria, vínculo, versão, classificação, validade, assinatura e hash SHA-256.
A interface permite verificar se o arquivo existe e se continua íntegro.

Equipamentos podem ser vinculados ao colaborador por patrimônio, origem,
data de entrega e termo documental. A devolução é auditável.

## Segurança

Foram adicionados perfis especializados:

- Diretoria de RH;
- Analista de RH;
- Gestor de pessoas;
- Colaborador;
- Auditor de RH.

Além da permissão do módulo, o RH possui permissões por ação. Dados
pessoais, bancários e de remuneração não são liberados automaticamente a
perfis externos ao RH. O colaborador consulta somente o próprio cadastro e o
gestor consulta apenas o próprio perfil e sua equipe direta.

A IA/Análise de RH apenas explica, alerta e recomenda. Contratação,
desligamento, alteração salarial e fechamento de folha continuam exigindo
ação humana autorizada.

## Analytics e relatórios

O Analytics central recebe o universo autorizado do novo cadastro de RH, sem
o limite silencioso de 1.000 registros. A remuneração é removida do DataFrame
quando o ator não possui permissão.

Relatórios de colaboradores, férias e folha podem ser gerados em PDF, XLSX ou
CSV. O agendamento fica persistido; a entrega externa depende da configuração
futura de um provedor de e-mail autorizado.

## Compatibilidade e migrações

As migrações `006_rh_departamental` e `007_rh_2_0_complementos` são
idempotentes. Colaboradores do cadastro legado são espelhados com IDs
negativos e referência de origem, sem alterar ou apagar a tabela anterior.
Novos registros criados pela API genérica também são sincronizados.

## Validação

- 99 testes automatizados aprovados;
- 7 smoke tests de Tkinter mantidos com execução condicionada a display;
- compilação de todos os arquivos Python aprovada;
- análise de indentacão com `tabnanny` aprovada;
- regressão do Financeiro 2.0 e dos demais módulos aprovada.

## Limites deliberados

Não são apresentados como concluídos:

- cálculo oficial de folha, rescisão, encargos, tributos ou eSocial;
- assinatura digital homologada;
- envio real por Gmail/Microsoft/SMTP sem credenciais e OAuth;
- integração bancária, fiscal ou governamental;
- medicina e segurança do trabalho regulatória;
- portal web externo ou aplicativo móvel.

Esses recursos exigem regras legais versionadas, integrações homologadas,
credenciais e validação especializada antes de uso com dados reais.
