"""Contrato de capacidade Microsoft 365; ativação depende de integração registrada."""
from enterprise.integrations.base import CapacidadeIntegracao
codigo="microsoft"; nome="Microsoft 365"
capacidades=(CapacidadeIntegracao("arquivos","Arquivos e documentos"),CapacidadeIntegracao("calendario","Calendário corporativo"),CapacidadeIntegracao("email","Correio corporativo"))
def validar_configuracao(configuracao: dict):
    tenant=str((configuracao or {}).get("tenant_id") or "").strip()
    return (bool(tenant),"Configuração válida." if tenant else "Informe tenant_id; credenciais devem permanecer no cofre.")
