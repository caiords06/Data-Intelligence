"""Cliente HTTP do Servidor Corporativo.

Mantém apenas o bearer token em memória. Senhas nunca são persistidas. A
identidade/estrutura recebida no login é copiada para o banco local como cache
mínimo para que o roteamento da interface continue funcionando offline; a
fonte de autenticação em nós central/cliente continua sendo o servidor.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
from pathlib import Path
import secrets
import urllib.error
import urllib.parse
import urllib.request

from auth import banco
from auth.seguranca import gerar_hash_senha
from core.nodo import carregar_config_nodo, usa_servidor_remoto

_TOKEN: str | None = None


def _cfg():
    cfg=carregar_config_nodo().validar()
    if not usa_servidor_remoto() or not cfg.servidor_url:
        raise RuntimeError("Este nó não está configurado para um servidor corporativo.")
    _validar_url(cfg.servidor_url,cfg.permitir_http_privado)
    return cfg


def _validar_url(url: str, permitir_http_privado: bool) -> None:
    p=urllib.parse.urlparse(url)
    if p.scheme == "https": return
    if p.scheme != "http": raise ValueError("Servidor corporativo exige HTTP ou HTTPS.")
    host=(p.hostname or "").lower()
    if host in {"localhost","127.0.0.1","::1"}: return
    try: privado=ipaddress.ip_address(host).is_private
    except ValueError: privado=False
    if not (permitir_http_privado and privado):
        raise ValueError("HTTP sem TLS só é permitido explicitamente para um IP privado de laboratório.")


def _request(path: str, *, metodo="GET", dados=None, corpo: bytes | None=None, headers=None, autenticar=True, timeout=20):
    cfg=_cfg(); url=f"{cfg.servidor_url}{path}"
    h={"User-Agent":"DataIntelligenceDesktop/1.0","Accept":"application/json"}
    if autenticar:
        if not _TOKEN: raise PermissionError("Entre novamente para restabelecer a sessão do servidor.")
        h["Authorization"]=f"Bearer {_TOKEN}"
    if headers: h.update({str(k):str(v) for k,v in headers.items()})
    if dados is not None:
        corpo=json.dumps(dados,ensure_ascii=False).encode("utf-8"); h["Content-Type"]="application/json; charset=utf-8"
    req=urllib.request.Request(url,data=corpo,headers=h,method=metodo)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            raw=resp.read(); ctype=str(resp.headers.get("Content-Type",""))
            return json.loads(raw.decode("utf-8")) if "application/json" in ctype else raw
    except urllib.error.HTTPError as e:
        try: msg=json.loads(e.read().decode("utf-8")).get("erro")
        except Exception: msg=f"Servidor respondeu HTTP {e.code}."
        if e.code in {401,403}: raise PermissionError(msg) from None
        raise ValueError(msg) from None
    except urllib.error.URLError as e:
        raise ConnectionError(f"Não foi possível conectar ao servidor corporativo: {e.reason}") from None


def testar_servidor() -> dict:
    return _request("/api/v1/health",autenticar=False,timeout=5)


def login_remoto(usuario: str, senha: str) -> dict:
    global _TOKEN
    resp=_request("/api/v1/auth/login",metodo="POST",dados={"usuario":usuario,"senha":senha},autenticar=False)
    _TOKEN=str(resp["token"]); _sincronizar_cache_identidade(resp)
    return dict(resp["usuario"])


def encerrar_sessao_remota() -> None:
    global _TOKEN; _TOKEN=None


def _sincronizar_cache_identidade(payload: dict) -> None:
    usuario=dict(payload.get("usuario") or {}); empresa=dict(payload.get("empresa") or {})
    if not usuario.get("id") or not empresa.get("id"): return
    # Hash aleatório nunca é usado para login remoto; evita manter a senha real no cache.
    hash_falso,salt=gerar_hash_senha(secrets.token_urlsafe(32))
    with banco.conectar() as con:
        con.execute(
            """INSERT INTO usuarios (id,nome,usuario,senha_hash,salt,perfil,perfil_acesso,email_corporativo,sessao_epoch,ativo)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET nome=excluded.nome,usuario=excluded.usuario,perfil=excluded.perfil,
               perfil_acesso=excluded.perfil_acesso,email_corporativo=excluded.email_corporativo,
               sessao_epoch=excluded.sessao_epoch,ativo=excluded.ativo""",
            (int(usuario["id"]),usuario.get("nome"),usuario.get("usuario"),hash_falso,salt,usuario.get("perfil","usuario"),usuario.get("perfil_acesso","analista"),usuario.get("email_corporativo"),int(usuario.get("sessao_epoch",0)),1 if usuario.get("ativo",True) else 0),
        )
        con.execute("INSERT INTO empresas (id,nome,cnpj,ativo) VALUES (?,?,?,1) ON CONFLICT(id) DO UPDATE SET nome=excluded.nome,cnpj=excluded.cnpj,ativo=1",(int(empresa["id"]),empresa.get("nome") or "Empresa",empresa.get("cnpj")))
        for f in payload.get("filiais",[]) or []:
            con.execute("INSERT INTO filiais (id,empresa_id,nome,codigo,cidade,estado,ativo) VALUES (?,?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET empresa_id=excluded.empresa_id,nome=excluded.nome,codigo=excluded.codigo,cidade=excluded.cidade,estado=excluded.estado,ativo=1",(int(f["id"]),int(f["empresa_id"]),f.get("nome") or "Filial",f.get("codigo") or f"F{f['id']}",f.get("cidade"),f.get("estado")))
        for d in payload.get("departamentos",[]) or []:
            con.execute("INSERT INTO departamentos (id,empresa_id,nome,codigo,ativo) VALUES (?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET empresa_id=excluded.empresa_id,nome=excluded.nome,codigo=excluded.codigo,ativo=1",(int(d["id"]),int(d["empresa_id"]),d.get("nome") or "Departamento",d.get("codigo") or f"D{d['id']}"))
        for c in payload.get("centros_custo",[]) or []:
            con.execute("INSERT INTO centros_custo (id,empresa_id,departamento_id,nome,codigo,ativo) VALUES (?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET empresa_id=excluded.empresa_id,departamento_id=excluded.departamento_id,nome=excluded.nome,codigo=excluded.codigo,ativo=1",(int(c["id"]),int(c["empresa_id"]),c.get("departamento_id"),c.get("nome") or "Centro",c.get("codigo") or f"C{c['id']}"))
        con.execute("INSERT OR REPLACE INTO usuarios_empresas (usuario_id,empresa_id,filial_id,ativo) VALUES (?,?,?,1)",(int(usuario["id"]),int(empresa["id"]),payload.get("filial_id")))
        con.execute("DELETE FROM permissoes_modulos WHERE usuario_id=? AND empresa_id=?",(int(usuario["id"]),int(empresa["id"])))
        for p in payload.get("permissoes",[]) or []:
            con.execute("INSERT INTO permissoes_modulos (usuario_id,empresa_id,modulo,pode_ler,pode_escrever,pode_aprovar) VALUES (?,?,?,?,?,?)",(int(usuario["id"]),int(empresa["id"]),p.get("modulo"),int(p.get("pode_ler",0)),int(p.get("pode_escrever",0)),int(p.get("pode_aprovar",0))))






def definir_contexto_remoto(empresa_id: int, filial_id: int | None) -> dict:
    return dict(_request(
        "/api/v1/context",
        metodo="PATCH",
        dados={"empresa_id": int(empresa_id), "filial_id": filial_id},
    ))

def alterar_propria_senha_remota(senha_atual: str, nova_senha: str) -> None:
    global _TOKEN
    _request(
        "/api/v1/account/password",
        metodo="PATCH",
        dados={"senha_atual": senha_atual, "nova_senha": nova_senha},
    )
    # A alteração incrementa sessao_epoch no servidor; força novo login local.
    _TOKEN = None

def listar_usuarios_remoto() -> list[dict]: return list(_request("/api/v1/users").get("usuarios",[]))
def criar_usuario_remoto(dados: dict) -> dict: return dict(_request("/api/v1/users",metodo="POST",dados=dados))
def atualizar_usuario_remoto(usuario_id: int, dados: dict) -> None: _request(f"/api/v1/users/{int(usuario_id)}",metodo="PATCH",dados=dados)

def listar_contatos_remoto(pesquisa="") -> list[dict]: return list(_request("/api/v1/mail/contacts?"+urllib.parse.urlencode({"q":pesquisa})).get("contatos",[]))
def listar_caixa_remoto(caixa="entrada",pesquisa="") -> list[dict]: return list(_request("/api/v1/mail?"+urllib.parse.urlencode({"box":caixa,"q":pesquisa})).get("mensagens",[]))
def obter_mensagem_remoto(mid: int) -> dict: return dict(_request(f"/api/v1/mail/{int(mid)}"))
def contagem_nao_lidas_remoto() -> int: return int(_request("/api/v1/mail/unread").get("nao_lidas",0))
def atualizar_estado_remoto(mid: int, **dados) -> None: _request(f"/api/v1/mail/{int(mid)}",metodo="PATCH",dados={k:v for k,v in dados.items() if v is not None})

def enviar_mensagem_remota(*,assunto,corpo,para,cc=None,cco=None,modulo_origem=None,anexos=None,resposta_de_id=None) -> int:
    itens=[]
    for caminho in anexos or []:
        p=Path(caminho).expanduser().resolve()
        if not p.is_file(): raise ValueError(f"Anexo não encontrado: {p.name}")
        if p.stat().st_size>25*1024*1024: raise ValueError(f"O anexo {p.name} excede 25 MB.")
        itens.append({"nome":p.name,"data_base64":base64.b64encode(p.read_bytes()).decode("ascii")})
    d={"assunto":assunto,"corpo":corpo,"para":para,"cc":cc,"cco":cco,"modulo_origem":modulo_origem,"anexos":itens,"resposta_de_id":resposta_de_id}
    return int(_request("/api/v1/mail",metodo="POST",dados=d)["id"])

def salvar_rascunho_remoto(assunto,corpo,modulo_origem=None) -> int:
    return int(_request("/api/v1/mail/draft",metodo="POST",dados={"assunto":assunto,"corpo":corpo,"modulo_origem":modulo_origem})["id"])


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()


def enviar_arquivo(caminho: str | Path, *, modulo="core", categoria="arquivo") -> dict:
    p=Path(caminho).expanduser().resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    return dict(_request("/api/v1/files",metodo="POST",corpo=p.read_bytes(),headers={"Content-Type":"application/octet-stream","X-File-Name":p.name,"X-Module":modulo,"X-Category":categoria,"X-SHA256":_sha256(p)},timeout=max(30,min(600,int(p.stat().st_size/1024/1024)*2+30))))


def enviar_backup(caminho: str | Path) -> dict:
    p=Path(caminho).expanduser().resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    return dict(_request("/api/v1/backups",metodo="POST",corpo=p.read_bytes(),headers={"Content-Type":"application/octet-stream","X-File-Name":p.name,"X-SHA256":_sha256(p)},timeout=max(60,min(1800,int(p.stat().st_size/1024/1024)*3+60))))


def listar_arquivos_servidor(backups=False) -> list[dict]: return list(_request("/api/v1/backups" if backups else "/api/v1/files").get("itens",[]))
def excluir_item_servidor(item_id: int, *, backup=False) -> None: _request(f"/api/v1/{'backups' if backup else 'files'}/{int(item_id)}",metodo="DELETE")


def espelhar_exportacao(caminho: str | Path, *, modulo="core", categoria="exportacao") -> dict | None:
    cfg=carregar_config_nodo()
    if not (usa_servidor_remoto() and cfg.sincronizar_exportacoes and _TOKEN): return None
    return enviar_arquivo(caminho,modulo=modulo,categoria=categoria)


def executar_rpc_remoto(modulo: str, funcao: str, args=(), kwargs=None):
    """Executa uma operação de domínio no Servidor Corporativo.

    O servidor substitui qualquer argumento ``ator`` pela identidade associada
    ao bearer token; o cliente não consegue elevar o próprio escopo enviando um
    dicionário adulterado.
    """
    from core.rpc_central import desserializar, serializar
    payload={
        "modulo": str(modulo),
        "funcao": str(funcao),
        "args": serializar(list(args)),
        "kwargs": serializar(dict(kwargs or {})),
    }
    resposta=_request("/api/v1/rpc",metodo="POST",dados=payload,timeout=120)
    return desserializar(resposta.get("resultado"))


def criar_backup_servidor() -> dict:
    return dict(_request("/api/v1/backups/create", metodo="POST", dados={}))
