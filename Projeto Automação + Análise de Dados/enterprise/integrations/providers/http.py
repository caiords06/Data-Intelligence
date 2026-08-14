"""Contrato para API HTTP/Webhook configurável."""
from enterprise.integrations.base import CapacidadeIntegracao
codigo="api_http"; nome="API HTTP / Webhook"
capacidades=(CapacidadeIntegracao("api","API HTTP"),CapacidadeIntegracao("webhook","Webhook","saida"))
def validar_configuracao(configuracao: dict):
    url=str((configuracao or {}).get("base_url") or "").strip()
    ok=url.startswith("https://") or url.startswith("http://127.0.0.1") or url.startswith("http://localhost")
    return (ok,"Configuração válida." if ok else "Use HTTPS para endpoints remotos.")
