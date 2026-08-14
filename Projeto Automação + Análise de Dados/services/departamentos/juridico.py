"""Fachada estável do Jurídico especializado V10.3.3."""
from enterprise.juridico import (
    criar_contrato, listar_contratos, criar_processo, listar_processos, contar_processos,
    criar_prazo, listar_prazos, concluir_prazo, criar_audiencia,
    listar_audiencias, registrar_risco, listar_riscos, criar_provisao,
    listar_provisoes, resumo_juridico, analisar_juridico, exportar_dataframe_juridico,
)
__all__=("criar_contrato","listar_contratos","criar_processo","listar_processos","contar_processos","criar_prazo","listar_prazos","concluir_prazo","criar_audiencia","listar_audiencias","registrar_risco","listar_riscos","criar_provisao","listar_provisoes","resumo_juridico","analisar_juridico","exportar_dataframe_juridico")
