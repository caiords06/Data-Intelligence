"""Adapter legado para nós da plataforma V9.

O inventário/agente canônico é ``ti_agentes`` via ``servidor_ti`` e
``servidor_corporativo``. Este módulo continua suportado para upgrade de
instalações antigas e por isso preserva o contrato HMAC histórico.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
import sqlite3
from pathlib import Path
from uuid import uuid4

from auth import banco
from auth.banco import conectar, registrar_auditoria
from enterprise.contexto import obter_escopo_ator


def _exigir_admin(ator: dict) -> None:
    if str((ator or {}).get("perfil", "")).lower() != "admin":
        raise PermissionError("Somente administradores podem gerenciar nós da plataforma.")


def cadastrar_no(dados: dict, ator: dict) -> dict:
    """Cadastra um nó e devolve o segredo uma única vez."""
    _exigir_admin(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    tipo = str(dados.get("tipo") or "Agente").strip().title()
    if tipo not in {"Servidor", "Central", "Agente"}:
        raise ValueError("Tipo de nó inválido.")
    nome = str(dados.get("nome") or "").strip()[:120]
    if len(nome) < 2:
        raise ValueError("Informe o nome do computador ou servidor.")
    identificador = str(dados.get("identificador") or uuid4()).strip()[:120]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,119}", identificador):
        raise ValueError(
            "O identificador deve ter de 8 a 120 caracteres e usar apenas "
            "letras, números, ponto, sublinhado ou hífen."
        )
    segredo = secrets.token_urlsafe(36)
    resumo = hashlib.sha256(segredo.encode("utf-8")).hexdigest()
    pasta = banco.STORAGE_DIR / "segredos_servidor"
    pasta.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # O servidor legado ainda é aceito como adapter, mas novos segredos não
        # ficam mais em texto puro no Windows. DPAPI protege no escopo da máquina.
        from agente_ti.credentials import _proteger_windows
        caminho = pasta / f"{identificador}.bin"
        protegido = _proteger_windows(segredo.encode("utf-8"))
        temporario = caminho.with_suffix(".tmp")
        temporario.write_bytes(base64.b64encode(protegido))
        os.replace(temporario, caminho)
    else:
        # Ambiente não-Windows é usado principalmente em testes/desenvolvimento.
        caminho = pasta / f"{identificador}.key"
        caminho.write_text(segredo, encoding="utf-8")
        try:
            os.chmod(caminho, 0o600)
        except OSError:
            pass
    relativo = caminho.relative_to(banco.STORAGE_DIR).as_posix()
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO nos_plataforma (
                    empresa_id,filial_id,identificador,nome,tipo,versao,sistema,
                    token_hash,segredo_ref,status,criado_por
                ) VALUES (?,?,?,?,?,?,?,?,?,'Ativo',?)
                """,
                (
                    empresa_id, filial_id, identificador, nome, tipo,
                    str(dados.get("versao") or "")[:40] or None,
                    str(dados.get("sistema") or "")[:120] or None,
                    resumo, relativo, int(ator["id"]),
                ),
            )
            no_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError as erro:
        caminho.unlink(missing_ok=True)
        raise ValueError("Este identificador de nó já está cadastrado.") from erro
    registrar_auditoria(
        "no_plataforma_cadastrado", usuario_id=int(ator["id"]),
        empresa_id=empresa_id, filial_id=filial_id, modulo="ti",
        entidade="nos_plataforma", entidade_id=no_id,
        dados_depois={"identificador": identificador, "nome": nome, "tipo": tipo},
    )
    return {"id": no_id, "identificador": identificador, "tipo": tipo, "token": segredo}


def listar_nos(ator: dict) -> list[dict]:
    _exigir_admin(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id,identificador,nome,tipo,versao,sistema,endereco_ip,status,
                   ultimo_heartbeat,criado_em
            FROM nos_plataforma
            WHERE empresa_id=? AND (filial_id IS ? OR filial_id IS NULL)
            ORDER BY tipo,nome
            """,
            (empresa_id, filial_id),
        ).fetchall()
    return [dict(item) for item in registros]


def alterar_status_no(no_id: int, status: str, ator: dict) -> None:
    _exigir_admin(ator)
    if status not in {"Ativo", "Bloqueado", "Revogado", "Offline"}:
        raise ValueError("Status do nó inválido.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute(
            "UPDATE nos_plataforma SET status=?,atualizado_em=CURRENT_TIMESTAMP "
            "WHERE id=? AND empresa_id=? AND (filial_id IS ? OR filial_id IS NULL)",
            (status, int(no_id), empresa_id, filial_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Nó não encontrado.")


def obter_no_por_identificador(identificador: str) -> dict | None:
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM nos_plataforma WHERE identificador=?",
            (str(identificador),),
        ).fetchone()
    return dict(registro) if registro is not None else None


def carregar_segredo_no(no: dict) -> str:
    referencia = str(no.get("segredo_ref") or "")
    caminho = (banco.STORAGE_DIR / referencia).resolve()
    raiz = banco.STORAGE_DIR.resolve()
    if raiz not in caminho.parents or not caminho.is_file():
        raise PermissionError("Credencial do nó não está disponível.")
    if os.name == "nt" and caminho.suffix.lower() == ".bin":
        from agente_ti.credentials import _desproteger_windows
        try:
            protegido = base64.b64decode(caminho.read_bytes(), validate=True)
            segredo = _desproteger_windows(protegido).decode("utf-8").strip()
        except Exception as erro:
            raise PermissionError("Credencial protegida do nó não pôde ser aberta.") from erro
    else:
        # Compatibilidade com instalações que antecedem a proteção DPAPI.
        segredo = caminho.read_text(encoding="utf-8").strip()
        if os.name == "nt" and caminho.suffix.lower() == ".key":
            try:
                from agente_ti.credentials import _proteger_windows
                novo = caminho.with_suffix(".bin")
                novo.write_bytes(base64.b64encode(_proteger_windows(segredo.encode("utf-8"))))
                with conectar() as conexao:
                    conexao.execute(
                        "UPDATE nos_plataforma SET segredo_ref=? WHERE id=?",
                        (novo.relative_to(banco.STORAGE_DIR).as_posix(), int(no["id"])),
                    )
                caminho.unlink(missing_ok=True)
            except Exception:
                # A leitura continua válida; uma próxima manutenção pode repetir
                # a migração caso o DPAPI esteja indisponível neste momento.
                pass
    if hashlib.sha256(segredo.encode("utf-8")).hexdigest() != no.get("token_hash"):
        raise PermissionError("Credencial do nó não passou na verificação de integridade.")
    return segredo
