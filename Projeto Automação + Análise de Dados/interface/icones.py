"""Vocabulário visual profissional da Data Intelligence V10.2.0.

Evita ícones com rostos e concentra símbolos de navegação em um único lugar.
Os caracteres escolhidos possuem bom suporte no Segoe UI/Segoe UI Symbol do
Windows e continuam legíveis em modo monocromático.
"""

ICONES = {
    "inicio": "⌂",
    "modulos": "▦",
    "analytics": "▥",
    "historico": "◷",
    "aprovacoes": "✓",
    "notificacoes": "◌",
    "correio": "✉",
    "configuracoes": "⚙",
    "organizacao": "◈",
    "usuarios": "◎",
    "financeiro": "¤",
    "rh": "♙",
    "estoque": "▣",
    "compras": "⇄",
    "ti": "⌘",
    "marketing": "↗",
    "administrativo": "☷",
    "juridico": "⚖",
    "comercial": "◇",
    "calendario": "◷",
    "documento": "▤",
    "relatorio": "▥",
    "alerta": "⚠",
    "sucesso": "✓",
    "busca": "⌕",
    "tema_escuro": "☾",
    "tema_claro": "☀",
    "seguranca": "◆",
}


def icone(chave: str, padrao: str = "•") -> str:
    return ICONES.get(str(chave or "").strip().lower(), padrao)
