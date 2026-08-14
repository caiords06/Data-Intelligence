"""Telemetria e snapshots dos agentes TI. Extraído na V9.5."""
from __future__ import annotations

from enterprise.domains.tecnologia.base import (
    _abrir_alerta, _decimal, _inteiro, _texto, conectar, exigir_acao, obter_escopo_ator,
)

def registrar_heartbeat(ativo_id: int, metricas: dict, ator: dict) -> int:
    exigir_acao(ator, "registrar_telemetria")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        ativo = conexao.execute("SELECT * FROM ti_ativos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1", (int(ativo_id), empresa_id, filial_id)).fetchone()
        if ativo is None:
            raise ValueError("Ativo não encontrado.")
        cpu = _decimal(metricas.get("cpu_percentual"), maximo=100)
        memoria = _decimal(metricas.get("memoria_percentual"), maximo=100)
        disco = _decimal(metricas.get("disco_percentual"), maximo=100)
        livre = _decimal(metricas.get("espaco_livre_gb"))
        latencia = _decimal(metricas.get("latencia_ms"))
        uptime = _inteiro(metricas.get("uptime_segundos") or 0)
        amostras = [x for x in (cpu, memoria, disco) if x is not None]
        saude = max(0.0, min(100.0, 100 - (sum(amostras) / len(amostras) if amostras else 0) * 0.35))
        telemetria_id = int(conexao.execute(
            """INSERT INTO ti_telemetria (
                ativo_id,cpu_percentual,memoria_percentual,disco_percentual,
                espaco_livre_gb,uptime_segundos,latencia_ms,agente_versao
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (int(ativo_id), cpu, memoria, disco, livre, uptime, latencia, _texto(metricas.get("agente_versao"), 40) or None),
        ).lastrowid)
        estado = "Com alerta" if any(x is not None and x >= 90 for x in (cpu, memoria, disco)) else "Online"
        conexao.execute(
            """UPDATE ti_ativos SET estado_conectividade=?,saude_percentual=?,ultimo_contato=CURRENT_TIMESTAMP,
               agente_versao=?,endereco_ip=COALESCE(?,endereco_ip),atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (estado, saude, _texto(metricas.get("agente_versao"), 40) or ativo["agente_versao"],
             _texto(metricas.get("endereco_ip"), 45) or None, int(ativo_id)),
        )
        if estado == "Com alerta":
            _abrir_alerta(conexao, ator, "telemetria", "Recurso acima do limite", f"{ativo['patrimonio']} apresentou consumo igual ou superior a 90%.", "Crítico", "ti_ativos", ativo_id)
        return telemetria_id


def registrar_snapshot_agente(payload: dict, ator: dict) -> int:
    """Ingere o contrato do agente já existente e atualiza ativo + telemetria.

    O método é independente do transporte HTTP; poderá ser usado pelo receptor
    central do agente sem acoplar o domínio a FastAPI/Flask.
    """
    exigir_acao(ator, "registrar_telemetria")
    empresa_id, filial_id = obter_escopo_ator(ator)
    patrimonio = _texto(payload.get("patrimonio"), 80)
    dispositivo = payload.get("dispositivo") or {}
    metricas = dict(payload.get("metricas") or {})
    remoto = payload.get("acesso_remoto") or {}
    if not patrimonio:
        raise ValueError("Snapshot do agente sem patrimônio.")
    with conectar() as conexao:
        ativo = conexao.execute(
            "SELECT * FROM ti_ativos WHERE empresa_id=? AND filial_id IS ? AND patrimonio=? AND ativo=1",
            (empresa_id, filial_id, patrimonio),
        ).fetchone()
        if ativo is None:
            raise ValueError("O patrimônio do agente ainda não está cadastrado como ativo.")
        ativo_id = int(ativo["id"])
        ips = dispositivo.get("enderecos_ip") or []
        macs = dispositivo.get("enderecos_mac") or []
        conexao.execute(
            """UPDATE ti_ativos SET agent_id=?,hostname=?,fqdn=?,endereco_ip=COALESCE(?,endereco_ip),
               endereco_mac=COALESCE(?,endereco_mac),sistema_operacional=?,versao_sistema=?,arquitetura=?,processador=?,
               memoria_gb=?,armazenamento_gb=?,usuario_sessao=?,agente_versao=?,remote_provider=?,remote_id=?,
               remote_alias=?,remote_status=?,remote_versao=?,estado_conectividade='Online',ultimo_contato=CURRENT_TIMESTAMP,
               atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (_texto(payload.get("agent_id"), 120) or None, _texto(dispositivo.get("hostname"), 120) or None,
             _texto(dispositivo.get("fqdn"), 180) or None, _texto(dispositivo.get("endereco_ip") or (ips[0] if ips else None), 45) or None,
             _texto(dispositivo.get("endereco_mac") or (macs[0] if macs else None), 30) or None,
             _texto(dispositivo.get("sistema_operacional"), 150) or None, _texto(dispositivo.get("versao_sistema"), 180) or None,
             _texto(dispositivo.get("arquitetura"), 80) or None, _texto(dispositivo.get("processador"), 180) or None,
             _decimal(dispositivo.get("memoria_total_gb") or 0, permite_vazio=False),
             _decimal(dispositivo.get("armazenamento_total_gb") or 0, permite_vazio=False),
             _texto(dispositivo.get("executado_como"), 120) or None, _texto(payload.get("agente_versao"), 40) or None,
             _texto(remoto.get("provedor"), 30) or None, _texto(remoto.get("identificador"), 120) or None,
             _texto(remoto.get("alias"), 120) or None, _texto(remoto.get("status"), 80) or None,
             _texto(remoto.get("versao"), 80) or None, int(ator["id"]), ativo_id),
        )
    metricas["agente_versao"] = payload.get("agente_versao")
    metricas["endereco_ip"] = dispositivo.get("endereco_ip") or (ips[0] if ips else None)
    registrar_heartbeat(ativo_id, metricas, ator)
    return ativo_id
