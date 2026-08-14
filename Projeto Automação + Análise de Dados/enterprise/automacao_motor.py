"""Fila durável, scheduler e workers idempotentes de automação corporativa."""
from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import threading
import time
from typing import Callable
from uuid import uuid4

from auth import banco
from auth.banco import conectar
from enterprise.contexto import obter_escopo_ator

Handler = Callable[[dict, dict, Callable[[], bool]], dict | None]
_HANDLERS: dict[str, Handler] = {}
_LOG = logging.getLogger("data_intelligence.automacao")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: datetime | None = None) -> str:
    return (valor or _agora()).astimezone(timezone.utc).isoformat(timespec="seconds")


def registrar_handler(nome: str):
    def decorar(funcao: Handler) -> Handler:
        chave = str(nome).strip()
        if not chave or chave in _HANDLERS:
            raise ValueError(f"Handler de automação inválido ou duplicado: {chave}")
        _HANDLERS[chave] = funcao
        return funcao
    return decorar


def enfileirar(
    handler: str,
    titulo: str,
    payload: dict,
    ator: dict,
    *,
    idempotency_key: str | None = None,
    max_tentativas: int = 3,
    prioridade: int = 100,
    requer_aprovacao: bool = False,
    disponivel_em: datetime | None = None,
) -> dict:
    handler = str(handler).strip()
    if handler not in _HANDLERS:
        raise ValueError(f"Handler de automação não registrado: {handler}")
    empresa_id, filial_id = obter_escopo_ator(ator)
    idem = str(idempotency_key or "").strip()[:240] or None
    if idem:
        with conectar() as con:
            existente = con.execute(
                "SELECT id,codigo,status FROM automacao_fila WHERE empresa_id=? AND idempotency_key=?",
                (empresa_id, idem),
            ).fetchone()
        if existente:
            return dict(existente)
    codigo = f"AUTO-{_agora():%Y%m%d}-{uuid4().hex[:10].upper()}"
    status = "Aguardando aprovação" if requer_aprovacao else "Pendente"
    parametros = (
        codigo, int(empresa_id), filial_id, int(ator["id"]), handler,
        str(titulo).strip()[:220], json.dumps(payload or {}, ensure_ascii=False, default=str),
        status, max(1, min(int(prioridade), 9999)), idem,
        max(1, min(int(max_tentativas), 20)), _iso(disponivel_em), int(bool(requer_aprovacao)),
    )
    try:
        with conectar() as con:
            cursor = con.execute(
                """INSERT INTO automacao_fila
                   (codigo,empresa_id,filial_id,usuario_id,handler,titulo,payload_json,
                    status,prioridade,idempotency_key,max_tentativas,disponivel_em,requer_aprovacao)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                parametros,
            )
            return {"id": int(cursor.lastrowid), "codigo": codigo, "status": status}
    except Exception:
        if idem:
            with conectar() as con:
                existente = con.execute(
                    "SELECT id,codigo,status FROM automacao_fila WHERE empresa_id=? AND idempotency_key=?",
                    (empresa_id, idem),
                ).fetchone()
            if existente:
                return dict(existente)
        raise


def aprovar(job_id: int, ator: dict) -> None:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("A aprovação de automações sensíveis exige administrador.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as con:
        cursor = con.execute(
            """UPDATE automacao_fila SET status='Pendente',aprovado_em=?,aprovado_por=?,atualizado_em=?
               WHERE id=? AND empresa_id=? AND status='Aguardando aprovação'""",
            (_iso(), int(ator["id"]), _iso(), int(job_id), int(empresa_id)),
        )
    if cursor.rowcount != 1:
        raise ValueError("Automação não encontrada ou não aguarda aprovação.")


def solicitar_cancelamento(job_id: int, ator: dict) -> None:
    empresa_id, _ = obter_escopo_ator(ator)
    admin = str(ator.get("perfil", "")).lower() == "admin"
    filtro = "" if admin else " AND usuario_id=?"
    parametros = [_iso(), int(job_id), int(empresa_id)]
    if not admin:
        parametros.append(int(ator["id"]))
    with conectar() as con:
        cursor = con.execute(
            f"""UPDATE automacao_fila SET cancelamento_solicitado=1,
                 status=CASE WHEN status IN ('Pendente','Aguardando aprovação') THEN 'Cancelado'
                             WHEN status='Executando' THEN 'Cancelamento solicitado' ELSE status END,
                 atualizado_em=? WHERE id=? AND empresa_id=?{filtro}
                 AND status NOT IN ('Concluído','Falhou','Cancelado','Dead-letter')""",
            tuple(parametros),
        )
    if cursor.rowcount != 1:
        raise ValueError("Automação não encontrada ou não cancelável.")


def reprocessar_dead_letter(job_id: int, ator: dict) -> None:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Reprocessamento de dead-letter exige administrador.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as con:
        cursor = con.execute(
            """UPDATE automacao_fila SET status='Pendente',tentativa_atual=0,erro=NULL,
               cancelamento_solicitado=0,lease_token=NULL,lease_expira_em=NULL,
               disponivel_em=?,atualizado_em=? WHERE id=? AND empresa_id=? AND status='Dead-letter'""",
            (_iso(), _iso(), int(job_id), int(empresa_id)),
        )
    if cursor.rowcount != 1:
        raise ValueError("Item de dead-letter não encontrado.")


def listar(ator: dict, *, status: str | None = None, limite: int = 100) -> list[dict]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    where = ["empresa_id=?", "(filial_id=? OR ? IS NULL)"]
    params: list = [empresa_id, filial_id, filial_id]
    if status:
        where.append("status=?")
        params.append(str(status))
    if str(ator.get("perfil", "")).lower() != "admin":
        where.append("usuario_id=?")
        params.append(int(ator["id"]))
    params.append(max(1, min(int(limite), 1000)))
    with conectar() as con:
        rows = con.execute(
            f"SELECT * FROM automacao_fila WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    saida = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json") or "{}")
        saida.append(item)
    return saida


def _recuperar_leases_expirados() -> None:
    agora = _iso()
    with conectar() as con:
        con.execute(
            """UPDATE automacao_fila SET
               status=CASE WHEN tentativa_atual>=max_tentativas THEN 'Dead-letter' ELSE 'Pendente' END,
               erro='Lease expirou antes da conclusão; trabalho recuperado pelo scheduler.',
               lease_token=NULL,lease_expira_em=NULL,heartbeat_em=NULL,disponivel_em=?,atualizado_em=?
               WHERE status IN ('Executando','Cancelamento solicitado') AND lease_expira_em<?""",
            (agora, agora, agora),
        )


def _adquirir(lease_segundos: int = 120) -> dict | None:
    _recuperar_leases_expirados()
    agora = _agora()
    lease = uuid4().hex
    with conectar() as con:
        row = con.execute(
            """SELECT id FROM automacao_fila
               WHERE status='Pendente' AND cancelamento_solicitado=0 AND disponivel_em<=?
               ORDER BY prioridade,id LIMIT 1""",
            (_iso(agora),),
        ).fetchone()
        if row is None:
            return None
        cursor = con.execute(
            """UPDATE automacao_fila SET status='Executando',tentativa_atual=tentativa_atual+1,
               lease_token=?,lease_expira_em=?,heartbeat_em=?,iniciado_em=COALESCE(iniciado_em,?),atualizado_em=?
               WHERE id=? AND status='Pendente' AND cancelamento_solicitado=0""",
            (lease, _iso(agora + timedelta(seconds=max(30, lease_segundos))), _iso(agora),
             _iso(agora), _iso(agora), int(row["id"])),
        )
        if cursor.rowcount != 1:
            return None
        item = con.execute("SELECT * FROM automacao_fila WHERE id=?", (int(row["id"]),)).fetchone()
    return dict(item) if item else None


def _ator_job(item: dict) -> dict:
    with conectar() as con:
        row = con.execute(
            "SELECT id,nome,usuario,perfil,perfil_acesso,email_corporativo,ativo,sessao_epoch FROM usuarios WHERE id=?",
            (int(item["usuario_id"]),),
        ).fetchone()
    if row is None or not bool(row["ativo"]):
        raise PermissionError("O responsável pela automação não está ativo.")
    return {
        **dict(row), "ativo": True, "_empresa_id": int(item["empresa_id"]),
        "_filial_id": int(item["filial_id"]) if item["filial_id"] is not None else None,
    }


def _cancelado(item_id: int, lease_token: str) -> bool:
    with conectar() as con:
        row = con.execute(
            "SELECT cancelamento_solicitado FROM automacao_fila WHERE id=? AND lease_token=?",
            (int(item_id), lease_token),
        ).fetchone()
    return row is None or bool(row["cancelamento_solicitado"])


def _manter_lease(job_id: int, lease_token: str, parar: threading.Event, *, lease_segundos: int = 120) -> None:
    """Renova a concessão enquanto um handler potencialmente longo está em execução."""
    intervalo = max(10.0, min(40.0, lease_segundos / 3))
    while not parar.wait(intervalo):
        agora = _agora()
        try:
            with conectar() as con:
                cursor = con.execute(
                    """UPDATE automacao_fila SET heartbeat_em=?,lease_expira_em=?,atualizado_em=?
                       WHERE id=? AND lease_token=? AND status IN ('Executando','Cancelamento solicitado')""",
                    (_iso(agora), _iso(agora + timedelta(seconds=lease_segundos)), _iso(agora),
                     int(job_id), str(lease_token)),
                )
            if cursor.rowcount != 1:
                return
        except Exception:
            _LOG.exception("Não foi possível renovar o lease da automação %s", job_id)


def executar_um() -> bool:
    lease_segundos = 120
    item = _adquirir(lease_segundos)
    if item is None:
        return False
    job_id = int(item["id"])
    lease = str(item["lease_token"])
    parar_heartbeat = threading.Event()
    heartbeat = threading.Thread(
        target=_manter_lease,
        args=(job_id, lease, parar_heartbeat),
        kwargs={"lease_segundos": lease_segundos},
        name=f"Automation-Lease-{job_id}",
        daemon=True,
    )
    heartbeat.start()
    try:
        handler = _HANDLERS.get(str(item["handler"]))
        if handler is None:
            raise RuntimeError(f"Handler não disponível: {item['handler']}")
        ator = _ator_job(item)
        payload = json.loads(item["payload_json"] or "{}")
        resultado = handler(payload, ator, lambda: _cancelado(job_id, lease)) or {}
        if _cancelado(job_id, lease):
            with conectar() as con:
                con.execute(
                    """UPDATE automacao_fila SET status='Cancelado',concluido_em=?,atualizado_em=?,
                       lease_token=NULL,lease_expira_em=NULL WHERE id=? AND lease_token=?""",
                    (_iso(), _iso(), job_id, lease),
                )
        else:
            with conectar() as con:
                con.execute(
                    """UPDATE automacao_fila SET status='Concluído',resultado_json=?,concluido_em=?,
                       atualizado_em=?,lease_token=NULL,lease_expira_em=NULL,heartbeat_em=?
                       WHERE id=? AND lease_token=?""",
                    (json.dumps(resultado, ensure_ascii=False, default=str), _iso(), _iso(), _iso(), job_id, lease),
                )
    except Exception as exc:
        tentativa = int(item["tentativa_atual"] or 0)
        maximo = int(item["max_tentativas"] or 1)
        final = tentativa >= maximo
        espera = min(900, 2 ** min(10, max(1, tentativa)))
        with conectar() as con:
            con.execute(
                """UPDATE automacao_fila SET status=?,erro=?,disponivel_em=?,atualizado_em=?,
                   concluido_em=?,lease_token=NULL,lease_expira_em=NULL,heartbeat_em=NULL
                   WHERE id=? AND lease_token=?""",
                (
                    "Dead-letter" if final else "Pendente", str(exc)[:4000],
                    _iso(_agora() + timedelta(seconds=espera)), _iso(), _iso() if final else None,
                    job_id, lease,
                ),
            )
        _LOG.exception("Falha na automação %s (%s)", item["codigo"], item["handler"])
    finally:
        parar_heartbeat.set()
        heartbeat.join(timeout=1.0)
    return True


def _proxima(data: datetime, frequencia: str) -> datetime | None:
    frequencia = str(frequencia or "Manual").casefold()
    if frequencia in {"manual", "sob demanda"}:
        return None
    if frequencia in {"diário", "diario"}:
        return data + timedelta(days=1)
    if frequencia == "semanal":
        return data + timedelta(days=7)
    meses = 3 if frequencia == "trimestral" else 1
    mes_base = data.month - 1 + meses
    ano = data.year + mes_base // 12
    mes = mes_base % 12 + 1
    dia = min(data.day, monthrange(ano, mes)[1])
    return data.replace(year=ano, month=mes, day=dia)


def registrar_agendamento(
    *,
    modulo: str,
    referencia_tipo: str,
    referencia_id: int,
    handler: str,
    payload: dict,
    frequencia: str,
    ator: dict,
    proxima_execucao: str | datetime | None = None,
) -> int:
    empresa_id, filial_id = obter_escopo_ator(ator)
    proxima: str | None
    if isinstance(proxima_execucao, datetime):
        proxima = _iso(proxima_execucao)
    elif proxima_execucao:
        texto = str(proxima_execucao).strip()
        if len(texto) == 10:
            texto += "T08:00:00+00:00"
        proxima = texto
    else:
        calculada = _proxima(_agora(), frequencia)
        proxima = _iso(calculada) if calculada else None
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO automacao_agendamentos
               (empresa_id,filial_id,usuario_id,modulo,referencia_tipo,referencia_id,
                handler,payload_json,frequencia,proxima_execucao,ativo)
               VALUES (?,?,?,?,?,?,?,?,?,?,1)
               ON CONFLICT(empresa_id,modulo,referencia_tipo,referencia_id) DO UPDATE SET
               usuario_id=excluded.usuario_id,handler=excluded.handler,payload_json=excluded.payload_json,
               frequencia=excluded.frequencia,proxima_execucao=excluded.proxima_execucao,ativo=1,atualizado_em=CURRENT_TIMESTAMP
               RETURNING id""",
            (
                empresa_id, filial_id, int(ator["id"]), str(modulo), str(referencia_tipo),
                int(referencia_id), handler, json.dumps(payload or {}, ensure_ascii=False, default=str),
                str(frequencia), proxima,
            ),
        )
        row = cursor.fetchone()
    return int(row["id"] if hasattr(row, "keys") else row[0])


def processar_agendamentos() -> int:
    agora = _agora()
    with conectar() as con:
        rows = con.execute(
            """SELECT * FROM automacao_agendamentos
               WHERE ativo=1 AND proxima_execucao IS NOT NULL AND proxima_execucao<=?
               ORDER BY proxima_execucao,id LIMIT 100""",
            (_iso(agora),),
        ).fetchall()
    total = 0
    for row in rows:
        item = dict(row)
        try:
            ator = _ator_job({
                "usuario_id": item["usuario_id"], "empresa_id": item["empresa_id"],
                "filial_id": item["filial_id"],
            })
            enfileirar(
                item["handler"], f"Agendamento {item['modulo']} #{item['id']}",
                json.loads(item["payload_json"] or "{}"), ator,
                idempotency_key=f"agenda:{item['id']}:{item['proxima_execucao']}",
            )
            base = datetime.fromisoformat(str(item["proxima_execucao"]).replace(" ", "T", 1))
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            proxima = _proxima(base, item["frequencia"])
            with conectar() as con:
                con.execute(
                    """UPDATE automacao_agendamentos SET ultima_execucao=?,proxima_execucao=?,
                       ativo=?,atualizado_em=? WHERE id=? AND proxima_execucao=?""",
                    (_iso(agora), _iso(proxima) if proxima else None, int(proxima is not None),
                     _iso(agora), int(item["id"]), item["proxima_execucao"]),
                )
            total += 1
        except Exception:
            _LOG.exception("Falha ao materializar agendamento %s", item["id"])
    return total


class WorkerAutomacao:
    def __init__(self, *, intervalo: float = 1.0, scheduler_intervalo: float = 30.0):
        self.intervalo = max(0.2, float(intervalo))
        self.scheduler_intervalo = max(5.0, float(scheduler_intervalo))
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="Corporate-Automation-Worker", daemon=True)

    def iniciar(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def parar(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=max(0.1, timeout))

    def _loop(self) -> None:
        proximo_scheduler = 0.0
        while not self._stop.is_set():
            try:
                agora_mono = time.monotonic()
                if agora_mono >= proximo_scheduler:
                    processar_agendamentos()
                    from enterprise.core_v11.eventos import publicar_eventos_pendentes
                    publicar_eventos_pendentes(limite=100)
                    proximo_scheduler = agora_mono + self.scheduler_intervalo
                executou = executar_um()
            except Exception:
                executou = False
                _LOG.exception("Falha no ciclo do worker de automação")
            self._stop.wait(0.05 if executou else self.intervalo)


@registrar_handler("workflow.executar")
def _executar_workflow(payload: dict, ator: dict, cancelar: Callable[[], bool]) -> dict:
    if cancelar():
        return {"cancelado": True}
    from enterprise.workflows import executar_workflows
    ids = executar_workflows(
        str(payload.get("evento_modulo") or ""), str(payload.get("evento_tipo") or ""),
        dict(payload.get("dados") or {}), ator,
        recurso_tipo=payload.get("recurso_tipo"), recurso_id=payload.get("recurso_id"),
    )
    return {"workflows_executados": ids}


@registrar_handler("relatorio.gerar")
def _gerar_relatorio(payload: dict, ator: dict, cancelar: Callable[[], bool]) -> dict:
    if cancelar():
        return {"cancelado": True}
    modulo = str(payload.get("modulo") or "").lower()
    tipo = str(payload.get("tipo") or "")
    formato = str(payload.get("formato") or "PDF").upper().replace("EXCEL", "XLSX")
    if modulo == "financeiro":
        from enterprise.financeiro import gerar_relatorio_financeiro
        filtros = dict(payload.get("filtros") or {})
        caminho = Path(gerar_relatorio_financeiro(
            tipo, formato, ator, inicio=filtros.get("inicio"), fim=filtros.get("fim")
        ))
    else:
        extensao = "xlsx" if formato == "XLSX" else formato.lower()
        pasta = banco.STORAGE_DIR / "relatorios_automaticos" / str(ator["_empresa_id"]) / modulo
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"{modulo}_{_agora():%Y%m%d_%H%M%S}_{uuid4().hex[:6]}.{extensao}"
        if modulo == "rh":
            from enterprise.rh import gerar_relatorio_rh
            caminho = Path(gerar_relatorio_rh(tipo, formato, caminho, ator))
        elif modulo == "compras":
            from enterprise.compras import gerar_relatorio_compras
            caminho = Path(gerar_relatorio_compras(tipo, formato, caminho, ator))
        elif modulo == "estoque":
            from enterprise.estoque import gerar_relatorio_estoque
            caminho = Path(gerar_relatorio_estoque(tipo, formato, caminho, ator))
        else:
            raise ValueError(f"Módulo de relatório automático não suportado: {modulo}")
    return {
        "arquivo": str(caminho.relative_to(banco.STORAGE_DIR)) if banco.STORAGE_DIR.resolve() in caminho.resolve().parents else caminho.name,
        "tamanho_bytes": caminho.stat().st_size,
        "destinatarios": str(payload.get("destinatarios") or ""),
        "entrega_externa": "pendente_de_provedor" if payload.get("destinatarios") else "nao_solicitada",
    }


@registrar_handler("webhook.entregar")
def _entregar_webhook(payload: dict, ator: dict, cancelar: Callable[[], bool]) -> dict:
    if cancelar():
        return {"cancelado": True}
    from enterprise.webhooks import entregar
    return entregar(int(payload["entrega_id"]), dict(payload.get("dados") or {}))


@registrar_handler("backup.restaurar")
def _restaurar_backup(payload: dict, ator: dict, cancelar: Callable[[], bool]) -> dict:
    if cancelar():
        return {"cancelado": True}
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Restauração de backup exige administrador.")
    from enterprise.backups import restaurar_backup
    return restaurar_backup(str(payload["arquivo"]), ator)


__all__ = (
    "WorkerAutomacao", "aprovar", "enfileirar", "executar_um", "listar",
    "processar_agendamentos", "registrar_agendamento", "registrar_handler",
    "reprocessar_dead_letter", "solicitar_cancelamento",
)
