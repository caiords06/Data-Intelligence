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
    "rh_diretoria": {
        "nome": "Diretoria de RH",
        "descricao": "Gestão completa, aprovações e informações sensíveis de RH.",
        "modulos": ("rh",),
        "permissoes": {"rh": {"ler": True, "escrever": True, "aprovar": True}},
    },
    "rh_analista": {
        "nome": "Analista de RH",
        "descricao": "Operações e cadastros de RH sem aprovações de alto impacto.",
        "modulos": ("rh",),
    },
    "gestor_pessoas": {
        "nome": "Gestor de pessoas",
        "descricao": "Consulta e aprovação restritas à própria equipe.",
        "modulos": ("rh",),
        "permissoes": {"rh": {"ler": True, "escrever": False, "aprovar": True}},
    },
    "colaborador": {
        "nome": "Colaborador",
        "descricao": "Portal pessoal com acesso somente aos próprios dados e solicitações.",
        "modulos": ("rh",),
        "permissoes": {"rh": {"ler": True, "escrever": False, "aprovar": False}},
    },
    "rh_auditor": {
        "nome": "Auditor de RH",
        "descricao": "Consulta de RH em modo leitura para auditoria autorizada.",
        "modulos": ("rh",),
        "permissoes": {"rh": {"ler": True, "escrever": False, "aprovar": False}},
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
    "financeiro_gestor": {
        "nome": "Gestor Financeiro",
        "descricao": "Gestão financeira, alçadas, aprovações, tesouraria e planejamento.",
        "modulos": ("financeiro", "compras"),
        "permissoes": {"financeiro": {"ler": True, "escrever": True, "aprovar": True}},
    },
    "diretoria": {
        "nome": "Diretoria",
        "descricao": "Aprovações executivas e leitura gerencial dos módulos autorizados.",
        "modulos": ("financeiro", "compras", "rh", "estoque", "administrativo", "juridico", "comercial", "marketing", "ti"),
        "permissoes": {
            "financeiro": {"ler": True, "escrever": False, "aprovar": True},
            "compras": {"ler": True, "escrever": False, "aprovar": True},
        },
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
    "estoque_operador": {
        "nome": "Operador de Estoque",
        "descricao": "Recebimento, separação, expedição, reservas e contagem física.",
        "modulos": ("estoque",),
    },
    "estoque_analista": {
        "nome": "Analista de Estoque",
        "descricao": "Operações, cadastros, indicadores, reposição e relatórios.",
        "modulos": ("estoque",),
    },
    "estoque_gestor": {
        "nome": "Gestor de Estoque",
        "descricao": "Gestão completa do Estoque, custos, aprovações e auditoria.",
        "modulos": ("estoque", "compras"),
        "permissoes": {"estoque": {"ler": True, "escrever": True, "aprovar": True}},
    },
    "estoque_auditor": {
        "nome": "Auditor de Estoque",
        "descricao": "Consulta de saldos, razão, custos, inventários e trilha de auditoria.",
        "modulos": ("estoque",),
        "permissoes": {"estoque": {"ler": True, "escrever": False, "aprovar": False}},
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
    "compras_solicitante": {
        "nome": "Solicitante de Compras",
        "descricao": "Cria, envia e acompanha as próprias solicitações.",
        "modulos": ("compras",),
        "permissoes": {"compras": {"ler": True, "escrever": True, "aprovar": False}},
    },
    "compras_comprador": {
        "nome": "Comprador",
        "descricao": "Cotações, negociações, fornecedores, pedidos e acompanhamento de entregas.",
        "modulos": ("compras",),
    },
    "compras_gestor": {
        "nome": "Gestor de Compras",
        "descricao": "Gestão completa, alçadas, homologações, divergências e auditoria.",
        "modulos": ("compras", "estoque", "financeiro"),
        "permissoes": {"compras": {"ler": True, "escrever": True, "aprovar": True}},
    },
    "compras_recebimento": {
        "nome": "Recebimento de Compras",
        "descricao": "Conferência de entregas, divergências e integração autorizada com Estoque.",
        "modulos": ("compras", "estoque"),
    },
    "compras_auditor": {
        "nome": "Auditor de Compras",
        "descricao": "Consulta do ciclo de compras, valores autorizados e trilha imutável.",
        "modulos": ("compras",),
        "permissoes": {"compras": {"ler": True, "escrever": False, "aprovar": False}},
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
    "ti_solicitante": {
        "nome": "Solicitante de TI",
        "descricao": "Abre e acompanha os próprios chamados e consulta a base de conhecimento.",
        "modulos": ("ti",),
        "permissoes": {"ti": {"ler": True, "escrever": False, "aprovar": False}},
    },
    "ti_suporte_n1": {
        "nome": "Suporte TI N1",
        "descricao": "Triagem, atendimento inicial, conhecimento e telemetria autorizada.",
        "modulos": ("ti",),
    },
    "ti_suporte_n2": {
        "nome": "Suporte TI N2",
        "descricao": "Atendimento avançado, ativos, infraestrutura, sistemas e acesso remoto auditado.",
        "modulos": ("ti",),
    },
    "ti_gestor": {
        "nome": "Gestor de Tecnologia",
        "descricao": "Gestão integral de TI, autorizações, mudanças, segurança e auditoria.",
        "modulos": ("ti", "compras", "estoque"),
        "permissoes": {"ti": {"ler": True, "escrever": True, "aprovar": True}},
    },
    "ti_auditor": {
        "nome": "Auditor de Tecnologia",
        "descricao": "Consulta de operações, indicadores, acessos remotos e trilha imutável.",
        "modulos": ("ti",),
        "permissoes": {"ti": {"ler": True, "escrever": False, "aprovar": False}},
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
    configuracao = PERFIS_ACESSO[codigo]
    permitidos = set(configuracao["modulos"])
    resultado = {
        modulo: {
            "ler": modulo in permitidos,
            "escrever": modulo in permitidos,
            "aprovar": False,
        }
        for modulo in ORDEM_MODULOS
    }
    for modulo, permissoes in configuracao.get("permissoes", {}).items():
        resultado[modulo].update(permissoes)
    return resultado


def opcoes_perfis_acesso() -> list[tuple[str, str]]:
    return [
        (codigo, configuracao["nome"])
        for codigo, configuracao in PERFIS_ACESSO.items()
    ]
