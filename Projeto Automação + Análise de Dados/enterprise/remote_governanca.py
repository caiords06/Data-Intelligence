"""Plano de controle do Data Intelligence Remote.

Esta camada emite autorizações efêmeras, aplica política e mantém uma trilha
encadeada. Captura/transmissão de tela e comandos do sistema operacional não
são implementados aqui e permanecem desabilitados até homologação específica.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets

from auth.banco import conectar
from enterprise.core_v11.common import escopo, registrar_evento, texto


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _hash_token(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _evento_remoto(con, autorizacao_id: int, tipo: str, detalhe: dict | None = None) -> str:
    anterior = con.execute(
        "SELECT hash_evento FROM ti_remote_eventos WHERE autorizacao_id=? ORDER BY id DESC LIMIT 1",
        (int(autorizacao_id),),
    ).fetchone()
    hash_anterior = str(anterior["hash_evento"]) if anterior else ""
    payload = json.dumps(detalhe or {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str)
    momento = _agora().isoformat()
    hash_evento = hashlib.sha256(f"{autorizacao_id}|{tipo}|{payload}|{momento}|{hash_anterior}".encode("utf-8")).hexdigest()
    con.execute(
        """INSERT INTO ti_remote_eventos(autorizacao_id,tipo,detalhe_json,hash_anterior,hash_evento,criado_em)
           VALUES (?,?,?,?,?,?)""", (int(autorizacao_id), str(tipo), payload, hash_anterior or None, hash_evento, momento),
    )
    return hash_evento


def salvar_politica_remota(dados: dict, ator: dict) -> int:
    empresa_id, filial_id = escopo(ator, "ti", "aprovar")
    nao_assistido = bool(dados.get("acesso_nao_assistido"))
    justificativa = texto(dados.get("justificativa_nao_assistido"), maximo=3000)
    if nao_assistido and len(justificativa) < 10:
        raise ValueError("Acesso não assistido exige finalidade, escopo e justificativa formal.")
    duracao = max(5, min(int(dados.get("duracao_max_minutos") or 60), 480))
    with conectar() as con:
        con.execute("UPDATE ti_remote_politicas SET ativo=0,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE empresa_id=? AND ativo=1", (int(ator["id"]), empresa_id))
        cursor = con.execute(
            """INSERT INTO ti_remote_politicas
               (empresa_id,nome,exige_chamado,exige_consentimento,acesso_nao_assistido,permite_clipboard,
                permite_transferencia,permite_terminal,duracao_max_minutos,justificativa_nao_assistido,
                ativo,criado_por,atualizado_por) VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?)""",
            (empresa_id, texto(dados.get("nome") or "Política corporativa", minimo=3, maximo=180),
             int(dados.get("exige_chamado", True)), int(dados.get("exige_consentimento", True)), int(nao_assistido),
             int(bool(dados.get("permite_clipboard"))), int(bool(dados.get("permite_transferencia"))),
             int(bool(dados.get("permite_terminal"))), duracao, justificativa, int(ator["id"]), int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="ti", tipo="remote.politica_ativada",
                         recurso_tipo="ti_remote_politicas", recurso_id=identificador, ator=ator,
                         payload={"nao_assistido": nao_assistido, "duracao_max_minutos": duracao})
    return identificador


def obter_politica_remota(ator: dict) -> dict | None:
    empresa_id, _ = escopo(ator, "ti", "ler")
    with conectar() as con:
        row = con.execute("SELECT * FROM ti_remote_politicas WHERE empresa_id=? AND ativo=1 ORDER BY id DESC LIMIT 1", (empresa_id,)).fetchone()
    return dict(row) if row else None


def emitir_autorizacao_remota(ativo_id: int, chamado_id: int | None, motivo: str, permissoes: dict, ator: dict, *, consentimento: bool) -> dict:
    empresa_id, filial_id = escopo(ator, "ti", "escrever")
    motivo = texto(motivo, minimo=10, maximo=2000, campo="Motivo")
    with conectar() as con:
        politica = con.execute("SELECT * FROM ti_remote_politicas WHERE empresa_id=? AND ativo=1 ORDER BY id DESC LIMIT 1", (empresa_id,)).fetchone()
        if politica is None:
            raise PermissionError("Defina e aprove a política de acesso remoto antes de emitir autorizações.")
        if politica["exige_chamado"] and not chamado_id:
            raise ValueError("A política exige vínculo com chamado.")
        if politica["exige_consentimento"] and not consentimento and not politica["acesso_nao_assistido"]:
            raise PermissionError("O usuário do equipamento precisa consentir com a sessão.")
        ativo = con.execute("SELECT id FROM ti_ativos WHERE id=? AND empresa_id=? AND (filial_id=? OR ? IS NULL) AND ativo=1", (int(ativo_id), empresa_id, filial_id, filial_id)).fetchone()
        if ativo is None: raise ValueError("Ativo não encontrado no contexto atual.")
        if chamado_id and con.execute("SELECT 1 FROM ti_chamados WHERE id=? AND empresa_id=?", (int(chamado_id), empresa_id)).fetchone() is None:
            raise ValueError("Chamado não pertence à empresa atual.")
        solicitadas = {str(k): bool(v) for k, v in dict(permissoes or {}).items() if str(k) in {"visualizar", "controlar", "clipboard", "transferencia", "terminal"}}
        efetivas = {
            "visualizar": bool(solicitadas.get("visualizar", True)),
            "controlar": bool(solicitadas.get("controlar", False)),
            "clipboard": bool(solicitadas.get("clipboard")) and bool(politica["permite_clipboard"]),
            "transferencia": bool(solicitadas.get("transferencia")) and bool(politica["permite_transferencia"]),
            "terminal": bool(solicitadas.get("terminal")) and bool(politica["permite_terminal"]),
        }
        token = secrets.token_urlsafe(32)
        expira = (_agora() + timedelta(minutes=5)).isoformat()
        cursor = con.execute(
            """INSERT INTO ti_remote_autorizacoes
               (empresa_id,filial_id,politica_id,ativo_id,chamado_id,tecnico_id,motivo,token_hash,
                consentimento_confirmado,permissoes_json,status,expira_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,'Emitida',?)""",
            (empresa_id, filial_id, int(politica["id"]), int(ativo_id), int(chamado_id) if chamado_id else None,
             int(ator["id"]), motivo, _hash_token(token), int(bool(consentimento)),
             json.dumps(efetivas, ensure_ascii=False, separators=(",", ":"), sort_keys=True), expira),
        )
        identificador = int(cursor.lastrowid)
        _evento_remoto(con, identificador, "autorizacao_emitida", {"permissoes": efetivas, "expira_em": expira})
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="ti", tipo="remote.autorizacao_emitida",
                         recurso_tipo="ti_remote_autorizacoes", recurso_id=identificador, ator=ator,
                         payload={"ativo_id": int(ativo_id), "chamado_id": chamado_id, "expira_em": expira})
    # O segredo é devolvido uma única vez e nunca persistido nem logado.
    return {"autorizacao_id": identificador, "token": token, "expira_em": expira, "permissoes": efetivas}


def consumir_autorizacao_remota(token: str, ativo_id: int) -> dict:
    token_hash = _hash_token(texto(token, minimo=20, maximo=256, campo="Token"))
    agora = _agora().isoformat()
    with conectar() as con:
        row = con.execute("SELECT * FROM ti_remote_autorizacoes WHERE token_hash=? AND ativo_id=?", (token_hash, int(ativo_id))).fetchone()
        if row is None: raise PermissionError("Autorização remota inválida.")
        if row["status"] != "Emitida" or row["consumido_em"] or str(row["expira_em"]) < agora:
            raise PermissionError("Autorização remota expirada ou já utilizada.")
        cursor = con.execute("UPDATE ti_remote_autorizacoes SET status='Em andamento',consumido_em=? WHERE id=? AND status='Emitida'", (agora, int(row["id"])))
        if cursor.rowcount != 1: raise PermissionError("Autorização remota já consumida.")
        _evento_remoto(con, int(row["id"]), "autorizacao_consumida", {"ativo_id": int(ativo_id)})
    return {"autorizacao_id": int(row["id"]), "empresa_id": int(row["empresa_id"]), "permissoes": json.loads(row["permissoes_json"] or "{}")}


def encerrar_autorizacao_remota(autorizacao_id: int, resultado: str, ator: dict) -> None:
    empresa_id, filial_id = escopo(ator, "ti", "escrever")
    with conectar() as con:
        row = con.execute("SELECT * FROM ti_remote_autorizacoes WHERE id=? AND empresa_id=?", (int(autorizacao_id), empresa_id)).fetchone()
        if row is None: raise ValueError("Autorização remota não encontrada.")
        if int(row["tecnico_id"]) != int(ator["id"]) and str(ator.get("perfil") or "").lower() != "admin":
            raise PermissionError("Somente o técnico da sessão ou administrador pode encerrá-la.")
        con.execute("UPDATE ti_remote_autorizacoes SET status='Encerrada',encerrado_em=CURRENT_TIMESTAMP,resultado=? WHERE id=?", (texto(resultado, minimo=3, maximo=3000), int(autorizacao_id)))
        _evento_remoto(con, int(autorizacao_id), "sessao_encerrada", {"resultado": texto(resultado, maximo=3000)})
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="ti", tipo="remote.sessao_encerrada",
                         recurso_tipo="ti_remote_autorizacoes", recurso_id=int(autorizacao_id), ator=ator, payload={})


def listar_autorizacoes_remotas(ator: dict, *, limite: int = 500) -> list[dict]:
    empresa_id, _ = escopo(ator, "ti", "ler")
    with conectar() as con:
        rows = con.execute(
            """SELECT a.id,a.empresa_id,a.filial_id,a.ativo_id,a.chamado_id,a.tecnico_id,a.motivo,
               a.consentimento_confirmado,a.permissoes_json,a.status,a.expira_em,a.consumido_em,a.encerrado_em,a.resultado,a.criado_em
               FROM ti_remote_autorizacoes a WHERE a.empresa_id=? ORDER BY a.id DESC LIMIT ?""",
            (empresa_id, max(1, min(int(limite), 2000))),
        ).fetchall()
    return [{**dict(x), "permissoes": json.loads(x["permissoes_json"] or "{}")} for x in rows]


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "consumir_autorizacao_remota", "emitir_autorizacao_remota", "encerrar_autorizacao_remota",
    "listar_autorizacoes_remotas", "obter_politica_remota", "salvar_politica_remota",
)
