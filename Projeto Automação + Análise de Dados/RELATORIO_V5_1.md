# Relatório de estabilização — Enterprise Platform V5.1

## Objetivo

A V5.1 preserva o backend empresarial da V5 e concentra mudanças em
estabilidade, autorização, navegação e consistência visual.

## Navegação

Os atalhos Central analítica e Nova análise foram removidos da sidebar. O fluxo
oficial passou a ser:

```text
Módulos → Central analítica → Nova análise
```

O Cockpit e a tela de resultados também deixaram de oferecer acessos diretos
que ignoravam essa hierarquia. Rotas internas continuam protegidas no backend.

## Perfis departamentais

Foram adicionados perfis base para RH, Financeiro, Estoque, Compras, TI,
Marketing, Administrativo, Jurídico e Comercial. Cada perfil acessa somente seu
departamento. As versões `+` combinam áreas relacionadas, por exemplo:

- RH+ → RH e Financeiro;
- Estoque+ → Estoque e Compras;
- Marketing+ → Marketing e Comercial;
- Jurídico+ → Jurídico e Financeiro.

O perfil Analista acessa o Analytics. Administradores mantêm acesso integral.
Permissões personalizadas por empresa continuam disponíveis e aprovações não
são concedidas automaticamente.

## Catálogo e tabelas

O catálogo exibe todos os módulos. Cards não autorizados apresentam uma
mensagem discreta de permissão insuficiente, sem botão nem ação oculta.

As tabelas operacionais receberam separadores verticais entre as colunas. A
mudança é apenas visual e não altera dados, ordenação ou persistência.

## Correções preventivas

- análise de módulo exige permissão explícita de escrita no Analytics;
- perfis de análise não podem ser abertos por rota indireta sem autorização;
- retornos da Central e de Nova análise apontam para a tela correta;
- tratamento de erros da estrutura organizacional foi restringido aos erros
  esperados, evitando mascarar falhas de programação;
- migração segura adiciona o perfil de acesso aos bancos já existentes e
  preserva o acesso analítico que usuários legados já possuíam na V5.

## Validação

- 44 testes automatizados aprovados;
- compilação integral e verificação de indentação;
- teste dos perfis base e `+`;
- teste da ausência dos atalhos antigos na sidebar;
- suíte completa da V5 preservada.
