"""Serviços transacionais de Tecnologia e Serviços 3.0.

O serviço concentra regras de ITSM, inventário/CMDB, telemetria,
monitoramento, licenças e governança. Operações sensíveis exigem permissão
granular; descoberta de rede exige autorização registrada e o acesso remoto
apenas produz um destino para abertura deliberada pela interface.
"""

from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import math
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import pandas as pd

from enterprise.repositories import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator, tem_permissao

from enterprise.domains.tecnologia.base import (
    ACOES_TECNOLOGIA,
    PERFIS_ACOES,
    SLA_MINUTOS,
    STATUS_CHAMADO,
    PROVEDORES_REMOTOS,
    _texto,
    _inteiro,
    _decimal,
    _centavos,
    _data,
    _numero,
    tem_permissao_tecnologia,
    exigir_acao,
    salvar_permissao_acao,
    _evento,
    _notificar,
    _abrir_alerta,
)

def garantir_catalogos(ator: dict) -> dict:
    """Importa uma única vez registros legados sem apagar sua origem."""
    exigir_permissao(ator, "ti", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    importados = {"ativos": 0, "chamados": 0}
    with conectar() as conexao:
        legados_ativos = conexao.execute(
            "SELECT * FROM ativos_ti WHERE empresa_id=? AND filial_id IS ? AND estado_registro='Ativo'",
            (empresa_id, filial_id),
        ).fetchall()
        for legado in legados_ativos:
            existe = conexao.execute(
                "SELECT 1 FROM ti_ativos WHERE empresa_id=? AND patrimonio=?",
                (empresa_id, legado["patrimonio"]),
            ).fetchone()
            if existe:
                continue
            conexao.execute(
                """INSERT INTO ti_ativos (
                    empresa_id,filial_id,patrimonio,nome,tipo,status,endereco_ip,
                    criado_por,atualizado_por
                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                (empresa_id, filial_id, legado["patrimonio"], legado["nome"],
                 legado["tipo"] or "Computador", legado["status"] or "Disponível",
                 legado["endereco_ip"], int(legado["criado_por"] or ator["id"]), int(ator["id"])),
            )
            importados["ativos"] += 1
        legados_chamados = conexao.execute(
            "SELECT * FROM chamados_ti WHERE empresa_id=? AND filial_id IS ? AND estado_registro='Ativo'",
            (empresa_id, filial_id),
        ).fetchall()
        for legado in legados_chamados:
            numero = f"LEG-CH-{int(legado['id']):06d}"
            if conexao.execute("SELECT 1 FROM ti_chamados WHERE empresa_id=? AND numero=?", (empresa_id, numero)).fetchone():
                continue
            prioridade = legado["prioridade"] if legado["prioridade"] in SLA_MINUTOS else "Média"
            sla_atendimento, sla_solucao = SLA_MINUTOS[prioridade]
            status = "Resolvido" if legado["status"] == "Concluído" else (legado["status"] if legado["status"] in STATUS_CHAMADO else "Novo")
            conexao.execute(
                """INSERT INTO ti_chamados (
                    empresa_id,filial_id,numero,titulo,descricao,categoria,prioridade,
                    status,solicitante_id,tecnico_id,sla_atendimento_minutos,
                    sla_solucao_minutos,criado_por,atualizado_por
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (empresa_id, filial_id, numero, legado["titulo"],
                 "Importado da estrutura anterior.", legado["categoria"], prioridade,
                 status, int(legado["criado_por"] or ator["id"]), None,
                 sla_atendimento, sla_solucao, int(legado["criado_por"] or ator["id"]), int(ator["id"])),
            )
            importados["chamados"] += 1
    return importados


def criar_chamado(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "abrir_chamado")
    empresa_id, filial_id = obter_escopo_ator(ator)
    titulo = _texto(dados.get("titulo"), 180)
    descricao = _texto(dados.get("descricao"), 5000)
    if not titulo or not descricao:
        raise ValueError("Título e descrição são obrigatórios.")
    prioridade = _texto(dados.get("prioridade") or "Média", 20).title()
    if prioridade not in SLA_MINUTOS:
        raise ValueError("Prioridade inválida.")
    atendimento, solucao = SLA_MINUTOS[prioridade]
    operador_ti = tem_permissao(ator, "ti", "ler")
    # O portal público de suporte nunca pode ser usado para forjar chamados em
    # nome de terceiros ou atribuir técnico/ativo/sistema. Usuários técnicos
    # mantêm os campos administrativos do Service Desk.
    solicitante_id = int(dados.get("solicitante_id") or ator["id"]) if operador_ti else int(ator["id"])
    tecnico_id = int(dados["tecnico_id"]) if operador_ti and dados.get("tecnico_id") else None
    departamento_id = int(dados["departamento_id"]) if operador_ti and dados.get("departamento_id") else None
    ativo_id = int(dados["ativo_id"]) if operador_ti and dados.get("ativo_id") else None
    sistema_id = int(dados["sistema_id"]) if operador_ti and dados.get("sistema_id") else None
    numero = _numero("CH")
    with conectar() as conexao:
        chamado_id = int(conexao.execute(
            """INSERT INTO ti_chamados (
                empresa_id,filial_id,numero,titulo,descricao,categoria,subcategoria,
                prioridade,impacto,urgencia,status,solicitante_id,tecnico_id,
                departamento_id,ativo_id,sistema_id,sla_atendimento_minutos,
                sla_solucao_minutos,criado_por,atualizado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,'Novo',?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, numero, titulo, descricao,
             _texto(dados.get("categoria"), 80) or None, _texto(dados.get("subcategoria"), 80) or None,
             prioridade, _texto(dados.get("impacto") or "Individual", 30),
             _texto(dados.get("urgencia") or "Normal", 30), solicitante_id,
             tecnico_id, departamento_id, ativo_id, sistema_id,
             atendimento, solucao, int(ator["id"]), int(ator["id"])),
        ).lastrowid)
        depois = dict(conexao.execute("SELECT * FROM ti_chamados WHERE id=?", (chamado_id,)).fetchone())
        _evento(conexao, ator, "chamado_aberto", "ti_chamados", chamado_id, depois=depois)
        if prioridade == "Crítica":
            _notificar(conexao, ator, "Chamado crítico aberto", f"{numero} · {titulo}", "critico", "ti_chamados", chamado_id)
        return chamado_id


def atualizar_chamado(chamado_id: int, dados: dict, ator: dict) -> None:
    exigir_acao(ator, "atender_chamado")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_chamados WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (int(chamado_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Chamado não encontrado.")
        status = _texto(dados.get("status") or atual["status"], 40)
        if status not in STATUS_CHAMADO:
            raise ValueError("Status de chamado inválido.")
        if status == "Resolvido" and not tem_permissao_tecnologia(ator, "resolver_chamado"):
            raise PermissionError("Seu perfil não pode resolver chamados.")
        tecnico_id = int(dados["tecnico_id"]) if dados.get("tecnico_id") else atual["tecnico_id"]
        primeira = atual["primeira_resposta_em"]
        if status in {"Em atendimento", "Aguardando usuário", "Aguardando terceiro", "Resolvido"} and not primeira:
            primeira = datetime.now().isoformat(sep=" ", timespec="seconds")
        resolvido = datetime.now().isoformat(sep=" ", timespec="seconds") if status == "Resolvido" else (None if status == "Reaberto" else atual["resolvido_em"])
        conexao.execute(
            """UPDATE ti_chamados SET status=?,tecnico_id=?,equipe=?,causa=?,solucao=?,
               primeira_resposta_em=?,resolvido_em=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
               WHERE id=?""",
            (status, tecnico_id, _texto(dados.get("equipe") or atual["equipe"], 80) or None,
             _texto(dados.get("causa") or atual["causa"], 1500) or None,
             _texto(dados.get("solucao") or atual["solucao"], 2500) or None,
             primeira, resolvido, int(ator["id"]), int(chamado_id)),
        )
        depois = dict(conexao.execute("SELECT * FROM ti_chamados WHERE id=?", (int(chamado_id),)).fetchone())
        _evento(conexao, ator, "chamado_atualizado", "ti_chamados", chamado_id, antes=dict(atual), depois=depois)


def adicionar_comentario(chamado_id: int, comentario: str, ator: dict, *, interno=False) -> int:
    exigir_acao(ator, "atender_chamado" if interno else "abrir_chamado")
    empresa_id, filial_id = obter_escopo_ator(ator)
    texto = _texto(comentario, 5000)
    if not texto:
        raise ValueError("O comentário não pode ficar vazio.")
    with conectar() as conexao:
        if conexao.execute("SELECT 1 FROM ti_chamados WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(chamado_id), empresa_id, filial_id)).fetchone() is None:
            raise ValueError("Chamado não encontrado.")
        comentario_id = int(conexao.execute(
            "INSERT INTO ti_chamado_comentarios (chamado_id,usuario_id,comentario,interno) VALUES (?,?,?,?)",
            (int(chamado_id), int(ator["id"]), texto, int(bool(interno))),
        ).lastrowid)
        _evento(conexao, ator, "comentario_adicionado", "ti_chamados", chamado_id, depois={"comentario_id": comentario_id, "interno": bool(interno)})
        return comentario_id


def criar_ativo(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_ativos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    patrimonio = _texto(dados.get("patrimonio"), 80)
    nome = _texto(dados.get("nome"), 180)
    if not patrimonio or not nome:
        raise ValueError("Patrimônio e nome do ativo são obrigatórios.")
    with conectar() as conexao:
        ativo_id = int(conexao.execute(
            """INSERT INTO ti_ativos (
                empresa_id,filial_id,patrimonio,nome,tipo,fabricante,modelo,
                numero_serie,hostname,endereco_ip,endereco_mac,sistema_operacional,
                processador,memoria_gb,armazenamento_gb,usuario_responsavel_id,
                departamento_id,centro_custo_id,localizacao,status,criticidade,
                comprado_em,garantia_ate,valor_centavos,fornecedor_id,estoque_item_id,
                remote_provider,remote_id,criado_por,atualizado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, patrimonio, nome, _texto(dados.get("tipo") or "Computador", 60),
             _texto(dados.get("fabricante"), 100) or None, _texto(dados.get("modelo"), 120) or None,
             _texto(dados.get("numero_serie"), 120) or None, _texto(dados.get("hostname"), 120) or None,
             _texto(dados.get("endereco_ip"), 45) or None, _texto(dados.get("endereco_mac"), 30) or None,
             _texto(dados.get("sistema_operacional"), 150) or None, _texto(dados.get("processador"), 150) or None,
             _decimal(dados.get("memoria_gb") or 0, permite_vazio=False),
             _decimal(dados.get("armazenamento_gb") or 0, permite_vazio=False),
             int(dados["usuario_responsavel_id"]) if dados.get("usuario_responsavel_id") else None,
             int(dados["departamento_id"]) if dados.get("departamento_id") else None,
             int(dados["centro_custo_id"]) if dados.get("centro_custo_id") else None,
             _texto(dados.get("localizacao"), 180) or None, _texto(dados.get("status") or "Disponível", 40),
             _texto(dados.get("criticidade") or "Média", 20), _data(dados.get("comprado_em")),
             _data(dados.get("garantia_ate")), _centavos(dados.get("valor")),
             int(dados["fornecedor_id"]) if dados.get("fornecedor_id") else None,
             int(dados["estoque_item_id"]) if dados.get("estoque_item_id") else None,
             _texto(dados.get("remote_provider"), 30) or None, _texto(dados.get("remote_id"), 120) or None,
             int(ator["id"]), int(ator["id"])),
        ).lastrowid)
        depois = dict(conexao.execute("SELECT * FROM ti_ativos WHERE id=?", (ativo_id,)).fetchone())
        _evento(conexao, ator, "ativo_cadastrado", "ti_ativos", ativo_id, depois=depois)
        return ativo_id


def criar_credencial_agente(ativo_id: int, ator: dict) -> dict:
    """Provisiona ou rotaciona a credencial de um agente para um ativo.

    O token em texto puro é retornado uma única vez. O banco guarda apenas
    SHA-256(token), que também é a chave derivada usada pelo HMAC do transporte.
    """
    exigir_acao(ator, "gerenciar_ativos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    agent_id = str(uuid4())
    with conectar() as conexao:
        ativo = conexao.execute(
            "SELECT * FROM ti_ativos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1",
            (int(ativo_id), empresa_id, filial_id),
        ).fetchone()
        if ativo is None:
            raise ValueError("Ativo não encontrado.")
        existente = conexao.execute(
            "SELECT * FROM ti_agentes WHERE ativo_id=?",
            (int(ativo_id),),
        ).fetchone()
        if existente is None:
            conexao.execute(
                """INSERT INTO ti_agentes (
                    empresa_id,filial_id,ativo_id,agent_id,token_hash,patrimonio,status,criado_por
                ) VALUES (?,?,?,?,?,?, 'Provisionado', ?)""",
                (empresa_id, filial_id, int(ativo_id), agent_id, token_hash, ativo["patrimonio"], int(ator["id"])),
            )
            evento = "agente_provisionado"
        else:
            agent_id = str(existente["agent_id"])
            conexao.execute(
                """UPDATE ti_agentes SET token_hash=?,patrimonio=?,status='Provisionado',
                   ultimo_ip=NULL,ultima_versao=NULL,ultimo_heartbeat=NULL,ativo=1,
                   criado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
                (token_hash, ativo["patrimonio"], int(ator["id"]), int(existente["id"])),
            )
            conexao.execute("DELETE FROM ti_agente_nonces WHERE agente_id=?", (int(existente["id"]),))
            evento = "agente_credencial_rotacionada"
        conexao.execute(
            "UPDATE ti_ativos SET agent_id=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (agent_id, int(ator["id"]), int(ativo_id)),
        )
        _evento(
            conexao, ator, evento, "ti_agentes", int(ativo_id),
            depois={"ativo_id": int(ativo_id), "agent_id": agent_id, "patrimonio": ativo["patrimonio"]},
            observacao="Credencial do agente gerada; o token em texto puro não foi persistido.",
        )
    return {
        "ativo_id": int(ativo_id),
        "patrimonio": str(ativo["patrimonio"]),
        "agent_id": agent_id,
        "token": token,
    }


def obter_credencial_agente(ativo_id: int, ator: dict) -> dict | None:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT g.id,g.ativo_id,g.agent_id,g.patrimonio,g.status,g.ultimo_ip,g.ultima_versao,
                      g.ultimo_heartbeat,g.criado_em,g.atualizado_em,g.ativo
               FROM ti_agentes g JOIN ti_ativos a ON a.id=g.ativo_id
               WHERE g.ativo_id=? AND g.empresa_id=? AND g.filial_id IS ? AND a.ativo=1""",
            (int(ativo_id), empresa_id, filial_id),
        ).fetchone()
    return dict(linha) if linha else None


def revogar_credencial_agente(ativo_id: int, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_ativos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        atual = conexao.execute(
            "SELECT * FROM ti_agentes WHERE ativo_id=? AND empresa_id=? AND filial_id IS ?",
            (int(ativo_id), empresa_id, filial_id),
        ).fetchone()
        if atual is None:
            raise ValueError("Este ativo ainda não possui agente provisionado.")
        conexao.execute(
            "UPDATE ti_agentes SET ativo=0,status='Revogado',atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(atual["id"]),),
        )
        conexao.execute("DELETE FROM ti_agente_nonces WHERE agente_id=?", (int(atual["id"]),))
        _evento(
            conexao, ator, "agente_revogado", "ti_agentes", int(atual["id"]),
            antes={"status": atual["status"], "ativo": bool(atual["ativo"])},
            depois={"status": "Revogado", "ativo": False},
        )


def listar_agentes_ti(ator: dict) -> list[dict]:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linhas = conexao.execute(
            """SELECT g.id,g.ativo_id,g.agent_id,g.patrimonio,g.status,g.ultimo_ip,g.ultima_versao,
                      g.ultimo_heartbeat,g.criado_em,g.atualizado_em,g.ativo,a.nome ativo_nome,a.hostname
               FROM ti_agentes g JOIN ti_ativos a ON a.id=g.ativo_id
               WHERE g.empresa_id=? AND g.filial_id IS ? AND a.ativo=1
               ORDER BY COALESCE(g.ultimo_heartbeat,g.criado_em) DESC""",
            (empresa_id, filial_id),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def iniciar_manutencao(ativo_id: int, problema: str, ator: dict, *, chamado_id=None, previsao=None) -> int:
    exigir_acao(ator, "gerenciar_manutencao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    descricao = _texto(problema, 1000)
    if not descricao:
        raise ValueError("Descreva o problema da manutenção.")
    with conectar() as conexao:
        ativo = conexao.execute("SELECT * FROM ti_ativos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1", (int(ativo_id), empresa_id, filial_id)).fetchone()
        if ativo is None:
            raise ValueError("Ativo não encontrado.")
        manutencao_id = int(conexao.execute(
            """INSERT INTO ti_manutencoes (
                empresa_id,filial_id,ativo_id,chamado_id,problema,previsao_em,criado_por
            ) VALUES (?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, int(ativo_id), int(chamado_id) if chamado_id else None,
             descricao, _data(previsao), int(ator["id"])),
        ).lastrowid)
        conexao.execute("UPDATE ti_ativos SET status='Em manutenção',estado_conectividade='Em manutenção',atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(ator["id"]), int(ativo_id)))
        _evento(conexao, ator, "manutencao_iniciada", "ti_manutencoes", manutencao_id, antes={"ativo_status": ativo["status"]}, depois={"ativo_status": "Em manutenção"})
        return manutencao_id


def concluir_manutencao(manutencao_id: int, diagnostico: str, ator: dict, *, custo=0) -> None:
    exigir_acao(ator, "gerenciar_manutencao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        manutencao = conexao.execute("SELECT * FROM ti_manutencoes WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(manutencao_id), empresa_id, filial_id)).fetchone()
        if manutencao is None:
            raise ValueError("Manutenção não encontrada.")
        conexao.execute("UPDATE ti_manutencoes SET diagnostico=?,custo_centavos=?,status='Concluída',concluido_em=CURRENT_TIMESTAMP WHERE id=?", (_texto(diagnostico, 2500), _centavos(custo), int(manutencao_id)))
        conexao.execute("UPDATE ti_ativos SET status='Disponível',estado_conectividade='Desconhecido',atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(ator["id"]), int(manutencao["ativo_id"])))
        _evento(conexao, ator, "manutencao_concluida", "ti_manutencoes", manutencao_id, antes=dict(manutencao), depois={"status": "Concluída", "diagnostico": diagnostico})


def criar_segmento_rede(dados: dict, ator: dict) -> int:
    """Cria um segmento ou reativa o mesmo CIDR previamente arquivado.

    O CRUD de segmentos usa remoção lógica para preservar auditoria. Por isso,
    tentar inserir novamente um CIDR arquivado não deve gerar um novo registro
    nem vazar ``sqlite3.IntegrityError`` para a interface. O registro anterior
    é reativado no mesmo escopo empresa/filial.
    """
    exigir_acao(ator, "gerenciar_rede")
    empresa_id, filial_id = obter_escopo_ator(ator)
    normalizado = _normalizar_segmento(dados)

    with conectar() as conexao:
        existente = conexao.execute(
            """SELECT * FROM ti_segmentos_rede
               WHERE empresa_id=? AND filial_id IS ? AND cidr=?
               ORDER BY id DESC LIMIT 1""",
            (empresa_id, filial_id, normalizado["cidr"]),
        ).fetchone()

        if existente is not None and bool(existente["ativo"]):
            raise ValueError(
                f"O segmento {normalizado['cidr']} já está cadastrado nesta filial. "
                "Edite o registro existente em vez de criar outro."
            )

        if existente is not None:
            segmento_id = int(existente["id"])
            antes = dict(existente)
            conexao.execute(
                """UPDATE ti_segmentos_rede
                   SET nome=?, vlan=?, gateway=?, dns=?, departamento_id=?,
                       ativo=1, autorizado=0, justificativa_autorizacao=NULL,
                       autorizado_por=NULL, autorizado_em=NULL,
                       firewall_status=NULL, firewall_regra=NULL,
                       ultima_varredura_em=NULL, ultima_varredura_total=0,
                       ultima_varredura_online=0
                   WHERE id=?""",
                (normalizado["nome"], normalizado["vlan"], normalizado["gateway"],
                 normalizado["dns"], normalizado["departamento_id"], segmento_id),
            )
            depois = dict(conexao.execute(
                "SELECT * FROM ti_segmentos_rede WHERE id=?",
                (segmento_id,),
            ).fetchone())
            _evento(
                conexao, ator, "segmento_reativado", "ti_segmentos_rede", segmento_id,
                antes=antes, depois=depois,
                observacao="Segmento arquivado reativado pelo cadastro do mesmo CIDR.",
            )
            return segmento_id

        try:
            segmento_id = int(conexao.execute(
                """INSERT INTO ti_segmentos_rede (
                    empresa_id,filial_id,nome,cidr,vlan,gateway,dns,departamento_id
                ) VALUES (?,?,?,?,?,?,?,?)""",
                (empresa_id, filial_id, normalizado["nome"], normalizado["cidr"],
                 normalizado["vlan"], normalizado["gateway"], normalizado["dns"],
                 normalizado["departamento_id"]),
            ).lastrowid)
        except sqlite3.IntegrityError as erro:
            # A interface nunca deve receber a mensagem bruta do SQLite.
            raise ValueError(
                f"Não foi possível cadastrar {normalizado['cidr']}: já existe um "
                "segmento com esse CIDR no mesmo escopo."
            ) from erro

        _evento(
            conexao, ator, "segmento_cadastrado", "ti_segmentos_rede", segmento_id,
            depois={"nome": normalizado["nome"], "cidr": normalizado["cidr"], "autorizado": False},
        )
        return segmento_id


def autorizar_segmento_rede(segmento_id: int, justificativa: str, ator: dict) -> None:
    exigir_acao(ator, "autorizar_descoberta")
    empresa_id, filial_id = obter_escopo_ator(ator)
    motivo = _texto(justificativa, 1000)
    if len(motivo) < 15:
        raise ValueError("Registre uma justificativa de autorização com pelo menos 15 caracteres.")
    with conectar() as conexao:
        segmento = conexao.execute("SELECT * FROM ti_segmentos_rede WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1", (int(segmento_id), empresa_id, filial_id)).fetchone()
        if segmento is None:
            raise ValueError("Segmento não encontrado.")
        conexao.execute("UPDATE ti_segmentos_rede SET autorizado=1,justificativa_autorizacao=?,autorizado_por=?,autorizado_em=CURRENT_TIMESTAMP WHERE id=?", (motivo, int(ator["id"]), int(segmento_id)))
        _evento(conexao, ator, "descoberta_autorizada", "ti_segmentos_rede", segmento_id, antes={"autorizado": False}, depois={"autorizado": True}, observacao=motivo)


def criar_licenca(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_licencas")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 180)
    if not nome:
        raise ValueError("Informe o nome da licença.")
    with conectar() as conexao:
        licenca_id = int(conexao.execute(
            """INSERT INTO ti_licencas (
                empresa_id,filial_id,nome,fornecedor_id,tipo,quantidade_contratada,
                custo_centavos,periodicidade,inicio_em,vencimento_em,
                renovacao_automatica,centro_custo_id,status,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, nome, int(dados["fornecedor_id"]) if dados.get("fornecedor_id") else None,
             _texto(dados.get("tipo") or "Assinatura", 40), _inteiro(dados.get("quantidade_contratada") or 1, minimo=1),
             _centavos(dados.get("custo")), _texto(dados.get("periodicidade") or "Mensal", 30),
             _data(dados.get("inicio_em")), _data(dados.get("vencimento_em")),
             int(bool(dados.get("renovacao_automatica"))), int(dados["centro_custo_id"]) if dados.get("centro_custo_id") else None,
             _texto(dados.get("status") or "Ativa", 30), int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "licenca_cadastrada", "ti_licencas", licenca_id, depois={"nome": nome})
        return licenca_id


def atribuir_licenca(licenca_id: int, ator: dict, *, usuario_id=None, ativo_id=None, identificador=None) -> int:
    exigir_acao(ator, "gerenciar_licencas")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        licenca = conexao.execute("SELECT * FROM ti_licencas WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(licenca_id), empresa_id, filial_id)).fetchone()
        if licenca is None:
            raise ValueError("Licença não encontrada.")
        usadas = conexao.execute("SELECT COUNT(*) n FROM ti_licenca_atribuicoes WHERE licenca_id=? AND ativo=1", (int(licenca_id),)).fetchone()["n"]
        if int(usadas) >= int(licenca["quantidade_contratada"]):
            raise ValueError("Não há licenças disponíveis para nova atribuição.")
        atribuicao_id = int(conexao.execute(
            "INSERT INTO ti_licenca_atribuicoes (licenca_id,usuario_id,ativo_id,identificador) VALUES (?,?,?,?)",
            (int(licenca_id), int(usuario_id) if usuario_id else None, int(ativo_id) if ativo_id else None, _texto(identificador, 180) or None),
        ).lastrowid)
        _evento(conexao, ator, "licenca_atribuida", "ti_licencas", licenca_id, depois={"atribuicao_id": atribuicao_id, "usuario_id": usuario_id, "ativo_id": ativo_id})
        return atribuicao_id


def criar_sistema(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_sistemas")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 180)
    if not nome:
        raise ValueError("Informe o nome do sistema.")
    with conectar() as conexao:
        sistema_id = int(conexao.execute(
            """INSERT INTO ti_sistemas (
                empresa_id,filial_id,nome,descricao,ambiente,criticidade,status,
                versao,url,servidor_ativo_id,fornecedor_id,responsavel_ti_id,
                responsavel_negocio_id,sla_disponibilidade
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, nome, _texto(dados.get("descricao"), 1500) or None,
             _texto(dados.get("ambiente") or "Produção", 40), _texto(dados.get("criticidade") or "Média", 20),
             _texto(dados.get("status") or "Operacional", 30), _texto(dados.get("versao"), 60) or None,
             _texto(dados.get("url"), 300) or None, int(dados["servidor_ativo_id"]) if dados.get("servidor_ativo_id") else None,
             int(dados["fornecedor_id"]) if dados.get("fornecedor_id") else None,
             int(dados["responsavel_ti_id"]) if dados.get("responsavel_ti_id") else None,
             int(dados["responsavel_negocio_id"]) if dados.get("responsavel_negocio_id") else None,
             _decimal(dados.get("sla_disponibilidade") or 99, maximo=100, permite_vazio=False)),
        ).lastrowid)
        _evento(conexao, ator, "sistema_cadastrado", "ti_sistemas", sistema_id, depois={"nome": nome})
        return sistema_id


def criar_monitor(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_monitoramento")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 180)
    tipo = _texto(dados.get("tipo"), 60)
    if not nome or not tipo:
        raise ValueError("Nome e tipo do monitor são obrigatórios.")
    with conectar() as conexao:
        monitor_id = int(conexao.execute(
            """INSERT INTO ti_monitores (
                empresa_id,filial_id,nome,tipo,ativo_id,sistema_id,alvo,
                intervalo_segundos,limite_aviso,limite_critico,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, nome, tipo, int(dados["ativo_id"]) if dados.get("ativo_id") else None,
             int(dados["sistema_id"]) if dados.get("sistema_id") else None, _texto(dados.get("alvo"), 300) or None,
             _inteiro(dados.get("intervalo_segundos") or 60, minimo=30), _decimal(dados.get("limite_aviso")),
             _decimal(dados.get("limite_critico")), int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "monitor_cadastrado", "ti_monitores", monitor_id, depois={"nome": nome, "tipo": tipo})
        return monitor_id


def registrar_evento_monitoramento(monitor_id: int, status: str, ator: dict, *, valor=None, mensagem="") -> int:
    exigir_acao(ator, "gerenciar_monitoramento")
    empresa_id, filial_id = obter_escopo_ator(ator)
    estado = _texto(status, 30)
    if estado not in {"Operacional", "Aviso", "Crítico", "Indisponível", "Sem dados"}:
        raise ValueError("Status de monitoramento inválido.")
    with conectar() as conexao:
        monitor = conexao.execute("SELECT * FROM ti_monitores WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(monitor_id), empresa_id, filial_id)).fetchone()
        if monitor is None:
            raise ValueError("Monitor não encontrado.")
        evento_id = int(conexao.execute("INSERT INTO ti_eventos_monitoramento (monitor_id,status,valor,mensagem) VALUES (?,?,?,?)", (int(monitor_id), estado, _decimal(valor) if valor not in (None, "") else None, _texto(mensagem, 1000) or None)).lastrowid)
        conexao.execute("UPDATE ti_monitores SET status=?,ultimo_valor=?,ultima_verificacao=CURRENT_TIMESTAMP WHERE id=?", (estado, _decimal(valor) if valor not in (None, "") else None, int(monitor_id)))
        if estado in {"Crítico", "Indisponível"}:
            _abrir_alerta(conexao, ator, "monitoramento", f"{monitor['nome']}: {estado}", mensagem or "Monitor fora do estado operacional.", "Crítico", "ti_monitores", monitor_id)
        _evento(conexao, ator, "evento_monitoramento", "ti_monitores", monitor_id, depois={"status": estado, "valor": valor, "evento_id": evento_id})
        return evento_id


def criar_artigo_conhecimento(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_conhecimento")
    empresa_id, _ = obter_escopo_ator(ator)
    titulo = _texto(dados.get("titulo"), 200)
    conteudo = _texto(dados.get("conteudo"), 20000)
    if not titulo or not conteudo:
        raise ValueError("Título e conteúdo são obrigatórios.")
    status = _texto(dados.get("status") or "Rascunho", 30)
    with conectar() as conexao:
        artigo_id = int(conexao.execute(
            """INSERT INTO ti_conhecimento (
                empresa_id,titulo,categoria,resumo,conteudo,palavras_chave,status,
                autor_id,publicado_em
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            (empresa_id, titulo, _texto(dados.get("categoria"), 80) or None,
             _texto(dados.get("resumo"), 500) or None, conteudo,
             _texto(dados.get("palavras_chave"), 300) or None, status,
             int(ator["id"]), datetime.now().isoformat(sep=" ", timespec="seconds") if status == "Publicado" else None),
        ).lastrowid)
        _evento(conexao, ator, "artigo_criado", "ti_conhecimento", artigo_id, depois={"titulo": titulo, "status": status})
        return artigo_id


def criar_contrato(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_contratos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    numero = _texto(dados.get("numero"), 80) or _numero("CTI")
    titulo = _texto(dados.get("titulo"), 200)
    if not titulo:
        raise ValueError("Informe o título do contrato.")
    with conectar() as conexao:
        contrato_id = int(conexao.execute(
            """INSERT INTO ti_contratos (
                empresa_id,filial_id,numero,titulo,fornecedor_id,tipo,inicio_em,
                termino_em,valor_centavos,periodicidade,sla,renovacao_automatica,
                responsavel_id,documento_id,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, numero, titulo, int(dados["fornecedor_id"]) if dados.get("fornecedor_id") else None,
             _texto(dados.get("tipo"), 60) or None, _data(dados.get("inicio_em")), _data(dados.get("termino_em")),
             _centavos(dados.get("valor")), _texto(dados.get("periodicidade"), 30) or None,
             _texto(dados.get("sla"), 500) or None, int(bool(dados.get("renovacao_automatica"))),
             int(dados["responsavel_id"]) if dados.get("responsavel_id") else None,
             int(dados["documento_id"]) if dados.get("documento_id") else None,
             _texto(dados.get("status") or "Ativo", 30)),
        ).lastrowid)
        _evento(conexao, ator, "contrato_cadastrado", "ti_contratos", contrato_id, depois={"numero": numero, "titulo": titulo})
        return contrato_id


def criar_problema(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_problemas")
    empresa_id, filial_id = obter_escopo_ator(ator)
    titulo, descricao = _texto(dados.get("titulo"), 200), _texto(dados.get("descricao"), 5000)
    if not titulo or not descricao:
        raise ValueError("Título e descrição são obrigatórios.")
    numero = _numero("PRB")
    with conectar() as conexao:
        problema_id = int(conexao.execute(
            """INSERT INTO ti_problemas (
                empresa_id,filial_id,numero,titulo,descricao,impacto,causa_raiz,
                workaround,solucao_definitiva,responsavel_id,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, numero, titulo, descricao, _texto(dados.get("impacto"), 300) or None,
             _texto(dados.get("causa_raiz"), 2000) or None, _texto(dados.get("workaround"), 2000) or None,
             _texto(dados.get("solucao_definitiva"), 2500) or None,
             int(dados["responsavel_id"]) if dados.get("responsavel_id") else None,
             _texto(dados.get("status") or "Investigando", 30)),
        ).lastrowid)
        for chamado_id in dados.get("chamados_ids") or ():
            conexao.execute("INSERT OR IGNORE INTO ti_problema_chamados (problema_id,chamado_id) VALUES (?,?)", (problema_id, int(chamado_id)))
        _evento(conexao, ator, "problema_registrado", "ti_problemas", problema_id, depois={"numero": numero, "titulo": titulo})
        return problema_id


def criar_mudanca(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_mudancas")
    empresa_id, filial_id = obter_escopo_ator(ator)
    titulo = _texto(dados.get("titulo"), 200)
    descricao = _texto(dados.get("descricao"), 5000)
    execucao = _texto(dados.get("plano_execucao"), 5000)
    rollback = _texto(dados.get("plano_rollback"), 5000)
    if not all((titulo, descricao, execucao, rollback)):
        raise ValueError("Título, descrição, plano de execução e rollback são obrigatórios.")
    numero = _numero("CHG")
    with conectar() as conexao:
        mudanca_id = int(conexao.execute(
            """INSERT INTO ti_mudancas (
                empresa_id,filial_id,numero,titulo,descricao,motivo,risco,impacto,
                plano_execucao,plano_rollback,janela_inicio,janela_fim,
                responsavel_id,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'Solicitada')""",
            (empresa_id, filial_id, numero, titulo, descricao, _texto(dados.get("motivo"), 1000) or None,
             _texto(dados.get("risco") or "Médio", 20), _texto(dados.get("impacto"), 1000) or None,
             execucao, rollback, _data(dados.get("janela_inicio")), _data(dados.get("janela_fim")),
             int(dados.get("responsavel_id") or ator["id"])),
        ).lastrowid)
        aprovacao_id = int(conexao.execute(
            """INSERT INTO aprovacoes (
                empresa_id,filial_id,solicitante_id,modulo,recurso_tipo,recurso_id,
                titulo,valor,status
            ) VALUES (?,?,?,'ti','ti_mudancas',?,?,0,'Pendente')""",
            (empresa_id, filial_id, int(ator["id"]), mudanca_id, f"Mudança {numero} · {titulo}"),
        ).lastrowid)
        conexao.execute("UPDATE ti_mudancas SET aprovacao_id=? WHERE id=?", (aprovacao_id, mudanca_id))
        _evento(conexao, ator, "mudanca_solicitada", "ti_mudancas", mudanca_id, depois={"numero": numero, "aprovacao_id": aprovacao_id})
        _notificar(conexao, ator, "Mudança aguardando aprovação", f"{numero} · {titulo}", "aviso", "ti_mudancas", mudanca_id)
        return mudanca_id


def decidir_mudanca(mudanca_id: int, decisao: str, ator: dict, observacao="") -> None:
    exigir_acao(ator, "aprovar_mudancas")
    empresa_id, filial_id = obter_escopo_ator(ator)
    mapa = {"Aprovar": "Aprovada", "Rejeitar": "Rejeitada", "Solicitar alteração": "Alteração solicitada"}
    if decisao not in mapa:
        raise ValueError("Decisão inválida.")
    with conectar() as conexao:
        mudanca = conexao.execute("SELECT * FROM ti_mudancas WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(mudanca_id), empresa_id, filial_id)).fetchone()
        if mudanca is None:
            raise ValueError("Mudança não encontrada.")
        conexao.execute("UPDATE ti_mudancas SET status=? WHERE id=?", (mapa[decisao], int(mudanca_id)))
        if mudanca["aprovacao_id"]:
            status_aprovacao = {"Aprovar": "Aprovado", "Rejeitar": "Rejeitado", "Solicitar alteração": "Alteração solicitada"}[decisao]
            conexao.execute("UPDATE aprovacoes SET status=?,responsavel_id=?,observacao=?,decidido_em=CURRENT_TIMESTAMP WHERE id=?", (status_aprovacao, int(ator["id"]), _texto(observacao, 1000), int(mudanca["aprovacao_id"])))
        _evento(conexao, ator, "mudanca_decidida", "ti_mudancas", mudanca_id, antes={"status": mudanca["status"]}, depois={"status": mapa[decisao]}, observacao=observacao)


def criar_incidente_seguranca(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_seguranca")
    empresa_id, filial_id = obter_escopo_ator(ator)
    titulo, descricao = _texto(dados.get("titulo"), 200), _texto(dados.get("descricao"), 5000)
    if not titulo or not descricao:
        raise ValueError("Título e descrição são obrigatórios.")
    numero = _numero("SEC")
    with conectar() as conexao:
        incidente_id = int(conexao.execute(
            """INSERT INTO ti_incidentes_seguranca (
                empresa_id,filial_id,numero,titulo,tipo,severidade,ativo_id,
                sistema_id,descricao,contencao,responsavel_id,status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,'Aberto')""",
            (empresa_id, filial_id, numero, titulo, _texto(dados.get("tipo") or "Incidente", 60),
             _texto(dados.get("severidade") or "Média", 20), int(dados["ativo_id"]) if dados.get("ativo_id") else None,
             int(dados["sistema_id"]) if dados.get("sistema_id") else None, descricao,
             _texto(dados.get("contencao"), 2500) or None, int(dados["responsavel_id"]) if dados.get("responsavel_id") else None),
        ).lastrowid)
        _evento(conexao, ator, "incidente_seguranca_aberto", "ti_incidentes_seguranca", incidente_id, depois={"numero": numero, "severidade": dados.get("severidade")})
        _notificar(conexao, ator, "Incidente de segurança", f"{numero} · {titulo}", "critico" if dados.get("severidade") == "Crítica" else "aviso", "ti_incidentes_seguranca", incidente_id)
        return incidente_id


def solicitar_acesso_remoto(ativo_id: int, provedor: str, justificativa: str, ator: dict, *, chamado_id=None, consentimento=False) -> dict:
    exigir_acao(ator, "acessar_remotamente")
    empresa_id, filial_id = obter_escopo_ator(ator)
    if provedor not in PROVEDORES_REMOTOS:
        raise ValueError("Provedor remoto não suportado.")
    motivo = _texto(justificativa, 1000)
    if len(motivo) < 10:
        raise ValueError("Informe a justificativa operacional do acesso.")
    if not chamado_id:
        raise ValueError("Vincule o acesso remoto a um chamado autorizado.")
    if not consentimento:
        raise PermissionError("Confirme o consentimento e a autorização antes de iniciar o acesso remoto.")
    with conectar() as conexao:
        ativo = conexao.execute("SELECT * FROM ti_ativos WHERE id=? AND empresa_id=? AND filial_id IS ? AND ativo=1", (int(ativo_id), empresa_id, filial_id)).fetchone()
        if ativo is None:
            raise ValueError("Ativo não encontrado.")
        identificador = _texto(ativo["remote_id"], 120)
        if not identificador:
            raise ValueError("O ativo não possui identificador de acesso remoto configurado.")
        if ativo["remote_provider"] and ativo["remote_provider"] != provedor:
            raise ValueError("O provedor escolhido não corresponde ao configurado no ativo.")
        acesso_id = int(conexao.execute(
            """INSERT INTO ti_acessos_remotos (
                empresa_id,filial_id,ativo_id,chamado_id,tecnico_id,provedor,
                identificador_destino,justificativa,consentimento_confirmado,
                status,iniciado_em
            ) VALUES (?,?,?,?,?,?,?,?,1,'Iniciada',CURRENT_TIMESTAMP)""",
            (empresa_id, filial_id, int(ativo_id), int(chamado_id) if chamado_id else None,
             int(ator["id"]), provedor, identificador, motivo),
        ).lastrowid)
        _evento(conexao, ator, "acesso_remoto_iniciado", "ti_acessos_remotos", acesso_id, depois={"ativo_id": ativo_id, "provedor": provedor, "chamado_id": chamado_id}, observacao=motivo)
        if provedor == "AnyDesk":
            destino = f"anydesk:{quote(identificador, safe='')}"
        elif provedor == "TeamViewer":
            destino = f"teamviewer10://control?device={quote(identificador, safe='')}"
        else:
            destino = f"rustdesk://connection/new/{quote(identificador, safe='')}"
        return {"acesso_id": acesso_id, "destino": destino, "provedor": provedor, "ativo": ativo["patrimonio"]}


def encerrar_acesso_remoto(acesso_id: int, resultado: str, ator: dict) -> None:
    exigir_acao(ator, "acessar_remotamente")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        acesso = conexao.execute("SELECT * FROM ti_acessos_remotos WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(acesso_id), empresa_id, filial_id)).fetchone()
        if acesso is None:
            raise ValueError("Sessão remota não encontrada.")
        conexao.execute("""UPDATE ti_acessos_remotos SET status='Encerrada',encerrado_em=CURRENT_TIMESTAMP,
            duracao_segundos=MAX(0,CAST((julianday('now')-julianday(iniciado_em))*86400 AS INTEGER)),resultado=? WHERE id=?""",
            (_texto(resultado, 1500), int(acesso_id)))
        _evento(conexao, ator, "acesso_remoto_encerrado", "ti_acessos_remotos", acesso_id, antes={"status": acesso["status"]}, depois={"status": "Encerrada", "resultado": resultado})


def gerar_alertas_tecnologia(ator: dict) -> int:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    antes = 0
    with conectar() as conexao:
        antes = int(conexao.execute("SELECT COUNT(*) n FROM ti_alertas WHERE empresa_id=? AND filial_id IS ? AND status='Aberto'", (empresa_id, filial_id)).fetchone()["n"])
        for ativo in conexao.execute(
            """SELECT * FROM ti_ativos WHERE empresa_id=? AND filial_id IS ? AND ativo=1
               AND status NOT IN ('Em manutenção','Desativado')
               AND ultimo_contato IS NOT NULL AND ultimo_contato<datetime('now','-5 minute')""",
            (empresa_id, filial_id),
        ).fetchall():
            conexao.execute("UPDATE ti_ativos SET estado_conectividade='Offline' WHERE id=?", (int(ativo["id"]),))
            _abrir_alerta(conexao, ator, "ativo_offline", "Ativo sem contato", f"{ativo['patrimonio']} não envia telemetria há mais de cinco minutos.", "Crítico" if ativo["criticidade"] == "Crítica" else "Aviso", "ti_ativos", ativo["id"])
        for licenca in conexao.execute(
            """SELECT * FROM ti_licencas WHERE empresa_id=? AND filial_id IS ? AND status='Ativa'
               AND vencimento_em BETWEEN date('now') AND date('now','+30 day')""",
            (empresa_id, filial_id),
        ).fetchall():
            _abrir_alerta(conexao, ator, "licenca_vencendo", "Licença próxima da renovação", f"{licenca['nome']} vence em {licenca['vencimento_em']}.", "Aviso", "ti_licencas", licenca["id"])
        for contrato in conexao.execute(
            """SELECT * FROM ti_contratos WHERE empresa_id=? AND filial_id IS ? AND status='Ativo'
               AND termino_em BETWEEN date('now') AND date('now','+45 day')""",
            (empresa_id, filial_id),
        ).fetchall():
            _abrir_alerta(conexao, ator, "contrato_vencendo", "Contrato de TI próximo do vencimento", f"{contrato['numero']} · {contrato['titulo']}.", "Aviso", "ti_contratos", contrato["id"])
        depois = int(conexao.execute("SELECT COUNT(*) n FROM ti_alertas WHERE empresa_id=? AND filial_id IS ? AND status='Aberto'", (empresa_id, filial_id)).fetchone()["n"])
    return max(0, depois - antes)


def resolver_alerta(alerta_id: int, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_monitoramento")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        alerta = conexao.execute("SELECT * FROM ti_alertas WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(alerta_id), empresa_id, filial_id)).fetchone()
        if alerta is None:
            raise ValueError("Alerta não encontrado.")
        conexao.execute("UPDATE ti_alertas SET status='Resolvido',responsavel_id=?,resolvido_em=CURRENT_TIMESTAMP WHERE id=?", (int(ator["id"]), int(alerta_id)))
        _evento(conexao, ator, "alerta_resolvido", "ti_alertas", alerta_id, antes={"status": alerta["status"]}, depois={"status": "Resolvido"})


def resumo_tecnologia(ator: dict) -> dict:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        q = lambda sql, p=(): conexao.execute(sql, p).fetchone()[0]
        escopo = (empresa_id, filial_id)
        total_ativos = int(q("SELECT COUNT(*) FROM ti_ativos WHERE empresa_id=? AND filial_id IS ? AND ativo=1", escopo))
        online = int(q("SELECT COUNT(*) FROM ti_ativos WHERE empresa_id=? AND filial_id IS ? AND ativo=1 AND estado_conectividade='Online'", escopo))
        return {
            "chamados_total": int(q("SELECT COUNT(*) FROM ti_chamados WHERE empresa_id=? AND filial_id IS ?", escopo)),
            "chamados_abertos": int(q("SELECT COUNT(*) FROM ti_chamados WHERE empresa_id=? AND filial_id IS ? AND status NOT IN ('Resolvido','Cancelado')", escopo)),
            "chamados_criticos": int(q("SELECT COUNT(*) FROM ti_chamados WHERE empresa_id=? AND filial_id IS ? AND prioridade='Crítica' AND status NOT IN ('Resolvido','Cancelado')", escopo)),
            "sla_vencido": int(q("""SELECT COUNT(*) FROM ti_chamados WHERE empresa_id=? AND filial_id IS ?
                AND status NOT IN ('Resolvido','Cancelado') AND datetime(sla_inicia_em,'+'||sla_solucao_minutos||' minutes')<datetime('now')""", escopo)),
            "ativos": total_ativos,
            "online": online,
            "offline": int(q("SELECT COUNT(*) FROM ti_ativos WHERE empresa_id=? AND filial_id IS ? AND ativo=1 AND estado_conectividade='Offline'", escopo)),
            "manutencao": int(q("SELECT COUNT(*) FROM ti_ativos WHERE empresa_id=? AND filial_id IS ? AND ativo=1 AND status='Em manutenção'", escopo)),
            "desconhecidos": int(q("SELECT COUNT(*) FROM ti_dispositivos_rede WHERE empresa_id=? AND filial_id IS ? AND ativo=1 AND ativo_id IS NULL AND status!='Ignorado'", escopo)),
            "licencas_vencendo": int(q("SELECT COUNT(*) FROM ti_licencas WHERE empresa_id=? AND filial_id IS ? AND status='Ativa' AND vencimento_em BETWEEN date('now') AND date('now','+30 day')", escopo)),
            "sistemas_indisponiveis": int(q("SELECT COUNT(*) FROM ti_sistemas WHERE empresa_id=? AND filial_id IS ? AND ativo=1 AND status!='Operacional'", escopo)),
            "alertas": int(q("SELECT COUNT(*) FROM ti_alertas WHERE empresa_id=? AND filial_id IS ? AND status='Aberto'", escopo)),
            "saude_percentual": round((online / total_ativos * 100) if total_ativos else 100.0, 1),
        }


def listar_secao(secao: str, ator: dict, *, pesquisa="", limite=500) -> list[dict]:
    exigir_acao(ator, "consultar_meus_chamados" if secao == "meus_chamados" else "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    termo = f"%{_texto(pesquisa, 100)}%"
    consultas = {
        "chamados": ("""SELECT c.*,s.nome solicitante_nome,t.nome tecnico_nome,a.patrimonio ativo_patrimonio,si.nome sistema_nome,
            CAST((julianday(datetime(c.sla_inicia_em,'+'||c.sla_solucao_minutos||' minutes'))-julianday('now'))*1440 AS INTEGER) sla_restante_minutos
            FROM ti_chamados c JOIN usuarios s ON s.id=c.solicitante_id LEFT JOIN usuarios t ON t.id=c.tecnico_id
            LEFT JOIN ti_ativos a ON a.id=c.ativo_id LEFT JOIN ti_sistemas si ON si.id=c.sistema_id
            WHERE c.empresa_id=? AND c.filial_id IS ? AND (c.numero LIKE ? OR c.titulo LIKE ? OR c.status LIKE ?)
            ORDER BY CASE c.prioridade WHEN 'Crítica' THEN 0 WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,c.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "meus_chamados": ("""SELECT c.*,t.nome tecnico_nome,a.patrimonio ativo_patrimonio FROM ti_chamados c
            LEFT JOIN usuarios t ON t.id=c.tecnico_id LEFT JOIN ti_ativos a ON a.id=c.ativo_id
            WHERE c.empresa_id=? AND c.filial_id IS ? AND c.solicitante_id=? AND (c.numero LIKE ? OR c.titulo LIKE ?)
            ORDER BY c.criado_em DESC""", (empresa_id, filial_id, int(ator["id"]), termo, termo)),
        "ativos": ("""SELECT a.*,u.nome usuario_responsavel,d.nome departamento_nome FROM ti_ativos a
            LEFT JOIN usuarios u ON u.id=a.usuario_responsavel_id LEFT JOIN departamentos d ON d.id=a.departamento_id
            WHERE a.empresa_id=? AND a.filial_id IS ? AND a.ativo=1 AND (a.patrimonio LIKE ? OR a.nome LIKE ? OR a.hostname LIKE ?)
            ORDER BY a.patrimonio""", (empresa_id, filial_id, termo, termo, termo)),
        "manutencoes": ("""SELECT m.*,a.patrimonio,a.nome ativo_nome,c.numero chamado_numero FROM ti_manutencoes m
            JOIN ti_ativos a ON a.id=m.ativo_id LEFT JOIN ti_chamados c ON c.id=m.chamado_id
            WHERE m.empresa_id=? AND m.filial_id IS ? AND (a.patrimonio LIKE ? OR m.problema LIKE ? OR m.status LIKE ?)
            ORDER BY m.inicio_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "rede": ("""SELECT d.*,s.nome segmento_nome,s.cidr,s.autorizado,a.patrimonio FROM ti_dispositivos_rede d
            JOIN ti_segmentos_rede s ON s.id=d.segmento_id LEFT JOIN ti_ativos a ON a.id=d.ativo_id
            WHERE d.empresa_id=? AND d.filial_id IS ? AND d.ativo=1 AND s.ativo=1 AND (d.endereco_ip LIKE ? OR d.hostname LIKE ? OR d.status LIKE ?)
            ORDER BY d.ultima_deteccao DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "segmentos": ("""SELECT s.*,u.nome autorizado_por_nome,d.nome departamento_nome FROM ti_segmentos_rede s
            LEFT JOIN usuarios u ON u.id=s.autorizado_por LEFT JOIN departamentos d ON d.id=s.departamento_id
            WHERE s.empresa_id=? AND s.filial_id IS ? AND s.ativo=1 AND (s.nome LIKE ? OR s.cidr LIKE ?)
            ORDER BY s.nome""", (empresa_id, filial_id, termo, termo)),
        "licencas": ("""SELECT l.*,COUNT(CASE WHEN a.ativo=1 THEN 1 END) quantidade_utilizada,
            l.quantidade_contratada-COUNT(CASE WHEN a.ativo=1 THEN 1 END) quantidade_disponivel
            FROM ti_licencas l LEFT JOIN ti_licenca_atribuicoes a ON a.licenca_id=l.id
            WHERE l.empresa_id=? AND l.filial_id IS ? AND (l.nome LIKE ? OR l.status LIKE ?)
            GROUP BY l.id ORDER BY l.nome""", (empresa_id, filial_id, termo, termo)),
        "sistemas": ("""SELECT s.*,a.patrimonio servidor_patrimonio,u.nome responsavel_ti_nome FROM ti_sistemas s
            LEFT JOIN ti_ativos a ON a.id=s.servidor_ativo_id LEFT JOIN usuarios u ON u.id=s.responsavel_ti_id
            WHERE s.empresa_id=? AND s.filial_id IS ? AND s.ativo=1 AND (s.nome LIKE ? OR s.status LIKE ? OR s.ambiente LIKE ?)
            ORDER BY s.criticidade DESC,s.nome""", (empresa_id, filial_id, termo, termo, termo)),
        "monitoramento": ("""SELECT m.*,a.patrimonio,si.nome sistema_nome FROM ti_monitores m
            LEFT JOIN ti_ativos a ON a.id=m.ativo_id LEFT JOIN ti_sistemas si ON si.id=m.sistema_id
            WHERE m.empresa_id=? AND m.filial_id IS ? AND (m.nome LIKE ? OR m.tipo LIKE ? OR m.status LIKE ?)
            ORDER BY CASE m.status WHEN 'Crítico' THEN 0 WHEN 'Indisponível' THEN 0 WHEN 'Aviso' THEN 1 ELSE 2 END,m.nome""", (empresa_id, filial_id, termo, termo, termo)),
        "conhecimento": ("""SELECT k.*,u.nome autor_nome FROM ti_conhecimento k JOIN usuarios u ON u.id=k.autor_id
            WHERE k.empresa_id=? AND (k.titulo LIKE ? OR k.categoria LIKE ? OR k.palavras_chave LIKE ?)
            ORDER BY CASE k.status WHEN 'Publicado' THEN 0 ELSE 1 END,k.criado_em DESC""", (empresa_id, termo, termo, termo)),
        "contratos": ("""SELECT c.*,f.razao_social fornecedor_nome,u.nome responsavel_nome FROM ti_contratos c
            LEFT JOIN cmp_fornecedores f ON f.id=c.fornecedor_id LEFT JOIN usuarios u ON u.id=c.responsavel_id
            WHERE c.empresa_id=? AND c.filial_id IS ? AND (c.numero LIKE ? OR c.titulo LIKE ? OR c.status LIKE ?)
            ORDER BY c.termino_em""", (empresa_id, filial_id, termo, termo, termo)),
        "mudancas": ("""SELECT m.*,u.nome responsavel_nome,a.status aprovacao_status FROM ti_mudancas m
            LEFT JOIN usuarios u ON u.id=m.responsavel_id LEFT JOIN aprovacoes a ON a.id=m.aprovacao_id
            WHERE m.empresa_id=? AND m.filial_id IS ? AND (m.numero LIKE ? OR m.titulo LIKE ? OR m.status LIKE ?)
            ORDER BY m.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "problemas": ("""SELECT p.*,u.nome responsavel_nome,COUNT(pc.chamado_id) chamados_relacionados FROM ti_problemas p
            LEFT JOIN usuarios u ON u.id=p.responsavel_id LEFT JOIN ti_problema_chamados pc ON pc.problema_id=p.id
            WHERE p.empresa_id=? AND p.filial_id IS ? AND (p.numero LIKE ? OR p.titulo LIKE ? OR p.status LIKE ?)
            GROUP BY p.id, u.nome ORDER BY p.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "seguranca": ("""SELECT i.*,a.patrimonio,si.nome sistema_nome,u.nome responsavel_nome FROM ti_incidentes_seguranca i
            LEFT JOIN ti_ativos a ON a.id=i.ativo_id LEFT JOIN ti_sistemas si ON si.id=i.sistema_id LEFT JOIN usuarios u ON u.id=i.responsavel_id
            WHERE i.empresa_id=? AND i.filial_id IS ? AND (i.numero LIKE ? OR i.titulo LIKE ? OR i.status LIKE ?)
            ORDER BY CASE i.severidade WHEN 'Crítica' THEN 0 WHEN 'Alta' THEN 1 ELSE 2 END,i.detectado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "alertas": ("""SELECT a.*,u.nome responsavel_nome FROM ti_alertas a LEFT JOIN usuarios u ON u.id=a.responsavel_id
            WHERE a.empresa_id=? AND a.filial_id IS ? AND (a.titulo LIKE ? OR a.mensagem LIKE ? OR a.status LIKE ?)
            ORDER BY CASE a.status WHEN 'Aberto' THEN 0 ELSE 1 END,CASE a.severidade WHEN 'Crítico' THEN 0 ELSE 1 END,a.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "acessos": ("""SELECT ar.*,a.patrimonio,u.nome tecnico_nome,c.numero chamado_numero FROM ti_acessos_remotos ar
            JOIN ti_ativos a ON a.id=ar.ativo_id JOIN usuarios u ON u.id=ar.tecnico_id LEFT JOIN ti_chamados c ON c.id=ar.chamado_id
            WHERE ar.empresa_id=? AND ar.filial_id IS ? AND (a.patrimonio LIKE ? OR u.nome LIKE ? OR ar.provedor LIKE ?)
            ORDER BY ar.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
        "auditoria": ("""SELECT h.*,u.nome usuario_nome FROM ti_historico h LEFT JOIN usuarios u ON u.id=h.usuario_id
            WHERE h.empresa_id=? AND h.filial_id IS ? AND (h.acao LIKE ? OR h.recurso_tipo LIKE ? OR u.nome LIKE ?)
            ORDER BY h.criado_em DESC""", (empresa_id, filial_id, termo, termo, termo)),
    }
    if secao not in consultas:
        return []
    sql, parametros = consultas[secao]
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(f"{sql} LIMIT ?", (*parametros, int(limite))).fetchall()]


def listar_usuarios_escopo(ator: dict) -> list[dict]:
    exigir_acao(ator, "consultar")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        return [dict(x) for x in conexao.execute(
            """SELECT DISTINCT u.id,u.nome,u.usuario FROM usuarios u JOIN usuarios_empresas ue ON ue.usuario_id=u.id
               WHERE ue.empresa_id=? AND ue.ativo=1 AND u.ativo=1 ORDER BY u.nome""", (empresa_id,)
        ).fetchall()]


def analisar_tecnologia(ator: dict) -> dict:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    resumo = resumo_tecnologia(ator)
    with conectar() as conexao:
        categorias = [dict(x) for x in conexao.execute(
            """SELECT COALESCE(categoria,'Sem categoria') categoria,COUNT(*) quantidade FROM ti_chamados
               WHERE empresa_id=? AND filial_id IS ? AND criado_em>=datetime('now','-30 day')
               GROUP BY categoria ORDER BY quantidade DESC LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
        reincidentes = [dict(x) for x in conexao.execute(
            """SELECT lower(titulo) titulo,COUNT(*) ocorrencias FROM ti_chamados
               WHERE empresa_id=? AND filial_id IS ? AND criado_em>=datetime('now','-90 day')
               GROUP BY lower(titulo) HAVING COUNT(*)>=3 ORDER BY ocorrencias DESC LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
        antigos = [dict(x) for x in conexao.execute(
            """SELECT patrimonio,nome,comprado_em FROM ti_ativos WHERE empresa_id=? AND filial_id IS ? AND ativo=1
               AND comprado_em IS NOT NULL AND comprado_em<date('now','-5 year') ORDER BY comprado_em LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
        ociosas = [dict(x) for x in conexao.execute(
            """SELECT l.nome,l.quantidade_contratada,COUNT(CASE WHEN a.ativo=1 THEN 1 END) utilizadas
               FROM ti_licencas l LEFT JOIN ti_licenca_atribuicoes a ON a.licenca_id=l.id
               WHERE l.empresa_id=? AND l.filial_id IS ? AND l.status='Ativa'
               GROUP BY l.id HAVING COUNT(CASE WHEN a.ativo=1 THEN 1 END) < l.quantidade_contratada*0.5 ORDER BY l.quantidade_contratada-COUNT(CASE WHEN a.ativo=1 THEN 1 END) DESC LIMIT 8""", (empresa_id, filial_id)
        ).fetchall()]
    pontos = []
    if resumo["sla_vencido"]:
        pontos.append(f"{resumo['sla_vencido']} chamado(s) ultrapassaram o SLA de solução.")
    if categorias:
        pontos.append(f"{categorias[0]['categoria']} concentra {categorias[0]['quantidade']} chamado(s) nos últimos 30 dias.")
    if reincidentes:
        pontos.append(f"O incidente '{reincidentes[0]['titulo']}' é reincidente e merece análise de causa raiz.")
    if antigos:
        pontos.append(f"{len(antigos)} ativo(s) da amostra possuem mais de cinco anos.")
    if ociosas:
        pontos.append(f"{ociosas[0]['nome']} possui utilização inferior a 50% das licenças contratadas.")
    if resumo["sistemas_indisponiveis"]:
        pontos.append(f"{resumo['sistemas_indisponiveis']} sistema(s) não estão operacionais.")
    if not pontos:
        pontos.append("Nenhum risco operacional relevante foi detectado no contexto atual de Tecnologia.")
    return {"resumo": resumo, "pontos_atencao": pontos, "categorias": categorias,
            "reincidentes": reincidentes, "ativos_antigos": antigos, "licencas_ociosas": ociosas}


def exportar_dataframe_tecnologia(ator: dict) -> pd.DataFrame:
    exigir_acao(ator, "consultar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linhas = conexao.execute(
            """SELECT c.numero,c.titulo,c.categoria,c.prioridade,c.impacto,c.urgencia,c.status,
                      c.sla_atendimento_minutos,c.sla_solucao_minutos,c.criado_em,
                      c.primeira_resposta_em,c.resolvido_em,s.nome solicitante,t.nome tecnico,
                      a.patrimonio,a.estado_conectividade,a.saude_percentual,si.nome sistema
               FROM ti_chamados c JOIN usuarios s ON s.id=c.solicitante_id
               LEFT JOIN usuarios t ON t.id=c.tecnico_id LEFT JOIN ti_ativos a ON a.id=c.ativo_id
               LEFT JOIN ti_sistemas si ON si.id=c.sistema_id
               WHERE c.empresa_id=? AND c.filial_id IS ? ORDER BY c.criado_em""",
            (empresa_id, filial_id),
        ).fetchall()
    return pd.DataFrame([dict(x) for x in linhas])


def gerar_relatorio_tecnologia(tipo: str, formato: str, destino: str | Path, ator: dict) -> Path:
    exigir_acao(ator, "gerar_relatorio")
    formato = _texto(formato, 10).lower()
    if formato not in {"csv", "json", "html"}:
        raise ValueError("Formato disponível: CSV, JSON ou HTML.")
    secao = {"chamados": "chamados", "ativos": "ativos", "licencas": "licencas", "sistemas": "sistemas", "alertas": "alertas", "auditoria": "auditoria"}.get(_texto(tipo, 30).lower())
    if not secao:
        raise ValueError("Tipo de relatório de Tecnologia inválido.")
    dados = listar_secao(secao, ator, limite=100000)
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if formato == "json":
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    elif formato == "html":
        frame = pd.DataFrame(dados)
        caminho.write_text("<meta charset='utf-8'><h1>Relatório de Tecnologia</h1>" + frame.to_html(index=False, border=0), encoding="utf-8")
    else:
        with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
            if dados:
                escritor = csv.DictWriter(arquivo, fieldnames=list(dados[0]))
                escritor.writeheader()
                escritor.writerows(dados)
            else:
                arquivo.write("sem_registros\n")
    return caminho

# ---------------------------------------------------------------------------
# Tecnologia 3.0 · operações interativas de rede / CRUD
# ---------------------------------------------------------------------------

# V9.5: operações de infraestrutura foram isoladas do núcleo ITSM.
from enterprise.domains.tecnologia.agentes import registrar_heartbeat, registrar_snapshot_agente
from enterprise.domains.tecnologia.infraestrutura import (
    registrar_dispositivo_descoberto, contar_segmentos_ativos, obter_segmento_rede, _normalizar_segmento, atualizar_segmento_rede,
    revogar_autorizacao_segmento_rede, preparar_firewall_segmento, remover_firewall_segmento,
    remover_segmento_rede, descobrir_segmento_rede, diagnosticar_segmento_rede, atualizar_ativo,
    remover_ativo, vincular_dispositivo_ativo, atualizar_dispositivo_rede, remover_dispositivo_rede,
    detalhar_ativo, detalhar_dispositivo_rede,
)

# V9.1+: em estações Central/Cliente, as APIs transacionais públicas desta fachada
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
