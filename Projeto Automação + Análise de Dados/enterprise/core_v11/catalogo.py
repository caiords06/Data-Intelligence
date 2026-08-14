"""Catálogo inicial configurável de capacidades e fluxos da V11."""
from __future__ import annotations


TIPOS_POR_MODULO: dict[str, tuple[tuple[str, str, str | None], ...]] = {
    "financeiro": (
        ("conta_pagar", "Conta a pagar", "financeiro_documento"), ("conta_receber", "Conta a receber", "financeiro_documento"),
        ("tesouraria", "Movimento de tesouraria", None), ("conciliacao", "Conciliação bancária", "financeiro_documento"),
        ("orcamento", "Orçamento", "financeiro_documento"), ("fluxo_caixa", "Cenário de fluxo de caixa", None),
        ("dre", "DRE gerencial", None), ("cobranca", "Cobrança", "financeiro_documento"),
        ("projecao", "Projeção financeira", None),
    ),
    "rh": (
        ("pessoa", "Pessoa", None), ("colaborador", "Colaborador", "rh_admissao"), ("recrutamento", "Processo seletivo", None),
        ("admissao", "Admissão", "rh_admissao"), ("ponto", "Registro de ponto", None), ("ferias", "Férias e ausência", None),
        ("beneficio", "Benefício", None), ("desempenho", "Avaliação de desempenho", None),
        ("treinamento", "Treinamento", None), ("folha", "Folha de pagamento", None), ("desligamento", "Desligamento", "rh_desligamento"),
    ),
    "compras": (
        ("solicitacao", "Solicitação de compra", "compras_ciclo"), ("alcada", "Alçada de aprovação", None),
        ("cotacao", "Cotação", "compras_ciclo"), ("mapa_comparativo", "Mapa comparativo", None),
        ("fornecedor", "Fornecedor", None), ("pedido", "Pedido de compra", "compras_ciclo"),
        ("recebimento", "Recebimento", "compras_ciclo"), ("avaliacao_fornecedor", "Avaliação de fornecedor", None),
    ),
    "estoque": (
        ("deposito", "Depósito", None), ("endereco", "Endereço de estoque", None), ("item", "Item de estoque", None),
        ("lote", "Lote", None), ("serial", "Número de série", None), ("validade", "Controle de validade", None),
        ("reserva", "Reserva", None), ("inventario", "Inventário", None), ("transferencia", "Transferência", None),
        ("patrimonio", "Patrimônio", None), ("curva_abc", "Classificação ABC", None), ("reposicao", "Reposição", "estoque_reposicao"),
    ),
    "crm": (
        ("conta", "Conta CRM", None), ("contato", "Contato", None), ("lead", "Lead", "comercial_venda"),
        ("atividade", "Atividade CRM", None),
    ),
    "comercial": (
        ("oportunidade", "Oportunidade", "comercial_venda"), ("proposta", "Proposta", "comercial_venda"),
        ("pedido", "Pedido de venda", "comercial_venda"), ("contrato", "Contrato comercial", "comercial_venda"),
        ("meta", "Meta", None), ("comissao", "Comissão", None),
    ),
    "marketing": (
        ("campanha", "Campanha", "marketing_campanha"), ("publico", "Público", None), ("jornada", "Jornada", None),
        ("conteudo", "Conteúdo", "marketing_campanha"), ("calendario", "Calendário editorial", None),
        ("lead_scoring", "Regra de lead scoring", None), ("atribuicao", "Atribuição", None),
        ("consentimento", "Consentimento", None), ("orcamento", "Orçamento de marketing", None),
    ),
    "administrativo": (
        ("facilities", "Demanda de facilities", "administrativo_solicitacao"), ("sala", "Sala", None),
        ("viagem", "Viagem", "administrativo_solicitacao"), ("reembolso", "Reembolso", "administrativo_solicitacao"),
        ("visitante", "Visitante", None), ("correspondencia", "Correspondência", None), ("frota", "Veículo de frota", None),
        ("material", "Material administrativo", None), ("manutencao", "Manutenção", "administrativo_solicitacao"),
    ),
    "juridico": (
        ("contrato", "Contrato jurídico", "juridico_contrato"), ("processo", "Processo", None), ("prazo", "Prazo", None),
        ("audiencia", "Audiência", None), ("obrigacao", "Obrigação contratual", "juridico_contrato"),
        ("risco", "Risco jurídico", None), ("provisao", "Provisão", None), ("compliance", "Controle de compliance", None),
    ),
    "ti": (
        ("cmdb", "Item de configuração CMDB", None), ("ativo", "Ativo de TI", None), ("agente", "Agente", None),
        ("chamado", "Chamado", "ti_incidente"), ("licenca", "Licença", None), ("patch", "Patch", "ti_incidente"),
        ("inventario", "Inventário de TI", None), ("rede", "Elemento de rede", None), ("alerta", "Alerta", "ti_incidente"),
        ("acao_remota", "Ação remota controlada", "ti_incidente"),
    ),
    "analytics": (
        ("catalogo_dados", "Ativo do catálogo de dados", None), ("metrica_semantica", "Métrica semântica", None),
        ("dashboard", "Dashboard", None), ("alerta", "Alerta analítico", "analytics_insight"),
        ("previsao", "Previsão", None), ("comparacao", "Comparação", None), ("causa_raiz", "Análise de causa", "analytics_insight"),
    ),
    "automacao": (
        ("workflow", "Workflow", None), ("regra", "Regra empresarial", None), ("agenda", "Agenda", None),
        ("fila", "Fila", None), ("conector", "Conector", None), ("aprovacao", "Aprovação", None),
        ("compensacao", "Compensação", None),
    ),
    "documentos": (
        ("documento", "Documento GED", "documento_ged"), ("versao", "Versão documental", None),
        ("modelo", "Modelo documental", None), ("assinatura", "Assinatura", "documento_ged"),
        ("classificacao", "Classificação documental", None), ("validade", "Validade documental", None),
        ("ocr", "Extração OCR", None), ("retencao", "Retenção documental", None),
    ),
}


FLUXOS: dict[str, dict] = {
    "financeiro_documento": {"nome": "Documento até conciliação", "modulo": "financeiro", "etapas": (
        ("documento", "Documento recebido", "financeiro", False), ("obrigacao", "Obrigação", "financeiro", False),
        ("aprovacao", "Aprovação", "financeiro", True), ("pagamento", "Pagamento", "financeiro", True),
        ("conciliacao", "Conciliação", "financeiro", False))},
    "rh_admissao": {"nome": "Admissão interdepartamental", "modulo": "rh", "etapas": (
        ("cadastro", "Cadastro", "rh", False), ("documentos", "Documentos", "rh", False),
        ("usuario", "Usuário e acessos", "ti", True), ("equipamento", "Equipamento", "estoque", True),
        ("onboarding", "Onboarding", "rh", False), ("ativo", "Ativação", "rh", True))},
    "rh_desligamento": {"nome": "Desligamento seguro", "modulo": "rh", "etapas": (
        ("solicitacao", "Solicitação", "rh", True), ("acessos", "Revogação de acessos", "ti", True),
        ("ativos", "Devolução de ativos", "estoque", True), ("financeiro", "Acerto financeiro", "financeiro", True),
        ("conclusao", "Conclusão", "rh", True))},
    "compras_ciclo": {"nome": "Ciclo de suprimentos", "modulo": "compras", "etapas": (
        ("necessidade", "Necessidade", "compras", False), ("cotacao", "Cotação", "compras", False),
        ("aprovacao", "Aprovação", "compras", True), ("pedido", "Pedido", "compras", False),
        ("recebimento", "Recebimento", "estoque", False), ("financeiro", "Obrigação", "financeiro", False))},
    "estoque_reposicao": {"nome": "Reposição automática", "modulo": "estoque", "etapas": (
        ("minimo", "Estoque mínimo", "estoque", False), ("solicitacao", "Solicitação", "compras", False),
        ("compra", "Compra", "compras", True), ("recebimento", "Recebimento", "estoque", False),
        ("atualizacao", "Atualização financeira", "financeiro", False))},
    "comercial_venda": {"nome": "Lead até cobrança", "modulo": "comercial", "etapas": (
        ("lead", "Lead", "crm", False), ("oportunidade", "Oportunidade", "comercial", False),
        ("proposta", "Proposta", "comercial", False), ("contrato", "Contrato", "juridico", True),
        ("venda", "Venda", "comercial", False), ("cobranca", "Cobrança", "financeiro", False))},
    "marketing_campanha": {"nome": "Campanha até CRM", "modulo": "marketing", "etapas": (
        ("planejamento", "Planejamento", "marketing", True), ("conteudo", "Conteúdo", "marketing", False),
        ("publicacao", "Publicação", "marketing", False), ("lead", "Lead", "crm", False),
        ("qualificacao", "Qualificação", "crm", False))},
    "administrativo_solicitacao": {"nome": "Solicitação administrativa", "modulo": "administrativo", "etapas": (
        ("solicitacao", "Solicitação", "administrativo", False), ("aprovacao", "Aprovação", "administrativo", True),
        ("execucao", "Execução", "administrativo", False), ("prestacao", "Prestação de contas", "financeiro", True))},
    "juridico_contrato": {"nome": "Contrato e obrigações", "modulo": "juridico", "etapas": (
        ("elaboracao", "Elaboração", "juridico", False), ("revisao", "Revisão", "juridico", True),
        ("assinatura", "Assinatura", "documentos", True), ("vigencia", "Vigência", "juridico", False),
        ("obrigacoes", "Obrigações", "juridico", False))},
    "ti_incidente": {"nome": "Alerta até evidência", "modulo": "ti", "etapas": (
        ("telemetria", "Telemetria", "ti", False), ("alerta", "Alerta", "ti", False),
        ("chamado", "Chamado", "ti", False), ("resolucao", "Resolução", "ti", True),
        ("evidencia", "Evidência", "documentos", False))},
    "analytics_insight": {"nome": "Insight até ação", "modulo": "analytics", "etapas": (
        ("evento", "Evento ou desvio", "analytics", False), ("insight", "Insight", "analytics", False),
        ("responsavel", "Responsável", "analytics", False), ("acao", "Ação", "automacao", True))},
    "documento_ged": {"nome": "Ciclo GED", "modulo": "documentos", "etapas": (
        ("entrada", "Documento", "documentos", False), ("extracao", "Extração", "documentos", False),
        ("classificacao", "Classificação", "documentos", False), ("aprovacao", "Aprovação", "documentos", True),
        ("arquivo", "Arquivamento", "documentos", False))},
}


def schema_padrao(nome: str) -> dict:
    return {
        "titulo": nome,
        "campos": [
            {"codigo": "descricao", "tipo": "texto_longo", "rotulo": "Descrição"},
            {"codigo": "responsavel", "tipo": "usuario", "rotulo": "Responsável"},
            {"codigo": "vencimento", "tipo": "data_hora", "rotulo": "Vencimento"},
            {"codigo": "valor", "tipo": "moeda", "rotulo": "Valor"},
        ],
    }


__all__ = ("FLUXOS", "TIPOS_POR_MODULO", "schema_padrao")
