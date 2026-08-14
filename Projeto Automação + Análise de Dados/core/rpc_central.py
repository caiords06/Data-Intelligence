"""RPC restrito para tornar o Servidor Corporativo a autoridade transacional.

Esta camada não expõe SQL. Somente funções explicitamente permitidas podem ser
chamadas remotamente. Em nós ``central``/``cliente``, as funções autorizadas
listadas abaixo são substituídas por proxies HTTP. No processo ``servidor`` e
no modo ``standalone`` continuam executando localmente.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path
from typing import Any
import base64
import logging
import sqlite3

try:
    import pandas as pd
except Exception:  # pragma: no cover - servidor mínimo sem pandas
    pd = None

# Operações que transportam arquivos ficam fora do RPC JSON genérico.
# Em estações remotas elas são roteadas pelo wrapper para o canal dedicado
# de upload/download de core.rpc_arquivos; nunca caem em persistência local.
RPC_BLOQUEADAS_REMOTO: dict[str, set[str]] = {
    "enterprise.rh": {"registrar_documento", "gerar_contracheque", "gerar_relatorio_rh"},
    "enterprise.financeiro": {"anexar_documento", "importar_extrato", "gerar_relatorio_financeiro"},
    "enterprise.compras": {"registrar_documento_fornecedor", "gerar_pdf_pedido", "gerar_relatorio_compras"},
    "enterprise.estoque": {"gerar_relatorio_estoque"},
    "enterprise.tecnologia": {"gerar_relatorio_tecnologia"},
    "enterprise.ferramentas": {"registrar_documento", "gerar_relatorio", "obter_arquivo_relatorio"},
    "enterprise.datasets": {"importar_conjunto", "substituir_arquivo_conjunto"},
    "enterprise.core_v11.documentos": {"registrar_midia", "registrar_documento", "adicionar_versao_documento"},
    "enterprise.core_v11.funcionarios": {"registrar_avatar"},
}

RPC_ALLOWLIST: dict[str, set[str]] = {
    "enterprise.analytics_inteligencia": {
        "obter_painel_executivo", "gerar_insights", "listar_insights", "contar_insights", "alterar_status_insight",
        "listar_regras", "salvar_regra", "definir_regra_ativa", "historico_execucoes",
    },
    "enterprise.orquestracao": {
        "converter_lead_em_oportunidade", "criar_fluxo_admissao", "criar_fluxo_desligamento",
        "encaminhar_provisao_financeiro", "criar_fluxo_reposicao", "listar_orquestracoes", "contar_orquestracoes",
        "listar_etapas_orquestracao", "concluir_etapa", "resumo_orquestracoes",
    },
    "enterprise.crm": {
        "criar_empresa_crm","listar_empresas_crm","criar_contato","listar_contatos",
        "criar_lead","listar_leads","contar_leads","atualizar_lead_status","registrar_atividade","resumo_crm",
    },
    "enterprise.marketing": {
        "criar_canal","listar_canais","criar_campanha","listar_campanhas","contar_campanhas","atualizar_status_campanha",
        "criar_conteudo","listar_conteudos","criar_automacao","listar_automacoes","registrar_metricas",
        "resumo_marketing","exportar_dataframe_marketing","analisar_marketing",
    },
    "enterprise.comercial": {
        "garantir_etapas_padrao","listar_etapas","criar_oportunidade","listar_oportunidades","contar_oportunidades","mover_oportunidade",
        "registrar_atividade","criar_proposta","listar_propostas","salvar_meta","resumo_comercial",
        "analisar_comercial","exportar_dataframe_comercial",
    },
    "enterprise.administrativo": {
        "criar_solicitacao","listar_solicitacoes","contar_solicitacoes","atualizar_status_solicitacao","criar_recurso","listar_recursos",
        "criar_reserva","listar_reservas","criar_viagem","listar_viagens","criar_reembolso","listar_reembolsos",
        "criar_manutencao","listar_manutencoes","resumo_administrativo","analisar_administrativo",
        "exportar_dataframe_administrativo",
    },
    "enterprise.juridico": {
        "criar_contrato","listar_contratos","criar_processo","listar_processos","contar_processos","criar_prazo","listar_prazos",
        "concluir_prazo","criar_audiencia","listar_audiencias","registrar_risco","listar_riscos","criar_provisao",
        "listar_provisoes","resumo_juridico","analisar_juridico","exportar_dataframe_juridico",
    },
    "configuracoes.preferencias": {"carregar_preferencias", "salvar_preferencias", "obter_preferencia"},
    "historico.repositorio": {
        "registrar_analise", "listar_historico", "obter_analise",
        "excluir_analise", "excluir_analises",
    },
    "enterprise.contexto": {
        "obter_permissoes_usuario", "salvar_permissoes_usuario",
        "aplicar_perfil_padrao_usuario",
    },
    "enterprise.organizacao": {
        "listar_empresas", "listar_filiais", "listar_departamentos", "listar_centros_custo",
        "criar_empresa", "criar_filial", "criar_departamento", "criar_centro_custo",
    },
    "enterprise.nos_plataforma": {"cadastrar_no", "listar_nos", "alterar_status_no"},
    "enterprise.rh": {
        "tem_permissao_rh","exigir_acao","salvar_permissao_acao","listar_catalogos","criar_colaborador",
        "listar_colaboradores","obter_colaborador","atualizar_colaborador","alterar_estado_registro_rh","adicionar_dependente","iniciar_admissao",
        "listar_admissoes","atualizar_admissao","iniciar_desligamento","concluir_desligamento","solicitar_ferias_ausencia",
        "decidir_ferias_ausencia","salvar_beneficio","vincular_beneficio","abrir_folha","adicionar_evento_folha",
        "fechar_folha","vincular_equipamento","devolver_equipamento","registrar_ponto","salvar_cargo","criar_vaga",
        "adicionar_candidato","salvar_avaliacao","salvar_pdi","salvar_treinamento","inscrever_treinamento",
        "verificar_documento","decidir_solicitacao","criar_solicitacao","listar_secao","resumo_rh","analisar_rh",
        "exportar_dataframe_rh","agendar_relatorio","listar_auditoria_rh",
    },
    "enterprise.financeiro": {
        "tem_permissao_financeira","exigir_acao","salvar_permissao_acao","garantir_catalogos","listar_catalogos",
        "criar_conta","criar_parte","criar_categoria","criar_lancamento","submeter_aprovacao","decidir_aprovacao",
        "registrar_baixa","contabilizar_lancamento","cancelar_lancamento","estornar_lancamento","listar_lancamentos",
        "obter_lancamento","atualizar_lancamento","listar_aprovacoes_financeiras","salvar_plano_conta","salvar_cartao",
        "listar_cartoes","listar_auditoria_financeira","atualizar_status_vencidos","listar_recorrencias",
        "gerar_recorrencias_pendentes","agendar_relatorio","listar_relatorios_agendados","salvar_orcamento",
        "listar_orcamentos","listar_conciliacoes","conciliar_item","saldo_conta","listar_contas_com_saldo",
        "projetar_fluxo_caixa","calcular_dre","resumo_financeiro","analisar_financeiro",
        "exportar_dataframe_financeiro","gerar_alertas_financeiros",
    },
    "enterprise.compras": {
        "tem_permissao_compras","exigir_acao","salvar_permissao_acao","garantir_catalogos","criar_categoria",
        "salvar_regra_aprovacao","criar_fornecedor","homologar_fornecedor","atualizar_fornecedor",
        "adicionar_contato_fornecedor","avaliar_fornecedor","criar_solicitacao","enviar_solicitacao","decidir_solicitacao",
        "criar_cotacao","registrar_proposta","registrar_negociacao","selecionar_fornecedor","criar_pedido",
        "aprovar_pedido","enviar_pedido","atualizar_status_pedido","registrar_recebimento",
        "integrar_recebimento_financeiro","registrar_divergencia_manual","resolver_divergencia","criar_contrato",
        "adicionar_aditivo","criar_item_catalogo","adicionar_comentario","gerar_alertas_compras","resolver_alerta",
        "resumo_compras","listar_secao","obter_itens_solicitacao","obter_itens_pedido","obter_fornecedores_cotacao",
        "analisar_compras","exportar_dataframe_compras","agendar_relatorio","listar_historico",
    },
    "enterprise.estoque": {
        "tem_permissao_estoque","exigir_acao","salvar_permissao_acao","garantir_catalogos","listar_catalogos",
        "criar_categoria","criar_fornecedor","criar_deposito","criar_localizacao","criar_item","atualizar_item",
        "listar_itens","obter_item","criar_operacao","aprovar_operacao","conferir_operacao","confirmar_operacao",
        "receber_transferencia","cancelar_operacao","listar_operacoes","listar_movimentacoes","criar_reserva",
        "liberar_reserva","listar_reservas","criar_solicitacao","decidir_solicitacao","listar_solicitacoes",
        "iniciar_inventario","registrar_contagem","finalizar_inventario","aprovar_inventario","listar_inventarios",
        "itens_inventario","registrar_ocorrencia","listar_secao","calcular_reposicao","encaminhar_reposicao_compras",
        "gerar_alertas_estoque","resolver_alerta","resumo_estoque","analisar_estoque","exportar_dataframe_estoque",
        "agendar_relatorio","listar_auditoria_estoque","obter_primeiro_item_operacao",
    },
    "enterprise.tecnologia": {
        "tem_permissao_tecnologia","exigir_acao","salvar_permissao_acao","garantir_catalogos","criar_chamado",
        "atualizar_chamado","adicionar_comentario","criar_ativo","criar_credencial_agente","obter_credencial_agente",
        "revogar_credencial_agente","listar_agentes_ti","registrar_heartbeat","iniciar_manutencao","concluir_manutencao",
        "criar_segmento_rede","autorizar_segmento_rede","registrar_dispositivo_descoberto","criar_licenca",
        "atribuir_licenca","criar_sistema","criar_monitor","registrar_evento_monitoramento","criar_artigo_conhecimento",
        "criar_contrato","criar_problema","criar_mudanca","decidir_mudanca","criar_incidente_seguranca",
        "solicitar_acesso_remoto","encerrar_acesso_remoto","gerar_alertas_tecnologia","resolver_alerta",
        "resumo_tecnologia","listar_secao","listar_usuarios_escopo","analisar_tecnologia","exportar_dataframe_tecnologia",
        "contar_segmentos_ativos","obter_segmento_rede","atualizar_segmento_rede","revogar_autorizacao_segmento_rede",
        "preparar_firewall_segmento","remover_firewall_segmento","descobrir_segmento_rede","diagnosticar_segmento_rede",
        "remover_segmento_rede","atualizar_ativo","remover_ativo","vincular_dispositivo_ativo",
        "atualizar_dispositivo_rede","remover_dispositivo_rede","detalhar_ativo","detalhar_dispositivo_rede",
        "registrar_snapshot_agente",
    },
    "enterprise.modulos": {
        "criar_registro","listar_registros","listar_registros_paginados","consultar_dados_para_analytics",
        "exportar_dataframe_modulo","obter_registro","atualizar_registro","alterar_estado_registro",
        "listar_historico_registro","movimentar_estoque","calcular_resumo_modulo",
    },
    "enterprise.central": {
        "listar_atividades","listar_notificacoes","marcar_notificacao_lida","listar_aprovacoes","decidir_aprovacao",
        "remover_aprovacao_da_fila","resumo_cockpit","busca_universal","registrar_atividade_analytics",
    },
    "enterprise.ferramentas": {
        "criar_tarefa","listar_tarefas","atualizar_status_tarefa","arquivar_tarefa","listar_documentos",
        "arquivar_documento","listar_relatorios","listar_auditoria","registrar_uso_ferramenta","verificar_documento",
    },
    "enterprise.recursos": {
        "criar_recurso","listar_recursos","obter_recurso","atualizar_recurso","alterar_estado_recurso","resumo_recursos",
    },
    "enterprise.workflows": {"criar_workflow","listar_workflows","definir_workflow_ativo","executar_workflows"},
    "enterprise.integracoes": {"registrar_integracao","listar_integracoes","definir_integracao_ativa"},
    "enterprise.compliance": {
        "abrir_incidente_privacidade", "atualizar_solicitacao_titular", "avaliar_incidente_privacidade",
        "criar_solicitacao_titular", "definir_bloqueio_retencao", "encerrar_bloqueio_retencao",
        "listar_bloqueios_retencao", "listar_incidentes_privacidade", "listar_solicitacoes_titulares",
        "listar_decisoes_analiticas", "listar_ripd", "listar_terceiros", "listar_tratamentos",
        "resumo_conformidade", "salvar_decisao_analitica", "salvar_ripd", "salvar_terceiro", "salvar_tratamento",
    },
    "enterprise.remote_governanca": {
        "emitir_autorizacao_remota", "encerrar_autorizacao_remota", "listar_autorizacoes_remotas",
        "obter_politica_remota", "salvar_politica_remota",
    },
    "enterprise.jobs": {
        "criar_job","iniciar_job","atualizar_job","concluir_job","falhar_job","solicitar_cancelamento",
        "cancelamento_solicitado","cancelar_job","listar_jobs",
    },
    "enterprise.datasets": {"listar_conjuntos","obter_conjunto","excluir_conjunto","atualizar_metadados_conjunto"},
    "enterprise.core_v11.pessoas": {"criar_pessoa", "vincular_papel", "listar_pessoas", "obter_pessoa", "sincronizar_colaborador"},
    "enterprise.core_v11.organizacao": {"criar_unidade", "listar_unidades", "arvore_organizacional", "atualizar_unidade"},
    "enterprise.core_v11.seguranca": {
        "criar_grupo", "adicionar_membro", "criar_funcao_contextual", "atribuir_funcao",
        "tem_permissao_contextual", "exigir_permissao_contextual", "listar_grupos_funcoes",
    },
    "enterprise.core_v11.colaboracao": {
        "adicionar_comentario", "listar_comentarios", "notificar", "criar_evento_calendario",
        "listar_calendario", "caixa_entrada", "salvar_dashboard", "listar_dashboards",
        "salvar_preferencia_contextual",
    },
    "enterprise.core_v11.metadados": {
        "definir_campo", "listar_campos", "salvar_campos_valores", "obter_campos_valores",
        "criar_etiqueta", "aplicar_etiqueta", "salvar_configuracao",
    },
    "enterprise.core_v11.documentos": {
        "registrar_midia_bytes", "obter_midia", "carregar_midia_bytes", "listar_documentos",
        "solicitar_assinatura", "registrar_evidencia_assinatura", "registrar_resultado_ocr",
    },
    "enterprise.core_v11.busca": {"busca_universal", "reindexar_core"},
    "enterprise.core_v11.registros": {
        "listar_tipos", "salvar_tipo", "criar_registro", "listar_registros", "obter_registro",
        "alterar_estado_registro", "atualizar_registro", "avancar_fluxo", "relacionar_registros", "resumo_operacional",
    },
    "enterprise.core_v11.funcionarios": {
        "garantir_vinculo", "obter_funcionario_360", "obter_meu_funcionario_360", "registrar_avatar_bytes",
        "carregar_avatar", "registrar_acesso", "registrar_feedback", "registrar_custo", "registrar_ocorrencia",
    },
    "enterprise.core_v11.transferencias": {
        "exportar_registros", "importar_registros_bytes", "listar_transferencias", "baixar_exportacao",
    },
    "enterprise.core_v11.integracoes": {"registrar_referencia_credencial", "listar_credenciais", "registrar_rotacao"},
}


def serializar(valor: Any) -> Any:
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, sqlite3.Row):
        return {k: serializar(valor[k]) for k in valor.keys()}
    if isinstance(valor, dict):
        return {str(k): serializar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [serializar(v) for v in valor]
    if isinstance(valor, (datetime, date)):
        return {"__di_type__": "datetime", "value": valor.isoformat()}
    if isinstance(valor, Decimal):
        return {"__di_type__": "decimal", "value": str(valor)}
    if isinstance(valor, Path):
        return {"__di_type__": "path", "value": str(valor)}
    if isinstance(valor, bytes):
        return {"__di_type__": "bytes", "value": base64.b64encode(valor).decode("ascii")}
    if pd is not None and isinstance(valor, pd.DataFrame):
        return {
            "__di_type__": "dataframe",
            "columns": [str(c) for c in valor.columns],
            "records": [serializar(x) for x in valor.to_dict(orient="records")],
        }
    # Numpy scalars e tipos equivalentes.
    item = getattr(valor, "item", None)
    if callable(item):
        try:
            return serializar(item())
        except Exception:
            logging.getLogger(__name__).debug("Conversão de escalar RPC por item() falhou", exc_info=True)
    raise TypeError(f"Tipo não suportado pelo RPC corporativo: {type(valor).__name__}")


def desserializar(valor: Any) -> Any:
    if isinstance(valor, list):
        return [desserializar(v) for v in valor]
    if not isinstance(valor, dict):
        return valor
    tipo = valor.get("__di_type__")
    if tipo == "datetime":
        return datetime.fromisoformat(str(valor.get("value")))
    if tipo == "decimal":
        return Decimal(str(valor.get("value")))
    if tipo == "path":
        return Path(str(valor.get("value")))
    if tipo == "bytes":
        return base64.b64decode(str(valor.get("value") or ""))
    if tipo == "dataframe":
        registros = [desserializar(v) for v in valor.get("records", [])]
        if pd is None:
            return registros
        return pd.DataFrame(registros, columns=valor.get("columns") or None)
    return {k: desserializar(v) for k, v in valor.items()}


def instalar_proxy_modulo(namespace: dict[str, Any], nome_modulo: str) -> None:
    """Substitui APIs autorizadas por wrappers que decidem local/remoto em runtime."""
    permitidas = RPC_ALLOWLIST.get(nome_modulo, set())
    bloqueadas = RPC_BLOQUEADAS_REMOTO.get(nome_modulo, set())
    for nome in sorted(permitidas | bloqueadas):
        original = namespace.get(nome)
        if not callable(original) or getattr(original, "__di_rpc_wrapper__", False):
            continue

        @wraps(original)
        def wrapper(*args, __nome=nome, __original=original, **kwargs):
            from core.nodo import usa_servidor_remoto
            if not usa_servidor_remoto():
                return __original(*args, **kwargs)
            if __nome in RPC_BLOQUEADAS_REMOTO.get(nome_modulo, set()):
                from enterprise.servidor_cliente import executar_operacao_arquivo_remota
                return executar_operacao_arquivo_remota(nome_modulo, __nome, args, kwargs)
            from enterprise.servidor_cliente import executar_rpc_remoto
            return executar_rpc_remoto(nome_modulo, __nome, args, kwargs)

        wrapper.__di_rpc_wrapper__ = True
        wrapper.__di_rpc_original__ = original
        namespace[nome] = wrapper


__all__ = ["RPC_ALLOWLIST", "RPC_BLOQUEADAS_REMOTO", "serializar", "desserializar", "instalar_proxy_modulo"]
