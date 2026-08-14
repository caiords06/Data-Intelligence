"""Fachada estável do CRM compartilhado — V11.1.0."""
from enterprise.crm import (
    atualizar_lead_status, contar_leads, criar_contato, criar_empresa_crm, criar_lead, listar_contatos,
    listar_empresas_crm, listar_leads, registrar_atividade, resumo_crm,
)
__all__=("atualizar_lead_status","contar_leads","criar_contato","criar_empresa_crm","criar_lead","listar_contatos",
         "listar_empresas_crm","listar_leads","registrar_atividade","resumo_crm")
