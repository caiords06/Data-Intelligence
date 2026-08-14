"""Inteligência empresarial integrada — V10.4.0/V10.4.1.

O Analytics deixa de depender apenas de arquivos importados e passa a ler os
resumos operacionais dos módulos especializados. A camada produz insights
explicáveis, persistentes e acionáveis sem executar decisões irreversíveis de
forma automática.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
import hashlib
import json
import time
from typing import Any, Callable

from auth.banco import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator, tem_permissao


SEVERIDADES = ("Informativa", "Atenção", "Crítica")
_STATUS_INSIGHT = ("Ativo", "Resolvido", "Ignorado")


@dataclass(frozen=True)
class Insight:
    modulo: str
    codigo: str
    titulo: str
    descricao: str
    severidade: str = "Atenção"
    prioridade: int = 50
    metrica_chave: str | None = None
    metrica_valor: float | int | None = None
    unidade: str | None = None
    acao_modulo: str | None = None
    acao_secao: str | None = None
    acao_rotulo: str | None = None
    tipo: str = "Regra"

    def serializar(self) -> dict[str, Any]:
        return asdict(self)


def _agora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _escopo(ator: dict) -> tuple[int, int | None]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    return int(empresa_id), int(filial_id) if filial_id is not None else None


def _fingerprint(empresa_id: int, filial_id: int | None, insight: Insight) -> str:
    base = f"{empresa_id}:{filial_id or 0}:{insight.modulo}:{insight.codigo}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _safe(nome: str, funcao: Callable[[], Any]) -> tuple[Any | None, dict | None]:
    try:
        return funcao(), None
    except PermissionError as exc:
        return None, {"modulo": nome, "tipo": "permissao", "erro": str(exc)}
    except Exception as exc:  # isolamento: um módulo não derruba o cockpit inteiro
        return None, {"modulo": nome, "tipo": type(exc).__name__, "erro": str(exc)}


def _carregadores() -> dict[str, tuple[Callable[[dict], dict], Callable[[dict], dict]]]:
    # imports tardios evitam ciclos e mantêm o custo de startup baixo.
    from enterprise.financeiro import resumo_financeiro, analisar_financeiro
    from enterprise.rh import resumo_rh, analisar_rh
    from enterprise.compras import resumo_compras, analisar_compras
    from enterprise.estoque import resumo_estoque, analisar_estoque
    from enterprise.tecnologia import resumo_tecnologia, analisar_tecnologia
    from enterprise.marketing import resumo_marketing, analisar_marketing
    from enterprise.comercial import resumo_comercial, analisar_comercial
    from enterprise.administrativo import resumo_administrativo, analisar_administrativo
    from enterprise.juridico import resumo_juridico, analisar_juridico

    return {
        "financeiro": (resumo_financeiro, analisar_financeiro),
        "rh": (resumo_rh, analisar_rh),
        "compras": (resumo_compras, analisar_compras),
        "estoque": (resumo_estoque, analisar_estoque),
        "ti": (resumo_tecnologia, analisar_tecnologia),
        "marketing": (resumo_marketing, analisar_marketing),
        "comercial": (resumo_comercial, analisar_comercial),
        "administrativo": (resumo_administrativo, analisar_administrativo),
        "juridico": (resumo_juridico, analisar_juridico),
    }


def obter_painel_executivo(ator: dict) -> dict:
    """Agrega somente módulos que o ator pode ler, sem vazar dados restritos."""
    exigir_permissao(ator, "analytics", "ler")
    inicio = time.perf_counter()
    modulos: dict[str, dict] = {}
    erros: list[dict] = []

    for modulo, (resumo_fn, analise_fn) in _carregadores().items():
        if not tem_permissao(ator, modulo, "ler"):
            continue
        resumo, erro = _safe(modulo, lambda f=resumo_fn: f(ator))
        if erro:
            erros.append(erro)
            continue
        analise, erro_analise = _safe(modulo, lambda f=analise_fn: f(ator))
        if erro_analise:
            erros.append(erro_analise)
            analise = {}
        modulos[modulo] = {
            "resumo": resumo or {},
            "analise": analise or {},
        }

    total_alertas = 0
    for dados in modulos.values():
        analise = dados.get("analise") or {}
        alertas = (
            analise.get("alertas")
            or analise.get("pontos_atencao")
            or analise.get("pontos")
            or []
        )
        total_alertas += len([x for x in alertas if x])

    return {
        "modulos": modulos,
        "modulos_processados": len(modulos),
        "alertas_origem": total_alertas,
        "erros": erros,
        "duracao_ms": int((time.perf_counter() - inicio) * 1000),
        "gerado_em": _agora(),
    }


def _add(lista: list[Insight], *, modulo: str, codigo: str, titulo: str, descricao: str,
         severidade: str = "Atenção", prioridade: int = 50, metrica_chave: str | None = None,
         metrica_valor: float | int | None = None, unidade: str | None = None,
         acao_secao: str | None = None, acao_rotulo: str | None = None,
         acao_modulo: str | None = None, tipo: str = "Regra") -> None:
    lista.append(Insight(
        modulo=modulo, codigo=codigo, titulo=titulo, descricao=descricao,
        severidade=severidade if severidade in SEVERIDADES else "Atenção",
        prioridade=max(0, min(100, int(prioridade))), metrica_chave=metrica_chave,
        metrica_valor=metrica_valor, unidade=unidade, acao_modulo=acao_modulo or modulo,
        acao_secao=acao_secao, acao_rotulo=acao_rotulo, tipo=tipo,
    ))


def _regras_financeiro(resumo: dict, analise: dict, out: list[Insight]) -> None:
    if resumo.get("risco_caixa"):
        valor = int(resumo.get("saldo_minimo_projetado_centavos") or 0)
        _add(out, modulo="financeiro", codigo="caixa_negativo", titulo="Caixa projetado abaixo de zero",
             descricao=f"A projeção aponta saldo mínimo de R$ {valor/100:,.2f} em {resumo.get('data_saldo_minimo') or 'data futura'}.",
             severidade="Crítica", prioridade=95, metrica_chave="saldo_minimo_projetado_centavos", metrica_valor=valor,
             unidade="centavos", acao_secao="fluxo", acao_rotulo="VER FLUXO DE CAIXA")
    vencidas = int(resumo.get("vencidas") or 0)
    if vencidas:
        _add(out, modulo="financeiro", codigo="contas_vencidas", titulo="Obrigações vencidas exigem atenção",
             descricao=f"Há {vencidas} obrigação(ões) vencida(s) no contexto atual.", severidade="Crítica", prioridade=90,
             metrica_chave="vencidas", metrica_valor=vencidas, unidade="itens", acao_secao="pagar", acao_rotulo="VER CONTAS")
    proximas = int(resumo.get("proximos_sete") or 0)
    if proximas:
        _add(out, modulo="financeiro", codigo="vencimentos_7_dias", titulo="Vencimentos concentrados nos próximos 7 dias",
             descricao=f"{proximas} conta(s) vencem nos próximos sete dias.", prioridade=65,
             metrica_chave="proximos_sete", metrica_valor=proximas, unidade="itens", acao_secao="pagar", acao_rotulo="REVISAR VENCIMENTOS")
    if int(resumo.get("despesas_centavos") or 0) > int(resumo.get("receitas_centavos") or 0):
        diferenca = int(resumo.get("despesas_centavos") or 0) - int(resumo.get("receitas_centavos") or 0)
        _add(out, modulo="financeiro", codigo="despesa_acima_receita", titulo="Despesas superam receitas no período",
             descricao=f"A diferença corrente é de R$ {diferenca/100:,.2f}.", prioridade=70,
             metrica_chave="gap_resultado_centavos", metrica_valor=diferenca, unidade="centavos", acao_secao="dre", acao_rotulo="ABRIR DRE")


def _regras_rh(resumo: dict, _analise: dict, out: list[Insight]) -> None:
    ferias = int(resumo.get("ferias_pendentes") or 0)
    if ferias:
        _add(out, modulo="rh", codigo="ferias_pendentes", titulo="Férias e ausências aguardam decisão",
             descricao=f"Existem {ferias} solicitação(ões) pendentes.", prioridade=60,
             metrica_chave="ferias_pendentes", metrica_valor=ferias, unidade="itens", acao_secao="ferias", acao_rotulo="REVISAR SOLICITAÇÕES")
    docs = int(resumo.get("documentos_vencendo") or 0)
    if docs:
        _add(out, modulo="rh", codigo="documentos_vencendo", titulo="Documentos de colaboradores vencem em até 30 dias",
             descricao=f"{docs} documento(s) exigem conferência ou renovação.", severidade="Crítica" if docs >= 5 else "Atenção",
             prioridade=78, metrica_chave="documentos_vencendo", metrica_valor=docs, unidade="itens", acao_secao="documentos", acao_rotulo="VER DOCUMENTOS")
    tarefas = int(resumo.get("tarefas_pendentes") or 0)
    if tarefas >= 3:
        _add(out, modulo="rh", codigo="tarefas_pendentes", titulo="Backlog operacional de RH",
             descricao=f"Há {tarefas} tarefa(s) de RH ainda pendentes.", prioridade=55,
             metrica_chave="tarefas_pendentes", metrica_valor=tarefas, unidade="itens", acao_secao="solicitacoes", acao_rotulo="VER PENDÊNCIAS")


def _regras_compras(resumo: dict, _analise: dict, out: list[Insight]) -> None:
    for chave, codigo, titulo, secao, prioridade, severidade in (
        ("urgentes", "demandas_urgentes", "Solicitações urgentes aguardam Compras", "solicitacoes", 85, "Crítica"),
        ("aguardando_aprovacao", "aprovacoes_pendentes", "Solicitações aguardam aprovação", "aprovacoes", 65, "Atenção"),
        ("entregas_atrasadas", "entregas_atrasadas", "Pedidos com entrega atrasada", "entregas", 90, "Crítica"),
        ("divergencias", "divergencias_abertas", "Divergências de recebimento abertas", "divergencias", 88, "Crítica"),
        ("contratos_vencendo", "contratos_vencendo", "Contratos de fornecedores vencem em até 30 dias", "contratos", 70, "Atenção"),
    ):
        valor = int(resumo.get(chave) or 0)
        if valor:
            _add(out, modulo="compras", codigo=codigo, titulo=titulo, descricao=f"Foram identificados {valor} registro(s) neste indicador.",
                 severidade=severidade, prioridade=prioridade, metrica_chave=chave, metrica_valor=valor, unidade="itens",
                 acao_secao=secao, acao_rotulo="ABRIR COMPRAS")


def _regras_estoque(resumo: dict, analise: dict, out: list[Insight]) -> None:
    zerados = int(resumo.get("zerados") or 0)
    criticos = int(resumo.get("criticos") or 0)
    vencendo = int(resumo.get("vencendo") or 0)
    if zerados:
        _add(out, modulo="estoque", codigo="itens_zerados", titulo="Itens sem estoque disponível",
             descricao=f"{zerados} item(ns) estão zerados e podem interromper a operação.", severidade="Crítica", prioridade=98,
             metrica_chave="zerados", metrica_valor=zerados, unidade="itens", acao_secao="alertas", acao_rotulo="VER ITENS CRÍTICOS")
    if criticos:
        _add(out, modulo="estoque", codigo="abaixo_minimo", titulo="Estoque abaixo do mínimo",
             descricao=f"{criticos} item(ns) estão abaixo do estoque mínimo configurado.", severidade="Crítica", prioridade=92,
             metrica_chave="criticos", metrica_valor=criticos, unidade="itens", acao_secao="reposicao", acao_rotulo="PLANEJAR REPOSIÇÃO")
    if vencendo:
        _add(out, modulo="estoque", codigo="lotes_vencendo", titulo="Lotes próximos do vencimento",
             descricao=f"{vencendo} lote(s) vencem nos próximos 30 dias.", prioridade=75,
             metrica_chave="vencendo", metrica_valor=vencendo, unidade="lotes", acao_secao="lotes", acao_rotulo="VER LOTES")
    parados = len((analise or {}).get("itens_parados") or [])
    if parados:
        _add(out, modulo="estoque", codigo="itens_parados", titulo="Capital imobilizado em itens sem giro",
             descricao=f"A análise encontrou {parados} item(ns) com saldo e sem movimentação há pelo menos 90 dias.", prioridade=68,
             metrica_chave="itens_parados", metrica_valor=parados, unidade="itens", acao_secao="inteligencia", acao_rotulo="ANALISAR GIRO")


def _regras_ti(resumo: dict, _analise: dict, out: list[Insight]) -> None:
    offline = int(resumo.get("offline") or 0)
    criticos = int(resumo.get("chamados_criticos") or 0)
    sla = int(resumo.get("sla_vencido") or 0)
    indisponiveis = int(resumo.get("sistemas_indisponiveis") or 0)
    if offline:
        _add(out, modulo="ti", codigo="ativos_offline", titulo="Ativos corporativos offline",
             descricao=f"{offline} ativo(s) conhecidos estão offline.", severidade="Crítica" if offline >= 3 else "Atenção", prioridade=88,
             metrica_chave="offline", metrica_valor=offline, unidade="ativos", acao_secao="ativos", acao_rotulo="VER ATIVOS")
    if criticos:
        _add(out, modulo="ti", codigo="chamados_criticos", titulo="Chamados críticos abertos",
             descricao=f"Existem {criticos} chamado(s) de prioridade crítica ainda abertos.", severidade="Crítica", prioridade=95,
             metrica_chave="chamados_criticos", metrica_valor=criticos, unidade="chamados", acao_secao="chamados", acao_rotulo="ABRIR SERVICE DESK")
    if sla:
        _add(out, modulo="ti", codigo="sla_vencido", titulo="SLA de solução ultrapassado",
             descricao=f"{sla} chamado(s) já ultrapassaram o SLA.", severidade="Crítica", prioridade=96,
             metrica_chave="sla_vencido", metrica_valor=sla, unidade="chamados", acao_secao="chamados", acao_rotulo="PRIORIZAR CHAMADOS")
    if indisponiveis:
        _add(out, modulo="ti", codigo="sistemas_indisponiveis", titulo="Sistemas corporativos indisponíveis",
             descricao=f"{indisponiveis} sistema(s) monitorado(s) não estão operacionais.", severidade="Crítica", prioridade=100,
             metrica_chave="sistemas_indisponiveis", metrica_valor=indisponiveis, unidade="sistemas", acao_secao="monitoramento", acao_rotulo="ABRIR MONITORAMENTO")


def _regras_marketing(resumo: dict, _analise: dict, out: list[Insight]) -> None:
    ativas = int(resumo.get("campanhas_ativas") or 0)
    leads = int(resumo.get("leads") or 0)
    mqls = int(resumo.get("mqls") or 0)
    roas = float(resumo.get("roas") or 0)
    investimento = int(resumo.get("investimento_centavos") or 0)
    if ativas and not leads:
        _add(out, modulo="marketing", codigo="campanha_sem_leads", titulo="Campanhas ativas sem geração de leads",
             descricao=f"Há {ativas} campanha(s) ativa(s), mas nenhum lead foi registrado.", severidade="Crítica", prioridade=85,
             metrica_chave="leads", metrica_valor=leads, unidade="leads", acao_secao="campanhas", acao_rotulo="REVISAR CAMPANHAS")
    if investimento and roas < 1:
        _add(out, modulo="marketing", codigo="roas_abaixo_1", titulo="Retorno de Marketing abaixo do investimento",
             descricao=f"O ROAS atual é {roas:.2f}. Receita atribuída está abaixo do investimento registrado.", severidade="Crítica", prioridade=90,
             metrica_chave="roas", metrica_valor=roas, unidade="x", acao_secao="atribuicao", acao_rotulo="ANALISAR ATRIBUIÇÃO")
    if leads and not mqls:
        _add(out, modulo="marketing", codigo="leads_sem_mql", titulo="Leads ainda não qualificados",
             descricao=f"Há {leads} lead(s), mas nenhum atingiu MQL.", prioridade=65,
             metrica_chave="mqls", metrica_valor=0, unidade="leads", acao_secao="leads", acao_rotulo="QUALIFICAR LEADS")


def _regras_comercial(resumo: dict, _analise: dict, out: list[Insight], ator: dict) -> None:
    meta = int(resumo.get("meta_centavos") or 0)
    ponderado = int(resumo.get("ponderado_centavos") or 0)
    abertas = int(resumo.get("abertas") or 0)
    if meta and ponderado < meta:
        gap = meta - ponderado
        _add(out, modulo="comercial", codigo="forecast_abaixo_meta", titulo="Forecast comercial abaixo da meta",
             descricao=f"O pipeline ponderado está R$ {gap/100:,.2f} abaixo da meta cadastrada.", severidade="Crítica", prioridade=92,
             metrica_chave="gap_meta_centavos", metrica_valor=gap, unidade="centavos", acao_secao="forecast", acao_rotulo="ABRIR FORECAST")
    if abertas:
        try:
            from enterprise.comercial import listar_oportunidades
            limite = datetime.now(timezone.utc) - timedelta(days=20)
            paradas = []
            for item in listar_oportunidades(ator, status="Aberta", limite=2000):
                bruto = item.get("atualizado_em") or item.get("criado_em")
                if not bruto:
                    continue
                try:
                    data = datetime.fromisoformat(str(bruto).replace("Z", "+00:00"))
                    if data.tzinfo is None:
                        data = data.replace(tzinfo=timezone.utc)
                    if data < limite:
                        paradas.append(item)
                except ValueError:
                    continue
            if paradas:
                valor = sum(int(x.get("valor_centavos") or 0) for x in paradas)
                _add(out, modulo="comercial", codigo="oportunidades_paradas_20d", titulo="Oportunidades sem evolução há mais de 20 dias",
                     descricao=f"{len(paradas)} oportunidade(s), totalizando R$ {valor/100:,.2f}, estão paradas no pipeline.",
                     severidade="Crítica" if len(paradas) >= 5 else "Atenção", prioridade=87,
                     metrica_chave="oportunidades_paradas", metrica_valor=len(paradas), unidade="oportunidades",
                     acao_secao="pipeline", acao_rotulo="ABRIR PIPELINE")
        except (PermissionError, RuntimeError):
            pass


def _regras_administrativo(resumo: dict, _analise: dict, out: list[Insight]) -> None:
    criticas = int(resumo.get("criticas") or 0)
    abertas = int(resumo.get("abertas") or 0)
    reemb = int(resumo.get("reembolsos_pendentes") or 0)
    if criticas:
        _add(out, modulo="administrativo", codigo="solicitacoes_criticas", titulo="Solicitações administrativas críticas",
             descricao=f"{criticas} solicitação(ões) de alta criticidade aguardam tratamento.", severidade="Crítica", prioridade=88,
             metrica_chave="criticas", metrica_valor=criticas, unidade="solicitações", acao_secao="solicitacoes", acao_rotulo="TRATAR SOLICITAÇÕES")
    if abertas >= 10:
        _add(out, modulo="administrativo", codigo="backlog_solicitacoes", titulo="Backlog administrativo elevado",
             descricao=f"Há {abertas} solicitações administrativas abertas.", prioridade=67,
             metrica_chave="abertas", metrica_valor=abertas, unidade="solicitações", acao_secao="solicitacoes", acao_rotulo="VER BACKLOG")
    if reemb >= 5:
        _add(out, modulo="administrativo", codigo="reembolsos_pendentes", titulo="Fila de reembolsos requer revisão",
             descricao=f"{reemb} reembolso(s) aguardam tratamento.", prioridade=72,
             metrica_chave="reembolsos_pendentes", metrica_valor=reemb, unidade="reembolsos", acao_secao="reembolsos", acao_rotulo="REVISAR REEMBOLSOS")


def _regras_juridico(resumo: dict, _analise: dict, out: list[Insight]) -> None:
    prazos = int(resumo.get("prazos_30_dias") or 0)
    riscos = int(resumo.get("riscos_abertos") or 0)
    exposicao = int(resumo.get("exposicao_centavos") or 0)
    provisoes = int(resumo.get("provisoes_centavos") or 0)
    if prazos:
        _add(out, modulo="juridico", codigo="prazos_30_dias", titulo="Prazos jurídicos próximos",
             descricao=f"{prazos} prazo(s) vencem nos próximos 30 dias.", severidade="Crítica" if prazos >= 3 else "Atenção", prioridade=94,
             metrica_chave="prazos_30_dias", metrica_valor=prazos, unidade="prazos", acao_secao="prazos", acao_rotulo="ABRIR AGENDA JURÍDICA")
    if riscos and exposicao:
        _add(out, modulo="juridico", codigo="exposicao_juridica", titulo="Exposição financeira jurídica registrada",
             descricao=f"Existem {riscos} risco(s) aberto(s), com exposição registrada de R$ {exposicao/100:,.2f}.", severidade="Crítica", prioridade=90,
             metrica_chave="exposicao_centavos", metrica_valor=exposicao, unidade="centavos", acao_secao="riscos", acao_rotulo="REVISAR RISCOS")
    if exposicao and provisoes < exposicao:
        gap = exposicao - provisoes
        _add(out, modulo="juridico", codigo="gap_provisao", titulo="Exposição jurídica maior que provisões registradas",
             descricao=f"Há R$ {gap/100:,.2f} de diferença entre exposição e provisões ativas.", prioridade=82,
             metrica_chave="gap_provisao_centavos", metrica_valor=gap, unidade="centavos", acao_secao="provisoes", acao_rotulo="REVISAR PROVISÕES")


def _regras_transversais(painel: dict, out: list[Insight]) -> None:
    mod = painel.get("modulos") or {}
    marketing = (mod.get("marketing") or {}).get("resumo") or {}
    comercial = (mod.get("comercial") or {}).get("resumo") or {}
    estoque = (mod.get("estoque") or {}).get("resumo") or {}
    compras = (mod.get("compras") or {}).get("resumo") or {}
    juridico = (mod.get("juridico") or {}).get("resumo") or {}

    mqls = int(marketing.get("mqls") or 0)
    abertas = int(comercial.get("abertas") or 0)
    if mqls >= 3 and abertas == 0:
        _add(out, modulo="comercial", codigo="mql_sem_pipeline", titulo="MQLs ainda não chegaram ao pipeline comercial",
             descricao=f"Marketing possui {mqls} MQL(s), enquanto o Comercial não possui oportunidade aberta.", severidade="Crítica", prioridade=91,
             metrica_chave="mqls_sem_pipeline", metrica_valor=mqls, unidade="leads", acao_modulo="marketing", acao_secao="leads",
             acao_rotulo="REVISAR REPASSE MARKETING → COMERCIAL", tipo="Transversal")

    criticos = int(estoque.get("criticos") or 0) + int(estoque.get("zerados") or 0)
    demandas = int(compras.get("solicitacoes_abertas") or 0)
    if criticos and demandas == 0:
        _add(out, modulo="estoque", codigo="estoque_sem_demanda_compra", titulo="Ruptura de estoque sem demanda de compra aberta",
             descricao=f"Há {criticos} item(ns) crítico(s)/zerado(s) e nenhuma solicitação de compra aberta.", severidade="Crítica", prioridade=97,
             metrica_chave="itens_sem_reposicao", metrica_valor=criticos, unidade="itens", acao_modulo="estoque", acao_secao="reposicao",
             acao_rotulo="GERAR REPOSIÇÃO", tipo="Transversal")

    exposicao = int(juridico.get("exposicao_centavos") or 0)
    provisoes = int(juridico.get("provisoes_centavos") or 0)
    if exposicao and provisoes < exposicao * 0.5:
        _add(out, modulo="juridico", codigo="provisao_financeira_baixa", titulo="Cobertura de provisão jurídica inferior a 50% da exposição",
             descricao="Jurídico e Financeiro devem revisar juntos o impacto provável e o calendário de provisões.", severidade="Crítica", prioridade=93,
             metrica_chave="cobertura_provisao", metrica_valor=round(provisoes / exposicao * 100, 1), unidade="%",
             acao_modulo="juridico", acao_secao="provisoes", acao_rotulo="REVISAR PROVISÕES", tipo="Transversal")


def _aplicar_regras_customizadas(ator: dict, painel: dict, out: list[Insight]) -> None:
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        rows = con.execute(
            """SELECT * FROM analytics_regras WHERE empresa_id=? AND ativo=1
               AND (filial_id=? OR filial_id IS NULL) ORDER BY id""",
            (empresa_id, filial_id),
        ).fetchall()
    for row in rows:
        regra = dict(row)
        modulo = str(regra.get("modulo") or "").strip().lower()
        dados = ((painel.get("modulos") or {}).get(modulo) or {}).get("resumo") or {}
        metrica = str(regra.get("metrica") or "")
        if metrica not in dados:
            continue
        try:
            atual = float(dados[metrica])
            limite = float(regra.get("limite") or 0)
        except (TypeError, ValueError):
            continue
        op = str(regra.get("operador") or ">").strip()
        atende = {
            ">": atual > limite, ">=": atual >= limite, "<": atual < limite,
            "<=": atual <= limite, "=": atual == limite, "==": atual == limite,
            "!=": atual != limite,
        }.get(op, False)
        if not atende:
            continue
        _add(out, modulo=modulo, codigo=f"custom_{regra['id']}_{regra['codigo']}", titulo=str(regra["nome"]),
             descricao=f"Regra personalizada disparada: {metrica} {op} {limite:g}. Valor atual: {atual:g}.",
             severidade=str(regra.get("severidade") or "Atenção"), prioridade=75,
             metrica_chave=metrica, metrica_valor=atual, acao_modulo=regra.get("acao_modulo") or modulo,
             acao_secao=regra.get("acao_secao"), acao_rotulo="ABRIR CONTEXTO", tipo="Regra personalizada")


def _persistir(ator: dict, insights: list[Insight], *, duracao_ms: int, erros: int, modulos: int) -> list[dict]:
    empresa_id, filial_id = _escopo(ator)
    agora = _agora()
    ativos: set[str] = set()
    with conectar() as con:
        for insight in insights:
            fp = _fingerprint(empresa_id, filial_id, insight)
            ativos.add(fp)
            con.execute(
                """INSERT INTO analytics_insights
                   (empresa_id,filial_id,modulo,codigo,titulo,descricao,severidade,prioridade,tipo,
                    metrica_chave,metrica_valor,unidade,acao_tipo,acao_modulo,acao_secao,acao_rotulo,
                    fingerprint,status,detectado_em,atualizado_em,criado_por)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'Ativo',?,?,?)
                   ON CONFLICT(fingerprint) DO UPDATE SET
                    titulo=excluded.titulo,descricao=excluded.descricao,severidade=excluded.severidade,
                    prioridade=excluded.prioridade,tipo=excluded.tipo,metrica_chave=excluded.metrica_chave,
                    metrica_valor=excluded.metrica_valor,unidade=excluded.unidade,acao_modulo=excluded.acao_modulo,
                    acao_secao=excluded.acao_secao,acao_rotulo=excluded.acao_rotulo,status='Ativo',
                    resolvido_em=NULL,resolvido_por=NULL,atualizado_em=excluded.atualizado_em""",
                (empresa_id, filial_id, insight.modulo, insight.codigo, insight.titulo, insight.descricao,
                 insight.severidade, insight.prioridade, insight.tipo, insight.metrica_chave,
                 insight.metrica_valor, insight.unidade, "navegar", insight.acao_modulo,
                 insight.acao_secao, insight.acao_rotulo, fp, agora, agora, int(ator["id"])),
            )
        # Insights automáticos que não reapareceram nesta execução deixam de poluir a fila.
        rows = con.execute(
            """SELECT id,fingerprint FROM analytics_insights WHERE empresa_id=?
               AND (filial_id=? OR filial_id IS NULL) AND status='Ativo'""",
            (empresa_id, filial_id),
        ).fetchall()
        for row in rows:
            if str(row["fingerprint"]) not in ativos:
                con.execute(
                    "UPDATE analytics_insights SET status='Resolvido',resolvido_em=?,atualizado_em=? WHERE id=?",
                    (agora, agora, int(row["id"])),
                )
        con.execute(
            """INSERT INTO analytics_execucoes
               (empresa_id,filial_id,origem,modulos_processados,insights_gerados,erros,duracao_ms,criado_por)
               VALUES (?,?, 'empresarial', ?,?,?,?,?)""",
            (empresa_id, filial_id, int(modulos), len(insights), int(erros), int(duracao_ms), int(ator["id"])),
        )
    return listar_insights(ator, status="Ativo", limite=500)


def gerar_insights(ator: dict, *, persistir: bool = True) -> dict:
    exigir_permissao(ator, "analytics", "ler")
    inicio = time.perf_counter()
    painel = obter_painel_executivo(ator)
    out: list[Insight] = []
    modulos = painel.get("modulos") or {}

    regras = {
        "financeiro": lambda r, a: _regras_financeiro(r, a, out),
        "rh": lambda r, a: _regras_rh(r, a, out),
        "compras": lambda r, a: _regras_compras(r, a, out),
        "estoque": lambda r, a: _regras_estoque(r, a, out),
        "ti": lambda r, a: _regras_ti(r, a, out),
        "marketing": lambda r, a: _regras_marketing(r, a, out),
        "comercial": lambda r, a: _regras_comercial(r, a, out, ator),
        "administrativo": lambda r, a: _regras_administrativo(r, a, out),
        "juridico": lambda r, a: _regras_juridico(r, a, out),
    }
    for modulo, dados in modulos.items():
        regra = regras.get(modulo)
        if regra:
            regra(dados.get("resumo") or {}, dados.get("analise") or {})
    _regras_transversais(painel, out)
    _aplicar_regras_customizadas(ator, painel, out)

    # Ordem determinística: prioridade, severidade e módulo.
    peso = {"Crítica": 3, "Atenção": 2, "Informativa": 1}
    out.sort(key=lambda x: (-x.prioridade, -peso.get(x.severidade, 0), x.modulo, x.codigo))
    duracao = int((time.perf_counter() - inicio) * 1000)
    if persistir:
        registros = _persistir(ator, out, duracao_ms=duracao, erros=len(painel.get("erros") or []), modulos=len(modulos))
    else:
        empresa_id, filial_id = _escopo(ator)
        registros = []
        for insight in out:
            item = insight.serializar()
            item.update({"fingerprint": _fingerprint(empresa_id, filial_id, insight), "status": "Ativo"})
            registros.append(item)
    return {
        "insights": registros,
        "total": len(registros),
        "criticos": sum(1 for x in registros if x.get("severidade") == "Crítica"),
        "atencao": sum(1 for x in registros if x.get("severidade") == "Atenção"),
        "painel": painel,
        "duracao_ms": duracao,
    }


def _filtro_insights(ator: dict, *, status: str = "Ativo", modulo: str | None = None,
                     severidade: str | None = None) -> tuple[list[str], list[Any]]:
    empresa_id, filial_id = _escopo(ator)
    where = ["empresa_id=?", "(filial_id=? OR filial_id IS NULL)"]
    params: list[Any] = [empresa_id, filial_id]
    if status and status != "Todos":
        if status not in _STATUS_INSIGHT:
            raise ValueError("Status de insight inválido.")
        where.append("status=?")
        params.append(status)
    if modulo:
        where.append("modulo=?")
        params.append(str(modulo).strip().lower())
    if severidade:
        if severidade not in SEVERIDADES:
            raise ValueError("Severidade inválida.")
        where.append("severidade=?")
        params.append(severidade)
    return where, params


def contar_insights(ator: dict, *, status: str = "Ativo", modulo: str | None = None,
                     severidade: str | None = None) -> int:
    exigir_permissao(ator, "analytics", "ler")
    where, params = _filtro_insights(ator, status=status, modulo=modulo, severidade=severidade)
    with conectar() as con:
        row = con.execute(f"SELECT COUNT(*) AS total FROM analytics_insights WHERE {' AND '.join(where)}", tuple(params)).fetchone()
    return int(row["total"] or 0)


def listar_insights(ator: dict, *, status: str = "Ativo", modulo: str | None = None,
                     severidade: str | None = None, limite: int = 200, offset: int = 0) -> list[dict]:
    exigir_permissao(ator, "analytics", "ler")
    where, params = _filtro_insights(ator, status=status, modulo=modulo, severidade=severidade)
    params.extend([max(1, min(5000, int(limite))), max(0, int(offset))])
    with conectar() as con:
        rows = con.execute(
            f"""SELECT * FROM analytics_insights WHERE {' AND '.join(where)}
                ORDER BY prioridade DESC,
                CASE severidade WHEN 'Crítica' THEN 3 WHEN 'Atenção' THEN 2 ELSE 1 END DESC,
                atualizado_em DESC LIMIT ? OFFSET ?""",
            tuple(params),
        ).fetchall()
    return [dict(x) for x in rows]


def alterar_status_insight(insight_id: int, status: str, ator: dict) -> dict:
    exigir_permissao(ator, "analytics", "escrever")
    if status not in {"Resolvido", "Ignorado", "Ativo"}:
        raise ValueError("Status de insight inválido.")
    empresa_id, filial_id = _escopo(ator)
    agora = _agora()
    with conectar() as con:
        cur = con.execute(
            """UPDATE analytics_insights SET status=?, atualizado_em=?,
               resolvido_em=CASE WHEN ?='Ativo' THEN NULL ELSE ? END,
               resolvido_por=CASE WHEN ?='Ativo' THEN NULL ELSE ? END
               WHERE id=? AND empresa_id=? AND (filial_id=? OR filial_id IS NULL)""",
            (status, agora, status, agora, status, int(ator["id"]), int(insight_id), empresa_id, filial_id),
        )
        if cur.rowcount != 1:
            raise ValueError("Insight não encontrado no contexto atual.")
    return {"id": int(insight_id), "status": status}


def listar_regras(ator: dict, *, modulo: str | None = None) -> list[dict]:
    exigir_permissao(ator, "analytics", "ler")
    empresa_id, filial_id = _escopo(ator)
    params: list[Any] = [empresa_id, filial_id]
    filtro = "empresa_id=? AND (filial_id=? OR filial_id IS NULL)"
    if modulo:
        filtro += " AND modulo=?"
        params.append(str(modulo).strip().lower())
    with conectar() as con:
        rows = con.execute(f"SELECT * FROM analytics_regras WHERE {filtro} ORDER BY modulo,nome", tuple(params)).fetchall()
    return [dict(x) for x in rows]


def salvar_regra(dados: dict, ator: dict) -> int:
    exigir_permissao(ator, "analytics", "escrever")
    empresa_id, filial_id = _escopo(ator)
    codigo = str(dados.get("codigo") or "").strip().lower().replace(" ", "_")[:80]
    nome = str(dados.get("nome") or "").strip()[:180]
    modulo = str(dados.get("modulo") or "").strip().lower()[:40]
    metrica = str(dados.get("metrica") or "").strip()[:100]
    operador = str(dados.get("operador") or ">").strip()
    if not codigo or not nome or not modulo or not metrica:
        raise ValueError("Código, nome, módulo e métrica são obrigatórios.")
    if operador not in {">", ">=", "<", "<=", "=", "==", "!="}:
        raise ValueError("Operador de regra inválido.")
    severidade = str(dados.get("severidade") or "Atenção")
    if severidade not in SEVERIDADES:
        raise ValueError("Severidade inválida.")
    limite = float(dados.get("limite") or 0)
    with conectar() as con:
        cur = con.execute(
            """INSERT INTO analytics_regras
               (empresa_id,filial_id,codigo,nome,modulo,metrica,operador,limite,severidade,acao_modulo,acao_secao,ativo,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(empresa_id,filial_id,codigo) DO UPDATE SET
                 nome=excluded.nome,modulo=excluded.modulo,metrica=excluded.metrica,operador=excluded.operador,
                 limite=excluded.limite,severidade=excluded.severidade,acao_modulo=excluded.acao_modulo,
                 acao_secao=excluded.acao_secao,ativo=excluded.ativo,atualizado_em=CURRENT_TIMESTAMP""",
            (empresa_id, filial_id, codigo, nome, modulo, metrica, operador, limite, severidade,
             str(dados.get("acao_modulo") or modulo), str(dados.get("acao_secao") or "visao"),
             1 if bool(dados.get("ativo", True)) else 0, int(ator["id"])),
        )
        # SQLite retorna lastrowid no INSERT; no conflito pode ser 0. Recuperamos o id canônico.
        row = con.execute(
            "SELECT id FROM analytics_regras WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL) AND codigo=? ORDER BY id DESC LIMIT 1",
            (empresa_id, filial_id, codigo),
        ).fetchone()
    return int(row["id"] if row else cur.lastrowid)


def definir_regra_ativa(regra_id: int, ativa: bool, ator: dict) -> dict:
    exigir_permissao(ator, "analytics", "escrever")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        cur = con.execute(
            "UPDATE analytics_regras SET ativo=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND (filial_id=? OR filial_id IS NULL)",
            (1 if ativa else 0, int(regra_id), empresa_id, filial_id),
        )
        if cur.rowcount != 1:
            raise ValueError("Regra não encontrada.")
    return {"id": int(regra_id), "ativo": bool(ativa)}


def historico_execucoes(ator: dict, *, limite: int = 50) -> list[dict]:
    exigir_permissao(ator, "analytics", "ler")
    empresa_id, filial_id = _escopo(ator)
    with conectar() as con:
        rows = con.execute(
            """SELECT * FROM analytics_execucoes WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL)
               ORDER BY id DESC LIMIT ?""",
            (empresa_id, filial_id, max(1, min(500, int(limite)))),
        ).fetchall()
    return [dict(x) for x in rows]


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo


__all__ = (
    "SEVERIDADES", "obter_painel_executivo", "gerar_insights", "listar_insights", "contar_insights",
    "alterar_status_insight", "listar_regras", "salvar_regra", "definir_regra_ativa",
    "historico_execucoes",
)
