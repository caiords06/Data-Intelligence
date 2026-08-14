"""Metadados do provedor SMTP; envio continua na infraestrutura de correio."""
from enterprise.integrations.base import CapacidadeIntegracao
codigo="smtp"; nome="SMTP / E-mail"
capacidades=(CapacidadeIntegracao("email_envio","Envio de e-mail corporativo","saida"),)
def validar_configuracao(configuracao: dict):
    host=str((configuracao or {}).get("host") or "").strip()
    return (bool(host), "Configuração válida." if host else "Informe o host SMTP.")
