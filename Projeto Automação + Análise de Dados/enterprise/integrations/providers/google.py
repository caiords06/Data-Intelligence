"""Contrato de capacidade Google Workspace; sem credenciais embutidas."""
from enterprise.integrations.base import CapacidadeIntegracao
codigo="google"; nome="Google Workspace"
capacidades=(CapacidadeIntegracao("arquivos","Google Drive"),CapacidadeIntegracao("calendario","Google Calendar"),CapacidadeIntegracao("email","Gmail corporativo"))
def validar_configuracao(configuracao: dict):
    dominio=str((configuracao or {}).get("dominio") or "").strip()
    return (bool(dominio),"Configuração válida." if dominio else "Informe o domínio Workspace; credenciais devem permanecer no cofre.")
