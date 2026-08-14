# Data Intelligence V9.4 — Refatoração Arquitetural + Navegação Unificada

A V9.4 preserva o comportamento funcional da V9.3 e remove uma fonte importante de inconsistência visual e de navegação: módulos especializados possuíam dois componentes diferentes para representar a mesma área departamental.

## Navegação canônica

A partir desta versão, `interface/navegacao_modulos.py` é a autoridade de navegação dos módulos. Ele centraliza:

- normalização de aliases de rotas antigas;
- escolha do renderizador adequado;
- construção da leftbox departamental;
- callbacks de seção encaminhados ao roteador principal.

Financeiro, RH, Estoque, Compras e Tecnologia usam uma única tela especializada tanto na Visão geral quanto nas seções internas. Por isso a leftbox não troca de estrutura ao navegar.

Aliases preservados:

- Financeiro: `registros -> lancamentos`;
- RH: `registros -> colaboradores`;
- Estoque: `registros -> itens`;
- Compras: `registros -> solicitacoes`;
- TI: `visao` e `registros` são resolvidos conforme a permissão do usuário, preservando o portal público de suporte.

Marketing, Administrativo, Jurídico e Comercial continuam usando seus renderizadores visuais, mas compartilham a mesma fábrica de sidebar e os mesmos callbacks canônicos.

## Validação visual

O catálogo de screenshots não usa mais uma tela diferente da aplicação para a Visão geral de departamentos especializados. Agora os prints exercitam exatamente os mesmos componentes usados pelo `main.py`.

O capturador também repete automaticamente um frame quando `ImageGrab` devolve uma imagem totalmente preta durante uma troca de tela.

Para gerar todas as telas:

```powershell
python scripts/gerar_capturas_interface.py --escopo completo --largura 1600 --altura 900 --falhar-em-erro
```

Somente Tecnologia:

```powershell
python scripts/gerar_capturas_interface.py --escopo completo --grupo Tecnologia --largura 1600 --altura 900 --falhar-em-erro
```

## Release

A cadeia de release reproduzível introduzida na V9.3 permanece obrigatória. Não compacte a pasta do projeto manualmente. Gere o source ZIP com:

```powershell
python scripts/empacotar_fonte_limpa.py
```

## Fronteiras de arquitetura

A V9.4 também cria duas fronteiras para reduzir o acoplamento sem reescrever as regras já homologadas:

```text
Interface Tkinter
       ↓
services/departamentos
       ↓
enterprise (regras de domínio)
       ↓
enterprise/repositories
       ↓
SQLite atual / provider futuro
```

As telas especializadas de Financeiro, RH, Estoque, Compras e Tecnologia passam a importar operações pela camada `services/departamentos`. Os cinco domínios deixam de importar `auth.banco.conectar` diretamente e usam o gateway `enterprise.repositories`.

Nesta versão o provider padrão continua sendo SQLite para preservar compatibilidade. A mudança cria um ponto controlado para a futura transição para PostgreSQL/API corporativa sem alterar simultaneamente centenas de chamadas da interface.
