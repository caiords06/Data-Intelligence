# Relatório de otimização e revisão — Data Analytics Platform V3

## 1. Apontar todos os erros iniciais.

## 2. Resumo executivo

| Item | Antes | Depois |
|---|---:|---:|
| Linhas Python do projeto | 7.482 | 6.176 |
| `interface/app.py` | 2.533 linhas | 1.359 linhas |
| Dependências no `requirements.txt` | 65 | 4 diretas |
| Testes automatizados | inexistentes | 12 testes |
| Orquestrador independente da UI | não | sim |
| Processamento de planilhas fora da thread da UI | não | sim |
| Análise estrutural configurável | parcial | funcional |
| Qualidade configurável | parcial | funcional |
| Período selecionado pela interface | não controlava o cálculo | mensal/trimestral/semestral/anual |
| Dashboard por categoria | fixo em vendas | títulos adaptativos + motor de vendas |

O maior ganho arquitetural foi a retirada do pipeline analítico de dentro de `interface/app.py`. A interface deixou de executar diretamente leitura, consolidação, classificação, qualidade, indicadores e análise temporal. Essas responsabilidades agora são coordenadas por `core/orquestrador.py`.

---

## 3. Bugs e problemas corrigidos

### 3.1. Tkinter sendo acessado a partir de threads secundárias

**Problema:** o processamento e a automação utilizavam threads, mas métodos de atualização da interface chamavam `root.after()` a partir da própria thread secundária. Tkinter não é thread-safe e isso pode causar erros intermitentes, travamentos ou `RuntimeError: main thread is not in main loop`.

**Correção:** foi criada uma fila própria de eventos de UI (`fila_ui`). Threads de trabalho apenas colocam eventos na fila; `processar_logs()`, executado na thread principal, aplica as mudanças nos widgets.

**Motivo:** elimina uma classe de bugs difíceis de reproduzir e reduz o risco de congelamento da interface.

### 3.2. `app.py` concentrava o motor de dados inteiro

**Problema:** `selecionar_arquivos()` possuía aproximadamente 900 linhas e fazia seleção, leitura, validação, consolidação, classificação, análise estrutural, qualidade, indicadores, temporal e atualização visual.

**Correção:** criado `core/orquestrador.py`.

**Motivo:** a interface passa a cuidar da interface; o motor passa a cuidar de dados. Isso facilita testes, novas categorias e futuras fontes como Google Drive e URL.

### 3.3. Logs com linhas duplicadas e função morta

**Problema:** `adicionar_log()` já adicionava `\n`, e `processar_logs()` acrescentava outro `\n`. Havia também uma função interna `escrever()` não utilizada que, se chamada, se reagendaria indefinidamente.

**Correção:** removida a rotina morta e mantida somente a fila de logs com uma quebra de linha.

**Motivo:** logs mais limpos e menos código sem função.

### 3.4. Lista visual de arquivos não era sincronizada com arquivos recebidos da tela anterior

**Problema:** a análise recebia os arquivos e o label mostrava a quantidade, mas a `Listbox` do dashboard podia permanecer vazia.

**Correção:** criado `_atualizar_lista_arquivos()` e sincronização antes do processamento.

**Motivo:** o dashboard agora representa corretamente o estado real da análise.

### 3.5. “Adicionar arquivos” no dashboard substituía a seleção anterior

**Problema:** o botão visualmente indicava adição, mas o fluxo sobrescrevia a lista existente.

**Correção:** arquivos selecionados manualmente são combinados com os já existentes, removendo duplicatas.

**Motivo:** comportamento coerente com o texto do botão e com análise de múltiplos períodos.

### 3.6. Seleção de período não controlava a análise temporal

**Problema:** `Mensal`, `Trimestral`, `Semestral` e `Anual` eram enviados pela tela de preparação, mas a análise agrupava sempre por mês.

**Correção:** `analysis/temporal.py` passou a aceitar granularidade e aplicar agrupamento mensal, trimestral, semestral ou anual.

**Motivo:** a configuração da interface passa a ter efeito real no motor.

**Observação:** `Personalizado` ainda não possui campos de data inicial/final na interface. A opção agora gera aviso explícito e utiliza mensal como fallback, em vez de fingir que o intervalo personalizado foi aplicado.

### 3.7. Mapeamento semântico incorreto na análise temporal

**Problema:** o classificador produz um mapa no formato `coluna_original -> informação_semântica`, mas `analysis/temporal.py` tentava buscar diretamente `campos.get("data")` e `campos.get("valor")`. O exemplo de vendas funcionava apenas porque o fallback encontrava nomes como “Data” e “Valor”.

**Correção:** criado `criar_mapa_campos()` para inverter corretamente para `campo_semântico -> coluna_original`.

**Motivo:** análise temporal passa a funcionar também quando os nomes originais diferem dos nomes esperados.

### 3.8. Categoria definida manualmente deixava indicadores sugeridos da categoria automática

**Problema:** ao selecionar manualmente Financeiro, Estoque etc., apenas `classificacao["categoria"]` era alterado; os indicadores sugeridos ainda podiam ser os da categoria detectada automaticamente.

**Correção:** a classificação agora preserva `categoria_detectada` e `confianca_detectada`, mas substitui os indicadores sugeridos pela categoria definida pelo usuário.

**Motivo:** evita informações contraditórias na interface e no log.

### 3.9. Classificação de Recursos Humanos não existia no classificador

**Problema:** a interface oferecia “Recursos Humanos”, mas a estrutura de classificação não possuía essa categoria nem sugestões.

**Correção:** adicionados campos semânticos e pesos iniciais para colaboradores, setor, admissão, desligamento, salário e status, além de indicadores sugeridos de RH.

**Motivo:** alinha parcialmente o backend ao que a interface já oferece.

### 3.10. Indicadores de vendas podiam quebrar em grupos vazios

**Problema:** rankings acessavam `index[0]` sem verificar se o agrupamento possuía dados; valores não numéricos também podiam ser somados pelo `groupby` original.

**Correção:** conversão numérica explícita, remoção de inválidos, verificação de séries vazias e função segura para rankings.

**Motivo:** evita `IndexError`, concatenação acidental de strings e valores `NaN` chegando ao dashboard.

### 3.11. Qualidade não considerava strings vazias como dados ausentes

**Problema:** `""` ou strings contendo apenas espaços não eram consideradas ausentes por `isna()`.

**Correção:** o diagnóstico passou a combinar `NaN/None` com strings vazias ou somente espaços.

**Motivo:** score de qualidade mais próximo da qualidade real da planilha.

### 3.12. Colunas técnicas distorciam o diagnóstico de qualidade

**Problema:** colunas como `arquivo_origem`, `periodo_origem`, `ano_origem` etc. são adicionadas pelo próprio sistema. Elas podiam impedir a identificação de duplicidades ou reduzir a completude quando o período não era identificado.

**Correção:** o módulo de qualidade avalia, por padrão, somente colunas de negócio.

**Motivo:** a qualidade deve medir a fonte de dados, não metadados criados pela plataforma.

### 3.13. Duplicidades entre arquivos iguais eram mascaradas

**Problema:** duas linhas de negócio idênticas vindas de arquivos diferentes deixavam de ser consideradas duplicadas porque `arquivo_origem` era diferente.

**Correção:** colunas técnicas foram removidas da chave de duplicidade.

**Motivo:** duplicidades reais passam a ser detectadas mesmo entre múltiplos arquivos.

### 3.14. Compatibilidade exigia a mesma ordem das colunas

**Problema:** dois arquivos com exatamente as mesmas colunas, mas em ordem diferente, eram rejeitados.

**Correção:** compatibilidade compara o conjunto de colunas. Na consolidação, cada DataFrame é realinhado para a ordem do arquivo de referência.

**Motivo:** ordem visual das colunas não deve tornar arquivos estruturalmente incompatíveis.

### 3.15. Metadados de período incorretos em arquivos com vários meses

**Problema:** quando um arquivo continha vários meses, `mes_origem`, `ano_origem`, trimestre e semestre eram preenchidos com base na primeira data do arquivo para todas as linhas.

**Correção:** quando existe coluna de data, os metadados são derivados linha a linha durante a consolidação.

**Motivo:** preservação correta da origem temporal de cada registro.

### 3.16. Ano inexistente no nome do arquivo era inventado

**Problema:** um arquivo como `Vendas - Jan.xlsx`, sem coluna de data e sem ano no nome, recebia automaticamente o ano corrente.

**Correção:** o sistema retorna `01/????` e `ano=None`.

**Motivo:** é melhor declarar desconhecimento do que introduzir um dado temporal falso.

### 3.17. Banco SQLite deixava conexões abertas

**Problema:** `with sqlite3.Connection` gerencia commit/rollback, mas não garante o fechamento da conexão. Os testes identificaram `ResourceWarning: unclosed database`.

**Correção:** `auth/banco.py` ganhou um context manager explícito que executa commit/rollback e sempre fecha a conexão.

**Motivo:** evita vazamento de recursos e possíveis locks futuros no SQLite.

### 3.18. Arquivos de pacote estavam nomeados `___init__.py`

**Problema:** existiam arquivos com três underscores antes de `init`, em vez de `__init__.py`.

**Correção:** todos os pacotes receberam `__init__.py` correto.

**Motivo:** torna a estrutura Python explícita e consistente, evitando dependência acidental de namespace packages.

### 3.19. `requirements.txt` continha o ambiente inteiro e estava em UTF-16

**Problema:** havia 65 pacotes, muitos ligados a Jupyter/IPython e ferramentas que não são dependências da aplicação. Além disso, `.xls` era anunciado como suportado, mas `xlrd` não estava listado.

**Correção:** criado `requirements.txt` UTF-8 com somente quatro dependências diretas:

```text
pandas>=2.2,<4
openpyxl>=3.1,<4
xlrd>=2.0,<3
selenium>=4.20,<5
```

**Motivo:** instalação mais previsível, rápida e reproduzível.

### 3.20. Selenium era uma dependência obrigatória até para análise local

**Problema:** imports de Selenium no topo da interface/driver faziam o projeto falhar na importação se Selenium não estivesse instalado, mesmo que o usuário quisesse apenas analisar planilhas locais.

**Correção:** imports de Selenium foram tornados tardios e usados apenas na automação web.

**Motivo:** desacopla a análise local da automação do navegador.

### 3.21. `winreg` impedia importação fora do Windows

**Problema:** `sistema/idbrowser.py` importava `winreg` ao carregar o módulo.

**Correção:** import tardio somente dentro da função de detecção, com erro explícito em SO não Windows.

**Motivo:** módulos de dados e testes podem ser executados sem depender do Windows.

### 3.22. Detecção do navegador possuía caminho de registro frágil

**Problema:** havia uma única chave de registro esperada.

**Correção:** adicionados fallbacks para associações HTTP/HTTPS do Windows.

**Motivo:** aumenta robustez em diferentes configurações do Windows.

### 3.23. Estado visual de indicadores ativo/desativado

**Problema:** `0` podia significar tanto “resultado zero” quanto “módulo não executado”. Também existia risco de repetir “Produto líder” dentro do label após a separação visual entre título e valor.

**Correção:** indicadores desativados usam `—`; mensagens de desativação continuam amarelas; títulos permanecem independentes e brancos; quando ativos, apenas nome/valor são atualizados.

**Motivo:** diferencia ausência de cálculo de resultado igual a zero.

### 3.24. Dashboard fixo em vendas para categorias sem motor específico

**Problema:** ao definir Financeiro, Estoque, Cadastro ou RH, os cards continuavam com títulos de vendas.

**Correção:** títulos dos quatro cards e dois destaques agora são adaptados à categoria. Somente o motor de indicadores de vendas está implementado; categorias sem motor mostram `—` e “Sem indicador específico”.

**Motivo:** evita apresentar semântica de vendas para bases de outro tipo e prepara o dashboard adaptativo.

### 3.25. Fontes Google Drive e URL eram selecionáveis sem implementação real

**Problema:** a interface permitia selecionar uma fonte que o backend ainda não sabe buscar.

**Correção:** a preparação bloqueia o processamento dessas fontes com mensagem clara.

**Motivo:** evita uma falsa impressão de funcionalidade pronta.

### 3.26. Checkbox de IA podia sugerir execução de IA inexistente

**Problema:** a configuração era enviada, mas nenhum provedor/modelo de IA está integrado.

**Correção:** o pipeline registra explicitamente que a IA foi solicitada, mas que a análise continuará pelo motor local desta versão.

**Motivo:** comportamento transparente até a implementação da V6.

### 3.27. `main.py` executava a aplicação ao ser importado

**Problema:** criação do `Tk()` e `mainloop()` aconteciam no nível global.

**Correção:** criada função `main()` protegida por `if __name__ == "__main__":`.

**Motivo:** permite importar o projeto em testes e ferramentas sem abrir a interface automaticamente.

---

## 4. Arquitetura após a revisão

Fluxo principal atual:

```text
TelaNovaAnalise
      │
      ▼
configuração
      │
      ▼
AplicacaoAutomacao
      │
      ▼
thread de processamento
      │
      ▼
core/OrquestradorAnalise
      │
      ├── leitura
      ├── compatibilidade
      ├── consolidação
      ├── análise estrutural
      ├── qualidade
      ├── classificação
      ├── indicadores por categoria
      └── análise temporal
      │
      ▼
resultado_analise
      │
      ▼
fila de eventos da UI
      │
      ▼
Dashboard
```

A regra central agora é: **Tkinter não executa regras de negócio e o motor de dados não manipula widgets**.

---

## 5. Arquivos criados

| Arquivo | Finalidade |
|---|---|
| `core/__init__.py` | Define o pacote de orquestração. |
| `core/orquestrador.py` | Pipeline principal independente da interface. |
| `tests/__init__.py` | Pacote de testes. |
| `tests/test_data_engine.py` | Testes de classificação, indicadores, qualidade, períodos, CSV e consolidação. |
| `tests/test_auth.py` | Testes de senha, autenticação e SQLite. |
| `RELATORIO_OTIMIZACAO.md` | Este relatório. |
| `*/__init__.py` | Substituem os antigos `___init__.py`. |

---

## 6. Arquivos modificados e motivo

| Arquivo | Mudanças principais |
|---|---|
| `main.py` | Entry point limpo e importável. |
| `interface/app.py` | Remoção do motor analítico da UI, fila thread-safe, processamento em background, atualização de arquivos, dashboard adaptativo e limpeza de logs. |
| `interface/nova_analise.py` | Validação de fontes não implementadas e correção visual do status. |
| `interface/login.py` | Remoção de import não utilizado. |
| `dados/analisador.py` | Validação de entrada, estatísticas robustas e remoção de dependência direta de NumPy. |
| `dados/estrutural.py` | Inferência temporal mais robusta e saída estrutural consolidada. |
| `dados/qualidade.py` | Strings vazias, duplicidade de negócio, exclusão de metadados e score. |
| `dados/leitor.py` | CSV robusto, compatibilidade por conjunto, realinhamento e período por linha. |
| `dados/periodos.py` | Sem invenção de ano e suporte a arquivo com múltiplos períodos. |
| `dados/classificador.py` | Mapeamento pré-normalizado, mapa semântico reverso, RH e indicadores sugeridos por categoria. |
| `dados/indicadores.py` | Cálculos seguros, conversão numérica e dispatcher de motores. |
| `analysis/temporal.py` | Correção semântica e granularidades configuráveis. |
| `auth/banco.py` | Fechamento garantido de conexão e validações SQLite. |
| `auth/autenticacao.py` | Fluxo simplificado, erros encadeados e validação de login. |
| `auth/seguranca.py` | Constantes de scrypt e verificação resiliente. |
| `auth/sessao.py` | Simplificação sem mudar a API. |
| `automacao/driver.py` | Selenium opcional/lazy e nomes de navegador normalizados. |
| `sistema/idbrowser.py` | `winreg` lazy e fallback de registro. |
| `sistema/iduser.py` | `LOCALAPPDATA` com fallback seguro. |
| `sistema/opsystemcheck.py` | Mensagem específica para automação web. |
| `requirements.txt` | 65 dependências → 4 dependências diretas; UTF-8; adicionado `xlrd`. |
| `.gitignore` | Permite versionar apenas dados fictícios de `dados_exemplo/`. |
| `README.md` | Status V3, arquitetura/estrutura atual e roadmap atualizado. |

As telas `principal.py`, `usuarios.py`, `primeiro_acesso.py` e `tema.py` foram preservadas funcionalmente porque não apresentaram bugs críticos nos fluxos revisados.

---

## 7. Validações executadas

### Sintaxe e indentação

```text
python -m compileall -q .     OK
python -m tabnanny .          OK
```

Todos os módulos Python compilam. Não foram detectadas inconsistências de tabs/espaços capazes de gerar erro de indentação.

### Imports

Foram importados individualmente os módulos principais, incluindo `main`, `interface.app`, autenticação, dados, orquestrador, automação e sistema. Resultado: **OK**.

### Testes automatizados

```text
Ran 12 tests
OK
```

Cobertura funcional dos testes criados:

- hash e validação de senha;
- autenticação em SQLite temporário;
- desativação de usuário;
- classificação automática de vendas;
- indicadores do arquivo real de exemplo;
- módulos analíticos independentes;
- categoria definida manualmente;
- compatibilidade com colunas em ordem diferente;
- detecção de string vazia e duplicidade entre origens;
- arquivo com mês sem ano;
- CSV separado por ponto-e-vírgula;
- metadados de período derivados linha a linha;
- análise temporal trimestral e semestral.

### Smoke tests de interface com Tkinter

A interface foi executada em ambiente gráfico virtual e o pipeline foi aguardado até a conclusão.

**Cenário vendas / indicadores ativos:** OK

```text
Faturamento:   R$ 2.917.311,00
Vendas:        3.787
Itens:         15.227
Produto líder: Terno Linho
Loja líder:    Iguatemi Campinas
```

**Cenário indicadores desativados:** OK — cards exibem `—` e mensagem amarela.

**Cenário categoria manual Financeiro:** OK — dashboard muda os títulos e não apresenta valores falsos de vendas.

---

## 8. Pontos que permanecem propositalmente pendentes

Estes itens não foram simulados nem “fingidos” como prontos:

1. **Indicadores específicos de Financeiro, Estoque, Cadastro e RH:** a arquitetura está preparada, mas somente Vendas possui motor matemático completo atualmente.
2. **Google Drive e URL:** continuam no roadmap; a interface agora informa que ainda não estão implementados.
3. **Período personalizado:** ainda falta criar os controles de data inicial/final. Atualmente há fallback mensal com aviso.
4. **IA:** checkbox/configuração existe, mas não há provedor/modelo integrado; o log deixa isso explícito.
5. **Tratamento automático de dados:** V3 já diagnostica, mas ainda não altera automaticamente dados inválidos, outliers ou tipos incorretos.
6. **Automação web:** permanece Windows + Selenium e continua separada do motor analítico.
7. **Dashboard plenamente dinâmico:** os títulos já se adaptam à categoria, mas os componentes ainda são quatro cards fixos até existirem motores suficientes para gerar layouts por schema de resultado.

---

## 9. Segurança e distribuição

- O banco `storage/app.db` foi **preservado no ZIP otimizado** para não apagar o acesso local já existente.
- `storage/` continua no `.gitignore`, portanto o banco não deve ser versionado no GitHub.
- `.git` não foi incluído no ZIP otimizado. Isso evita transportar metadados internos do repositório e deixa o pacote mais limpo. Para atualizar o repositório existente, copie/substitua os arquivos do ZIP dentro da pasta do projeto que já contém seu `.git`.
- Senhas continuam armazenadas com `scrypt` + salt aleatório, sem senha em texto puro.

---

## 10. Próxima evolução recomendada

A base agora está em condição melhor para avançar sem voltar a inflar `app.py`. A próxima rodada deveria continuar no backend:

```text
V3 restante
├── validação de tipos
├── tratamento de datas
├── tratamento numérico
├── inconsistências
└── outliers

V4
├── motor financeiro
├── motor de estoque
├── motor de cadastro
├── motor de RH
├── indicadores universais
└── schema de dashboard adaptativo
```

A recomendação é não adicionar IA, Gmail ou Google Drive ao motor central antes de finalizar esses contratos de dados. O projeto já possui agora o ponto de extensão correto: `core/orquestrador.py`.

---

## 11. Conclusão

O projeto continua visualmente e funcionalmente reconhecível, mas o núcleo foi alterado de uma aplicação Tkinter que concentrava a lógica para uma arquitetura em que **interface, orquestração e análise de dados têm responsabilidades separadas**.

A revisão não se limitou a “formatar” o código: foram corrigidos bugs de threading, períodos, duplicidades, SQLite, dependências, classificação manual, semântica temporal e sincronização visual. Também foram adicionados testes para impedir que as correções principais regressem nas próximas versões.
