"""Utilidades pequenas para domínios departamentais especializados."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enterprise.contexto import obter_escopo_ator


def linha(row):
    return {k: row[k] for k in row.keys()} if row is not None else None


def texto(valor, *, obrigatorio=False, nome="Campo", maximo=1000):
    valor = str(valor or "").strip()
    if obrigatorio and not valor:
        raise ValueError(f"{nome} é obrigatório.")
    if len(valor) > maximo:
        raise ValueError(f"{nome} deve possuir no máximo {maximo} caracteres.")
    return valor


def centavos(valor) -> int:
    if valor in (None, ""):
        return 0
    bruto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(bruto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor monetário inválido.") from exc
    if not numero.is_finite() or numero < 0:
        raise ValueError("O valor monetário deve ser positivo e finito.")
    return int(numero * 100)


def escopo(ator):
    empresa_id, filial_id = obter_escopo_ator(ator)
    return int(empresa_id), int(filial_id) if filial_id is not None else None
