"""Cliente HTTP do Servidor Corporativo.

Mantém bearer token, identidade e contexto apenas em memória. Senhas e dados
corporativos nunca são persistidos na estação; a fonte de verdade é sempre o
Servidor Corporativo/PostgreSQL.
"""

from __future__ import annotations

import atexit
import base64
import hashlib
import http.client
import importlib
import inspect
import os
import tempfile
import ipaddress
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from core.nodo import carregar_config_nodo, usa_servidor_remoto

_TOKEN: str | None = None
_BOOTSTRAP_MEMORIA: dict = {}
_ARQUIVOS_TEMPORARIOS: set[Path] = set()


def _limpar_arquivos_temporarios() -> None:
    for caminho in list(_ARQUIVOS_TEMPORARIOS):
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            pass
    _ARQUIVOS_TEMPORARIOS.clear()


atexit.register(_limpar_arquivos_temporarios)


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
    global _TOKEN, _BOOTSTRAP_MEMORIA
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
            return json.loads(raw.decode("utf-8-sig")) if "application/json" in ctype else raw
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8-sig"))
            msg = payload.get("erro") if isinstance(payload, dict) else None
            if not msg and isinstance(payload, dict):
                erro = payload.get("error")
                if isinstance(erro, dict):
                    msg = erro.get("message")
            if not msg:
                msg = f"Servidor respondeu HTTP {e.code}."
        except Exception:
            msg=f"Servidor respondeu HTTP {e.code}."
        request_id = str(e.headers.get("X-Request-ID") or "").strip() if e.headers else ""
        if request_id:
            msg = f"{msg} [ID da requisição: {request_id}]"
        if e.code in {401,403}:
            if e.code == 401:
                # Não reutilize um token que o servidor já declarou inválido/expirado.
                _TOKEN = None
                _BOOTSTRAP_MEMORIA = {}
            raise PermissionError(msg) from None
        raise ValueError(msg) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # A UI já trata ValueError como falha operacional exibível. Não deixe
        # indisponibilidade de rede/DNS/timeout escapar como traceback de callback Tk.
        motivo = getattr(e, "reason", None) or str(e) or type(e).__name__
        raise ValueError(f"Servidor corporativo indisponível: {motivo}") from None


def testar_servidor() -> dict:
    return _request("/api/v1/health",autenticar=False,timeout=5)


def login_remoto(usuario: str, senha: str, *, codigo_mfa: str = "") -> dict:
    global _TOKEN
    resp=_request(
        "/api/v1/auth/login", metodo="POST",
        dados={"usuario":usuario,"senha":senha,"codigo_mfa":codigo_mfa},
        autenticar=False,
    )
    _TOKEN=str(resp["token"])
    _atualizar_bootstrap_memoria(resp)
    return dict(resp["usuario"])


def encerrar_sessao_remota() -> None:
    global _TOKEN, _BOOTSTRAP_MEMORIA
    try:
        if _TOKEN:
            _request("/api/v1/auth/logout", metodo="POST", dados={})
    finally:
        _TOKEN=None
        _BOOTSTRAP_MEMORIA={}


def _atualizar_bootstrap_memoria(payload: dict) -> None:
    """Mantém somente o bootstrap necessário à UI durante a sessão atual."""
    global _BOOTSTRAP_MEMORIA
    _BOOTSTRAP_MEMORIA = {
        "usuario": dict(payload.get("usuario") or {}),
        "empresa": dict(payload.get("empresa") or {}),
        "filial_id": payload.get("filial_id"),
        "filiais": [dict(x) for x in (payload.get("filiais") or [])],
        "departamentos": [dict(x) for x in (payload.get("departamentos") or [])],
        "centros_custo": [dict(x) for x in (payload.get("centros_custo") or [])],
        "permissoes": [dict(x) for x in (payload.get("permissoes") or [])],
    }


def contexto_memoria() -> dict:
    return dict(_BOOTSTRAP_MEMORIA)


def definir_contexto_remoto(empresa_id: int, filial_id: int | None) -> dict:
    payload = dict(_request(
        "/api/v1/context",
        metodo="PATCH",
        dados={"empresa_id": int(empresa_id), "filial_id": filial_id},
    ))
    _atualizar_bootstrap_memoria(payload)
    return payload


def validar_sessao_remota() -> dict:
    """Valida o bearer no servidor e atualiza somente o contexto em memória."""
    payload = dict(_request("/api/v1/bootstrap"))
    _atualizar_bootstrap_memoria(payload)
    return payload


def obter_permissoes_usuario_remoto(usuario_id: int) -> dict:
    return dict(executar_rpc_remoto(
        "enterprise.contexto", "obter_permissoes_usuario",
        args=(int(usuario_id), None),
    ))


def salvar_permissoes_usuario_remoto(usuario_id: int, permissoes: dict) -> None:
    executar_rpc_remoto(
        "enterprise.contexto", "salvar_permissoes_usuario",
        args=(int(usuario_id), permissoes, None),
    )

def alterar_propria_senha_remota(senha_atual: str, nova_senha: str) -> None:
    global _TOKEN
    _request(
        "/api/v1/account/password",
        metodo="PATCH",
        dados={"senha_atual": senha_atual, "nova_senha": nova_senha},
    )
    # A alteração incrementa sessao_epoch no servidor; força novo login na estação.
    _TOKEN = None

def listar_usuarios_remoto() -> list[dict]: return list(_request("/api/v1/users").get("usuarios",[]))
def criar_usuario_remoto(dados: dict) -> dict: return dict(_request("/api/v1/users",metodo="POST",dados=dados))
def atualizar_usuario_remoto(usuario_id: int, dados: dict) -> None:
    usuario_id = int(usuario_id)
    atual = next((x for x in listar_usuarios_remoto() if int(x.get("id", 0)) == usuario_id), None)
    if atual is None:
        raise ValueError("Usuário não encontrado no servidor.")
    _request(
        f"/api/v1/users/{usuario_id}", metodo="PATCH", dados=dados,
        headers={"If-Match": f'"{int(atual.get("sessao_epoch", 0))}"'},
    )

def listar_contatos_remoto(pesquisa="") -> list[dict]: return list(_request("/api/v1/mail/contacts?"+urllib.parse.urlencode({"q":pesquisa})).get("contatos",[]))
def listar_caixa_remoto(caixa="entrada",pesquisa="") -> list[dict]: return list(_request("/api/v1/mail?"+urllib.parse.urlencode({"box":caixa,"q":pesquisa})).get("mensagens",[]))
def obter_mensagem_remoto(mid: int) -> dict: return dict(_request(f"/api/v1/mail/{int(mid)}"))
def contagem_nao_lidas_remoto() -> int: return int(_request("/api/v1/mail/unread").get("nao_lidas",0))
def atualizar_estado_remoto(mid: int, **dados) -> None: _request(f"/api/v1/mail/{int(mid)}",metodo="PATCH",dados={k:v for k,v in dados.items() if v is not None})

def enviar_mensagem_remota(*,assunto,corpo,para,cc=None,cco=None,modulo_origem=None,anexos=None,resposta_de_id=None) -> int:
    # O servidor aceita no máximo 32 MiB de JSON. Base64 acrescenta ~33%;
    # validamos o conjunto antes de ler os arquivos para não aceitar localmente
    # uma mensagem que inevitavelmente seria recusada no modo remoto.
    caminhos=[]
    estimativa_base64=0
    for caminho in anexos or []:
        p=Path(caminho).expanduser().resolve()
        if not p.is_file(): raise ValueError(f"Anexo não encontrado: {p.name}")
        tamanho=p.stat().st_size
        if tamanho>25*1024*1024: raise ValueError(f"O anexo {p.name} excede 25 MB.")
        estimativa_base64 += 4 * ((tamanho + 2) // 3)
        caminhos.append(p)
    overhead=len(str(assunto or "").encode("utf-8"))+len(str(corpo or "").encode("utf-8"))+1024*1024
    if estimativa_base64 + overhead > 31*1024*1024:
        raise ValueError(
            "No modo remoto, o total de anexos desta mensagem excede o limite seguro de transporte. "
            "Reduza os anexos ou envie os arquivos pelo armazenamento corporativo."
        )
    itens=[
        {"nome":p.name,"data_base64":base64.b64encode(p.read_bytes()).decode("ascii")}
        for p in caminhos
    ]
    d={"assunto":assunto,"corpo":corpo,"para":para,"cc":cc,"cco":cco,"modulo_origem":modulo_origem,"anexos":itens,"resposta_de_id":resposta_de_id}
    return int(_request("/api/v1/mail",metodo="POST",dados=d)["id"])

def salvar_rascunho_remoto(assunto,corpo,modulo_origem=None) -> int:
    return int(_request("/api/v1/mail/draft",metodo="POST",dados={"assunto":assunto,"corpo":corpo,"modulo_origem":modulo_origem})["id"])


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()


def _upload_streaming(p: Path, endpoint: str, *, headers: dict, timeout: int) -> dict:
    """Envia arquivo sem materializá-lo inteiro em memória."""
    cfg=_cfg()
    if not _TOKEN:
        raise PermissionError("Entre novamente para restabelecer a sessão do servidor.")
    parsed=urllib.parse.urlparse(cfg.servidor_url)
    host=parsed.hostname
    if not host:
        raise ValueError("URL do servidor corporativo inválida.")
    porta=parsed.port or (443 if parsed.scheme=="https" else 80)
    classe=http.client.HTTPSConnection if parsed.scheme=="https" else http.client.HTTPConnection
    conexao=classe(host,porta,timeout=timeout)
    base=parsed.path.rstrip("/")
    alvo=f"{base}{endpoint}" or "/"
    cabecalhos={
        "User-Agent":"DataIntelligenceDesktop/1.0",
        "Accept":"application/json",
        "Authorization":f"Bearer {_TOKEN}",
        "Content-Type":"application/octet-stream",
        "Content-Length":str(p.stat().st_size),
        **{str(k):str(v) for k,v in headers.items()},
    }
    try:
        conexao.putrequest("POST",alvo)
        for chave,valor in cabecalhos.items():
            conexao.putheader(chave,valor)
        conexao.endheaders()
        with p.open("rb") as arquivo:
            for bloco in iter(lambda:arquivo.read(1024*1024),b""):
                conexao.send(bloco)
        resposta=conexao.getresponse()
        raw=resposta.read()
        if resposta.status >= 400:
            try: msg=json.loads(raw.decode("utf-8-sig")).get("erro")
            except Exception: msg=f"Servidor respondeu HTTP {resposta.status}."
            if resposta.status in {401,403}:
                raise PermissionError(msg)
            raise ValueError(msg)
        ctype=str(resposta.getheader("Content-Type") or "")
        return dict(json.loads(raw.decode("utf-8-sig"))) if "application/json" in ctype else {"conteudo":raw}
    except OSError as erro:
        # Mantém o mesmo contrato das demais chamadas remotas: falha operacional
        # exibível pela UI, sem traceback de callback Tkinter.
        raise ValueError(f"Não foi possível enviar o arquivo ao servidor corporativo: {erro}") from None
    finally:
        conexao.close()


def enviar_arquivo(caminho: str | Path, *, modulo="core", categoria="arquivo") -> dict:
    p=Path(caminho).expanduser().resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    timeout=max(30,min(600,int(p.stat().st_size/1024/1024)*2+30))
    return _upload_streaming(
        p,"/api/v1/files",timeout=timeout,
        headers={"X-File-Name":p.name,"X-Module":modulo,"X-Category":categoria,"X-SHA256":_sha256(p)},
    )


def enviar_bytes_servidor(conteudo: bytes, nome: str, *, modulo="core", categoria="exportacao") -> dict:
    """Persiste um artefato gerado em memória diretamente no Servidor Corporativo.

    É usado por estações Central/Cliente para que exportações internas não sejam
    criadas primeiro no disco local. O payload segue para o servidor em uma única
    requisição autenticada e passa a ser registrado em ``arquivos_corporativos``.
    """
    bruto = bytes(conteudo)
    if not bruto:
        raise ValueError("O artefato de exportação está vazio.")
    nome_seguro = Path(str(nome or "exportacao.bin")).name
    if not nome_seguro:
        nome_seguro = "exportacao.bin"
    timeout = max(30, min(600, int(len(bruto) / 1024 / 1024) * 2 + 30))
    return dict(_request(
        "/api/v1/exports",
        metodo="POST",
        corpo=bruto,
        headers={
            "Content-Type": "application/octet-stream",
            "X-File-Name": nome_seguro,
            "X-Module": str(modulo or "core"),
            "X-Category": str(categoria or "exportacao"),
            "X-SHA256": hashlib.sha256(bruto).hexdigest(),
        },
        timeout=timeout,
    ))


def enviar_backup(caminho: str | Path) -> dict:
    p=Path(caminho).expanduser().resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    timeout=max(60,min(1800,int(p.stat().st_size/1024/1024)*3+60))
    return _upload_streaming(
        p,"/api/v1/backups",timeout=timeout,
        headers={"X-File-Name":p.name,"X-SHA256":_sha256(p)},
    )


def listar_arquivos_servidor(backups=False) -> list[dict]: return list(_request("/api/v1/backups" if backups else "/api/v1/files").get("itens",[]))
def excluir_item_servidor(item_id: int, *, backup=False) -> None: _request(f"/api/v1/{'backups' if backup else 'files'}/{int(item_id)}",metodo="DELETE")


def espelhar_exportacao(caminho: str | Path, *, modulo="core", categoria="exportacao") -> dict | None:
    cfg=carregar_config_nodo()
    if not (usa_servidor_remoto() and cfg.sincronizar_exportacoes and _TOKEN): return None
    return enviar_arquivo(caminho,modulo=modulo,categoria=categoria)


def _funcao_original(modulo: str, funcao: str):
    mod = importlib.import_module(str(modulo))
    alvo = getattr(mod, str(funcao), None)
    if alvo is None or not callable(alvo):
        raise ValueError(f"Operação remota indisponível: {modulo}.{funcao}.")
    return getattr(alvo, "__di_rpc_original__", alvo)


def _marcar_parametro_arquivo(modulo: str, funcao: str, args, kwargs, parametro: str, marcador: str):
    alvo = _funcao_original(modulo, funcao)
    assinatura = inspect.signature(alvo)
    try:
        ligados = assinatura.bind_partial(*args, **dict(kwargs or {}))
    except TypeError as erro:
        raise ValueError(str(erro)) from None
    if parametro not in ligados.arguments:
        raise ValueError(f"Parâmetro de arquivo ausente: {parametro}.")
    original = ligados.arguments[parametro]
    ligados.arguments[parametro] = {marcador: True}
    return list(ligados.args), dict(ligados.kwargs), original


def _meta_rpc_arquivo(args, kwargs) -> str:
    from core.rpc_central import serializar
    bruto = json.dumps(
        {"args": serializar(list(args)), "kwargs": serializar(dict(kwargs or {}))},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(bruto).decode("ascii")


def _decodificar_resultado_header(valor: str | None):
    from core.rpc_central import desserializar
    if not valor:
        return None
    try:
        bruto = base64.urlsafe_b64decode(valor.encode("ascii"))
        return desserializar(json.loads(bruto.decode("utf-8")))
    except Exception:
        return None


def _arquivo_temporario_download(nome: str) -> Path:
    nome = Path(str(nome or "resultado.bin")).name
    sufixo = Path(nome).suffix
    fd, caminho = tempfile.mkstemp(prefix="dataintelligence_rpc_", suffix=sufixo)
    os.close(fd)
    destino = Path(caminho)
    _ARQUIVOS_TEMPORARIOS.add(destino)
    return destino


def _request_armazenar_resultado_arquivo(payload: dict) -> dict:
    """Solicita geração e persistência do arquivo no servidor, sem baixar bytes."""
    from core.rpc_central import serializar
    resposta = _request(
        "/api/v1/rpc/file-store",
        metodo="POST",
        dados={
            **payload,
            "args": serializar(payload.get("args") or []),
            "kwargs": serializar(payload.get("kwargs") or {}),
        },
        timeout=180,
    )
    resultado = resposta.get("resultado") or {}
    if not isinstance(resultado, dict):
        raise ValueError("Servidor retornou metadados inválidos para o arquivo gerado.")
    return dict(resultado)


def _request_resultado_arquivo(payload: dict) -> tuple[bytes, str, object]:
    cfg = _cfg()
    if not _TOKEN:
        raise PermissionError("Entre novamente para restabelecer a sessão do servidor.")
    from core.rpc_central import serializar
    corpo = json.dumps(
        {
            **payload,
            "args": serializar(payload.get("args") or []),
            "kwargs": serializar(payload.get("kwargs") or {}),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    url = f"{cfg.servidor_url}/api/v1/rpc/file-result"
    req = urllib.request.Request(
        url,
        data=corpo,
        headers={
            "User-Agent": "DataIntelligenceDesktop/1.0",
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            conteudo = resp.read()
            nome = str(resp.headers.get("X-DI-File-Name") or "resultado.bin")
            resultado = _decodificar_resultado_header(resp.headers.get("X-DI-RPC-Result"))
            return conteudo, Path(nome).name, resultado
    except urllib.error.HTTPError as erro:
        try:
            mensagem = json.loads(erro.read().decode("utf-8-sig")).get("erro")
        except Exception:
            mensagem = f"Servidor respondeu HTTP {erro.code}."
        request_id = str(erro.headers.get("X-Request-ID") or "").strip() if erro.headers else ""
        if request_id:
            mensagem = f"{mensagem} [ID da requisição: {request_id}]"
        if erro.code in {401, 403}:
            raise PermissionError(mensagem) from None
        raise ValueError(mensagem) from None
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        motivo = getattr(erro, "reason", None) or str(erro) or type(erro).__name__
        raise ValueError(f"Servidor corporativo indisponível durante geração do arquivo: {motivo}") from None


def _gravar_resultado_arquivo(conteudo: bytes, destino: Path) -> Path:
    destino = destino.expanduser().resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".part")
    try:
        temporario.write_bytes(conteudo)
        os.replace(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)
    return destino


def _ajustar_resultado_para_caminho_local(resultado, caminho: Path):
    if isinstance(resultado, Path):
        return caminho
    if isinstance(resultado, str):
        return str(caminho)
    if isinstance(resultado, dict):
        copia = dict(resultado)
        if "arquivo" in copia:
            copia["arquivo"] = str(caminho)
        if "caminho" in copia and isinstance(copia.get("caminho"), (str, Path)):
            copia["caminho"] = str(caminho)
        return copia
    return resultado if resultado is not None else str(caminho)


def executar_operacao_arquivo_remota(modulo: str, funcao: str, args=(), kwargs=None):
    """Transporta arquivos sem permitir que a estação acesse o filesystem do servidor."""
    from core.rpc_arquivos import (
        RPC_ARQUIVO_ENTRADA,
        RPC_ARQUIVO_SAIDA_PARAM,
        RPC_ARQUIVO_RETORNO,
        RPC_ARQUIVO_PERSISTE_SERVIDOR,
        MARCADOR_ENTRADA,
        MARCADOR_SAIDA,
    )
    from core.rpc_central import desserializar, serializar

    chave = (str(modulo), str(funcao))
    kwargs = dict(kwargs or {})
    if chave in RPC_ARQUIVO_ENTRADA:
        parametro = RPC_ARQUIVO_ENTRADA[chave]
        args_rpc, kwargs_rpc, caminho = _marcar_parametro_arquivo(
            modulo, funcao, args, kwargs, parametro, MARCADOR_ENTRADA
        )
        arquivo = Path(caminho).expanduser().resolve()
        if not arquivo.is_file():
            raise ValueError(f"Arquivo selecionado não encontrado: {arquivo.name}")
        resposta = _upload_streaming(
            arquivo,
            "/api/v1/rpc/file-upload",
            timeout=max(60, min(1800, int(arquivo.stat().st_size / 1024 / 1024) * 3 + 60)),
            headers={
                "X-RPC-Module": modulo,
                "X-RPC-Function": funcao,
                "X-RPC-Meta": _meta_rpc_arquivo(args_rpc, kwargs_rpc),
                "X-File-Name": arquivo.name,
                "X-SHA256": _sha256(arquivo),
            },
        )
        return desserializar(resposta.get("resultado"))

    nome_destino = None
    destino_local = None
    args_rpc, kwargs_rpc = list(args), kwargs
    if chave in RPC_ARQUIVO_PERSISTE_SERVIDOR:
        return _request_armazenar_resultado_arquivo({
            "modulo": modulo,
            "funcao": funcao,
            "args": args_rpc,
            "kwargs": kwargs_rpc,
            "categoria": "relatorio",
        })
    if chave in RPC_ARQUIVO_SAIDA_PARAM:
        parametro = RPC_ARQUIVO_SAIDA_PARAM[chave]
        args_rpc, kwargs_rpc, destino = _marcar_parametro_arquivo(
            modulo, funcao, args, kwargs, parametro, MARCADOR_SAIDA
        )
        destino_texto = str(destino or "").strip()
        if destino_texto.lower().startswith("server://"):
            nome_destino = Path(destino_texto[len("server://"):]).name or "resultado.bin"
            return _request_armazenar_resultado_arquivo({
                "modulo": modulo,
                "funcao": funcao,
                "args": args_rpc,
                "kwargs": kwargs_rpc,
                "nome_destino": nome_destino,
                "categoria": "relatorio",
            })
        destino_local = Path(destino).expanduser().resolve()
        nome_destino = destino_local.name
    elif chave not in RPC_ARQUIVO_RETORNO:
        raise ValueError(f"Operação de arquivo remota não cadastrada: {modulo}.{funcao}.")

    conteudo, nome_servidor, resultado = _request_resultado_arquivo({
        "modulo": modulo,
        "funcao": funcao,
        "args": args_rpc,
        "kwargs": kwargs_rpc,
        "nome_destino": nome_destino,
    })
    if destino_local is None:
        destino_local = _arquivo_temporario_download(nome_servidor)
    _gravar_resultado_arquivo(conteudo, destino_local)
    return _ajustar_resultado_para_caminho_local(resultado, destino_local)


def baixar_conjunto_remoto(conjunto_id: int, ator: dict | None = None) -> dict:
    """Baixa uma cópia transitória do dataset administrado pelo servidor."""
    return dict(executar_operacao_arquivo_remota(
        "enterprise.datasets", "obter_conjunto",
        args=(int(conjunto_id), ator or {}),
    ))


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
