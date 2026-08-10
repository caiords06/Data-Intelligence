"""Perfis departamentais reutilizáveis e suas permissões padrão.

O perfil define um ponto de partida seguro. Um administrador ainda pode
personalizar as permissões de um usuário para uma empresa específica.
"""

from __future__ import annotations

from enterprise.catalogo import ORDEM_MODULOS


PERFIS_ACESSO = {
    "analista": {
        "nome": "Analista",
        "descricao": "Acesso ao motor analítico central.",
        "modulos": ("analytics",),
    },
    "rh": {
        "nome": "RH",
        "descricao": "Acesso exclusivo a Recursos Humanos.",
        "modulos": ("rh",),
    },
    "rh_plus": {
        "nome": "RH+",
        "descricao": "Recursos Humanos e Financeiro.",
        "modulos": ("rh", "financeiro"),
    },
    "financeiro": {
        "nome": "Financeiro",
        "descricao": "Acesso exclusivo ao Financeiro.",
        "modulos": ("financeiro",),
    },
    "financeiro_plus": {
        "nome": "Financeiro+",
        "descricao": "Financeiro e Compras.",
        "modulos": ("financeiro", "compras"),
    },
    "estoque": {
        "nome": "Estoque",
        "descricao": "Acesso exclusivo ao Estoque.",
        "modulos": ("estoque",),
    },
    "estoque_plus": {
        "nome": "Estoque+",
        "descricao": "Estoque e Compras.",
        "modulos": ("estoque", "compras"),
    },
    "compras": {
        "nome": "Compras",
        "descricao": "Acesso exclusivo a Compras.",
        "modulos": ("compras",),
    },
    "compras_plus": {
        "nome": "Compras+",
        "descricao": "Compras, Estoque e Financeiro.",
        "modulos": ("compras", "estoque", "financeiro"),
    },
    "ti": {
        "nome": "TI",
        "descricao": "Acesso exclusivo à Tecnologia.",
        "modulos": ("ti",),
    },
    "ti_plus": {
        "nome": "TI+",
        "descricao": "Tecnologia e Administrativo.",
        "modulos": ("ti", "administrativo"),
    },
    "marketing": {
        "nome": "Marketing",
        "descricao": "Acesso exclusivo ao Marketing.",
        "modulos": ("marketing",),
    },
    "marketing_plus": {
        "nome": "Marketing+",
        "descricao": "Marketing e Comercial.",
        "modulos": ("marketing", "comercial"),
    },
    "administrativo": {
        "nome": "Administrativo",
        "descricao": "Acesso exclusivo ao Administrativo.",
        "modulos": ("administrativo",),
    },
    "administrativo_plus": {
        "nome": "Administrativo+",
        "descricao": "Administrativo, Compras e Financeiro.",
        "modulos": ("administrativo", "compras", "financeiro"),
    },
    "juridico": {
        "nome": "Jurídico",
        "descricao": "Acesso exclusivo ao Jurídico.",
        "modulos": ("juridico",),
    },
    "juridico_plus": {
        "nome": "Jurídico+",
        "descricao": "Jurídico e Financeiro.",
        "modulos": ("juridico", "financeiro"),
    },
    "comercial": {
        "nome": "Comercial",
        "descricao": "Acesso exclusivo ao Comercial.",
        "modulos": ("comercial",),
    },
    "comercial_plus": {
        "nome": "Comercial+",
        "descricao": "Comercial e Marketing.",
        "modulos": ("comercial", "marketing"),
    },
}


def validar_perfil_acesso(perfil: str | None) -> str:
    codigo = str(perfil or "analista").strip().lower()
    if codigo not in PERFIS_ACESSO:
        raise ValueError("Perfil de acesso inválido.")
    return codigo


def nome_perfil_acesso(perfil: str | None, *, administrador: bool = False) -> str:
    if administrador:
        return "Administrador"
    codigo = str(perfil or "analista").strip().lower()
    return PERFIS_ACESSO.get(codigo, PERFIS_ACESSO["analista"])["nome"]


def obter_permissoes_perfil(perfil: str | None) -> dict[str, dict[str, bool]]:
    codigo = validar_perfil_acesso(perfil)
    permitidos = set(PERFIS_ACESSO[codigo]["modulos"])
    return {
        modulo: {
            "ler": modulo in permitidos,
            "escrever": modulo in permitidos,
            "aprovar": False,
        }
        for modulo in ORDEM_MODULOS
    }


def opcoes_perfis_acesso() -> list[tuple[str, str]]:
    return [
        (codigo, configuracao["nome"])
        for codigo, configuracao in PERFIS_ACESSO.items()
    ]
