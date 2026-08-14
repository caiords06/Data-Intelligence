# Auditoria funcional V10.1.1 — pós-login, Server First e PostgreSQL

Data: 12/08/2026

## Sintoma investigado

Após autenticação bem-sucedida, a janela permanecia preenchida apenas pelo fundo escuro e o título continuava `Data Intelligence · Acesso corporativo · V10.1.1`.

## Causa raiz reproduzida

O login remoto concluía normalmente, porém o fluxo seguinte executava `main.py -> abrir_principal() -> preparar_tela() -> garantir_contexto_sessao()`. A implementação de `enterprise/contexto.py` ainda utilizava `auth.banco.conectar()` na Central/Cliente. Como, por arquitetura, a estação remota não possui a senha do PostgreSQL, a validação falhava antes da construção de `TelaPrincipal`. O código antigo já havia destruído o login, deixando apenas a janela raiz com o fundo aplicado.

## Correções aplicadas

1. `enterprise/contexto.py`
   - Central/Cliente obtêm empresa, filial, usuário e permissões exclusivamente do bootstrap autenticado do Servidor Corporativo.
   - Nenhuma conexão PostgreSQL é aberta diretamente na estação.
   - Não existe fallback para SQLite/banco local.
   - Escopo congelado de ator e permissões foram adaptados ao contexto remoto.

2. `interface/login.py`
   - O login não é destruído antes de a tela de destino validar sessão/contexto.
   - Uma falha de servidor deixa a tela atual recuperável, em vez de produzir uma janela vazia.

3. `main.py`
   - `garantir_contexto_sessao()` ocorre antes de `limpar_janela()`.
   - O binding `<Return>` do login é removido durante troca de tela.
   - Foi instalado `report_callback_exception` do Tk.
   - Exceções de callback são registradas em `logs/desktop.jsonl`.
   - Se uma falha ocorrer após uma limpeza de tela, a aplicação monta uma tela de recuperação com “TENTAR NOVAMENTE” e “SAIR DA SESSÃO”.
   - O watchdog de sessão continua sendo reagendado quando o servidor/preferências ficam temporariamente indisponíveis.
   - A rotina periódica de backup também não morre por erro de configuração transitório.

4. RPC e arquivos — Central/Cliente -> Servidor Corporativo
   - Foi criado `core/rpc_arquivos.py` para operações com arquivo.
   - Importações de documentos/extratos/datasets usam upload binário em streaming.
   - Relatórios, PDFs, contracheques e arquivos gerados no servidor usam download binário controlado.
   - O servidor substitui o parâmetro `ator` pelo ator autenticado da sessão bearer; a estação não consegue forjar empresa/filial/usuário.
   - O servidor valida allowlist, tamanho de upload, SHA-256, nome seguro e diretório autorizado.
   - Arquivos temporários de entrada são removidos ao final da operação.
   - Downloads transitórios na estação são registrados para limpeza ao encerrar o processo.

5. Analytics / datasets
   - “Usar dataset” não tenta mais abrir o caminho físico do Servidor Corporativo como se fosse um caminho local da Central.
   - Em modo remoto, o dataset é baixado apenas quando necessário para a análise e usado como cópia transitória.

6. Backup
   - O botão “Criar backup verificado” não solicita mais uma pasta local quando a estação está conectada.
   - O backup é criado, verificado e catalogado no Servidor Corporativo.
   - A resposta remota não expõe o caminho físico do filesystem do servidor.

7. PostgreSQL / persistência
   - PostgreSQL permanece o backend obrigatório de produção.
   - SQLite permanece somente em rotas explícitas de migração/testes legados.
   - Central/Cliente não executam bootstrap de schema, histórico ou enterprise local.
   - Preferências corporativas e histórico permanecem no backend remoto.
   - `node.json`, logs, credenciais protegidas do próprio servidor, arquivos temporários e exportações escolhidas pelo usuário são dados técnicos/transitórios; não constituem banco corporativo local.

8. Instalador / release
   - Mantidas as correções anteriores de configuração PostgreSQL e do `Type mismatch` do Inno Setup.
   - Validadores estáticos V10 e V10.1 aprovados.

## Verificações executadas

### Compilação Python

`python -m compileall -q .` — aprovado.

### Suíte padrão

Resultado consolidado após as correções desta auditoria:

- 303 testes aprovados;
- 16 testes ignorados;
- 0 falhas.

Os ignorados são testes condicionais que exigem PostgreSQL real ou flags/display gráfico específicos.

### Tk gráfico real

Executado sob Xvfb:

- 24 testes gráficos aprovados;
- 79 subtestes gráficos aprovados;
- 0 falhas.

### Fluxo exato do problema

Foi executado um smoke dedicado com Tk real simulando:

`TelaLogin -> autenticação -> SESSAO -> garantir_contexto_sessao remoto -> limpar login -> TelaPrincipal`

Resultado:

`LOGIN_TRANSITION_OK 1 Data Intelligence · Enterprise Platform · V10.1.1`

Isso confirma que a transição não termina mais na janela vazia e que o título é atualizado para a aplicação principal.

### Capturas de interface

A bateria visual essencial gerou 38 PNGs. O relatório automático classificou 36 como aprovados, 2 como alertas de baixa variedade visual e 0 como rejeitados. Não houve tela principal vazia nas capturas renderizadas.

### Transporte HTTP de arquivo

Foi executado teste ponta a ponta do endpoint HTTP especializado de upload com Servidor Corporativo real no ambiente de teste:

`FILE_RPC_HTTP_OK 1 True`

O fluxo cobriu upload -> armazenamento controlado -> metadados -> verificação de integridade.

### Instalador

- `scripts/verificar_instalador_v10.py` — aprovado.
- `scripts/verificar_instalador_v10_1.py` — aprovado.

## Limitações do ambiente de auditoria

O ambiente usado nesta auditoria possui Python 3.13.5 e não possui `psycopg` nem um servidor PostgreSQL real instalado. O próprio projeto exige Python 3.14 para o build oficial V10.1.1. Portanto, o teste de integração que realmente abre uma instância PostgreSQL foi corretamente mantido como `skip` neste ambiente; não foi simulada uma aprovação inexistente.

No computador Windows de build/servidor, use Python 3.14 e execute o teste PostgreSQL com uma instância real antes da publicação final.

## Build recomendado

Na raiz do projeto, no Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_distribuicao_windows.ps1
```

Esse é o build completo. Ele recria a distribuição e gera o Setup unificado no final.

## Diagnóstico caso uma falha futura ocorra

A aplicação não deve mais permanecer silenciosamente em tela vazia. Falhas não tratadas da interface são mostradas ao usuário e registradas em:

`<pasta de dados do Data Intelligence>\logs\desktop.jsonl`

Esse arquivo deve ser o primeiro artefato coletado em um novo erro pós-login.
