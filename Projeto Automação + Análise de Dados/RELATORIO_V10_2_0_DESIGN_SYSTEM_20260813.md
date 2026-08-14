# Relatório V10.2.0 — Design System, temas e identidade visual

Data: 13/08/2026

## Escopo entregue

A V10.2.0 preserva a arquitetura Server First/PostgreSQL da base auditada e concentra a evolução no front-end corporativo.

### Design System

- `interface/tema.py` passou a concentrar duas paletas completas e tokens semânticos.
- `CORES` permanece como o mesmo dicionário mutável e é atualizado in-place, evitando referências quebradas em módulos já importados.
- Estilos oficiais `App.*` foram adicionados para Treeview, Combobox, Notebook e Scrollbar.
- Aliases `Dark.*` continuam configurados durante a transição para não quebrar telas legadas.
- Tokens `on_primary`, `on_success`, `on_warning` e `on_danger` definem cores de conteúdo sobre ações.

### Temas

- **Escuro tecnológico**: azul-marinho, sem preto puro, com destaques azuis e contraste de leitura.
- **Claro suave**: cinza-azulado, cards quase brancos e contraste confortável sem grandes superfícies em branco puro.
- `tema_interface` foi incorporado às preferências corporativas do usuário.
- O tema é aplicado depois do login usando a preferência salva no servidor.
- A troca dentro de Configurações salva a preferência, atualiza os tokens e recria a tela com segurança.

### Identidade visual

- Criado `interface/icones.py` com vocabulário visual profissional, sem emojis de rosto.
- Navegação global passou a consumir o catálogo central de ícones.
- Catálogo de módulos usa os símbolos centralizados quando disponíveis.
- Marca lateral recebeu assinatura compacta `ENTERPRISE PLATFORM` para evitar corte em notebooks e 1366×768.

### Login e primeiro acesso

- O login foi refeito como composição vetorial em Tkinter.
- Foram eliminadas as imagens rasterizadas antigas de fundo/ecossistema do login.
- A ilustração usa nós, conexões, monograma e barras de marca gerados por `Canvas`.
- O login permite alternar Escuro/Claro sem perder usuário/senha digitados.
- O primeiro acesso também possui alternância de tema e persiste a escolha no perfil do administrador criado.

### Testes visuais

O gerador `scripts/gerar_capturas_interface.py` agora aceita:

```powershell
python scripts\gerar_capturas_interface.py --tema escuro
python scripts\gerar_capturas_interface.py --tema claro
```

A fixture visual foi ajustada para usar SQLite somente em modo explícito de teste legado, sem enfraquecer a regra PostgreSQL-only da aplicação real.

Validação executada em 1366×768 sob display gráfico isolado:

- Escuro: 38 telas; 35 aprovadas, 3 alertas heurísticos, 0 reprovadas.
- Claro: 38 telas; 35 aprovadas, 3 alertas heurísticos, 0 reprovadas.
- `tests/test_interface_screenshots.py`: 1 teste visual completo aprovado.

Os três alertas são de baixa variedade visual em telas intencionalmente minimalistas/vazias (login, primeiro acesso e histórico sem registros), sem widget fora da janela ou falha de renderização.

## Compatibilidade e release

- Versão canônica: `10.2.0` / `V10.2.0`.
- Setup: `DataIntelligence_Setup_V10.2.0.exe`.
- Pacote-fonte: `DataIntelligence-Source-V10.2.0.zip`.
- Workflow CI e scripts de build foram atualizados para V10.2.0.
- `VERSAO_V10_2_0.txt` e `README_V10_2_DESIGN_SYSTEM.md` foram adicionados.

## Regressão

A suíte foi executada por grupos isolados. Os seis grupos concluíram sem arquivos de teste com falha. Testes dependentes de PostgreSQL real ou desktop gráfico permanecem condicionais; a captura Tk foi executada separadamente sob Xvfb e aprovada.
