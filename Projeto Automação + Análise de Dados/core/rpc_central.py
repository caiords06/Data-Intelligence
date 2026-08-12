"""RPC restrito para tornar o Servidor Corporativo a autoridade transacional.

Esta camada não expõe SQL. Somente funções explicitamente permitidas podem ser
chamadas remotamente. Em nós ``central``/``cliente``, as funções de domínio
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
import sqlite3

try:
    import pandas as pd
except Exception:  # pragma: no cover - servidor mínimo sem pandas
    pd = None

# Operações de arquivo local e aquisição de rede ficam fora do RPC genérico.
# Elas precisam de upload/download ou execução na estação e nunca devem cair
# silenciosamente no banco-cache local.
RPC_BLOQUEADAS_REMOTO: dict[str, set[str]] = {
    "enterprise.rh": {"registrar_documento", "gerar_contracheque", "gerar_relatorio_rh"},
    "enterprise.financeiro": {"anexar_documento", "importar_extrato", "gerar_relatorio_financeiro"},
    "enterprise.compras": {"registrar_documento_fornecedor", "gerar_pdf_pedido", "gerar_relatorio_compras"},
    "enterprise.estoque": {"gerar_relatorio_estoque"},
    "enterprise.tecnologia": {"gerar_relatorio_tecnologia"},
    "enterprise.ferramentas": {"registrar_documento", "verificar_documento", "gerar_relatorio", "obter_arquivo_relatorio"},
    "enterprise.datasets": {"importar_conjunto", "substituir_arquivo_conjunto"},
}

RPC_ALLOWLIST: dict[str, set[str]] = {
    "enterprise.rh": {
        "tem_permissao_rh","exigir_acao","salvar_permissao_acao","listar_catalogos","criar_colaborador",
        "listar_colaboradores","obter_colaborador","atualizar_colaborador","adicionar_dependente","iniciar_admissao",
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
        "listar_relatorios","listar_auditoria","registrar_uso_ferramenta",
    },
    "enterprise.recursos": {
        "criar_recurso","listar_recursos","obter_recurso","atualizar_recurso","alterar_estado_recurso","resumo_recursos",
    },
    "enterprise.workflows": {"criar_workflow","listar_workflows","definir_workflow_ativo","executar_workflows"},
    "enterprise.integracoes": {"registrar_integracao","listar_integracoes","definir_integracao_ativa"},
    "enterprise.jobs": {
        "criar_job","iniciar_job","atualizar_job","concluir_job","falhar_job","solicitar_cancelamento",
        "cancelamento_solicitado","cancelar_job","listar_jobs",
    },
    "enterprise.datasets": {"listar_conjuntos","obter_conjunto","excluir_conjunto","atualizar_metadados_conjunto"},
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
            pass
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
                raise ValueError(
                    f"A operação {nome_modulo}.{__nome} usa arquivo/rede local e precisa do fluxo "
                    "específico de upload/execução da estação. Ela foi bloqueada para impedir gravação "
                    "acidental no banco-cache local."
                )
            from enterprise.servidor_cliente import executar_rpc_remoto
            return executar_rpc_remoto(nome_modulo, __nome, args, kwargs)

        wrapper.__di_rpc_wrapper__ = True
        wrapper.__di_rpc_original__ = original
        namespace[nome] = wrapper


__all__ = ["RPC_ALLOWLIST", "RPC_BLOQUEADAS_REMOTO", "serializar", "desserializar", "instalar_proxy_modulo"]
