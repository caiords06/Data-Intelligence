# Data Intelligence V10.2.0 — Design System

A V10.2.0 consolida a identidade visual da plataforma sem alterar a arquitetura Server First.

## Temas

- **Escuro tecnológico**: superfícies azul-marinho, contraste confortável e azul corporativo.
- **Claro suave**: fundo cinza-azulado e superfícies de baixa agressividade luminosa.

A preferência `tema_interface` é armazenada junto das preferências corporativas do usuário. A aplicação inicia o login no tema padrão escuro e, após autenticação, aplica automaticamente a preferência da conta.

## Arquitetura visual

- `interface/tema.py`: tokens, paletas, tipografia e estilos ttk.
- `interface/gerenciador_tema.py`: aplicação, alternância e carregamento da preferência de sessão.
- `interface/icones.py`: vocabulário visual profissional.
- `interface/login.py`: login vetorial responsivo e independente de imagens rasterizadas.

`CORES` permanece o mesmo dicionário mutável durante toda a execução. A troca de tema atualiza seus valores in-place, preservando módulos que importaram a referência anteriormente.

## Compatibilidade

Os estilos `App.*` são os nomes oficiais da V10.2. Os aliases `Dark.*` continuam configurados durante a transição para evitar regressões em telas legadas.
