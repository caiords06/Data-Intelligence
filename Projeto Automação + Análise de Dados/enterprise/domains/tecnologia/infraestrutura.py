"""Infraestrutura, rede e inventário avançado de TI. Extraído na V9.5."""
from __future__ import annotations

import ipaddress
import sqlite3

from enterprise.domains.tecnologia.base import (
    _abrir_alerta, _decimal, _evento, _texto, conectar, exigir_acao, obter_escopo_ator,
)


def registrar_dispositivo_descoberto(segmento_id: int, dados: dict, ator: dict) -> int:
    """Registra resultado vindo de agente/conector; não executa varredura."""
    exigir_acao(ator, "registrar_descoberta")
    empresa_id, filial_id = obter_escopo_ator(ator)
    endereco = _texto(dados.get("endereco_ip"), 45)
    try:
        ip = ipaddress.ip_address(endereco)
    except ValueError as erro:
        raise ValueError("Endereço IP inválido.") from erro
    with conectar() as conexao:
        segmento = conexao.execute("SELECT * FROM ti_segmentos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1", (int(segmento_id), empresa_id, filial_id)).fetchone()
        if segmento is None or not segmento["autorizado"]:
            raise PermissionError("A descoberta só pode registrar dados em segmento previamente autorizado.")
        if ip not in ipaddress.ip_network(segmento["cidr"]):
            raise ValueError("O endereço não pertence ao segmento autorizado.")
        existente = conexao.execute("SELECT id FROM ti_dispositivos_rede WHERE segmento_id=? AND endereco_ip=?", (int(segmento_id), endereco)).fetchone()
        if existente:
            dispositivo_id = int(existente["id"])
            conexao.execute("""UPDATE ti_dispositivos_rede SET endereco_mac=COALESCE(?,endereco_mac),hostname=COALESCE(?,hostname),
                fabricante=COALESCE(?,fabricante),tipo_estimado=COALESCE(?,tipo_estimado),status=?,origem=?,
                ultimo_ping_ms=?,ativo=1,ultima_deteccao=CURRENT_TIMESTAMP WHERE id=?""",
                (_texto(dados.get("endereco_mac"), 30) or None, _texto(dados.get("hostname"), 120) or None,
                 _texto(dados.get("fabricante"), 120) or None, _texto(dados.get("tipo_estimado"), 60) or None,
                 _texto(dados.get("status") or "Online", 30), _texto(dados.get("origem") or "Agente", 30),
                 _decimal(dados.get("ultimo_ping_ms")), dispositivo_id))
        else:
            dispositivo_id = int(conexao.execute(
                """INSERT INTO ti_dispositivos_rede (
                    empresa_id,filial_id,segmento_id,endereco_ip,endereco_mac,hostname,
                    fabricante,tipo_estimado,status,origem,ultimo_ping_ms,ativo
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
                (empresa_id, filial_id, int(segmento_id), endereco,
                 _texto(dados.get("endereco_mac"), 30) or None, _texto(dados.get("hostname"), 120) or None,
                 _texto(dados.get("fabricante"), 120) or None, _texto(dados.get("tipo_estimado"), 60) or None,
                 _texto(dados.get("status") or "Novo", 30), _texto(dados.get("origem") or "Agente", 30),
                 _decimal(dados.get("ultimo_ping_ms"))),
            ).lastrowid)
            _abrir_alerta(conexao, ator, "dispositivo_novo", "Novo dispositivo identificado", f"{endereco} ainda não está vinculado ao patrimônio.", "Aviso", "ti_dispositivos_rede", dispositivo_id)
        _evento(conexao, ator, "descoberta_registrada", "ti_dispositivos_rede", dispositivo_id, depois={"ip": endereco, "origem": dados.get("origem") or "Agente"})
        return dispositivo_id

def contar_segmentos_ativos(ator: dict) -> int:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return int(conexao.execute(
            "SELECT COUNT(*) FROM ti_segmentos_rede WHERE empresa_id=? AND filial_id IS ? AND ativo=1",
            (empresa_id, filial_id),
        ).fetchone()[0])


def obter_segmento_rede(segmento_id: int, ator: dict) -> dict:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT * FROM ti_segmentos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(segmento_id), empresa_id, filial_id),
        ).fetchone()
    if linha is None:
        raise ValueError("Segmento não encontrado.")
    return dict(linha)


def _normalizar_segmento(dados: dict) -> dict:
    nome = _texto(dados.get("nome"), 120)
    if not nome:
        raise ValueError("Informe um nome para o segmento.")
    try:
        rede = ipaddress.ip_network(_texto(dados.get("cidr"), 60), strict=False)
    except ValueError as erro:
        raise ValueError("Informe uma rede CIDR válida, como 192.168.1.0/24.") from erro
    if not rede.is_private:
        raise ValueError("Somente segmentos privados administrados pela empresa podem ser cadastrados.")
    if rede.num_addresses > 4096:
        raise ValueError("O segmento é amplo demais. Divida-o em redes de até 4096 endereços.")
    gateway = _texto(dados.get("gateway"), 45) or None
    if gateway:
        try:
            gateway_ip = ipaddress.ip_address(gateway)
        except ValueError as erro:
            raise ValueError("Gateway inválido.") from erro
        if gateway_ip not in rede:
            raise ValueError("O gateway deve pertencer ao CIDR informado.")
    return {
        "nome": nome,
        "cidr": str(rede),
        "vlan": _texto(dados.get("vlan"), 30) or None,
        "gateway": gateway,
        "dns": _texto(dados.get("dns"), 120) or None,
        "departamento_id": int(dados["departamento_id"]) if dados.get("departamento_id") else None,
    }


def atualizar_segmento_rede(segmento_id: int, dados: dict, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_rede")
    empresa_id, filial_id = obter_escopo_ator(ator)
    normalizado = _normalizar_segmento(dados)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_segmentos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(segmento_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Segmento não encontrado.")
        if str(atual["cidr"]) != normalizado["cidr"]:
            dispositivos = int(conexao.execute(
                "SELECT COUNT(*) FROM ti_dispositivos_rede WHERE segmento_id=? AND ativo=1",
                (int(segmento_id),),
            ).fetchone()[0])
            if dispositivos:
                raise ValueError("O CIDR não pode ser alterado enquanto houver dispositivos registrados. Arquive os dispositivos ou crie um novo segmento.")
            conflito = conexao.execute(
                """SELECT id, ativo FROM ti_segmentos_rede
                   WHERE empresa_id=? AND filial_id IS ? AND cidr=? AND id<>?
                   LIMIT 1""",
                (empresa_id, filial_id, normalizado["cidr"], int(segmento_id)),
            ).fetchone()
            if conflito is not None:
                estado = "ativo" if bool(conflito["ativo"]) else "arquivado"
                raise ValueError(
                    f"O CIDR {normalizado['cidr']} já pertence a outro segmento {estado} desta filial."
                )
        try:
            conexao.execute(
                """UPDATE ti_segmentos_rede SET nome=?,cidr=?,vlan=?,gateway=?,dns=?,departamento_id=?
                   WHERE id=?""",
                (normalizado["nome"], normalizado["cidr"], normalizado["vlan"], normalizado["gateway"],
                 normalizado["dns"], normalizado["departamento_id"], int(segmento_id)),
            )
        except sqlite3.IntegrityError as erro:
            raise ValueError(
                f"Não foi possível alterar o segmento para {normalizado['cidr']}: o CIDR já está em uso."
            ) from erro
        depois = dict(conexao.execute("SELECT * FROM ti_segmentos_rede WHERE id=?", (int(segmento_id),)).fetchone())
        _evento(conexao, ator, "segmento_atualizado", "ti_segmentos_rede", segmento_id, antes=dict(atual), depois=depois)


def revogar_autorizacao_segmento_rede(segmento_id: int, ator: dict, motivo: str = "") -> None:
    exigir_acao(ator, "autorizar_descoberta")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_segmentos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(segmento_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Segmento não encontrado.")
        conexao.execute(
            """UPDATE ti_segmentos_rede SET autorizado=0,justificativa_autorizacao=NULL,
               autorizado_por=NULL,autorizado_em=NULL WHERE id=?""",
            (int(segmento_id),),
        )
        _evento(conexao, ator, "descoberta_revogada", "ti_segmentos_rede", segmento_id,
                antes={"autorizado": bool(atual["autorizado"])}, depois={"autorizado": False},
                observacao=_texto(motivo, 1000) or "Autorização revogada pelo operador.")


def preparar_firewall_segmento(segmento_id: int, ator: dict) -> dict:
    exigir_acao(ator, "autorizar_descoberta")
    segmento = obter_segmento_rede(segmento_id, ator)
    from enterprise.firewall_ti import FirewallError, preparar_descoberta_local
    try:
        resultado = preparar_descoberta_local(segmento_id, segmento["cidr"])
    except FirewallError as erro:
        raise ValueError(f"Não foi possível preparar o Firewall do Windows: {erro}") from None
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            "UPDATE ti_segmentos_rede SET firewall_status=?,firewall_regra=? WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (resultado.get("status"), resultado.get("regra"), int(segmento_id), empresa_id, filial_id),
        )
        _evento(conexao, ator, "firewall_segmento_preparado", "ti_segmentos_rede", segmento_id,
                depois={"status": resultado.get("status"), "regra": resultado.get("regra")},
                observacao=resultado.get("mensagem"))
    return resultado


def remover_firewall_segmento(segmento_id: int, ator: dict) -> dict:
    exigir_acao(ator, "autorizar_descoberta")
    segmento = obter_segmento_rede(segmento_id, ator)
    from enterprise.firewall_ti import FirewallError, remover_descoberta_local
    try:
        resultado = remover_descoberta_local(segmento_id)
    except FirewallError as erro:
        raise ValueError(f"Não foi possível remover a regra do Firewall do Windows: {erro}") from None
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            "UPDATE ti_segmentos_rede SET firewall_status='Removida',firewall_regra=NULL WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (int(segmento_id), empresa_id, filial_id),
        )
        _evento(conexao, ator, "firewall_segmento_removido", "ti_segmentos_rede", segmento_id,
                antes={"firewall_status": segmento.get("firewall_status")}, depois={"firewall_status": "Removida"})
    return resultado


def remover_segmento_rede(segmento_id: int, ator: dict) -> dict:
    """Arquiva o segmento. A trilha e as descobertas permanecem no histórico."""
    exigir_acao(ator, "gerenciar_rede")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_segmentos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(segmento_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Segmento não encontrado.")
        conexao.execute(
            "UPDATE ti_segmentos_rede SET ativo=0,autorizado=0 WHERE id=?",
            (int(segmento_id),),
        )
        conexao.execute(
            "UPDATE ti_dispositivos_rede SET ativo=0,status='Arquivado' WHERE segmento_id=?",
            (int(segmento_id),),
        )
        _evento(conexao, ator, "segmento_removido", "ti_segmentos_rede", segmento_id,
                antes=dict(atual), depois={"ativo": False, "autorizado": False})
    aviso = None
    if atual["firewall_regra"]:
        try:
            from enterprise.firewall_ti import remover_descoberta_local
            remover_descoberta_local(segmento_id)
        except Exception as erro:
            aviso = f"O segmento foi arquivado, mas a regra do firewall precisa ser removida manualmente: {erro}"
    return {"removido": True, "aviso": aviso}


def descobrir_segmento_rede(segmento_id: int, ator: dict) -> dict:
    exigir_acao(ator, "registrar_descoberta")
    segmento = obter_segmento_rede(segmento_id, ator)
    if not segmento["autorizado"]:
        raise PermissionError("Autorize explicitamente o segmento antes de executar a descoberta.")
    from enterprise.rede_ti import descobrir_hosts
    resultado = descobrir_hosts(segmento["cidr"])
    vistos: set[str] = set()
    for dispositivo in resultado["dispositivos"]:
        vistos.add(dispositivo["endereco_ip"])
        registrar_dispositivo_descoberto(segmento_id, dispositivo, ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        existentes = conexao.execute(
            "SELECT id,endereco_ip FROM ti_dispositivos_rede WHERE segmento_id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(segmento_id), empresa_id, filial_id),
        ).fetchall()
        for item in existentes:
            if item["endereco_ip"] not in vistos:
                conexao.execute(
                    "UPDATE ti_dispositivos_rede SET status='Não respondeu' WHERE id=?",
                    (int(item["id"]),),
                )
        conexao.execute(
            """UPDATE ti_segmentos_rede SET ultima_varredura_em=CURRENT_TIMESTAMP,
               ultima_varredura_total=?,ultima_varredura_online=? WHERE id=?""",
            (int(resultado["total_testados"]), int(resultado["online"]), int(segmento_id)),
        )
        _evento(conexao, ator, "descoberta_executada", "ti_segmentos_rede", segmento_id,
                depois={"total_testados": resultado["total_testados"], "online": resultado["online"], "duracao_segundos": resultado["duracao_segundos"]})
    return resultado


def diagnosticar_segmento_rede(segmento_id: int, ator: dict) -> dict:
    exigir_acao(ator, "consultar")
    segmento = obter_segmento_rede(segmento_id, ator)
    from enterprise.rede_ti import diagnosticar_conectividade
    resultado = diagnosticar_conectividade(gateway=segmento.get("gateway"))
    resultado.update({"segmento_id": int(segmento_id), "segmento": segmento["nome"], "cidr": segmento["cidr"]})
    return resultado


def atualizar_ativo(ativo_id: int, dados: dict, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_ativos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    permitidos = {
        "nome", "tipo", "fabricante", "modelo", "numero_serie", "hostname", "endereco_ip",
        "endereco_mac", "sistema_operacional", "processador", "localizacao", "status", "criticidade",
        "remote_provider", "remote_id", "usuario_sessao", "remote_alias",
    }
    campos = {k: _texto(v, 180) or None for k, v in dados.items() if k in permitidos}
    for chave in ("memoria_gb", "armazenamento_gb"):
        if chave in dados:
            campos[chave] = _decimal(dados.get(chave) or 0, permite_vazio=False)
    if "usuario_responsavel_id" in dados:
        campos["usuario_responsavel_id"] = int(dados["usuario_responsavel_id"]) if dados.get("usuario_responsavel_id") else None
    if not campos:
        raise ValueError("Nenhum campo informado para atualização.")
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_ativos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(ativo_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Ativo não encontrado.")
        atribuicoes = ",".join(f"{campo}=?" for campo in campos)
        conexao.execute(
            f"UPDATE ti_ativos SET {atribuicoes},atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (*campos.values(), int(ator["id"]), int(ativo_id)),
        )
        depois = dict(conexao.execute("SELECT * FROM ti_ativos WHERE id=?", (int(ativo_id),)).fetchone())
        _evento(conexao, ator, "ativo_atualizado", "ti_ativos", ativo_id, antes=dict(atual), depois=depois)


def remover_ativo(ativo_id: int, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_ativos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_ativos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(ativo_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Ativo não encontrado.")
        conexao.execute("UPDATE ti_dispositivos_rede SET ativo_id=NULL WHERE ativo_id=?", (int(ativo_id),))
        conexao.execute(
            "UPDATE ti_ativos SET ativo=0,status='Desativado',estado_conectividade='Desconhecido',atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(ator["id"]), int(ativo_id)),
        )
        _evento(conexao, ator, "ativo_removido", "ti_ativos", ativo_id, antes=dict(atual), depois={"ativo": False, "status": "Desativado"})


def vincular_dispositivo_ativo(dispositivo_id: int, ativo_id: int, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_ativos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        dispositivo = conexao.execute(
            "SELECT * FROM ti_dispositivos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(dispositivo_id), empresa_id, filial_id),
        ).fetchone()
        ativo = conexao.execute(
            "SELECT * FROM ti_ativos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(ativo_id), empresa_id, filial_id),
        ).fetchone()
        if dispositivo is None or ativo is None:
            raise ValueError("Dispositivo ou ativo não encontrado no escopo atual.")
        conexao.execute("UPDATE ti_dispositivos_rede SET ativo_id=? WHERE id=?", (int(ativo_id), int(dispositivo_id)))
        conexao.execute(
            """UPDATE ti_ativos SET endereco_ip=COALESCE(?,endereco_ip),endereco_mac=COALESCE(?,endereco_mac),
               hostname=COALESCE(?,hostname),estado_conectividade=?,ultimo_contato=CURRENT_TIMESTAMP,
               atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (dispositivo["endereco_ip"], dispositivo["endereco_mac"], dispositivo["hostname"],
             "Online" if dispositivo["status"] == "Online" else ativo["estado_conectividade"], int(ator["id"]), int(ativo_id)),
        )
        _evento(conexao, ator, "dispositivo_vinculado", "ti_dispositivos_rede", dispositivo_id,
                depois={"ativo_id": int(ativo_id), "patrimonio": ativo["patrimonio"]})


def atualizar_dispositivo_rede(dispositivo_id: int, dados: dict, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_rede")
    empresa_id, filial_id = obter_escopo_ator(ator)
    campos = {
        "hostname": _texto(dados.get("hostname"), 120) or None,
        "fabricante": _texto(dados.get("fabricante"), 120) or None,
        "tipo_estimado": _texto(dados.get("tipo_estimado"), 60) or None,
        "observacao": _texto(dados.get("observacao"), 1000) or None,
    }
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_dispositivos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(dispositivo_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Dispositivo não encontrado.")
        conexao.execute(
            "UPDATE ti_dispositivos_rede SET hostname=?,fabricante=?,tipo_estimado=?,observacao=? WHERE id=?",
            (*campos.values(), int(dispositivo_id)),
        )
        _evento(conexao, ator, "dispositivo_identificado", "ti_dispositivos_rede", dispositivo_id, antes=dict(atual), depois=campos)


def remover_dispositivo_rede(dispositivo_id: int, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_rede")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_dispositivos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(dispositivo_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Dispositivo não encontrado.")
        conexao.execute("UPDATE ti_dispositivos_rede SET ativo=0,status='Arquivado' WHERE id=?", (int(dispositivo_id),))
        _evento(conexao, ator, "dispositivo_removido", "ti_dispositivos_rede", dispositivo_id, antes=dict(atual), depois={"ativo": False})


def detalhar_ativo(ativo_id: int, ator: dict) -> dict:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT a.*,u.nome usuario_responsavel,d.nome departamento_nome,
               t.cpu_percentual,t.memoria_percentual,t.disco_percentual,t.espaco_livre_gb,t.uptime_segundos,t.latencia_ms,t.coletado_em telemetria_em,
               g.status agent_status,g.ultimo_heartbeat agent_heartbeat,g.ultimo_ip agent_ultimo_ip
               FROM ti_ativos a LEFT JOIN usuarios u ON u.id=a.usuario_responsavel_id
               LEFT JOIN departamentos d ON d.id=a.departamento_id
               LEFT JOIN ti_telemetria t ON t.id=(SELECT id FROM ti_telemetria WHERE ativo_id=a.id ORDER BY coletado_em DESC,id DESC LIMIT 1)
               LEFT JOIN ti_agentes g ON g.ativo_id=a.id AND g.ativo=1
               WHERE a.id=? AND a.empresa_id=? AND a.filial_id IS ? AND a.ativo=1""",
            (int(ativo_id), empresa_id, filial_id),
        ).fetchone()
    if linha is None:
        raise ValueError("Ativo não encontrado.")
    return dict(linha)


def detalhar_dispositivo_rede(dispositivo_id: int, ator: dict) -> dict:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT d.*,s.nome segmento_nome,s.cidr,s.gateway,s.dns,s.vlan,
               a.patrimonio,a.nome ativo_nome,a.fabricante ativo_fabricante,a.modelo,a.numero_serie,
               a.sistema_operacional,a.versao_sistema,a.arquitetura,a.processador,a.memoria_gb,a.armazenamento_gb,
               a.usuario_sessao,a.usuario_responsavel_id,a.localizacao,a.estado_conectividade,a.saude_percentual,
               a.remote_provider,a.remote_id,a.remote_alias,a.remote_status,a.remote_versao,a.agente_versao,a.ultimo_contato,
               u.nome usuario_responsavel,
               t.cpu_percentual,t.memoria_percentual,t.disco_percentual,t.espaco_livre_gb,t.uptime_segundos,t.latencia_ms
               FROM ti_dispositivos_rede d JOIN ti_segmentos_rede s ON s.id=d.segmento_id
               LEFT JOIN ti_ativos a ON a.id=d.ativo_id LEFT JOIN usuarios u ON u.id=a.usuario_responsavel_id
               LEFT JOIN ti_telemetria t ON t.id=(SELECT id FROM ti_telemetria WHERE ativo_id=a.id ORDER BY coletado_em DESC,id DESC LIMIT 1)
               WHERE d.id=? AND d.empresa_id=? AND d.filial_id IS ? AND d.ativo=1""",
            (int(dispositivo_id), empresa_id, filial_id),
        ).fetchone()
    if linha is None:
        raise ValueError("Dispositivo não encontrado.")
    return dict(linha)
