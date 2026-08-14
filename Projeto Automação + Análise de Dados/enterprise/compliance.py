"""Casos de uso de governança jurídica e privacidade.

Os controles deste módulo geram evidências e aplicam segregação. Eles não
substituem a definição de bases legais, prazos setoriais ou decisões do
encarregado/assessoria jurídica de cada organização.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from uuid import uuid4

from auth.banco import conectar
from enterprise.core_v11.common import escopo, registrar_evento, registrar_historico, texto


_PERFIS_GOVERNANCA = {"compliance", "dpo", "encarregado", "juridico", "diretoria"}
_STATUS_TRATAMENTO = {"Em revisão", "Ativo", "Suspenso", "Encerrado"}
_TIPOS_TITULAR = {
    "Confirmação", "Acesso", "Correção", "Anonimização", "Bloqueio",
    "Eliminação", "Portabilidade", "Informação", "Revogação",
}
_STATUS_TITULAR = {"Recebida", "Identidade pendente", "Em atendimento", "Aguardando titular", "Concluída", "Recusada"}
_STATUS_INCIDENTE = {"Em avaliação", "Contido", "Em comunicação", "Monitoramento", "Encerrado"}
_STATUS_RIPD = {"Rascunho", "Em revisão", "Aprovado", "Substituído"}
_STATUS_DECISAO = {"Em homologação", "Ativo", "Suspenso", "Encerrado"}


def _exigir_governanca(ator: dict) -> tuple[int, int | None]:
    perfil = str(ator.get("perfil_acesso") or "").strip().lower()
    if str(ator.get("perfil") or "").lower() != "admin" and perfil not in _PERFIS_GOVERNANCA:
        raise PermissionError("A Central de Conformidade exige administrador, encarregado, Jurídico ou Compliance.")
    return escopo(ator)


def _utc_agora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data(valor, *, campo: str) -> str:
    bruto = str(valor or "").strip()
    try:
        return datetime.fromisoformat(bruto.replace("Z", "+00:00")).replace(microsecond=0).isoformat()
    except ValueError as exc:
        raise ValueError(f"{campo} deve usar data/hora ISO válida.") from exc


def _dias_uteis(inicio: date, quantidade: int) -> date:
    atual = inicio
    restantes = int(quantidade)
    while restantes:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            restantes -= 1
    return atual


def _protocolo(prefixo: str) -> str:
    return f"{prefixo}-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"


def _inteiro_opcional(valor, *, campo: str) -> int | None:
    """Normaliza campos numéricos opcionais recebidos pela UI ou por RPC."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{campo} deve ser um número inteiro.") from exc
    if numero < 0:
        raise ValueError(f"{campo} não pode ser negativo.")
    return numero


def _lista_json(valor, *, campo: str) -> str:
    if isinstance(valor, str):
        itens = [item.strip() for item in valor.splitlines() if item.strip()]
    elif isinstance(valor, (list, tuple)):
        itens = [str(item).strip() for item in valor if str(item).strip()]
    elif valor in (None, ""):
        itens = []
    else:
        raise ValueError(f"{campo} deve ser uma lista ou texto com um item por linha.")
    return json.dumps(itens, ensure_ascii=False, separators=(",", ":"))


def resumo_conformidade(ator: dict) -> dict:
    empresa_id, _ = _exigir_governanca(ator)
    hoje = date.today().isoformat()
    with conectar() as con:
        tratamento = con.execute(
            "SELECT COUNT(*) total,SUM(CASE WHEN status='Em revisão' THEN 1 ELSE 0 END) revisar FROM compliance_tratamentos WHERE empresa_id=?",
            (empresa_id,),
        ).fetchone()
        titulares = con.execute(
            """SELECT COUNT(*) total,SUM(CASE WHEN status NOT IN ('Concluída','Recusada') THEN 1 ELSE 0 END) abertos,
               SUM(CASE WHEN status NOT IN ('Concluída','Recusada') AND prazo_resposta<? THEN 1 ELSE 0 END) vencidos
               FROM compliance_solicitacoes_titulares WHERE empresa_id=?""",
            (hoje, empresa_id),
        ).fetchone()
        incidentes = con.execute(
            """SELECT COUNT(*) total,SUM(CASE WHEN status<>'Encerrado' THEN 1 ELSE 0 END) abertos,
               SUM(CASE WHEN status<>'Encerrado' AND comunicar_anpd=1 AND comunicado_anpd_em IS NULL
                   AND prazo_regulatorio IS NOT NULL AND prazo_regulatorio<? THEN 1 ELSE 0 END) prazo_critico
               FROM compliance_incidentes WHERE empresa_id=?""",
            (hoje, empresa_id),
        ).fetchone()
        terceiros = con.execute(
            """SELECT COUNT(*) total,SUM(CASE WHEN status<>'Aprovado' OR contrato_dpa=0 THEN 1 ELSE 0 END) pendentes
               FROM compliance_terceiros WHERE empresa_id=?""", (empresa_id,),
        ).fetchone()
    return {
        "tratamentos": int(tratamento["total"] or 0), "tratamentos_em_revisao": int(tratamento["revisar"] or 0),
        "solicitacoes_titulares": int(titulares["total"] or 0), "solicitacoes_abertas": int(titulares["abertos"] or 0),
        "solicitacoes_vencidas": int(titulares["vencidos"] or 0), "incidentes": int(incidentes["total"] or 0),
        "incidentes_abertos": int(incidentes["abertos"] or 0), "incidentes_prazo_critico": int(incidentes["prazo_critico"] or 0),
        "terceiros": int(terceiros["total"] or 0), "terceiros_pendentes": int(terceiros["pendentes"] or 0),
    }


def salvar_tratamento(dados: dict, ator: dict, *, tratamento_id: int | None = None, versao: int | None = None) -> int:
    empresa_id, filial_id = _exigir_governanca(ator)
    status = texto(dados.get("status") or "Em revisão", maximo=30)
    if status not in _STATUS_TRATAMENTO:
        raise ValueError("Status de tratamento inválido.")
    obrigatorios = {
        "codigo": texto(dados.get("codigo"), minimo=2, maximo=80, campo="Código").upper(),
        "nome": texto(dados.get("nome"), minimo=3, maximo=180, campo="Nome"),
        "controlador": texto(dados.get("controlador"), minimo=2, maximo=180, campo="Controlador"),
        "finalidade": texto(dados.get("finalidade"), minimo=5, maximo=3000, campo="Finalidade"),
        "base_legal": texto(dados.get("base_legal"), minimo=3, maximo=500, campo="Base legal"),
        "categorias_titulares": texto(dados.get("categorias_titulares"), minimo=2, maximo=1500, campo="Titulares"),
        "categorias_dados": texto(dados.get("categorias_dados"), minimo=2, maximo=3000, campo="Dados"),
        "prazo_retencao": texto(dados.get("prazo_retencao"), minimo=2, maximo=500, campo="Retenção"),
        "medidas_seguranca": texto(dados.get("medidas_seguranca"), minimo=5, maximo=3000, campo="Medidas de segurança"),
    }
    with conectar() as con:
        if tratamento_id is None:
            cursor = con.execute(
                """INSERT INTO compliance_tratamentos
                   (empresa_id,codigo,nome,controlador,operador,encarregado,finalidade,base_legal,
                    categorias_titulares,categorias_dados,dados_sensiveis,compartilhamentos,
                    transferencia_internacional,paises_salvaguardas,prazo_retencao,medidas_seguranca,
                    responsavel_id,status,criado_por,atualizado_por)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (empresa_id, obrigatorios["codigo"], obrigatorios["nome"], obrigatorios["controlador"],
                 texto(dados.get("operador"), maximo=1000), texto(dados.get("encarregado"), maximo=500),
                 obrigatorios["finalidade"], obrigatorios["base_legal"], obrigatorios["categorias_titulares"],
                 obrigatorios["categorias_dados"], int(bool(dados.get("dados_sensiveis"))),
                 texto(dados.get("compartilhamentos"), maximo=3000), int(bool(dados.get("transferencia_internacional"))),
                 texto(dados.get("paises_salvaguardas"), maximo=2000), obrigatorios["prazo_retencao"],
                 obrigatorios["medidas_seguranca"], dados.get("responsavel_id"), status, int(ator["id"]), int(ator["id"])),
            )
            identificador = int(cursor.lastrowid)
            acao, antes = "Tratamento criado", None
        else:
            if versao is None:
                raise ValueError("A versão atual é obrigatória para editar o tratamento.")
            atual = con.execute(
                "SELECT * FROM compliance_tratamentos WHERE id=? AND empresa_id=?", (int(tratamento_id), empresa_id),
            ).fetchone()
            if atual is None:
                raise ValueError("Tratamento não encontrado.")
            cursor = con.execute(
                """UPDATE compliance_tratamentos SET codigo=?,nome=?,controlador=?,operador=?,encarregado=?,finalidade=?,
                   base_legal=?,categorias_titulares=?,categorias_dados=?,dados_sensiveis=?,compartilhamentos=?,
                   transferencia_internacional=?,paises_salvaguardas=?,prazo_retencao=?,medidas_seguranca=?,
                   responsavel_id=?,status=?,versao_registro=versao_registro+1,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=? AND empresa_id=? AND versao_registro=?""",
                (obrigatorios["codigo"], obrigatorios["nome"], obrigatorios["controlador"], texto(dados.get("operador"), maximo=1000),
                 texto(dados.get("encarregado"), maximo=500), obrigatorios["finalidade"], obrigatorios["base_legal"],
                 obrigatorios["categorias_titulares"], obrigatorios["categorias_dados"], int(bool(dados.get("dados_sensiveis"))),
                 texto(dados.get("compartilhamentos"), maximo=3000), int(bool(dados.get("transferencia_internacional"))),
                 texto(dados.get("paises_salvaguardas"), maximo=2000), obrigatorios["prazo_retencao"],
                 obrigatorios["medidas_seguranca"], dados.get("responsavel_id"), status, int(ator["id"]),
                 int(tratamento_id), empresa_id, int(versao)),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("O tratamento foi alterado por outra pessoa. Atualize a tela e tente novamente.")
            identificador, acao, antes = int(tratamento_id), "Tratamento atualizado", dict(atual)
        registrar_historico(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                            recurso_tipo="compliance_tratamentos", recurso_id=identificador, acao=acao,
                            ator=ator, antes=antes, depois={**obrigatorios, "status": status})
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                         tipo="compliance.tratamento_salvo", recurso_tipo="compliance_tratamentos",
                         recurso_id=identificador, ator=ator, payload={"status": status})
    return identificador


def listar_tratamentos(ator: dict, *, status: str | None = None, limite: int = 500) -> list[dict]:
    empresa_id, _ = _exigir_governanca(ator)
    filtro, params = "empresa_id=?", [empresa_id]
    if status:
        filtro += " AND status=?"; params.append(str(status))
    params.append(max(1, min(int(limite), 2000)))
    with conectar() as con:
        return [dict(x) for x in con.execute(
            f"SELECT * FROM compliance_tratamentos WHERE {filtro} ORDER BY atualizado_em DESC,id DESC LIMIT ?", tuple(params),
        ).fetchall()]


def criar_solicitacao_titular(dados: dict, ator: dict) -> int:
    empresa_id, filial_id = _exigir_governanca(ator)
    tipo = texto(dados.get("tipo"), minimo=2, maximo=40, campo="Tipo")
    if tipo not in _TIPOS_TITULAR:
        raise ValueError("Tipo de direito do titular inválido.")
    recebido = _data(dados.get("recebido_em") or _utc_agora(), campo="Recebimento")
    prazo = (datetime.fromisoformat(recebido).date() + timedelta(days=15)).isoformat()
    documento_hash = texto(dados.get("titular_documento_hash"), maximo=128) or None
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO compliance_solicitacoes_titulares
               (empresa_id,protocolo,tipo,titular_nome,titular_documento_hash,canal,identidade_verificada,
                escopo,status,responsavel_id,recebido_em,prazo_resposta,criado_por,atualizado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, _protocolo("TIT"), tipo, texto(dados.get("titular_nome"), minimo=2, maximo=180, campo="Titular"),
             documento_hash, texto(dados.get("canal") or "Atendimento", maximo=80), int(bool(dados.get("identidade_verificada"))),
             texto(dados.get("escopo"), maximo=3000), "Recebida" if dados.get("identidade_verificada") else "Identidade pendente",
             dados.get("responsavel_id"), recebido, prazo, int(ator["id"]), int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                         tipo="privacidade.solicitacao_titular_recebida", recurso_tipo="compliance_solicitacoes_titulares",
                         recurso_id=identificador, ator=ator, payload={"tipo": tipo, "prazo": prazo})
    return identificador


def atualizar_solicitacao_titular(solicitacao_id: int, dados: dict, ator: dict, *, versao: int) -> None:
    empresa_id, filial_id = _exigir_governanca(ator)
    status = texto(dados.get("status"), maximo=40)
    if status not in _STATUS_TITULAR:
        raise ValueError("Status da solicitação inválido.")
    if status == "Concluída" and not texto(dados.get("resposta_resumo"), maximo=5000):
        raise ValueError("Registre o resumo da resposta antes de concluir.")
    if status == "Recusada" and not texto(dados.get("fundamento_recusa"), maximo=3000):
        raise ValueError("A recusa exige fundamento registrado.")
    with conectar() as con:
        atual = con.execute("SELECT * FROM compliance_solicitacoes_titulares WHERE id=? AND empresa_id=?", (int(solicitacao_id), empresa_id)).fetchone()
        if atual is None: raise ValueError("Solicitação não encontrada.")
        cursor = con.execute(
            """UPDATE compliance_solicitacoes_titulares SET status=?,identidade_verificada=?,responsavel_id=?,
               resposta_resumo=?,fundamento_recusa=?,evidencia_documento_id=?,
               respondido_em=CASE WHEN ? IN ('Concluída','Recusada') THEN CURRENT_TIMESTAMP ELSE respondido_em END,
               versao_registro=versao_registro+1,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
               WHERE id=? AND empresa_id=? AND versao_registro=?""",
            (status, int(bool(dados.get("identidade_verificada"))), dados.get("responsavel_id"),
             texto(dados.get("resposta_resumo"), maximo=5000), texto(dados.get("fundamento_recusa"), maximo=3000),
             dados.get("evidencia_documento_id"), status, int(ator["id"]), int(solicitacao_id), empresa_id, int(versao)),
        )
        if cursor.rowcount != 1: raise RuntimeError("A solicitação mudou. Atualize a tela antes de salvar.")
        registrar_historico(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                            recurso_tipo="compliance_solicitacoes_titulares", recurso_id=int(solicitacao_id),
                            acao="Solicitação de titular atualizada", ator=ator, antes=dict(atual), depois={"status": status})


def listar_solicitacoes_titulares(ator: dict, *, limite: int = 500) -> list[dict]:
    empresa_id, _ = _exigir_governanca(ator)
    with conectar() as con:
        return [dict(x) for x in con.execute(
            "SELECT * FROM compliance_solicitacoes_titulares WHERE empresa_id=? ORDER BY prazo_resposta,id DESC LIMIT ?",
            (empresa_id, max(1, min(int(limite), 2000))),
        ).fetchall()]


def abrir_incidente_privacidade(dados: dict, ator: dict) -> int:
    empresa_id, filial_id = _exigir_governanca(ator)
    detectado = _data(dados.get("detectado_em") or _utc_agora(), campo="Detecção")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO compliance_incidentes
               (empresa_id,filial_id,protocolo,titulo,descricao,detectado_em,dados_afetados,titulares_afetados,
                risco_dano,medidas_contencao,status,responsavel_id,criado_por,atualizado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, _protocolo("INC"), texto(dados.get("titulo"), minimo=3, maximo=200, campo="Título"),
             texto(dados.get("descricao"), minimo=10, maximo=8000, campo="Descrição"), detectado,
             texto(dados.get("dados_afetados"), maximo=3000),
             _inteiro_opcional(dados.get("titulares_afetados"), campo="Titulares afetados"),
             texto(dados.get("risco_dano") or "Em avaliação", maximo=80), texto(dados.get("medidas_contencao"), maximo=5000),
             "Em avaliação", dados.get("responsavel_id"), int(ator["id"]), int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="ti",
                         tipo="privacidade.incidente_aberto", recurso_tipo="compliance_incidentes",
                         recurso_id=identificador, ator=ator, payload={"risco": dados.get("risco_dano") or "Em avaliação"})
    return identificador


def avaliar_incidente_privacidade(incidente_id: int, dados: dict, ator: dict, *, versao: int) -> None:
    empresa_id, filial_id = _exigir_governanca(ator)
    status = texto(dados.get("status"), maximo=40)
    if status not in _STATUS_INCIDENTE: raise ValueError("Status do incidente inválido.")
    comunicar_anpd = bool(dados.get("comunicar_anpd")); comunicar_titulares = bool(dados.get("comunicar_titulares"))
    justificativa = texto(dados.get("justificativa_decisao"), maximo=5000)
    if not justificativa: raise ValueError("A decisão de comunicação exige justificativa registrada.")
    confirmado = _data(dados.get("confirmado_em") or _utc_agora(), campo="Confirmação")
    prazo = _dias_uteis(datetime.fromisoformat(confirmado).date(), 3).isoformat() if (comunicar_anpd or comunicar_titulares) else None
    with conectar() as con:
        atual = con.execute("SELECT * FROM compliance_incidentes WHERE id=? AND empresa_id=?", (int(incidente_id), empresa_id)).fetchone()
        if atual is None: raise ValueError("Incidente não encontrado.")
        cursor = con.execute(
            """UPDATE compliance_incidentes SET status=?,confirmado_em=?,dados_afetados=?,titulares_afetados=?,
               risco_dano=?,medidas_contencao=?,responsavel_id=?,comunicar_anpd=?,comunicar_titulares=?,
               prazo_regulatorio=?,comunicado_anpd_em=?,comunicado_titulares_em=?,justificativa_decisao=?,
               encerrado_em=CASE WHEN ?='Encerrado' THEN CURRENT_TIMESTAMP ELSE encerrado_em END,
               versao_registro=versao_registro+1,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
               WHERE id=? AND empresa_id=? AND versao_registro=?""",
            (status, confirmado, texto(dados.get("dados_afetados"), maximo=3000),
             _inteiro_opcional(dados.get("titulares_afetados"), campo="Titulares afetados"),
             texto(dados.get("risco_dano") or "Em avaliação", maximo=80), texto(dados.get("medidas_contencao"), maximo=5000),
             dados.get("responsavel_id"), int(comunicar_anpd), int(comunicar_titulares), prazo,
             dados.get("comunicado_anpd_em"), dados.get("comunicado_titulares_em"), justificativa, status,
             int(ator["id"]), int(incidente_id), empresa_id, int(versao)),
        )
        if cursor.rowcount != 1: raise RuntimeError("O incidente mudou. Atualize a tela antes de salvar.")
        registrar_historico(con, empresa_id=empresa_id, filial_id=filial_id, modulo="ti",
                            recurso_tipo="compliance_incidentes", recurso_id=int(incidente_id), acao="Incidente avaliado",
                            ator=ator, antes=dict(atual), depois={"status": status, "prazo_regulatorio": prazo})


def listar_incidentes_privacidade(ator: dict, *, limite: int = 500) -> list[dict]:
    empresa_id, _ = _exigir_governanca(ator)
    with conectar() as con:
        return [dict(x) for x in con.execute(
            "SELECT * FROM compliance_incidentes WHERE empresa_id=? ORDER BY detectado_em DESC,id DESC LIMIT ?",
            (empresa_id, max(1, min(int(limite), 2000))),
        ).fetchall()]


def salvar_ripd(dados: dict, ator: dict) -> int:
    """Cria uma versão imutável de RIPD; revisões geram nova versão."""
    empresa_id, filial_id = _exigir_governanca(ator)
    codigo = texto(dados.get("codigo"), minimo=2, maximo=80, campo="Código").upper()
    status = texto(dados.get("status") or "Rascunho", maximo=30)
    if status not in _STATUS_RIPD - {"Substituído"}:
        raise ValueError("Status de RIPD inválido.")
    necessidade = texto(dados.get("necessidade_proporcionalidade"), minimo=10, maximo=8000,
                        campo="Necessidade e proporcionalidade")
    riscos = _lista_json(dados.get("riscos"), campo="Riscos")
    salvaguardas = _lista_json(dados.get("salvaguardas"), campo="Salvaguardas")
    if status == "Aprovado" and (riscos == "[]" or salvaguardas == "[]"):
        raise ValueError("Um RIPD aprovado precisa registrar riscos e salvaguardas.")
    with conectar() as con:
        anterior = con.execute(
            "SELECT id,versao FROM compliance_ripd WHERE empresa_id=? AND codigo=? ORDER BY versao DESC LIMIT 1",
            (empresa_id, codigo),
        ).fetchone()
        versao = int(anterior["versao"] or 0) + 1 if anterior else 1
        cursor = con.execute(
            """INSERT INTO compliance_ripd
               (empresa_id,tratamento_id,codigo,titulo,necessidade_proporcionalidade,riscos_json,
                salvaguardas_json,risco_residual,aprovado_por,status,versao,criado_por,atualizado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, _inteiro_opcional(dados.get("tratamento_id"), campo="Tratamento"), codigo,
             texto(dados.get("titulo"), minimo=3, maximo=200, campo="Título"), necessidade, riscos,
             salvaguardas, texto(dados.get("risco_residual") or "Em avaliação", maximo=500),
             int(ator["id"]) if status == "Aprovado" else None, status, versao, int(ator["id"]), int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        if anterior:
            con.execute("UPDATE compliance_ripd SET status='Substituído',atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                        (int(ator["id"]), int(anterior["id"])))
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                         tipo="compliance.ripd_versionado", recurso_tipo="compliance_ripd",
                         recurso_id=identificador, ator=ator, payload={"codigo": codigo, "versao": versao, "status": status})
    return identificador


def listar_ripd(ator: dict, *, limite: int = 500) -> list[dict]:
    empresa_id, _ = _exigir_governanca(ator)
    with conectar() as con:
        rows = con.execute(
            "SELECT * FROM compliance_ripd WHERE empresa_id=? ORDER BY codigo,versao DESC LIMIT ?",
            (empresa_id, max(1, min(int(limite), 2000))),
        ).fetchall()
    resultado = []
    for row in rows:
        item = dict(row)
        item["riscos"] = json.loads(item.pop("riscos_json") or "[]")
        item["salvaguardas"] = json.loads(item.pop("salvaguardas_json") or "[]")
        resultado.append(item)
    return resultado


def salvar_decisao_analitica(dados: dict, ator: dict, *, decisao_id: int | None = None) -> int:
    """Cataloga regra/modelo e impede ativação de impacto humano sem revisão humana."""
    empresa_id, filial_id = _exigir_governanca(ator)
    impacto = texto(dados.get("impacto_pessoas") or "Nenhum", maximo=500)
    revisao_humana = bool(dados.get("revisao_humana", True))
    status = texto(dados.get("status") or "Em homologação", maximo=30)
    if status not in _STATUS_DECISAO:
        raise ValueError("Status da decisão analítica inválido.")
    if impacto.strip().lower() not in {"", "nenhum", "não", "nao"} and not revisao_humana:
        raise ValueError("Decisões que impactam pessoas exigem revisão humana registrada.")
    valores = (
        texto(dados.get("codigo"), minimo=2, maximo=80, campo="Código").upper(),
        texto(dados.get("nome"), minimo=3, maximo=180, campo="Nome"),
        texto(dados.get("tipo") or "Regra determinística", maximo=80),
        texto(dados.get("finalidade"), minimo=5, maximo=3000, campo="Finalidade"),
        texto(dados.get("dados_entrada"), minimo=2, maximo=3000, campo="Dados de entrada"),
        texto(dados.get("logica_resumo"), minimo=5, maximo=5000, campo="Lógica"), impacto,
        int(revisao_humana), _inteiro_opcional(dados.get("responsavel_id"), campo="Responsável"),
        texto(dados.get("versao") or "1", maximo=40), status, dados.get("ultima_validacao") or None,
    )
    with conectar() as con:
        if decisao_id is None:
            cursor = con.execute(
                """INSERT INTO analytics_catalogo_decisoes
                   (empresa_id,codigo,nome,tipo,finalidade,dados_entrada,logica_resumo,impacto_pessoas,
                    revisao_humana,responsavel_id,versao,status,ultima_validacao,criado_por)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (empresa_id, *valores, int(ator["id"])),
            )
            identificador = int(cursor.lastrowid)
        else:
            cursor = con.execute(
                """UPDATE analytics_catalogo_decisoes SET codigo=?,nome=?,tipo=?,finalidade=?,dados_entrada=?,
                   logica_resumo=?,impacto_pessoas=?,revisao_humana=?,responsavel_id=?,versao=?,status=?,
                   ultima_validacao=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?""",
                (*valores, int(decisao_id), empresa_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Decisão analítica não encontrada.")
            identificador = int(decisao_id)
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="analytics",
                         tipo="analytics.decisao_catalogada", recurso_tipo="analytics_catalogo_decisoes",
                         recurso_id=identificador, ator=ator, payload={"status": status, "revisao_humana": revisao_humana})
    return identificador


def listar_decisoes_analiticas(ator: dict, *, limite: int = 500) -> list[dict]:
    empresa_id, _ = _exigir_governanca(ator)
    with conectar() as con:
        return [dict(x) for x in con.execute(
            "SELECT * FROM analytics_catalogo_decisoes WHERE empresa_id=? ORDER BY atualizado_em DESC,id DESC LIMIT ?",
            (empresa_id, max(1, min(int(limite), 2000))),
        ).fetchall()]


def salvar_terceiro(dados: dict, ator: dict, *, terceiro_id: int | None = None, versao: int | None = None) -> int:
    empresa_id, filial_id = _exigir_governanca(ator)
    valores = (
        texto(dados.get("nome"), minimo=2, maximo=180, campo="Terceiro"), texto(dados.get("papel") or "Operador", maximo=80),
        texto(dados.get("dados_tratados"), minimo=2, maximo=3000, campo="Dados tratados"),
        texto(dados.get("finalidade"), minimo=3, maximo=3000, campo="Finalidade"), int(bool(dados.get("contrato_dpa"))),
        int(bool(dados.get("transferencia_internacional"))), texto(dados.get("mecanismo_transferencia"), maximo=1500),
        texto(dados.get("avaliacao_seguranca"), maximo=5000), dados.get("proxima_revisao"),
        texto(dados.get("status") or "Em avaliação", maximo=40),
    )
    with conectar() as con:
        if terceiro_id is None:
            cursor = con.execute(
                """INSERT INTO compliance_terceiros
                   (empresa_id,nome,papel,dados_tratados,finalidade,contrato_dpa,transferencia_internacional,
                    mecanismo_transferencia,avaliacao_seguranca,proxima_revisao,status,criado_por,atualizado_por)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (empresa_id, *valores, int(ator["id"]), int(ator["id"])),
            )
            identificador = int(cursor.lastrowid)
        else:
            if versao is None: raise ValueError("A versão atual é obrigatória para editar o terceiro.")
            cursor = con.execute(
                """UPDATE compliance_terceiros SET nome=?,papel=?,dados_tratados=?,finalidade=?,contrato_dpa=?,
                   transferencia_internacional=?,mecanismo_transferencia=?,avaliacao_seguranca=?,proxima_revisao=?,status=?,
                   versao_registro=versao_registro+1,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
                   WHERE id=? AND empresa_id=? AND versao_registro=?""",
                (*valores, int(ator["id"]), int(terceiro_id), empresa_id, int(versao)),
            )
            if cursor.rowcount != 1: raise RuntimeError("O cadastro mudou. Atualize a tela antes de salvar.")
            identificador = int(terceiro_id)
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                         tipo="compliance.terceiro_salvo", recurso_tipo="compliance_terceiros",
                         recurso_id=identificador, ator=ator, payload={"status": valores[-1]})
    return identificador


def listar_terceiros(ator: dict, *, limite: int = 500) -> list[dict]:
    empresa_id, _ = _exigir_governanca(ator)
    with conectar() as con:
        return [dict(x) for x in con.execute(
            "SELECT * FROM compliance_terceiros WHERE empresa_id=? ORDER BY atualizado_em DESC,id DESC LIMIT ?",
            (empresa_id, max(1, min(int(limite), 2000))),
        ).fetchall()]


def definir_bloqueio_retencao(recurso_tipo: str, recurso_id: int, motivo: str, fundamento: str, ator: dict, *, valido_ate: str | None = None) -> int:
    empresa_id, filial_id = _exigir_governanca(ator)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO compliance_bloqueios_retencao
               (empresa_id,recurso_tipo,recurso_id,motivo,fundamento,valido_ate,criado_por)
               VALUES (?,?,?,?,?,?,?)""",
            (empresa_id, texto(recurso_tipo, minimo=2, maximo=100), int(recurso_id),
             texto(motivo, minimo=5, maximo=2000), texto(fundamento, minimo=3, maximo=1000), valido_ate, int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                         tipo="compliance.legal_hold_ativado", recurso_tipo=recurso_tipo, recurso_id=int(recurso_id),
                         ator=ator, payload={"bloqueio_id": identificador, "valido_ate": valido_ate})
    return identificador


def encerrar_bloqueio_retencao(bloqueio_id: int, ator: dict) -> None:
    empresa_id, filial_id = _exigir_governanca(ator)
    with conectar() as con:
        row = con.execute("SELECT * FROM compliance_bloqueios_retencao WHERE id=? AND empresa_id=?", (int(bloqueio_id), empresa_id)).fetchone()
        if row is None: raise ValueError("Bloqueio de retenção não encontrado.")
        if row["status"] != "Ativo": return
        con.execute("UPDATE compliance_bloqueios_retencao SET status='Encerrado',encerrado_por=?,encerrado_em=CURRENT_TIMESTAMP WHERE id=?", (int(ator["id"]), int(bloqueio_id)))
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="juridico",
                         tipo="compliance.legal_hold_encerrado", recurso_tipo=row["recurso_tipo"], recurso_id=int(row["recurso_id"]),
                         ator=ator, payload={"bloqueio_id": int(bloqueio_id)})


def listar_bloqueios_retencao(ator: dict, *, somente_ativos: bool = True) -> list[dict]:
    empresa_id, _ = _exigir_governanca(ator)
    filtro = " AND status='Ativo'" if somente_ativos else ""
    with conectar() as con:
        return [dict(x) for x in con.execute(
            f"SELECT * FROM compliance_bloqueios_retencao WHERE empresa_id=?{filtro} ORDER BY criado_em DESC", (empresa_id,),
        ).fetchall()]


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "abrir_incidente_privacidade", "atualizar_solicitacao_titular", "avaliar_incidente_privacidade",
    "criar_solicitacao_titular", "definir_bloqueio_retencao", "encerrar_bloqueio_retencao",
    "listar_bloqueios_retencao", "listar_incidentes_privacidade", "listar_solicitacoes_titulares",
    "listar_decisoes_analiticas", "listar_ripd", "listar_terceiros", "listar_tratamentos",
    "resumo_conformidade", "salvar_decisao_analitica", "salvar_ripd", "salvar_terceiro", "salvar_tratamento",
)
