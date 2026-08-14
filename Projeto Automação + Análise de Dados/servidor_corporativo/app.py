"""API LAN/HTTPS para identidade, correio, arquivos e backups corporativos.

O servidor nunca expõe SQL remoto. Todas as operações passam por endpoints
específicos, autenticação bearer e escopo empresa/filial.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import ssl
import tempfile
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from core.observabilidade import RegistroSaude, novo_request_id
from core.ciclo_vida import aguardar_thread

from core.rpc_arquivos import (
    RPC_ARQUIVO_ENTRADA,
    RPC_ARQUIVO_SAIDA_PARAM,
    RPC_ARQUIVO_RETORNO,
    RPC_ARQUIVO_PERSISTE_SERVIDOR,
    MARCADOR_ENTRADA,
    MARCADOR_SAIDA,
)
from core.rpc_central import desserializar, serializar

from auth import banco
from auth.autenticacao import (
    _criar_usuario,
    autenticar_usuario,
    definir_perfil_acesso_usuario,
    definir_status_usuario,
    redefinir_senha,
    alterar_propria_senha,
)
from auth.banco import ConcorrenciaConflito, atualizar_email_corporativo_usuario, conectar, backend_banco
from enterprise.backups import criar_backup as criar_backup_local
from enterprise.correio import (
    atualizar_estado,
    contagem_nao_lidas,
    enviar_mensagem,
    listar_caixa,
    listar_contatos,
    obter_mensagem,
    salvar_rascunho,
)
from servidor_corporativo import VERSAO_SERVIDOR
from servidor_corporativo.config import ConfigServidor
from servidor_corporativo.rpc import executar_rpc, executar_alvo_autenticado, RPCError
from servidor_ti.app import processar_heartbeat as processar_heartbeat_ti
from servidor_ti.security import AgentAuthError
from servidor_corporativo.sessoes import (
    alterar_contexto as alterar_contexto_sessao,
    criar as criar_sessao,
    listar_usuario as listar_sessoes_usuario,
    obter as obter_sessao,
    revogar as revogar_sessao,
    revogar_usuario as revogar_sessoes_usuario,
)
from servidor_corporativo.api_v1 import APIError, PUBLIC_ENDPOINTS, dispatch_get as dispatch_api_get, dispatch_post as dispatch_api_post, eh_endpoint_publico, erro_payload as api_erro_payload
from servidor_corporativo.controles_api import IdempotenciaEmProcessamento, RateLimitExcedido, executar_idempotente, verificar_limite

_JSON_MAX = 32 * 1024 * 1024
_NOME_SEGURO = re.compile(r"[^A-Za-z0-9._() -]+")


def _json_bytes(dados: Any) -> bytes:
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _erro_resposta(codigo: str, mensagem: str, request_id: str) -> dict:
    """Envelope único; ``erro`` permanece apenas como alias de compatibilidade."""
    return {
        "ok": False, "error": {"code": str(codigo), "message": str(mensagem)},
        "request_id": str(request_id), "erro": str(mensagem),
    }


class SessaoInvalida(PermissionError):
    """Token bearer ausente, expirado ou revogado (401, não 403)."""


def _contexto_usuario(usuario: dict) -> tuple[int, int | None]:
    uid = int(usuario["id"])
    with conectar() as con:
        if str(usuario.get("perfil")) == "admin":
            row = con.execute(
                "SELECT e.id empresa_id,(SELECT id FROM filiais WHERE empresa_id=e.id AND ativo=1 ORDER BY id LIMIT 1) filial_id "
                "FROM empresas e WHERE e.ativo=1 ORDER BY e.id LIMIT 1"
            ).fetchone()
        else:
            row = con.execute(
                "SELECT ue.empresa_id,ue.filial_id FROM usuarios_empresas ue JOIN empresas e ON e.id=ue.empresa_id "
                "WHERE ue.usuario_id=? AND ue.ativo=1 AND e.ativo=1 ORDER BY ue.empresa_id LIMIT 1", (uid,)
            ).fetchone()
    if row is None:
        raise PermissionError("Usuário sem empresa ativa vinculada.")
    return int(row["empresa_id"]), int(row["filial_id"]) if row["filial_id"] is not None else None


def _bootstrap(sessao) -> dict:
    with conectar() as con:
        empresa = con.execute("SELECT id,nome,cnpj FROM empresas WHERE id=? AND ativo=1", (sessao.empresa_id,)).fetchone()
        filiais = con.execute("SELECT id,empresa_id,nome,codigo,cidade,estado FROM filiais WHERE empresa_id=? AND ativo=1 ORDER BY nome", (sessao.empresa_id,)).fetchall()
        deps = con.execute("SELECT id,empresa_id,nome,codigo FROM departamentos WHERE empresa_id=? AND ativo=1 ORDER BY nome", (sessao.empresa_id,)).fetchall()
        centros = con.execute("SELECT id,empresa_id,departamento_id,nome,codigo FROM centros_custo WHERE empresa_id=? AND ativo=1 ORDER BY nome", (sessao.empresa_id,)).fetchall()
        perms = con.execute("SELECT modulo,pode_ler,pode_escrever,pode_aprovar FROM permissoes_modulos WHERE usuario_id=? AND empresa_id=?", (int(sessao.usuario["id"]), sessao.empresa_id)).fetchall()
    return {
        "usuario": sessao.usuario,
        "empresa": dict(empresa) if empresa else None,
        "filial_id": sessao.filial_id,
        "filiais": [dict(x) for x in filiais],
        "departamentos": [dict(x) for x in deps],
        "centros_custo": [dict(x) for x in centros],
        "permissoes": [dict(x) for x in perms],
    }


class AutorizacaoNegada(PermissionError):
    """Sessão válida sem privilégio suficiente para a operação."""


def _admin(sessao) -> None:
    if str(sessao.usuario.get("perfil", "")).lower() != "admin":
        raise AutorizacaoNegada("Operação exclusiva do administrador.")


def _filtro_empresa_filial(sessao, *, prefixo: str = "") -> tuple[str, tuple]:
    """Retorna filtro SQL coerente para contexto de filial ou visão corporativa."""
    p = f"{prefixo}." if prefixo else ""
    if sessao.filial_id is None:
        return f"{p}empresa_id=?", (sessao.empresa_id,)
    return (
        f"{p}empresa_id=? AND ({p}filial_id=? OR {p}filial_id IS NULL)",
        (sessao.empresa_id, sessao.filial_id),
    )


def _nome_seguro(nome: str) -> str:
    nome = _NOME_SEGURO.sub("_", Path(str(nome or "arquivo")).name).strip(" .")[:180]
    return nome or "arquivo.bin"


class CorporateRequestHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self._inicio_requisicao = time.perf_counter()
        self._request_id = novo_request_id()

    server_version = "DataIntelligenceCorporate/" + VERSAO_SERVIDOR
    sys_version = ""

    @property
    def config(self) -> ConfigServidor:
        return self.server.config  # type: ignore[attr-defined]

    def _origem_cors_permitida(self) -> str | None:
        origem = str(self.headers.get("Origin", "") or "").strip().rstrip("/")
        if not origem:
            return None
        permitidas = tuple(getattr(self.config, "cors_origins", ()) or ())
        normalizada = origem.lower()
        if "*" in permitidas:
            return "*"
        mapa = {str(x).strip().rstrip("/").lower() for x in permitidas}
        return origem if normalizada in mapa else None

    def end_headers(self):
        origem = self._origem_cors_permitida()
        if origem:
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Vary", "Origin")
        super().end_headers()

    def do_OPTIONS(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        origem_recebida = str(self.headers.get("Origin", "") or "").strip()
        origem = self._origem_cors_permitida()
        if not path.startswith("/api/v1/"):
            self._responder_json(HTTPStatus.NOT_FOUND, _erro_resposta("not_found", "Rota não encontrada.", self._request_id))
            return
        if origem_recebida and not origem:
            self._responder_json(
                HTTPStatus.FORBIDDEN,
                api_erro_payload(APIError(HTTPStatus.FORBIDDEN, "cors_forbidden", "Origem Web não autorizada."), self._request_id),
            )
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type, Idempotency-Key, If-Match, X-Confirm-Restore, X-File-Name, X-Module, X-Category, X-RPC-Module, X-RPC-Function, X-RPC-Meta",
        )
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-ID", self._request_id)
        self.end_headers()

    def _responder_json(self, status: int, dados: Any) -> None:
        corpo = _json_bytes(dados)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Request-ID", self._request_id)
        for nome, valor in dict(getattr(self, "_cabecalhos_resposta", {}) or {}).items():
            self.send_header(str(nome), str(valor))
        self._cabecalhos_resposta = {}
        observabilidade = getattr(self.server, "observabilidade", None)
        if observabilidade is not None:
            observabilidade.registrar_requisicao(int(status), (time.perf_counter() - self._inicio_requisicao) * 1000)
        self.end_headers()
        self.wfile.write(corpo)

    def _responder_texto(self, status: int, texto: str, content_type: str) -> None:
        corpo = str(texto).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Request-ID", self._request_id)
        observabilidade = getattr(self.server, "observabilidade", None)
        if observabilidade is not None:
            observabilidade.registrar_requisicao(int(status), (time.perf_counter() - self._inicio_requisicao) * 1000)
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_json(self) -> dict:
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            tamanho = -1
        if tamanho < 0 or tamanho > _JSON_MAX:
            raise ValueError("Payload JSON acima do limite.")
        if tamanho == 0:
            return {}
        try:
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("JSON inválido.") from None
        if not isinstance(dados, dict):
            raise ValueError("O corpo deve ser um objeto JSON.")
        return dados

    @staticmethod
    def _rpc_substituir_marcador(valor, marcador: str, caminho: Path):
        if isinstance(valor, list):
            return [CorporateRequestHandler._rpc_substituir_marcador(v, marcador, caminho) for v in valor]
        if isinstance(valor, tuple):
            return tuple(CorporateRequestHandler._rpc_substituir_marcador(v, marcador, caminho) for v in valor)
        if isinstance(valor, dict):
            if valor.get(marcador) is True:
                return caminho
            return {k: CorporateRequestHandler._rpc_substituir_marcador(v, marcador, caminho) for k, v in valor.items()}
        return valor

    @staticmethod
    def _rpc_meta_header(valor: Any) -> str:
        bruto = _json_bytes(serializar(valor))
        return base64.urlsafe_b64encode(bruto).decode("ascii")

    @staticmethod
    def _rpc_decodificar_meta_header(valor: str) -> dict:
        try:
            bruto = base64.urlsafe_b64decode(str(valor or "").encode("ascii"))
            payload = json.loads(bruto.decode("utf-8"))
            return desserializar(payload)
        except Exception:
            raise ValueError("Metadados RPC de arquivo inválidos.") from None

    def _responder_arquivo_rpc(self, caminho: Path, resultado: Any) -> None:
        arquivo = Path(caminho).resolve()
        if not arquivo.is_file():
            raise FileNotFoundError("O arquivo gerado não está disponível.")
        nome = _nome_seguro(arquivo.name)
        meta = self._rpc_meta_header(resultado)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(arquivo.stat().st_size))
        self.send_header("Content-Disposition", f'attachment; filename="{nome}"')
        self.send_header("X-DI-File-Name", nome)
        self.send_header("X-DI-RPC-Result", meta)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Request-ID", self._request_id)
        observabilidade = getattr(self.server, "observabilidade", None)
        if observabilidade is not None:
            observabilidade.registrar_requisicao(200, (time.perf_counter() - self._inicio_requisicao) * 1000)
        self.end_headers()
        with arquivo.open("rb") as origem:
            for bloco in iter(lambda: origem.read(1024 * 1024), b""):
                self.wfile.write(bloco)

    def _rpc_upload_arquivo(self, sessao) -> Any:
        modulo = str(self.headers.get("X-RPC-Module", "")).strip()
        funcao = str(self.headers.get("X-RPC-Function", "")).strip()
        chave = (modulo, funcao)
        if chave not in RPC_ARQUIVO_ENTRADA:
            raise PermissionError("Operação de upload RPC não autorizada.")
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            tamanho = -1
        limite = int(self.config.max_upload_mb) * 1024 * 1024
        if tamanho <= 0 or tamanho > limite:
            raise ValueError(f"Arquivo vazio ou acima do limite de {self.config.max_upload_mb} MB.")
        meta = self._rpc_decodificar_meta_header(self.headers.get("X-RPC-Meta", ""))
        args = meta.get("args") or []
        kwargs = meta.get("kwargs") or {}
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise ValueError("Argumentos RPC de arquivo inválidos.")
        nome = _nome_seguro(self.headers.get("X-File-Name", "arquivo.bin"))
        with tempfile.TemporaryDirectory(prefix="di_rpc_upload_") as tmp:
            temporario = Path(tmp) / nome
            digest = hashlib.sha256()
            restante = tamanho
            with temporario.open("xb") as destino:
                while restante:
                    bloco = self.rfile.read(min(1024 * 1024, restante))
                    if not bloco:
                        raise ValueError("Upload interrompido antes do tamanho informado.")
                    destino.write(bloco)
                    digest.update(bloco)
                    restante -= len(bloco)
            esperado = str(self.headers.get("X-SHA256", "")).lower().strip()
            if esperado and digest.hexdigest() != esperado:
                raise ValueError("Hash SHA-256 do upload RPC não confere.")
            args = self._rpc_substituir_marcador(args, MARCADOR_ENTRADA, temporario)
            kwargs = self._rpc_substituir_marcador(kwargs, MARCADOR_ENTRADA, temporario)
            return executar_alvo_autenticado(sessao, modulo, funcao, args, kwargs)

    def _gerar_resultado_rpc_arquivo(self, sessao, payload: dict):
        """Executa uma operação de arquivo somente no Servidor Corporativo.

        O retorno mantém o arquivo dentro de um diretório temporário do servidor
        até que o chamador decida entre enviá-lo como cópia transitória ou
        promovê-lo ao armazenamento corporativo persistente.
        """
        modulo = str(payload.get("modulo") or "").strip()
        funcao = str(payload.get("funcao") or "").strip()
        chave = (modulo, funcao)
        if (
            chave not in RPC_ARQUIVO_SAIDA_PARAM
            and chave not in RPC_ARQUIVO_RETORNO
            and chave not in RPC_ARQUIVO_PERSISTE_SERVIDOR
        ):
            raise PermissionError("Operação de arquivo RPC não autorizada.")
        args = desserializar(payload.get("args") or [])
        kwargs = desserializar(payload.get("kwargs") or {})
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise ValueError("Argumentos RPC de arquivo inválidos.")
        temporario = tempfile.TemporaryDirectory(prefix="di_rpc_result_")
        try:
            tmpdir = Path(temporario.name).resolve()
            destino_tmp = None
            if chave in RPC_ARQUIVO_SAIDA_PARAM:
                nome = _nome_seguro(payload.get("nome_destino") or "resultado.bin")
                destino_tmp = tmpdir / nome
                args = self._rpc_substituir_marcador(args, MARCADOR_SAIDA, destino_tmp)
                kwargs = self._rpc_substituir_marcador(kwargs, MARCADOR_SAIDA, destino_tmp)
            resultado = executar_alvo_autenticado(sessao, modulo, funcao, args, kwargs)
            candidato = destino_tmp
            if candidato is None or not candidato.is_file():
                if isinstance(resultado, (str, Path)):
                    candidato = Path(resultado)
                elif isinstance(resultado, dict) and resultado.get("arquivo"):
                    candidato = Path(str(resultado["arquivo"]))
                elif isinstance(resultado, dict) and resultado.get("caminho"):
                    candidato = Path(str(resultado["caminho"]))
            if candidato is None:
                raise FileNotFoundError("A operação não retornou arquivo.")
            candidato = candidato.expanduser().resolve()
            storage = banco.STORAGE_DIR.resolve()
            permitido = candidato == destino_tmp or storage in candidato.parents
            if not permitido:
                raise PermissionError("Arquivo de saída fora do armazenamento autorizado.")
            return temporario, candidato, resultado, modulo, funcao
        except Exception:
            temporario.cleanup()
            raise

    def _persistir_arquivo_existente(self, sessao, origem: Path, *, nome: str, modulo: str, categoria: str) -> dict:
        """Promove um arquivo já gerado no servidor para o repositório corporativo."""
        origem = Path(origem).expanduser().resolve()
        if not origem.is_file():
            raise FileNotFoundError("Arquivo gerado não encontrado no servidor.")
        nome = _nome_seguro(nome or origem.name)
        modulo = str(modulo or "core")[:50]
        categoria = str(categoria or "exportacao")[:60]
        tamanho = origem.stat().st_size
        limite = int(self.config.max_upload_mb) * 1024 * 1024
        if tamanho <= 0 or tamanho > limite:
            raise ValueError(f"Arquivo vazio ou acima do limite de {self.config.max_upload_mb} MB.")
        digest = hashlib.sha256()
        with origem.open("rb") as entrada:
            for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
                digest.update(bloco)
        sha256 = digest.hexdigest()
        raiz = banco.STORAGE_DIR / "corporativo" / str(sessao.empresa_id)
        raiz.mkdir(parents=True, exist_ok=True)
        destino = raiz / f"{uuid4().hex}_{nome}"
        temporario = destino.with_name(destino.name + ".part")
        movido = False
        try:
            with origem.open("rb") as entrada, temporario.open("xb") as saida:
                for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
                    saida.write(bloco)
            relativo = destino.relative_to(banco.STORAGE_DIR).as_posix()
            with conectar() as con:
                cursor = con.execute(
                    "INSERT INTO arquivos_corporativos (empresa_id,filial_id,modulo,categoria,nome,caminho_relativo,tamanho_bytes,sha256,origem,criado_por) VALUES (?,?,?,?,?,?,?,?, 'gerado_servidor', ?)",
                    (sessao.empresa_id, sessao.filial_id, modulo, categoria, nome, relativo, tamanho, sha256, int(sessao.usuario["id"])),
                )
                os.replace(temporario, destino)
                movido = True
            return {
                "id": int(cursor.lastrowid), "nome": nome, "tamanho_bytes": tamanho,
                "sha256": sha256, "categoria": categoria, "modulo": modulo,
                "armazenamento": "servidor_corporativo",
            }
        except Exception:
            temporario.unlink(missing_ok=True)
            if movido:
                destino.unlink(missing_ok=True)
            raise

    def _rpc_gerar_arquivo(self, sessao, payload: dict) -> None:
        temporario, candidato, resultado, _modulo, _funcao = self._gerar_resultado_rpc_arquivo(sessao, payload)
        try:
            self._responder_arquivo_rpc(candidato, resultado)
        finally:
            temporario.cleanup()

    def _rpc_armazenar_arquivo(self, sessao, payload: dict) -> dict:
        """Gera e persiste o resultado diretamente no servidor, sem download."""
        temporario, candidato, resultado_operacao, modulo, funcao = self._gerar_resultado_rpc_arquivo(sessao, payload)
        try:
            nome = _nome_seguro(payload.get("nome_destino") or candidato.name)
            categoria = str(payload.get("categoria") or f"relatorio_{funcao}")[:60]
            metadados = self._persistir_arquivo_existente(
                sessao, candidato, nome=nome, modulo=modulo, categoria=categoria
            )
            if isinstance(resultado_operacao, dict):
                for chave, valor in resultado_operacao.items():
                    if chave in {"arquivo", "caminho"} or chave in metadados:
                        continue
                    if valor is None or isinstance(valor, (str, int, float, bool)):
                        metadados[chave] = valor
            return metadados
        finally:
            temporario.cleanup()

    def _sessao(self):
        cab = str(self.headers.get("Authorization", ""))
        token = cab[7:].strip() if cab.lower().startswith("bearer ") else ""
        sessao = obter_sessao(token)
        if sessao is None:
            raise SessaoInvalida("Sessão ausente, expirada ou revogada.")
        return sessao

    def _arquivo_upload(self, sessao, *, backup: bool = False) -> dict:
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            tamanho = -1
        limite = int(self.config.max_upload_mb) * 1024 * 1024
        if tamanho <= 0 or tamanho > limite:
            raise ValueError(f"Arquivo vazio ou acima do limite de {self.config.max_upload_mb} MB.")
        nome = _nome_seguro(self.headers.get("X-File-Name", "arquivo.bin"))
        modulo = str(self.headers.get("X-Module", "core"))[:50]
        categoria = "backup" if backup else str(self.headers.get("X-Category", "arquivo"))[:60]
        raiz = banco.STORAGE_DIR / ("servidor_backups" if backup else "corporativo") / str(sessao.empresa_id)
        raiz.mkdir(parents=True, exist_ok=True)
        destino = raiz / f"{uuid4().hex}_{nome}"
        temporario = destino.with_name(destino.name + ".part")
        digest = hashlib.sha256()
        restante = tamanho
        movido = False
        try:
            with temporario.open("xb") as out:
                while restante:
                    bloco = self.rfile.read(min(1024 * 1024, restante))
                    if not bloco:
                        raise ValueError("Upload interrompido antes do tamanho informado.")
                    out.write(bloco)
                    digest.update(bloco)
                    restante -= len(bloco)
            esperado = str(self.headers.get("X-SHA256", "")).lower().strip()
            atual = digest.hexdigest()
            if esperado and esperado != atual:
                raise ValueError("Hash SHA-256 do upload não confere.")
            relativo = destino.relative_to(banco.STORAGE_DIR).as_posix()
            with conectar() as con:
                if backup:
                    cursor = con.execute(
                        "INSERT INTO backups_empresariais (empresa_id,filial_id,tipo,arquivo_relativo,tamanho_bytes,sha256,criado_por) VALUES (?,?, 'Completo', ?,?,?,?)",
                        (sessao.empresa_id, sessao.filial_id, relativo, tamanho, atual, int(sessao.usuario["id"])),
                    )
                else:
                    cursor = con.execute(
                        "INSERT INTO arquivos_corporativos (empresa_id,filial_id,modulo,categoria,nome,caminho_relativo,tamanho_bytes,sha256,origem,criado_por) VALUES (?,?,?,?,?,?,?,?, 'sincronizado', ?)",
                        (sessao.empresa_id, sessao.filial_id, modulo, categoria, nome, relativo, tamanho, atual, int(sessao.usuario["id"])),
                    )
                # O rename ocorre antes do commit; se commit/rename falhar, o
                # bloco externo remove o arquivo e o context manager faz rollback.
                os.replace(temporario, destino)
                movido = True
            return {"id": int(cursor.lastrowid), "nome": nome, "tamanho_bytes": tamanho, "sha256": atual, "categoria": categoria}
        except Exception:
            temporario.unlink(missing_ok=True)
            if movido:
                destino.unlink(missing_ok=True)
            raise

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)
            if path in {"/", "/health", "/api/v1/health", "/api/v1/health/live"}:
                self._responder_json(HTTPStatus.OK, {
                    "ok": True,
                    "servico": "data-intelligence-corporate-server",
                    "versao": VERSAO_SERVIDOR,
                    "autoridade_transacional": True,
                    "rpc_dominio": "1.0",
                    "api_publica": "v1",
                    "api_endpoints": len(PUBLIC_ENDPOINTS),
                    "agentes_ti": True,
                    "backend_banco": backend_banco(),
                })
                return
            if path == "/api/v1/openapi.json":
                from servidor_corporativo.openapi import documento_openapi
                self._responder_json(HTTPStatus.OK, documento_openapi()); return
            if path == "/api/v1/health/ready":
                try:
                    with conectar() as con:
                        con.execute("SELECT 1").fetchone()
                    banco_pronto = True
                except Exception:
                    banco_pronto = False
                status = HTTPStatus.OK if banco_pronto else HTTPStatus.SERVICE_UNAVAILABLE
                self._responder_json(status, {
                    "ok": banco_pronto,
                    "pronto": banco_pronto,
                    "banco": banco_pronto,
                    "backend_banco": backend_banco(),
                    "versao": VERSAO_SERVIDOR,
                    "api": "v1",
                    "servico": "data-intelligence-corporate-server",
                })
                return
            sessao = self._sessao()
            api = dispatch_api_get(path, qs, sessao, self._request_id)
            if api is not None:
                status_api, payload_api = api
                self._responder_json(status_api, payload_api); return
            if path == "/api/v1/health/details":
                _admin(sessao)
                with conectar() as con:
                    agentes = con.execute("SELECT COUNT(*) n FROM ti_agentes WHERE ativo=1 AND status='Online'").fetchone()
                    jobs = con.execute("SELECT COUNT(*) n FROM jobs WHERE status IN ('Pendente','Executando','Cancelamento solicitado')").fetchone()
                banco_detalhes={"backend":backend_banco()}
                if backend_banco()=="postgresql":
                    try:
                        from enterprise.postgresql.bootstrap import health_postgresql
                        banco_detalhes=health_postgresql()
                    except Exception as exc:
                        banco_detalhes={"backend":"postgresql","ok":False,"erro":str(exc)}
                try:
                    from enterprise.backups import validar_dependencias_backup
                    backup_detalhes = validar_dependencias_backup()
                except RuntimeError as exc:
                    backup_detalhes = {"backend": backend_banco(), "ok": False, "erro": str(exc)}
                self._responder_json(HTTPStatus.OK, {
                    "ok": True,
                    "observabilidade": self.server.observabilidade.snapshot(),
                    "banco": banco_detalhes,
                    "backup": backup_detalhes,
                    "agentes_online": int(agentes["n"] if agentes else 0),
                    "jobs_ativos": int(jobs["n"] if jobs else 0),
                })
                return
            if path == "/api/v1/metrics":
                _admin(sessao)
                with conectar() as con:
                    fila = con.execute(
                        """SELECT
                           SUM(CASE WHEN status='Pendente' THEN 1 ELSE 0 END) pendentes,
                           SUM(CASE WHEN status='Executando' THEN 1 ELSE 0 END) executando,
                           SUM(CASE WHEN status='Dead-letter' THEN 1 ELSE 0 END) dead_letter
                           FROM automacao_fila"""
                    ).fetchone()
                    sessoes_ativas = con.execute(
                        "SELECT COUNT(*) n FROM sessoes_servidor WHERE revogado_em IS NULL AND expira_em>CURRENT_TIMESTAMP"
                    ).fetchone()
                self._responder_texto(
                    HTTPStatus.OK,
                    self.server.observabilidade.prometheus({
                        "automation_pending": int((fila["pendentes"] if fila else 0) or 0),
                        "automation_running": int((fila["executando"] if fila else 0) or 0),
                        "automation_dead_letter": int((fila["dead_letter"] if fila else 0) or 0),
                        "sessions_active": int((sessoes_ativas["n"] if sessoes_ativas else 0) or 0),
                    }),
                    "text/plain; version=0.0.4; charset=utf-8",
                )
                return
            if path == "/api/v1/privacy/read-audit":
                from enterprise.privacidade import listar_leituras_sensiveis
                self._responder_json(
                    HTTPStatus.OK,
                    {"ok": True, "data": listar_leituras_sensiveis(
                        sessao.ator(), limite=int((qs.get("limit") or [200])[0]),
                    )},
                ); return
            if path == "/api/v1/webhooks":
                from enterprise.webhooks import listar_endpoints
                self._responder_json(HTTPStatus.OK, {"ok": True, "data": listar_endpoints(sessao.ator())}); return
            if path == "/api/v1/bootstrap":
                self._responder_json(HTTPStatus.OK, _bootstrap(sessao)); return
            if path == "/api/v1/account/sessions":
                self._responder_json(
                    HTTPStatus.OK,
                    {"ok": True, "sessoes": listar_sessoes_usuario(int(sessao.usuario["id"]))},
                ); return
            if path == "/api/v1/automations/jobs":
                from enterprise.automacao_motor import listar as listar_automacoes
                self._responder_json(
                    HTTPStatus.OK,
                    {"ok": True, "data": listar_automacoes(
                        sessao.ator(), status=(qs.get("status") or [None])[0],
                        limite=int((qs.get("limit") or [100])[0]),
                    )},
                ); return
            if path == "/api/v1/rpc/capabilities":
                from core.rpc_central import RPC_ALLOWLIST
                self._responder_json(HTTPStatus.OK,{
                    "rpc_dominio":"1.0",
                    "modulos":{k:sorted(v) for k,v in RPC_ALLOWLIST.items()},
                }); return
            if path == "/api/v1/users":
                _admin(sessao)
                with conectar() as con:
                    linhas = con.execute(
                        "SELECT DISTINCT u.id,u.nome,u.usuario,u.email_corporativo,u.perfil,u.perfil_acesso,u.ativo,u.sessao_epoch,u.ultimo_login "
                        "FROM usuarios u JOIN usuarios_empresas ue ON ue.usuario_id=u.id WHERE ue.empresa_id=? ORDER BY u.nome COLLATE NOCASE",
                        (sessao.empresa_id,),
                    ).fetchall()
                self._responder_json(HTTPStatus.OK, {"usuarios": [dict(x) for x in linhas]}); return
            if path == "/api/v1/mail/contacts":
                self._responder_json(HTTPStatus.OK, {"contatos": listar_contatos(sessao.ator(), (qs.get("q") or [""])[0])}); return
            if path == "/api/v1/mail/unread":
                self._responder_json(HTTPStatus.OK, {"nao_lidas": contagem_nao_lidas(sessao.ator())}); return
            if path == "/api/v1/mail":
                caixa=(qs.get("box") or ["entrada"])[0]; pesquisa=(qs.get("q") or [""])[0]
                self._responder_json(HTTPStatus.OK, {"mensagens": listar_caixa(sessao.ator(), caixa, pesquisa=pesquisa)}); return
            if path.startswith("/api/v1/mail/"):
                mid=int(path.rsplit("/",1)[1]); self._responder_json(HTTPStatus.OK, obter_mensagem(mid, sessao.ator())); return
            if path in {"/api/v1/files", "/api/v1/backups"}:
                _admin(sessao)
                backup = path.endswith("backups")
                filtro, parametros = _filtro_empresa_filial(sessao)
                with conectar() as con:
                    if backup:
                        rows=con.execute(
                            "SELECT id,tipo,arquivo_relativo,tamanho_bytes,sha256,criado_em,restaurado_em "
                            f"FROM backups_empresariais WHERE {filtro} ORDER BY id DESC LIMIT 500",
                            parametros,
                        ).fetchall()
                    else:
                        rows=con.execute(
                            "SELECT id,modulo,categoria,nome,tamanho_bytes,sha256,origem,criado_em "
                            f"FROM arquivos_corporativos WHERE {filtro} AND excluido_em IS NULL "
                            "ORDER BY id DESC LIMIT 1000",
                            parametros,
                        ).fetchall()
                self._responder_json(HTTPStatus.OK, {"itens": [dict(x) for x in rows]}); return
            m=re.fullmatch(r"/api/v1/(files|backups)/(\d+)/download", path)
            if m:
                _admin(sessao)
                backup=m.group(1)=="backups"; iid=int(m.group(2))
                filtro, parametros = _filtro_empresa_filial(sessao)
                with conectar() as con:
                    sql = (
                        "SELECT arquivo_relativo AS caminho, NULL AS nome FROM backups_empresariais "
                        f"WHERE id=? AND {filtro}"
                        if backup
                        else "SELECT caminho_relativo AS caminho, nome FROM arquivos_corporativos "
                        f"WHERE id=? AND {filtro} AND excluido_em IS NULL"
                    )
                    row=con.execute(sql,(iid,*parametros)).fetchone()
                if row is None: raise FileNotFoundError("Arquivo não encontrado.")
                arq=(banco.STORAGE_DIR/str(row["caminho"])).resolve()
                if banco.STORAGE_DIR.resolve() not in arq.parents or not arq.is_file(): raise FileNotFoundError("Arquivo físico não encontrado.")
                nome=row["nome"] or arq.name
                self.send_response(HTTPStatus.OK); self.send_header("Content-Type","application/octet-stream"); self.send_header("Content-Length",str(arq.stat().st_size)); self.send_header("Content-Disposition",f'attachment; filename="{_nome_seguro(nome)}"'); self.end_headers()
                with arq.open("rb") as f:
                    for bloco in iter(lambda:f.read(1024*1024),b""): self.wfile.write(bloco)
                return
            self._responder_json(HTTPStatus.NOT_FOUND, _erro_resposta("not_found", "Rota não encontrada.", self._request_id))
        except APIError as e: self._responder_json(e.status, api_erro_payload(e, self._request_id))
        except AutorizacaoNegada as e:
            self._responder_json(HTTPStatus.FORBIDDEN, _erro_resposta("forbidden", str(e), self._request_id))
        except SessaoInvalida as e:
            self._responder_json(HTTPStatus.UNAUTHORIZED, _erro_resposta("unauthorized", str(e), self._request_id))
        except PermissionError as e:
            self._responder_json(HTTPStatus.FORBIDDEN, _erro_resposta("forbidden", str(e), self._request_id))
        except (ValueError, FileNotFoundError) as e:
            self._responder_json(HTTPStatus.BAD_REQUEST, _erro_resposta("invalid_request", str(e), self._request_id))
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha GET", extra={"request_id": self._request_id, "metodo": "GET", "caminho": self.path})
            payload = _erro_resposta("internal_error", "Falha interna do servidor.", self._request_id)
            self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR, payload)

    def do_POST(self):
        try:
            path=urlparse(self.path).path.rstrip("/")
            if path == "/api/v1/auth/login":
                verificar_limite(
                    f"login:{self.client_address[0]}", limite=10, janela_segundos=300,
                )
                from servidor_corporativo.dto import validar_login
                dados=validar_login(self._ler_json()); usuario=autenticar_usuario(dados["usuario"], dados["senha"], dados["codigo_mfa"]); empresa_id,filial_id=_contexto_usuario(usuario); sessao=criar_sessao(
                    usuario, empresa_id, filial_id,
                    ip_hash=hashlib.sha256(self.client_address[0].encode("utf-8")).hexdigest(),
                    cliente=self.headers.get("User-Agent", ""),
                )
                self._responder_json(HTTPStatus.OK, {"token":sessao.token,"expira_em":sessao.expira_em.isoformat(),**_bootstrap(sessao)}); return
            if path == "/api/v1/ti/agentes/heartbeat":
                tipo=str(self.headers.get("Content-Type","")).lower()
                if "application/json" not in tipo:
                    self._responder_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE,_erro_resposta("unsupported_media_type", "Use application/json.", self._request_id)); return
                try: tamanho=int(self.headers.get("Content-Length","0"))
                except ValueError: tamanho=-1
                if tamanho <= 0 or tamanho > 128*1024:
                    self._responder_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE,_erro_resposta("payload_too_large", "Payload vazio ou acima do limite.", self._request_id)); return
                corpo=self.rfile.read(tamanho)
                try:
                    resultado=processar_heartbeat_ti(self.headers,corpo,self.client_address[0])
                except AgentAuthError:
                    self._responder_json(HTTPStatus.UNAUTHORIZED,_erro_resposta("unauthorized", "Agente não autorizado.", self._request_id)); return
                self._responder_json(HTTPStatus.ACCEPTED,resultado); return
            sessao=self._sessao()
            verificar_limite(
                f"api-write:{sessao.usuario['id']}:{path}", limite=300, janela_segundos=60,
            )
            if path == "/api/v1/auth/logout":
                revogar_sessao(sessao.token)
                self._responder_json(HTTPStatus.OK, {"ok": True}); return
            if path == "/api/v1/account/sessions/revoke-all":
                quantidade = revogar_sessoes_usuario(int(sessao.usuario["id"]))
                self._responder_json(
                    HTTPStatus.OK, {"ok": True, "sessoes_revogadas": quantidade, "relogin_necessario": True},
                ); return
            if path == "/api/v1/account/mfa/setup":
                from auth.mfa import preparar_mfa
                self._responder_json(
                    HTTPStatus.CREATED, preparar_mfa(int(sessao.usuario["id"]), sessao.ator()),
                ); return
            if path == "/api/v1/account/mfa/confirm":
                from auth.mfa import confirmar_mfa
                d = self._ler_json()
                self._responder_json(
                    HTTPStatus.OK,
                    confirmar_mfa(int(sessao.usuario["id"]), str(d.get("codigo") or ""), sessao.ator()),
                ); return
            if path == "/api/v1/account/mfa/recovery/regenerate":
                from auth.mfa import regenerar_codigos_recuperacao
                d = self._ler_json()
                self._responder_json(
                    HTTPStatus.OK,
                    {"codigos_recuperacao": regenerar_codigos_recuperacao(
                        int(sessao.usuario["id"]), str(d.get("codigo") or ""), sessao.ator(),
                    )},
                ); return
            if path == "/api/v1/account/mfa/disable":
                from auth.mfa import desabilitar_mfa
                d = self._ler_json()
                desabilitar_mfa(int(sessao.usuario["id"]), sessao.ator(), str(d.get("codigo") or ""))
                self._responder_json(HTTPStatus.OK, {"ok": True, "relogin_necessario": True}); return
            if path == "/api/v1/webhooks":
                _admin(sessao)
                from enterprise.webhooks import cadastrar_endpoint
                d = self._ler_json()
                eventos = d.get("eventos")
                if not isinstance(eventos, list):
                    raise ValueError("eventos deve ser uma lista de tipos.")
                self._responder_json(
                    HTTPStatus.CREATED,
                    {"ok": True, "data": cadastrar_endpoint(
                        str(d.get("nome") or ""), str(d.get("url") or ""), eventos, sessao.ator(),
                    )},
                ); return
            if path == "/api/v1/webhooks/events":
                _admin(sessao)
                from enterprise.webhooks import publicar_evento
                d = self._ler_json()
                if not isinstance(d.get("dados", {}), dict):
                    raise ValueError("dados deve ser um objeto.")
                self._responder_json(
                    HTTPStatus.ACCEPTED,
                    {"ok": True, "data": publicar_evento(
                        str(d.get("tipo") or ""), d.get("dados") or {}, sessao.ator(),
                        evento_id=str(d.get("evento_id") or "") or None,
                    )},
                ); return
            if path == "/api/v1/privacy/retention/policies":
                _admin(sessao)
                from enterprise.privacidade import definir_politica_retencao
                d = self._ler_json()
                iid = definir_politica_retencao(
                    str(d.get("modulo") or ""), str(d.get("entidade") or ""),
                    int(d.get("dias_retencao") or 0), sessao.ator(), acao=str(d.get("acao") or "Anonimizar"),
                )
                self._responder_json(HTTPStatus.CREATED, {"ok": True, "data": {"id": iid}}); return
            if path == "/api/v1/privacy/retention/run-rh":
                _admin(sessao)
                from enterprise.privacidade import executar_retencao_rh
                d = self._ler_json()
                self._responder_json(
                    HTTPStatus.OK,
                    {"ok": True, "data": executar_retencao_rh(sessao.ator(), simular=bool(d.get("simular", True)))},
                ); return
            m_automacao = re.fullmatch(r"/api/v1/automations/jobs/(\d+)/(approve|cancel|reprocess)", path)
            if m_automacao:
                from enterprise.automacao_motor import aprovar, reprocessar_dead_letter, solicitar_cancelamento
                job_id = int(m_automacao.group(1)); acao = m_automacao.group(2)
                if acao == "approve":
                    aprovar(job_id, sessao.ator())
                elif acao == "cancel":
                    solicitar_cancelamento(job_id, sessao.ator())
                else:
                    reprocessar_dead_letter(job_id, sessao.ator())
                self._responder_json(HTTPStatus.OK, {"ok": True, "id": job_id, "acao": acao}); return
            m_restore = re.fullmatch(r"/api/v1/backups/(\d+)/restore", path)
            if m_restore:
                _admin(sessao); backup_id = int(m_restore.group(1))
                if str(self.headers.get("X-Confirm-Restore", "")) != f"RESTORE-{backup_id}":
                    raise ValueError("Confirme a operação com X-Confirm-Restore: RESTORE-<id>.")
                with conectar() as con:
                    row = con.execute(
                        "SELECT arquivo_relativo FROM backups_empresariais WHERE id=? AND empresa_id=?",
                        (backup_id, sessao.empresa_id),
                    ).fetchone()
                if row is None:
                    raise ValueError("Backup não encontrado no escopo atual.")
                caminho = Path(str(row["arquivo_relativo"]))
                if not caminho.is_absolute():
                    caminho = banco.STORAGE_DIR / caminho
                caminho = caminho.resolve()
                if banco.STORAGE_DIR.resolve() not in caminho.parents or not caminho.is_file():
                    raise FileNotFoundError("Arquivo de backup indisponível.")
                from enterprise.automacao_motor import enfileirar
                job = enfileirar(
                    "backup.restaurar", f"Restaurar backup #{backup_id}", {"arquivo": str(caminho)},
                    sessao.ator(), idempotency_key=f"restore:{backup_id}:{caminho.stat().st_mtime_ns}",
                    max_tentativas=1, requer_aprovacao=True, prioridade=1,
                )
                self._responder_json(
                    HTTPStatus.ACCEPTED,
                    {"ok": True, "data": job, "aprovacao_adicional_necessaria": True},
                ); return
            if eh_endpoint_publico(path):
                d = self._ler_json()
                api_idempotente = executar_idempotente(
                    usuario_id=int(sessao.usuario["id"]), metodo="POST", caminho=path,
                    chave=self.headers.get("Idempotency-Key", ""), dados=d,
                    executar=lambda: dispatch_api_post(path, d, sessao, self._request_id),
                )
                api = None if api_idempotente is None else api_idempotente[:2]
                if api is not None:
                    status_api, payload_api = api
                    if api_idempotente and api_idempotente[2]:
                        self._cabecalhos_resposta = {"X-Idempotent-Replay": "true"}
                    self._responder_json(status_api, payload_api); return
            if path == "/api/v1/rpc/file-upload":
                resultado = self._rpc_upload_arquivo(sessao)
                self._responder_json(HTTPStatus.OK, {"resultado": serializar(resultado)}); return
            if path == "/api/v1/rpc/file-result":
                d = self._ler_json()
                self._rpc_gerar_arquivo(sessao, d); return
            if path == "/api/v1/rpc/file-store":
                d = self._ler_json()
                resultado = self._rpc_armazenar_arquivo(sessao, d)
                self._responder_json(HTTPStatus.CREATED, {"resultado": resultado}); return
            if path == "/api/v1/rpc":
                d=self._ler_json()
                resultado=executar_rpc(sessao,d)
                self._responder_json(HTTPStatus.OK,{"resultado":resultado}); return
            if path == "/api/v1/users":
                _admin(sessao); d=self._ler_json()
                criado=_criar_usuario(d.get("nome"),d.get("usuario"),d.get("senha"),d.get("perfil","usuario"),d.get("perfil_acesso","analista"),empresa_id=sessao.empresa_id,filial_id=d.get("filial_id",sessao.filial_id),email_corporativo=d.get("email_corporativo"))
                self._responder_json(HTTPStatus.CREATED, criado); return
            if path == "/api/v1/mail":
                d=self._ler_json(); anexos=[]
                with tempfile.TemporaryDirectory(prefix="mail_upload_") as tmp:
                    usados: set[str] = set()
                    for indice, item in enumerate(d.get("anexos",[]) or [], start=1):
                        raw=base64.b64decode(str(item.get("data_base64", "")), validate=True)
                        if len(raw) > 25 * 1024 * 1024:
                            raise ValueError("Cada anexo de mensagem pode ter no máximo 25 MB.")
                        nome=_nome_seguro(item.get("nome","anexo.bin"))
                        if nome.casefold() in usados:
                            base_nome=Path(nome).stem or "anexo"; sufixo=Path(nome).suffix
                            nome=f"{base_nome}_{indice}{sufixo}"
                        usados.add(nome.casefold())
                        alvo=Path(tmp)/nome; alvo.write_bytes(raw); anexos.append(alvo)
                    mid=enviar_mensagem(d.get("assunto"),d.get("corpo"),d.get("para"),sessao.ator(),cc=d.get("cc"),cco=d.get("cco"),modulo_origem=d.get("modulo_origem"),anexos=anexos,resposta_de_id=d.get("resposta_de_id"))
                self._responder_json(HTTPStatus.CREATED,{"id":mid}); return
            if path == "/api/v1/mail/draft":
                d=self._ler_json(); mid=salvar_rascunho(d.get("assunto"),d.get("corpo"),sessao.ator(),modulo_origem=d.get("modulo_origem")); self._responder_json(HTTPStatus.CREATED,{"id":mid}); return
            if path == "/api/v1/exports":
                # Exportações produzidas pela própria UI podem ser persistidas por
                # qualquer sessão autenticada, sempre no escopo empresa/filial do
                # token. A estação não grava primeiro em disco local.
                self._responder_json(HTTPStatus.CREATED,self._arquivo_upload(sessao,backup=False)); return
            if path == "/api/v1/files":
                _admin(sessao)
                self._responder_json(HTTPStatus.CREATED,self._arquivo_upload(sessao,backup=False)); return
            if path == "/api/v1/backups":
                _admin(sessao); self._responder_json(HTTPStatus.CREATED,self._arquivo_upload(sessao,backup=True)); return
            if path == "/api/v1/backups/create":
                _admin(sessao)
                try:
                    resultado=criar_backup_local(sessao.ator(), sincronizar_servidor=False)
                except RuntimeError as exc:
                    self._responder_json(HTTPStatus.BAD_REQUEST, _erro_resposta("backup_unavailable", str(exc), self._request_id)); return
                seguro={k:v for k,v in resultado.items() if k not in {"arquivo"}}
                self._responder_json(HTTPStatus.CREATED,seguro); return
            self._responder_json(HTTPStatus.NOT_FOUND,_erro_resposta("not_found", "Rota não encontrada.", self._request_id))
        except RateLimitExcedido as e:
            self._cabecalhos_resposta = {"Retry-After": str(e.retry_after)}
            self._responder_json(HTTPStatus.TOO_MANY_REQUESTS, {"ok":False,"error":{"code":"rate_limited","message":str(e)},"request_id":self._request_id,"erro":str(e)})
        except IdempotenciaEmProcessamento as e:
            self._responder_json(HTTPStatus.CONFLICT, _erro_resposta("idempotency_in_progress", str(e), self._request_id))
        except APIError as e: self._responder_json(e.status, api_erro_payload(e, self._request_id))
        except AutorizacaoNegada as e:
            self._responder_json(HTTPStatus.FORBIDDEN,_erro_resposta("forbidden", str(e), self._request_id))
        except SessaoInvalida as e:
            self._responder_json(HTTPStatus.UNAUTHORIZED,_erro_resposta("unauthorized", str(e), self._request_id))
        except PermissionError as e:
            self._responder_json(HTTPStatus.FORBIDDEN,_erro_resposta("forbidden", str(e), self._request_id))
        except (ValueError,TypeError,base64.binascii.Error) as e:
            self._responder_json(HTTPStatus.BAD_REQUEST,_erro_resposta("invalid_request", str(e), self._request_id))
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha POST", extra={"request_id": self._request_id, "metodo": "POST", "caminho": self.path})
            payload = _erro_resposta("internal_error", "Falha interna do servidor.", self._request_id)
            self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR,payload)

    def do_PATCH(self):
        try:
            path=urlparse(self.path).path.rstrip("/"); sessao=self._sessao(); d=self._ler_json()
            if path == "/api/v1/context":
                alterar_contexto_sessao(
                    sessao,
                    int(d.get("empresa_id") or sessao.empresa_id),
                    (int(d["filial_id"]) if d.get("filial_id") not in (None, "") else None),
                )
                self._responder_json(HTTPStatus.OK,_bootstrap(sessao)); return
            if path == "/api/v1/account/password":
                alterar_propria_senha(
                    sessao.ator(),
                    str(d.get("senha_atual") or ""),
                    str(d.get("nova_senha") or ""),
                )
                self._responder_json(HTTPStatus.OK,{"ok":True,"relogin_necessario":True}); return
            m=re.fullmatch(r"/api/v1/users/(\d+)",path)
            if m:
                _admin(sessao); uid=int(m.group(1)); ator=sessao.ator()
                alteracoes = [k for k in ("ativo", "perfil_acesso", "nova_senha", "email_corporativo") if k in d]
                desconhecidos = sorted(set(d) - set(alteracoes))
                if desconhecidos or len(alteracoes) != 1:
                    raise ValueError("Envie exatamente uma alteração de usuário por requisição.")
                bruto_match = str(self.headers.get("If-Match", "")).strip()
                match = re.fullmatch(r'(?:W/)?"?(\d+)"?', bruto_match)
                if not match:
                    self._responder_json(
                        HTTPStatus.PRECONDITION_REQUIRED,
                        {"ok": False, "error": {"code": "if_match_required", "message": "Informe If-Match com sessao_epoch atual."}, "request_id": self._request_id},
                    ); return
                versao = int(match.group(1)); campo = alteracoes[0]
                if campo == "ativo":
                    definir_status_usuario(uid, bool(d[campo]), ator=ator, expected_epoch=versao)
                elif campo == "perfil_acesso":
                    definir_perfil_acesso_usuario(uid, d[campo], ator=ator, expected_epoch=versao)
                elif campo == "nova_senha":
                    redefinir_senha(uid, d[campo], ator=ator, expected_epoch=versao)
                else:
                    atualizar_email_corporativo_usuario(
                        uid, str(d[campo]).strip().lower(), expected_epoch=versao,
                    )
                with conectar() as con:
                    atual = con.execute("SELECT sessao_epoch FROM usuarios WHERE id=?", (uid,)).fetchone()
                nova_versao = int(atual["sessao_epoch"])
                self._cabecalhos_resposta = {"ETag": f'"{nova_versao}"'}
                self._responder_json(HTTPStatus.OK,{"ok":True,"version":nova_versao}); return
            m=re.fullmatch(r"/api/v1/mail/(\d+)",path)
            if m:
                atualizar_estado(int(m.group(1)),sessao.ator(),arquivada=d.get("arquivada"),excluida=d.get("excluida"),estrela=d.get("estrela")); self._responder_json(HTTPStatus.OK,{"ok":True}); return
            m=re.fullmatch(r"/api/v1/operations/records/(\d+)",path)
            if m:
                bruto_match = str(self.headers.get("If-Match", "")).strip()
                match = re.fullmatch(r'(?:W/)?"?(\d+)"?', bruto_match)
                if not match:
                    self._responder_json(
                        HTTPStatus.PRECONDITION_REQUIRED,
                        {"ok":False,"error":{"code":"if_match_required","message":"Informe If-Match com a versão atual do registro."},"request_id":self._request_id},
                    ); return
                from services.operacoes_v11 import alterar_estado_registro, atualizar_registro
                versao = int(match.group(1)); registro_id = int(m.group(1))
                if "estado" in d:
                    desconhecidos = set(d) - {"estado"}
                    if desconhecidos:
                        raise ValueError("Altere o estado separadamente dos demais dados.")
                    nova = alterar_estado_registro(registro_id, str(d["estado"]), sessao.ator(), expected_version=versao)
                else:
                    nova = atualizar_registro(registro_id, d, sessao.ator(), expected_version=versao)
                self._cabecalhos_resposta = {"ETag": f'"{nova}"'}
                self._responder_json(HTTPStatus.OK,{"ok":True,"version":nova}); return
            self._responder_json(HTTPStatus.NOT_FOUND,_erro_resposta("not_found", "Rota não encontrada.", self._request_id))
        except ConcorrenciaConflito as e:
            self._responder_json(HTTPStatus.CONFLICT,{"ok":False,"error":{"code":"version_conflict","message":str(e)},"request_id":self._request_id})
        except AutorizacaoNegada as e: self._responder_json(HTTPStatus.FORBIDDEN,_erro_resposta("forbidden", str(e), self._request_id))
        except SessaoInvalida as e: self._responder_json(HTTPStatus.UNAUTHORIZED,_erro_resposta("unauthorized", str(e), self._request_id))
        except PermissionError as e: self._responder_json(HTTPStatus.FORBIDDEN,_erro_resposta("forbidden", str(e), self._request_id))
        except ValueError as e:
            conflito = "alterado por outro usuário" in str(e).lower()
            self._responder_json(HTTPStatus.CONFLICT if conflito else HTTPStatus.BAD_REQUEST,_erro_resposta("version_conflict" if conflito else "invalid_request", str(e), self._request_id))
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha PATCH", extra={"request_id": self._request_id, "metodo": "PATCH", "caminho": self.path}); self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR,_erro_resposta("internal_error", "Falha interna do servidor.", self._request_id))

    def do_DELETE(self):
        try:
            path=urlparse(self.path).path.rstrip("/"); sessao=self._sessao()
            operacao=re.fullmatch(r"/api/v1/operations/records/(\d+)",path)
            if operacao:
                bruto_match = str(self.headers.get("If-Match", "")).strip()
                match = re.fullmatch(r'(?:W/)?"?(\d+)"?', bruto_match)
                if not match:
                    self._responder_json(
                        HTTPStatus.PRECONDITION_REQUIRED,
                        {"ok":False,"error":{"code":"if_match_required","message":"Informe If-Match com a versão atual do registro."},"request_id":self._request_id},
                    ); return
                from services.operacoes_v11 import alterar_estado_registro
                nova = alterar_estado_registro(
                    int(operacao.group(1)), "Lixeira", sessao.ator(), expected_version=int(match.group(1)),
                )
                self._cabecalhos_resposta = {"ETag": f'"{nova}"'}
                self._responder_json(HTTPStatus.OK,{"ok":True,"version":nova,"estado":"Lixeira"}); return
            _admin(sessao)
            m=re.fullmatch(r"/api/v1/(files|backups)/(\d+)",path)
            if not m: self._responder_json(HTTPStatus.NOT_FOUND,_erro_resposta("not_found", "Rota não encontrada.", self._request_id)); return
            backup=m.group(1)=="backups"; iid=int(m.group(2))
            filtro, parametros = _filtro_empresa_filial(sessao)
            with conectar() as con:
                if backup:
                    row=con.execute(
                        f"SELECT arquivo_relativo caminho FROM backups_empresariais WHERE id=? AND {filtro}",
                        (iid,*parametros),
                    ).fetchone()
                    if row: con.execute(
                        f"DELETE FROM backups_empresariais WHERE id=? AND {filtro}",
                        (iid,*parametros),
                    )
                else:
                    row=con.execute(
                        f"SELECT caminho_relativo caminho FROM arquivos_corporativos WHERE id=? AND {filtro} AND excluido_em IS NULL",
                        (iid,*parametros),
                    ).fetchone()
                    if row: con.execute(
                        f"UPDATE arquivos_corporativos SET excluido_em=CURRENT_TIMESTAMP WHERE id=? AND {filtro}",
                        (iid,*parametros),
                    )
            if row is None: raise FileNotFoundError("Item não encontrado.")
            arq=(banco.STORAGE_DIR/str(row["caminho"])).resolve()
            if banco.STORAGE_DIR.resolve() in arq.parents: arq.unlink(missing_ok=True)
            self._responder_json(HTTPStatus.OK,{"ok":True})
        except AutorizacaoNegada as e: self._responder_json(HTTPStatus.FORBIDDEN,_erro_resposta("forbidden", str(e), self._request_id))
        except SessaoInvalida as e: self._responder_json(HTTPStatus.UNAUTHORIZED,_erro_resposta("unauthorized", str(e), self._request_id))
        except PermissionError as e: self._responder_json(HTTPStatus.FORBIDDEN,_erro_resposta("forbidden", str(e), self._request_id))
        except FileNotFoundError as e: self._responder_json(HTTPStatus.NOT_FOUND,_erro_resposta("not_found", str(e), self._request_id))
        except ValueError as e:
            conflito = "alterado por outro usuário" in str(e).lower()
            self._responder_json(HTTPStatus.CONFLICT if conflito else HTTPStatus.BAD_REQUEST,_erro_resposta("version_conflict" if conflito else "invalid_request", str(e), self._request_id))
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha DELETE", extra={"request_id": self._request_id, "metodo": "DELETE", "caminho": self.path}); self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR,_erro_resposta("internal_error", "Falha interna do servidor.", self._request_id))

    def log_message(self, formato, *args):
        logging.getLogger("data_intelligence.corporate_server").info("%s %s - %s",self.client_address[0],self.path,formato%args)


class CorporateServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True
    def __init__(self, address, handler, config):
        self.config=config
        self.observabilidade = RegistroSaude("data-intelligence-corporate-server")
        self._monitor_stop=threading.Event()
        super().__init__(address,handler)
        self._monitor_thread=threading.Thread(
            target=self._monitorar_agentes, name="Corporate-Agent-Monitor", daemon=True
        )
        self._monitor_thread.start()
        from enterprise.automacao_motor import WorkerAutomacao
        self._automation_worker = WorkerAutomacao()
        self._automation_worker.iniciar()

    def _monitorar_agentes(self):
        while not self._monitor_stop.wait(30):
            try:
                with conectar() as con:
                    rows=con.execute(
                        """SELECT id,ativo_id FROM ti_agentes
                           WHERE ativo=1 AND status='Online' AND ultimo_heartbeat IS NOT NULL
                             AND datetime(ultimo_heartbeat) < datetime('now','-180 seconds')"""
                    ).fetchall()
                    for row in rows:
                        con.execute(
                            "UPDATE ti_agentes SET status='Degradado',atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                            (int(row["id"]),),
                        )
                        con.execute(
                            """UPDATE ti_ativos SET estado_conectividade='Offline',atualizado_em=CURRENT_TIMESTAMP
                               WHERE id=? AND ativo=1 AND estado_conectividade!='Em manutenção'""",
                            (int(row["ativo_id"]),),
                        )
            except Exception:
                logging.getLogger("data_intelligence.corporate_server").exception(
                    "Falha ao atualizar agentes expirados"
                )

    def server_close(self):
        self._monitor_stop.set()
        self._automation_worker.parar(timeout=5.0)
        try:
            return super().server_close()
        finally:
            aguardar_thread(self._monitor_thread, timeout=3.0)


def criar_servidor(config: ConfigServidor) -> CorporateServer:
    config=config.validar(); srv=CorporateServer((config.host,config.porta),CorporateRequestHandler,config)
    if config.tls:
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.minimum_version=ssl.TLSVersion.TLSv1_2; ctx.load_cert_chain(config.certificado,config.chave_privada); srv.socket=ctx.wrap_socket(srv.socket,server_side=True)
    return srv
