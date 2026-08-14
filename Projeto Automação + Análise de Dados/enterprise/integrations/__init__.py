"""Contratos de integração homologável — V11.1.0."""
from .base import CapacidadeIntegracao, ProvedorIntegracao
from .registro import catalogo_provedores, obter_provedor, status_provedores
__all__=("CapacidadeIntegracao","ProvedorIntegracao","catalogo_provedores","obter_provedor","status_provedores")
