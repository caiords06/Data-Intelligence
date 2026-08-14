"""Validação tipada dos contratos de entrada da API v1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Campo:
    tipos: tuple[type, ...]
    obrigatorio: bool = False
    maximo: int | None = None


CONTRATOS_POST: dict[str, dict[str, Campo]] = {
    "/api/v1/crm/leads": {
        "contato_id": Campo((int, str, type(None))), "crm_empresa_id": Campo((int, str, type(None))),
        "campanha_id": Campo((int, str, type(None))), "origem": Campo((str,), maximo=160),
        "score": Campo((int, float, str)), "temperatura": Campo((str,), maximo=40),
        "status": Campo((str,), maximo=40),
    },
    "/api/v1/comercial/oportunidades": {
        "titulo": Campo((str,), obrigatorio=True, maximo=220), "valor": Campo((int, float, str)),
        "probabilidade": Campo((int, float, str)), "status": Campo((str,), maximo=40),
        "etapa_id": Campo((int, str, type(None))), "lead_id": Campo((int, str, type(None))),
        "crm_empresa_id": Campo((int, str, type(None))), "contato_id": Campo((int, str, type(None))),
        "fechamento_previsto": Campo((str,), maximo=40), "proxima_acao": Campo((str,), maximo=500),
    },
    "/api/v1/marketing/campanhas": {
        "nome": Campo((str,), obrigatorio=True, maximo=220), "objetivo": Campo((str,), maximo=500),
        "publico": Campo((str,), maximo=500), "status": Campo((str,), maximo=40),
        "canal_id": Campo((int, str, type(None))), "orcamento": Campo((int, float, str)),
        "investimento": Campo((int, float, str)), "receita_atribuida": Campo((int, float, str)),
        "inicio": Campo((str,), maximo=40), "fim": Campo((str,), maximo=40),
    },
    "/api/v1/juridico/processos": {
        "numero": Campo((str,), obrigatorio=True, maximo=120), "titulo": Campo((str,), obrigatorio=True, maximo=220),
        "tribunal": Campo((str,), maximo=180), "parte_contraria": Campo((str,), maximo=220),
        "advogado_responsavel": Campo((str,), maximo=180), "tipo": Campo((str,), maximo=100),
        "fase": Campo((str,), maximo=100), "valor_causa": Campo((int, float, str)),
        "probabilidade": Campo((str,), maximo=40), "risco": Campo((str,), maximo=40),
        "status": Campo((str,), maximo=40),
    },
    "/api/v1/administrativo/solicitacoes": {
        "titulo": Campo((str,), obrigatorio=True, maximo=220), "categoria": Campo((str,), maximo=100),
        "descricao": Campo((str,), maximo=4000), "prioridade": Campo((str,), maximo=40),
        "sla_horas": Campo((int, float, str)), "prazo": Campo((str,), maximo=40),
        "valor": Campo((int, float, str)), "centro_custo_id": Campo((int, str, type(None))),
    },
    "/api/v1/crm/leads/to-opportunity": {
        "lead_id": Campo((int, str), obrigatorio=True), "titulo": Campo((str,), maximo=220),
        "valor": Campo((int, float, str)), "probabilidade": Campo((int, float, str)),
        "fechamento_previsto": Campo((str,), maximo=40), "proxima_acao": Campo((str,), maximo=500),
    },
}


def validar_login(dados: Any) -> dict:
    if not isinstance(dados, dict):
        raise ValueError("O corpo do login deve ser um objeto JSON.")
    usuario = dados.get("usuario")
    senha = dados.get("senha")
    codigo = dados.get("codigo_mfa", "")
    if not isinstance(usuario, str) or not 3 <= len(usuario.strip()) <= 180:
        raise ValueError("Usuário inválido.")
    if not isinstance(senha, str) or not 1 <= len(senha) <= 1024:
        raise ValueError("Senha inválida.")
    if not isinstance(codigo, str) or len(codigo) > 64:
        raise ValueError("Código MFA inválido.")
    return {"usuario": usuario.strip(), "senha": senha, "codigo_mfa": codigo.strip()}


def validar_payload(path: str, dados: Any) -> dict:
    if not isinstance(dados, dict):
        raise ValueError("O corpo deve ser um objeto JSON.")
    contrato = CONTRATOS_POST.get(path)
    if not contrato:
        return dados
    desconhecidos = sorted(set(dados) - set(contrato))
    if desconhecidos:
        raise ValueError("Campos não reconhecidos: " + ", ".join(desconhecidos))
    for nome, campo in contrato.items():
        valor = dados.get(nome)
        if campo.obrigatorio and (valor is None or (isinstance(valor, str) and not valor.strip())):
            raise ValueError(f"Campo obrigatório ausente: {nome}.")
        if valor is None:
            continue
        if isinstance(valor, bool) and bool not in campo.tipos:
            raise ValueError(f"Tipo inválido para {nome}.")
        if not isinstance(valor, campo.tipos):
            raise ValueError(f"Tipo inválido para {nome}.")
        if campo.maximo is not None and isinstance(valor, str) and len(valor) > campo.maximo:
            raise ValueError(f"Campo {nome} excede {campo.maximo} caracteres.")
    return dados


__all__ = ("CONTRATOS_POST", "validar_login", "validar_payload")
