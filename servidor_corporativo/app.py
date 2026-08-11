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
from pathlib import Path
import re
import ssl
import tempfile
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from auth import banco
from auth.autenticacao import (
    _criar_usuario,
    autenticar_usuario,
    definir_perfil_acesso_usuario,
    definir_status_usuario,
    redefinir_senha,
    alterar_propria_senha,
)
from auth.banco import atualizar_email_corporativo_usuario, conectar
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
from servidor_corporativo.rpc import executar_rpc, RPCError
from servidor_ti.app import processar_heartbeat as processar_heartbeat_ti
from servidor_ti.security import AgentAuthError
from servidor_corporativo.sessoes import criar as criar_sessao, obter as obter_sessao, alterar_contexto as alterar_contexto_sessao

_JSON_MAX = 32 * 1024 * 1024
_NOME_SEGURO = re.compile(r"[^A-Za-z0-9._() -]+")


def _json_bytes(dados: Any) -> bytes:
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


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


def _admin(sessao) -> None:
    if str(sessao.usuario.get("perfil", "")).lower() != "admin":
        raise PermissionError("Operação exclusiva do administrador.")


def _nome_seguro(nome: str) -> str:
    nome = _NOME_SEGURO.sub("_", Path(str(nome or "arquivo")).name).strip(" .")[:180]
    return nome or "arquivo.bin"


class CorporateRequestHandler(BaseHTTPRequestHandler):
    server_version = "DataIntelligenceCorporate/" + VERSAO_SERVIDOR
    sys_version = ""

    @property
    def config(self) -> ConfigServidor:
        return self.server.config  # type: ignore[attr-defined]

    def _responder_json(self, status: int, dados: Any) -> None:
        corpo = _json_bytes(dados)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
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

    def _sessao(self):
        cab = str(self.headers.get("Authorization", ""))
        token = cab[7:].strip() if cab.lower().startswith("bearer ") else ""
        sessao = obter_sessao(token)
        if sessao is None:
            raise PermissionError("Sessão ausente, expirada ou revogada.")
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
        digest = hashlib.sha256()
        restante = tamanho
        with destino.open("wb") as out:
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
            destino.unlink(missing_ok=True)
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
        return {"id": int(cursor.lastrowid), "nome": nome, "tamanho_bytes": tamanho, "sha256": atual, "categoria": categoria}

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)
            if path in {"/", "/health", "/api/v1/health"}:
                self._responder_json(HTTPStatus.OK, {
                    "ok": True,
                    "servico": "data-intelligence-corporate-server",
                    "versao": VERSAO_SERVIDOR,
                    "autoridade_transacional": True,
                    "rpc_dominio": "1.0",
                    "agentes_ti": True,
                })
                return
            sessao = self._sessao()
            if path == "/api/v1/bootstrap":
                self._responder_json(HTTPStatus.OK, _bootstrap(sessao)); return
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
                backup = path.endswith("backups")
                if backup: _admin(sessao)
                tabela = "backups_empresariais" if backup else "arquivos_corporativos"
                with conectar() as con:
                    if backup:
                        rows=con.execute("SELECT id,tipo,arquivo_relativo,tamanho_bytes,sha256,criado_em,restaurado_em FROM backups_empresariais WHERE empresa_id=? ORDER BY id DESC LIMIT 500", (sessao.empresa_id,)).fetchall()
                    else:
                        rows=con.execute("SELECT id,modulo,categoria,nome,tamanho_bytes,sha256,origem,criado_em FROM arquivos_corporativos WHERE empresa_id=? AND excluido_em IS NULL ORDER BY id DESC LIMIT 1000", (sessao.empresa_id,)).fetchall()
                self._responder_json(HTTPStatus.OK, {"itens": [dict(x) for x in rows]}); return
            m=re.fullmatch(r"/api/v1/(files|backups)/(\d+)/download", path)
            if m:
                backup=m.group(1)=="backups"; iid=int(m.group(2))
                if backup: _admin(sessao)
                with conectar() as con:
                    sql = (
                        "SELECT arquivo_relativo AS caminho, NULL AS nome FROM backups_empresariais WHERE id=? AND empresa_id=?"
                        if backup
                        else "SELECT caminho_relativo AS caminho, nome FROM arquivos_corporativos WHERE id=? AND empresa_id=? AND excluido_em IS NULL"
                    )
                    row=con.execute(sql,(iid,sessao.empresa_id)).fetchone()
                if row is None: raise FileNotFoundError("Arquivo não encontrado.")
                arq=(banco.STORAGE_DIR/str(row["caminho"])).resolve()
                if banco.STORAGE_DIR.resolve() not in arq.parents or not arq.is_file(): raise FileNotFoundError("Arquivo físico não encontrado.")
                nome=row["nome"] or arq.name
                self.send_response(HTTPStatus.OK); self.send_header("Content-Type","application/octet-stream"); self.send_header("Content-Length",str(arq.stat().st_size)); self.send_header("Content-Disposition",f'attachment; filename="{_nome_seguro(nome)}"'); self.end_headers()
                with arq.open("rb") as f:
                    for bloco in iter(lambda:f.read(1024*1024),b""): self.wfile.write(bloco)
                return
            self._responder_json(HTTPStatus.NOT_FOUND, {"erro":"Rota não encontrada."})
        except PermissionError as e: self._responder_json(HTTPStatus.UNAUTHORIZED, {"erro":str(e)})
        except (ValueError, FileNotFoundError) as e: self._responder_json(HTTPStatus.BAD_REQUEST, {"erro":str(e)})
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha GET")
            self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"erro":"Falha interna do servidor."})

    def do_POST(self):
        try:
            path=urlparse(self.path).path.rstrip("/")
            if path == "/api/v1/auth/login":
                dados=self._ler_json(); usuario=autenticar_usuario(dados.get("usuario"), dados.get("senha")); empresa_id,filial_id=_contexto_usuario(usuario); sessao=criar_sessao(usuario,empresa_id,filial_id)
                self._responder_json(HTTPStatus.OK, {"token":sessao.token,"expira_em":sessao.expira_em.isoformat(),**_bootstrap(sessao)}); return
            if path == "/api/v1/ti/agentes/heartbeat":
                tipo=str(self.headers.get("Content-Type","")).lower()
                if "application/json" not in tipo:
                    self._responder_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE,{"erro":"Use application/json."}); return
                try: tamanho=int(self.headers.get("Content-Length","0"))
                except ValueError: tamanho=-1
                if tamanho <= 0 or tamanho > 128*1024:
                    self._responder_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE,{"erro":"Payload vazio ou acima do limite."}); return
                corpo=self.rfile.read(tamanho)
                try:
                    resultado=processar_heartbeat_ti(self.headers,corpo,self.client_address[0])
                except AgentAuthError:
                    self._responder_json(HTTPStatus.UNAUTHORIZED,{"erro":"Agente não autorizado."}); return
                self._responder_json(HTTPStatus.ACCEPTED,resultado); return
            sessao=self._sessao()
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
                    for item in d.get("anexos",[]) or []:
                        raw=base64.b64decode(str(item.get("data_base64", "")), validate=True); nome=_nome_seguro(item.get("nome","anexo.bin")); alvo=Path(tmp)/nome; alvo.write_bytes(raw); anexos.append(alvo)
                    mid=enviar_mensagem(d.get("assunto"),d.get("corpo"),d.get("para"),sessao.ator(),cc=d.get("cc"),cco=d.get("cco"),modulo_origem=d.get("modulo_origem"),anexos=anexos,resposta_de_id=d.get("resposta_de_id"))
                self._responder_json(HTTPStatus.CREATED,{"id":mid}); return
            if path == "/api/v1/mail/draft":
                d=self._ler_json(); mid=salvar_rascunho(d.get("assunto"),d.get("corpo"),sessao.ator(),modulo_origem=d.get("modulo_origem")); self._responder_json(HTTPStatus.CREATED,{"id":mid}); return
            if path == "/api/v1/files":
                self._responder_json(HTTPStatus.CREATED,self._arquivo_upload(sessao,backup=False)); return
            if path == "/api/v1/backups":
                _admin(sessao); self._responder_json(HTTPStatus.CREATED,self._arquivo_upload(sessao,backup=True)); return
            if path == "/api/v1/backups/create":
                _admin(sessao)
                resultado=criar_backup_local(sessao.ator(), sincronizar_servidor=False)
                seguro={k:v for k,v in resultado.items() if k not in {"arquivo"}}
                self._responder_json(HTTPStatus.CREATED,seguro); return
            self._responder_json(HTTPStatus.NOT_FOUND,{"erro":"Rota não encontrada."})
        except PermissionError as e: self._responder_json(HTTPStatus.UNAUTHORIZED,{"erro":str(e)})
        except (ValueError,TypeError,base64.binascii.Error) as e: self._responder_json(HTTPStatus.BAD_REQUEST,{"erro":str(e)})
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha POST"); self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR,{"erro":"Falha interna do servidor."})

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
                if "ativo" in d: definir_status_usuario(uid,bool(d["ativo"]),ator=ator)
                if d.get("perfil_acesso"): definir_perfil_acesso_usuario(uid,d["perfil_acesso"],ator=ator)
                if d.get("nova_senha"): redefinir_senha(uid,d["nova_senha"],ator=ator)
                if d.get("email_corporativo"): atualizar_email_corporativo_usuario(uid,str(d["email_corporativo"]).strip().lower())
                self._responder_json(HTTPStatus.OK,{"ok":True}); return
            m=re.fullmatch(r"/api/v1/mail/(\d+)",path)
            if m:
                atualizar_estado(int(m.group(1)),sessao.ator(),arquivada=d.get("arquivada"),excluida=d.get("excluida"),estrela=d.get("estrela")); self._responder_json(HTTPStatus.OK,{"ok":True}); return
            self._responder_json(HTTPStatus.NOT_FOUND,{"erro":"Rota não encontrada."})
        except PermissionError as e: self._responder_json(HTTPStatus.UNAUTHORIZED,{"erro":str(e)})
        except ValueError as e: self._responder_json(HTTPStatus.BAD_REQUEST,{"erro":str(e)})
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha PATCH"); self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR,{"erro":"Falha interna do servidor."})

    def do_DELETE(self):
        try:
            path=urlparse(self.path).path.rstrip("/"); sessao=self._sessao(); _admin(sessao)
            m=re.fullmatch(r"/api/v1/(files|backups)/(\d+)",path)
            if not m: self._responder_json(HTTPStatus.NOT_FOUND,{"erro":"Rota não encontrada."}); return
            backup=m.group(1)=="backups"; iid=int(m.group(2))
            with conectar() as con:
                if backup:
                    row=con.execute("SELECT arquivo_relativo caminho FROM backups_empresariais WHERE id=? AND empresa_id=?",(iid,sessao.empresa_id)).fetchone()
                    if row: con.execute("DELETE FROM backups_empresariais WHERE id=? AND empresa_id=?",(iid,sessao.empresa_id))
                else:
                    row=con.execute("SELECT caminho_relativo caminho FROM arquivos_corporativos WHERE id=? AND empresa_id=? AND excluido_em IS NULL",(iid,sessao.empresa_id)).fetchone()
                    if row: con.execute("UPDATE arquivos_corporativos SET excluido_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=?",(iid,sessao.empresa_id))
            if row is None: raise FileNotFoundError("Item não encontrado.")
            arq=(banco.STORAGE_DIR/str(row["caminho"])).resolve()
            if banco.STORAGE_DIR.resolve() in arq.parents: arq.unlink(missing_ok=True)
            self._responder_json(HTTPStatus.OK,{"ok":True})
        except PermissionError as e: self._responder_json(HTTPStatus.UNAUTHORIZED,{"erro":str(e)})
        except FileNotFoundError as e: self._responder_json(HTTPStatus.NOT_FOUND,{"erro":str(e)})
        except Exception:
            logging.getLogger("data_intelligence.corporate_server").exception("Falha DELETE"); self._responder_json(HTTPStatus.INTERNAL_SERVER_ERROR,{"erro":"Falha interna do servidor."})

    def log_message(self, formato, *args):
        logging.getLogger("data_intelligence.corporate_server").info("%s %s - %s",self.client_address[0],self.path,formato%args)


class CorporateServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True
    def __init__(self, address, handler, config):
        self.config=config
        self._monitor_stop=threading.Event()
        super().__init__(address,handler)
        self._monitor_thread=threading.Thread(
            target=self._monitorar_agentes, name="Corporate-Agent-Monitor", daemon=True
        )
        self._monitor_thread.start()

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
        return super().server_close()


def criar_servidor(config: ConfigServidor) -> CorporateServer:
    config=config.validar(); srv=CorporateServer((config.host,config.porta),CorporateRequestHandler,config)
    if config.tls:
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.minimum_version=ssl.TLSVersion.TLSv1_2; ctx.load_cert_chain(config.certificado,config.chave_privada); srv.socket=ctx.wrap_socket(srv.socket,server_side=True)
    return srv
