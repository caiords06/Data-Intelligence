"""Contrato mínimo para provedores externos sem prometer conectores inexistentes."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True, slots=True)
class CapacidadeIntegracao:
    codigo: str
    titulo: str
    direcao: str = "bidirecional"

class ProvedorIntegracao(Protocol):
    codigo: str
    nome: str
    capacidades: tuple[CapacidadeIntegracao, ...]
    def validar_configuracao(self, configuracao: dict) -> tuple[bool, str]: ...
