"""Contratos REST explícitos da API corporativa V11.1.0.

O RPC continua atendendo o desktop legado, mas integrações e futuros clientes
Web usam recursos estáveis, escopados pelo bearer do Servidor Corporativo.
"""
from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
import base64
import re
from typing import Any, Callable


@dataclass(slots=True)
class APIError(Exception):
    status: int
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def erro_payload(exc: APIError, request_id: str) -> dict:
    return {
        "ok": False, "error": {"code": exc.code, "message": exc.message},
        "request_id": request_id, "erro": exc.message,
    }


def _inteiro(valor, padrao: int, minimo: int, maximo: int) -> int:
    try:
        n = int(valor)
    except (TypeError, ValueError):
        n = padrao
    return max(minimo, min(maximo, n))


def _paginacao(qs: dict[str, list[str]]) -> tuple[int, int]:
    page = _inteiro((qs.get("page") or [1])[0], 1, 1, 100000)
    page_size = _inteiro((qs.get("page_size") or [50])[0], 50, 1, 100)
    return page, page_size


def _envelope_paginado(itens: list[dict], total: int, page: int, page_size: int, request_id: str) -> dict:
    inicio = (page - 1) * page_size
    total = max(0, int(total))
    return {
        "ok": True,
        "data": itens,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": inicio + len(itens) < total,
        },
        "request_id": request_id,
    }


def _texto_query(qs: dict[str, list[str]], chave: str, padrao: str = "") -> str:
    return str((qs.get(chave) or [padrao])[0] or padrao).strip()


def _pagina_args(qs: dict[str, list[str]]) -> tuple[int, int, int]:
    page, page_size = _paginacao(qs)
    return page, page_size, (page - 1) * page_size


def _get_crm_leads(ator, qs):
    from services.crm import contar_leads, listar_leads
    page, page_size, offset = _pagina_args(qs)
    filtros = {"status": _texto_query(qs, "status") or None, "pesquisa": _texto_query(qs, "q")}
    return listar_leads(ator, **filtros, limite=page_size, offset=offset), contar_leads(ator, **filtros), page, page_size


def _get_comercial(ator, qs):
    from services.departamentos.comercial import contar_oportunidades, listar_oportunidades
    page, page_size, offset = _pagina_args(qs)
    filtros = {"status": _texto_query(qs, "status") or None}
    return listar_oportunidades(ator, **filtros, limite=page_size, offset=offset), contar_oportunidades(ator, **filtros), page, page_size


def _get_marketing(ator, qs):
    from services.departamentos.marketing import contar_campanhas, listar_campanhas
    page, page_size, offset = _pagina_args(qs)
    filtros = {"pesquisa": _texto_query(qs, "q"), "status": _texto_query(qs, "status") or None}
    return listar_campanhas(ator, **filtros, limite=page_size, offset=offset), contar_campanhas(ator, **filtros), page, page_size


def _get_juridico(ator, qs):
    from services.departamentos.juridico import contar_processos, listar_processos
    page, page_size, offset = _pagina_args(qs)
    return listar_processos(ator, limite=page_size, offset=offset), contar_processos(ator), page, page_size


def _get_administrativo(ator, qs):
    from services.departamentos.administrativo import contar_solicitacoes, listar_solicitacoes
    page, page_size, offset = _pagina_args(qs)
    filtros = {"status": _texto_query(qs, "status") or None}
    return listar_solicitacoes(ator, **filtros, limite=page_size, offset=offset), contar_solicitacoes(ator, **filtros), page, page_size


def _get_insights(ator, qs):
    from services.analytics import contar_insights, listar_insights
    page, page_size, offset = _pagina_args(qs)
    filtros = {
        "status": _texto_query(qs, "status", "Ativo") or "Ativo",
        "modulo": _texto_query(qs, "modulo") or None,
        "severidade": _texto_query(qs, "severidade") or None,
    }
    return listar_insights(ator, **filtros, limite=page_size, offset=offset), contar_insights(ator, **filtros), page, page_size


_GET_LISTAS: dict[str, Callable[[dict, dict], tuple[list[dict], int, int, int]]] = {
    "/api/v1/crm/leads": _get_crm_leads,
    "/api/v1/comercial/oportunidades": _get_comercial,
    "/api/v1/marketing/campanhas": _get_marketing,
    "/api/v1/juridico/processos": _get_juridico,
    "/api/v1/administrativo/solicitacoes": _get_administrativo,
    "/api/v1/analytics/insights": _get_insights,
}


def dispatch_get(path: str, qs: dict[str, list[str]], sessao, request_id: str) -> tuple[int, dict] | None:
    ator = sessao.ator()
    if path in _GET_LISTAS:
        itens, total, page, page_size = _GET_LISTAS[path](ator, qs)
        return HTTPStatus.OK, _envelope_paginado(itens, total, page, page_size, request_id)
    if path == "/api/v1/analytics/executive":
        from services.analytics import obter_painel_executivo
        return HTTPStatus.OK, {"ok": True, "data": obter_painel_executivo(ator), "request_id": request_id}
    if path == "/api/v1/orquestracoes":
        from services.orquestracao import contar_orquestracoes, listar_orquestracoes
        page, page_size, offset = _pagina_args(qs)
        filtros = {"tipo": _texto_query(qs, "tipo") or None, "status": _texto_query(qs, "status") or None}
        itens = listar_orquestracoes(ator, **filtros, limite=page_size, offset=offset)
        total = contar_orquestracoes(ator, **filtros)
        return HTTPStatus.OK, _envelope_paginado(itens, total, page, page_size, request_id)
    if path == "/api/v1/core/search":
        from services.core_empresarial import busca_universal
        page, page_size = _paginacao(qs)
        resultado = busca_universal(
            _texto_query(qs, "q"), ator, modulo=_texto_query(qs, "modulo") or None,
            pagina=page, tamanho=page_size,
        )
        return HTTPStatus.OK, _envelope_paginado(resultado["itens"], resultado["total"], page, page_size, request_id)
    if path == "/api/v1/core/inbox":
        from services.core_empresarial import caixa_entrada
        return HTTPStatus.OK, {"ok": True, "data": caixa_entrada(ator, limite=_inteiro(_texto_query(qs, "limit", "100"), 100, 1, 500)), "request_id": request_id}
    if path == "/api/v1/core/calendar":
        from services.core_empresarial import listar_calendario
        inicio = _texto_query(qs, "start"); fim = _texto_query(qs, "end")
        if not inicio or not fim:
            raise APIError(HTTPStatus.BAD_REQUEST, "period_required", "start e end são obrigatórios.")
        return HTTPStatus.OK, {"ok": True, "data": listar_calendario(ator, inicio=inicio, fim=fim, modulo=_texto_query(qs, "modulo") or None), "request_id": request_id}
    if path == "/api/v1/core/dashboards":
        from services.core_empresarial import listar_dashboards
        return HTTPStatus.OK, {"ok": True, "data": listar_dashboards(ator), "request_id": request_id}
    if path == "/api/v1/core/organization":
        from services.core_empresarial import arvore_organizacional
        return HTTPStatus.OK, {"ok": True, "data": arvore_organizacional(ator), "request_id": request_id}
    if path == "/api/v1/core/people":
        from services.core_empresarial import listar_pessoas
        page, page_size = _paginacao(qs)
        resultado = listar_pessoas(ator, papel=_texto_query(qs, "role") or None, pesquisa=_texto_query(qs, "q"), pagina=page, tamanho=page_size)
        return HTTPStatus.OK, _envelope_paginado(resultado["itens"], resultado["total"], page, page_size, request_id)
    if path == "/api/v1/operations/types":
        from services.operacoes_v11 import listar_tipos
        return HTTPStatus.OK, {"ok": True, "data": listar_tipos(ator, modulo=_texto_query(qs, "module") or None), "request_id": request_id}
    if path == "/api/v1/operations/records":
        from services.operacoes_v11 import listar_registros
        page, page_size = _paginacao(qs)
        resultado = listar_registros(
            ator, modulo=_texto_query(qs, "module") or None, tipo=_texto_query(qs, "type") or None,
            status=_texto_query(qs, "status") or None, pesquisa=_texto_query(qs, "q"), pagina=page, tamanho=page_size,
            estado=_texto_query(qs, "state", "Ativo"),
        )
        return HTTPStatus.OK, _envelope_paginado(resultado["itens"], resultado["total"], page, page_size, request_id)
    if path == "/api/v1/operations/summary":
        from services.operacoes_v11 import resumo_operacional
        return HTTPStatus.OK, {"ok": True, "data": resumo_operacional(ator), "request_id": request_id}
    match = re.fullmatch(r"/api/v1/operations/records/(\d+)", path)
    if match:
        from services.operacoes_v11 import obter_registro
        return HTTPStatus.OK, {"ok": True, "data": obter_registro(int(match.group(1)), ator), "request_id": request_id}
    if path == "/api/v1/employees/me/360":
        from services.funcionario_360 import obter_meu_funcionario_360
        return HTTPStatus.OK, {"ok": True, "data": obter_meu_funcionario_360(ator), "request_id": request_id}
    match = re.fullmatch(r"/api/v1/employees/(\d+)/360", path)
    if match:
        from services.funcionario_360 import obter_funcionario_360
        return HTTPStatus.OK, {"ok": True, "data": obter_funcionario_360(
            int(match.group(1)), ator, visao=_texto_query(qs, "view") or None, request_id=request_id,
        ), "request_id": request_id}
    if path == "/api/v1/core/transfers":
        from services.core_empresarial import listar_transferencias
        return HTTPStatus.OK, {"ok": True, "data": listar_transferencias(
            ator, modulo=_texto_query(qs, "module") or None, limite=_inteiro(_texto_query(qs, "limit", "100"), 100, 1, 1000),
        ), "request_id": request_id}
    return None


def _validar_objeto(dados: Any) -> dict:
    if not isinstance(dados, dict):
        raise APIError(HTTPStatus.BAD_REQUEST, "invalid_payload", "O corpo deve ser um objeto JSON.")
    return dados


def dispatch_post(path: str, dados: dict, sessao, request_id: str) -> tuple[int, dict] | None:
    from servidor_corporativo.dto import validar_payload
    ator = sessao.ator(); dados = validar_payload(path, _validar_objeto(dados))
    if path == "/api/v1/crm/leads":
        from services.crm import criar_lead
        iid = criar_lead(dados, ator)
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}, "request_id": request_id}
    if path == "/api/v1/comercial/oportunidades":
        from services.departamentos.comercial import criar_oportunidade
        iid = criar_oportunidade(dados, ator)
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}, "request_id": request_id}
    if path == "/api/v1/marketing/campanhas":
        from services.departamentos.marketing import criar_campanha
        iid = criar_campanha(dados, ator)
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}, "request_id": request_id}
    if path == "/api/v1/juridico/processos":
        from services.departamentos.juridico import criar_processo
        iid = criar_processo(dados, ator)
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}, "request_id": request_id}
    if path == "/api/v1/administrativo/solicitacoes":
        from services.departamentos.administrativo import criar_solicitacao
        iid = criar_solicitacao(dados, ator)
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}, "request_id": request_id}
    if path == "/api/v1/analytics/insights/refresh":
        from services.analytics import gerar_insights
        return HTTPStatus.OK, {"ok": True, "data": gerar_insights(ator, persistir=True), "request_id": request_id}
    if path == "/api/v1/crm/leads/to-opportunity":
        from services.orquestracao import converter_lead_em_oportunidade
        lead_id = int(dados.get("lead_id") or 0)
        if not lead_id:
            raise APIError(HTTPStatus.BAD_REQUEST, "lead_required", "lead_id é obrigatório.")
        return HTTPStatus.CREATED, {"ok": True, "data": converter_lead_em_oportunidade(lead_id, dados, ator), "request_id": request_id}
    if path == "/api/v1/core/people":
        from services.core_empresarial import criar_pessoa
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": criar_pessoa(dados, ator, modulo=str(dados.pop("modulo", "rh")))}, "request_id": request_id}
    if path == "/api/v1/core/calendar":
        from services.core_empresarial import criar_evento_calendario
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": criar_evento_calendario(dados, ator)}, "request_id": request_id}
    if path == "/api/v1/core/dashboards":
        from services.core_empresarial import salvar_dashboard
        resultado = salvar_dashboard(dados, ator, dashboard_id=dados.pop("id", None), expected_version=dados.pop("expected_version", None))
        return HTTPStatus.CREATED, {"ok": True, "data": resultado, "request_id": request_id}
    if path == "/api/v1/core/comments":
        from services.core_empresarial import adicionar_comentario
        iid = adicionar_comentario(
            str(dados.get("recurso_tipo") or ""), int(dados.get("recurso_id") or 0),
            str(dados.get("comentario") or ""), ator, modulo=str(dados.get("modulo") or ""),
            comentario_pai_id=int(dados["resposta_a_id"]) if dados.get("resposta_a_id") else None,
        )
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}, "request_id": request_id}
    if path == "/api/v1/core/search/reindex":
        from services.core_empresarial import reindexar_core
        return HTTPStatus.OK, {"ok": True, "data": reindexar_core(ator), "request_id": request_id}
    if path == "/api/v1/operations/types":
        from services.operacoes_v11 import salvar_tipo
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": salvar_tipo(dados, ator)}, "request_id": request_id}
    if path == "/api/v1/operations/records":
        from services.operacoes_v11 import criar_registro
        modulo = str(dados.pop("modulo", "")); codigo_tipo = str(dados.pop("tipo", ""))
        return HTTPStatus.CREATED, {"ok": True, "data": criar_registro(modulo, codigo_tipo, dados, ator), "request_id": request_id}
    match = re.fullmatch(r"/api/v1/operations/records/(\d+)/transition", path)
    if match:
        from services.operacoes_v11 import avancar_fluxo
        resultado = avancar_fluxo(
            int(match.group(1)), ator, expected_version=int(dados.get("expected_version") or 0),
            aprovar=bool(dados.get("approve")), observacao=str(dados.get("note") or ""),
        )
        return HTTPStatus.OK, {"ok": True, "data": resultado, "request_id": request_id}
    if path == "/api/v1/operations/relations":
        from services.operacoes_v11 import relacionar_registros
        iid = relacionar_registros(
            str(dados.get("origem_tipo") or ""), int(dados.get("origem_id") or 0), str(dados.get("relacao") or ""),
            str(dados.get("destino_tipo") or ""), int(dados.get("destino_id") or 0), ator, dados=dados.get("dados") or {},
        )
        return HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}, "request_id": request_id}
    match = re.fullmatch(r"/api/v1/employees/(\d+)/(avatar|access|feedback|cost|occurrence)", path)
    if match:
        from services import funcionario_360 as servico
        colaborador_id = int(match.group(1)); acao = match.group(2)
        if acao == "avatar":
            try:
                bruto = base64.b64decode(str(dados.get("content_base64") or ""), validate=True)
            except (ValueError, TypeError):
                raise APIError(HTTPStatus.BAD_REQUEST, "invalid_file", "content_base64 inválido.") from None
            resultado = servico.registrar_avatar_bytes(
                colaborador_id, bruto, str(dados.get("name") or "avatar.jpg"), ator, mime_type=dados.get("mime_type"),
            )
        else:
            funcoes = {"access": servico.registrar_acesso, "feedback": servico.registrar_feedback,
                       "cost": servico.registrar_custo, "occurrence": servico.registrar_ocorrencia}
            resultado = {"id": funcoes[acao](colaborador_id, dados, ator)}
        return HTTPStatus.CREATED, {"ok": True, "data": resultado, "request_id": request_id}
    if path == "/api/v1/core/transfers/export":
        from services.core_empresarial import exportar_registros
        resultado = exportar_registros(
            str(dados.get("modulo") or ""), ator, formato=str(dados.get("formato") or "XLSX"),
            tipo=dados.get("tipo"), status=dados.get("status"), pesquisa=str(dados.get("pesquisa") or ""),
        )
        return HTTPStatus.CREATED, {"ok": True, "data": resultado, "request_id": request_id}
    if path == "/api/v1/core/transfers/import":
        from services.core_empresarial import importar_registros_bytes
        try:
            bruto = base64.b64decode(str(dados.get("content_base64") or ""), validate=True)
        except (ValueError, TypeError):
            raise APIError(HTTPStatus.BAD_REQUEST, "invalid_file", "content_base64 inválido.") from None
        resultado = importar_registros_bytes(
            str(dados.get("modulo") or ""), str(dados.get("tipo") or ""), bruto,
            str(dados.get("name") or "importacao.csv"), ator, formato=dados.get("formato"),
            mapeamento=dados.get("mapeamento") or {}, continuar_com_erros=bool(dados.get("continuar_com_erros", True)),
        )
        return HTTPStatus.CREATED, {"ok": True, "data": resultado, "request_id": request_id}
    return None


PUBLIC_ENDPOINTS = tuple(sorted(set(_GET_LISTAS) | {
    "/api/v1/analytics/executive", "/api/v1/analytics/insights/refresh", "/api/v1/orquestracoes",
    "/api/v1/crm/leads/to-opportunity", "/api/v1/core/search", "/api/v1/core/inbox",
    "/api/v1/core/calendar", "/api/v1/core/dashboards", "/api/v1/core/organization", "/api/v1/core/people",
    "/api/v1/core/comments", "/api/v1/core/search/reindex", "/api/v1/core/transfers",
    "/api/v1/core/transfers/export", "/api/v1/core/transfers/import", "/api/v1/operations/types",
    "/api/v1/operations/records", "/api/v1/operations/relations", "/api/v1/operations/summary",
    "/api/v1/employees/me/360",
}))


def eh_endpoint_publico(path: str) -> bool:
    return path in PUBLIC_ENDPOINTS or bool(re.fullmatch(
        r"/api/v1/(?:operations/records/\d+(?:/transition)?|employees/\d+/(?:360|avatar|access|feedback|cost|occurrence))",
        str(path),
    ))

__all__=("APIError","PUBLIC_ENDPOINTS","dispatch_get","dispatch_post","eh_endpoint_publico","erro_payload")
