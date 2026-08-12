# Relatório de evolução — Data Analytics Platform V3.2

## Objetivo

A V3.2 conclui o núcleo de qualidade e tratamento seguro de dados. O pipeline
agora diferencia claramente a fonte original da cópia utilizada nas análises,
mantém um relatório de auditoria e não remove registros automaticamente.

## Implementações

### 1. Tratamento auditável

Foi criado `dados/tratamento.py`, responsável por:

- normalizar nomes de colunas para `snake_case`;
- resolver colisões de nomes sem descartar colunas;
- remover espaços excedentes em textos;
- converter marcadores como `N/A`, `null` e campos vazios em ausência real;
- converter números brasileiros, incluindo moeda e separadores de milhar;
- converter datas com preferência pelo formato dia/mês/ano;
- registrar quantidades convertidas, inválidas e ajustadas.

O DataFrame recebido nunca é modificado diretamente. O resultado do
orquestrador contém `dataframe_original`, `dataframe` e `tratamento`.

### 2. Inconsistências e outliers

Foi criado `dados/inconsistencias.py`, com diagnóstico de:

- valores negativos em campos naturalmente não negativos;
- datas futuras;
- desligamento anterior à admissão;
- variações textuais equivalentes, como diferenças de caixa e acentuação;
- possíveis outliers numéricos pelo método IQR.

Outliers são apenas sinalizados. Nenhum valor é removido ou substituído.

### 3. Score de qualidade ampliado

O relatório de qualidade passou a considerar cinco dimensões:

- completude;
- unicidade;
- presença de colunas válidas;
- validade de tipos;
- consistência.

Os outliers permanecem informativos e não reduzem automaticamente o score.

### 4. Interface e orquestração

A tela de configuração ganhou a opção `Tratamento e validação`. O orquestrador
executa o tratamento antes da classificação, dos indicadores e da análise
temporal. O dashboard apresenta o nível e o score de qualidade ao concluir.

### 5. Privacidade e configuração

O banco local foi removido do pacote de trabalho. A URL de validação do
Selenium deixou de conter um endereço particular e agora pode ser definida
pela variável de ambiente `AUTOMACAO_URL_VALIDACAO`, usando
`https://example.com` como valor seguro de demonstração.

As duas cópias binariamente idênticas da planilha de demonstração também foram
retiradas. A pasta `dados_exemplo` mantém somente uma base de vendas.

O ciclo de vida do Selenium foi reforçado: uma instância anterior é encerrada
antes de uma nova validação, falhas fecham o driver criado e o navegador é
encerrado quando a janela principal da aplicação é fechada.

## Validação

- compilação completa dos módulos;
- verificação de indentação com `tabnanny`;
- importação dos módulos sem efeitos colaterais;
- 18 testes automatizados aprovados;
- execução ponta a ponta com a planilha de vendas;
- preservação dos mesmos indicadores financeiros da V3.1;
- nenhuma linha removida pelo tratamento.

## Próxima versão sugerida

A V4 deve iniciar os motores analíticos específicos para Financeiro, Estoque,
Cadastro e Recursos Humanos, além de indicadores universais e comparações.
