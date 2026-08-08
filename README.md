# 📊 Automação de Análise de Planilhas e Relatórios

Projeto desenvolvido em **Python** com o objetivo de automatizar o processo de obtenção, tratamento e análise de dados provenientes de planilhas, gerando relatórios de forma rápida e organizada e permitindo o envio das informações por e-mail.

A proposta da aplicação é reduzir tarefas manuais relacionadas à análise de planilhas, centralizando o processo em uma interface simples e intuitiva.

---

## 🚀 Sobre o projeto

Em muitas rotinas administrativas e empresariais, planilhas precisam ser baixadas, analisadas, tratadas e posteriormente encaminhadas para gestores ou outros responsáveis.

Esse processo pode consumir tempo e estar sujeito a erros humanos.

Este projeto busca automatizar esse fluxo.

A aplicação foi planejada para realizar etapas como:

* obtenção automática de planilhas;
* leitura e tratamento dos dados;
* identificação dos principais indicadores;
* análise dos valores encontrados;
* geração de um resumo das informações;
* preparação de relatórios;
* envio automático por e-mail;
* escolha do serviço de e-mail utilizado.

---

## 🎯 Objetivo

O principal objetivo do projeto é desenvolver uma solução capaz de transformar uma planilha bruta em informações relevantes para tomada de decisão.

O fluxo esperado da aplicação é:

```text
Google Drive
     ↓
Download da planilha
     ↓
Leitura dos dados
     ↓
Tratamento
     ↓
Análise
     ↓
Geração do resumo
     ↓
Relatório
     ↓
Envio por e-mail
```

---

## ⚙️ Funcionalidades

### 📥 Obtenção de planilhas

A aplicação poderá obter arquivos automaticamente a partir do **Google Drive**, eliminando a necessidade de realizar o download manualmente.

---

### 📊 Análise dos dados

Após carregar a planilha, o sistema realiza o tratamento das informações e identifica dados importantes para análise.

Dependendo do tipo de planilha, poderão ser analisados indicadores como:

* valores totais;
* médias;
* maiores valores;
* menores valores;
* quantidade de registros;
* diferenças entre períodos;
* variações percentuais;
* desempenho por categoria;
* desempenho por vendedor;
* desempenho por produto;
* desempenho por região;
* metas;
* resultados;
* possíveis inconsistências nos dados.

---

## 🧠 Geração de resumo

Após analisar as informações, a aplicação deverá gerar automaticamente um resumo com os principais resultados encontrados.

Exemplo:

```text
Resumo da análise

Total de vendas: R$ 325.400,00

Melhor resultado:
Região Sudeste

Produto com maior volume de vendas:
Produto A

Crescimento em relação ao período anterior:
12,4%

Foram identificados 3 registros que precisam de verificação.
```

O objetivo é permitir que o responsável consiga compreender rapidamente os principais acontecimentos apresentados na planilha.

---

## 📧 Envio de relatório

Após a análise, o usuário poderá encaminhar o relatório diretamente pela aplicação.

Inicialmente, o sistema está sendo desenvolvido para permitir integração com:

* Gmail
* Outlook

A própria interface permitirá escolher qual serviço será utilizado para realizar o envio.

---

## 🖥️ Interface

O projeto contará com uma interface gráfica para facilitar a utilização da automação.

A ideia é permitir que o usuário consiga realizar todo o processo sem precisar utilizar comandos diretamente no terminal.

Entre as opções previstas estão:

```text
Selecionar planilha

Selecionar origem do arquivo

Selecionar tipo de análise

Selecionar indicadores

Selecionar serviço de e-mail

Definir destinatário

Executar análise

Visualizar relatório

Enviar relatório
```

---

## 🛠️ Tecnologias

O projeto utiliza principalmente:

* Python
* Pandas
* Automação de processos
* Manipulação de arquivos Excel
* APIs e integrações externas
* Google Drive
* Gmail
* Outlook
* Git
* GitHub

Novas tecnologias poderão ser adicionadas conforme a evolução da aplicação.

---

## 📁 Estrutura do projeto

Uma possível organização da aplicação é:

```text
automacao-planilhas/
│
├── src/
│   │
│   ├── interface/
│   │
│   ├── services/
│   │
│   ├── analysis/
│   │
│   └── utils/
│
├── tests/
│
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── main.py
```

### `interface`

Responsável pela interface gráfica da aplicação.

### `services`

Responsável pelas integrações externas, como:

* Google Drive;
* Gmail;
* Outlook.

### `analysis`

Responsável pela leitura, tratamento e análise dos dados das planilhas.

### `utils`

Funções auxiliares utilizadas pelo restante da aplicação.

---

## 🔐 Segurança

Dados sensíveis não devem ser enviados para o repositório.

Arquivos contendo informações como:

```text
.env
credentials.json
token.json
client_secret.json
```

devem permanecer protegidos e adicionados ao arquivo `.gitignore`.

Credenciais, senhas, tokens e chaves de API nunca devem ser publicadas no GitHub.

---

## 📦 Instalação

Clone o repositório:

```bash
git clone https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
```

Entre na pasta:

```bash
cd SEU-REPOSITORIO
```

Crie um ambiente virtual:

```bash
python -m venv venv
```

Ative o ambiente virtual no Windows:

```bash
venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## ▶️ Execução

Para executar o projeto:

```bash
python main.py
```

---

## 🗺️ Roadmap

### Versão 1.0

* [x] Estrutura inicial do projeto
* [x] Leitura de planilhas
* [ ] Tratamento automático dos dados
* [ ] Análise de indicadores
* [ ] Geração automática de resumo
* [ ] Interface gráfica
* [ ] Integração com Google Drive
* [ ] Envio pelo Gmail
* [ ] Envio pelo Outlook
* [ ] Configuração personalizada dos indicadores
* [ ] Geração automática de relatórios

---

## 💡 Próximas melhorias

Entre as funcionalidades planejadas para versões futuras estão:

* identificação automática do tipo de planilha;
* escolha dinâmica dos indicadores;
* dashboard com os principais resultados;
* geração de gráficos;
* exportação de relatórios;
* histórico de análises;
* agendamento automático de análises;
* envio recorrente de relatórios;
* integração com diferentes fontes de dados;
* utilização de Inteligência Artificial para interpretação dos resultados.

---

## 📌 Status do projeto

🚧 **Em desenvolvimento**

Esta é a primeira versão do projeto.

Novas funcionalidades e melhorias serão adicionadas conforme o desenvolvimento da aplicação avançar.

---

## 👨‍💻 Autor

**Caio Rodrigues**

Desenvolvedor em formação com foco em desenvolvimento de software, automação, análise de dados e aplicações backend.

Tecnologias de interesse:

`Python` • `Java` • `SQL` • `Git` • `GitHub` • `Automação` • `APIs` • `Análise de Dados`

---

## 📄 Licença

Este projeto foi desenvolvido para fins de estudo, desenvolvimento profissional e criação de portfólio.

---

⭐ Se este projeto for útil ou interessante para você, considere deixar uma estrela no repositório.
