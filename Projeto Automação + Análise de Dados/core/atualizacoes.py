"""Atualizações assinadas, preparadas fora do processo e com rollback."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from auth import banco
from core.versao import VERSAO_PLATAFORMA

_MAX_MANIFESTO = 1024 * 1024
_MAX_PACOTE = 2 * 1024 * 1024 * 1024
_VERSAO_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}$")


class AtualizacaoInvalida(ValueError):
    pass


class _SemRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _url_publica_https(url: str) -> str:
    texto = str(url or "").strip()
    parsed = urlparse(texto)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise AtualizacaoInvalida("Atualizações exigem URL HTTPS sem credenciais embutidas.")
    if parsed.port not in {None, 443}:
        raise AtualizacaoInvalida("O servidor de atualizações deve usar a porta 443.")
    try:
        ips = {x[4][0] for x in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise AtualizacaoInvalida("Servidor de atualizações não resolvido.") from exc
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise AtualizacaoInvalida("Servidor de atualizações não pode usar rede privada/reservada.")
    return texto


def _chave_publica() -> Ed25519PublicKey:
    texto = str(os.environ.get("DATA_INTELLIGENCE_UPDATE_PUBLIC_KEY", "")).strip()
    if not texto:
        raise AtualizacaoInvalida("Chave pública de atualização não configurada.")
    try:
        bruto = base64.b64decode(texto, validate=True)
        if len(bruto) != 32:
            raise ValueError
        return Ed25519PublicKey.from_public_bytes(bruto)
    except (ValueError, TypeError) as exc:
        raise AtualizacaoInvalida("Chave pública Ed25519 inválida.") from exc


def _baixar_json(url: str) -> dict:
    with build_opener(_SemRedirect).open(Request(_url_publica_https(url)), timeout=15) as resposta:
        tamanho = int(resposta.headers.get("Content-Length") or 0)
        if tamanho > _MAX_MANIFESTO:
            raise AtualizacaoInvalida("Manifesto de atualização acima do limite.")
        dados = resposta.read(_MAX_MANIFESTO + 1)
    if len(dados) > _MAX_MANIFESTO:
        raise AtualizacaoInvalida("Manifesto de atualização acima do limite.")
    payload = json.loads(dados.decode("utf-8"))
    if not isinstance(payload, dict):
        raise AtualizacaoInvalida("Manifesto deve ser um objeto JSON.")
    return payload


def validar_manifesto(manifesto: dict) -> dict:
    campos = {"versao", "url", "sha256", "tamanho_bytes", "assinatura"}
    if not campos.issubset(manifesto):
        raise AtualizacaoInvalida("Manifesto de atualização incompleto.")
    assinatura_texto = str(manifesto["assinatura"])
    assinado = {k: manifesto[k] for k in sorted(manifesto) if k != "assinatura"}
    canonico = json.dumps(assinado, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    try:
        _chave_publica().verify(base64.b64decode(assinatura_texto, validate=True), canonico)
    except Exception as exc:
        raise AtualizacaoInvalida("Assinatura Ed25519 do manifesto inválida.") from exc
    sha = str(manifesto["sha256"]).lower()
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise AtualizacaoInvalida("SHA-256 do pacote inválido.")
    tamanho = int(manifesto["tamanho_bytes"])
    if tamanho <= 0 or tamanho > _MAX_PACOTE:
        raise AtualizacaoInvalida("Tamanho de pacote inválido.")
    versao = str(manifesto["versao"]).strip()
    if not _VERSAO_RE.fullmatch(versao):
        raise AtualizacaoInvalida("Versão do pacote inválida.")
    return {
        **manifesto,
        "versao": versao,
        "url": _url_publica_https(str(manifesto["url"])),
        "sha256": sha,
        "tamanho_bytes": tamanho,
    }


def _partes_versao(valor: str) -> tuple[int, int, int, int]:
    partes = [int(item) for item in str(valor).split(".")]
    return tuple((partes + [0, 0, 0, 0])[:4])  # type: ignore[return-value]


def _validar_zip(caminho: Path) -> None:
    with zipfile.ZipFile(caminho) as zf:
        for membro in zf.infolist():
            partes = Path(membro.filename).parts
            if Path(membro.filename).is_absolute() or ".." in partes:
                raise AtualizacaoInvalida("Pacote de atualização contém caminho inseguro.")
            if membro.is_dir():
                continue
            if (membro.external_attr >> 16) & 0o170000 == 0o120000:
                raise AtualizacaoInvalida("Pacote de atualização contém link simbólico.")


def preparar_atualizacao(manifesto_url: str) -> dict:
    manifesto = validar_manifesto(_baixar_json(manifesto_url))
    permite_downgrade = str(os.environ.get("DATA_INTELLIGENCE_ALLOW_SIGNED_DOWNGRADE", "")).strip() == "1"
    if not permite_downgrade and _partes_versao(manifesto["versao"]) <= _partes_versao(VERSAO_PLATAFORMA):
        raise AtualizacaoInvalida(
            f"A atualização {manifesto['versao']} não é superior à versão instalada {VERSAO_PLATAFORMA}."
        )
    pasta = banco.STORAGE_DIR / "updates" / "staging"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"DataIntelligence-{str(manifesto['versao'])[:40]}.zip"
    temporario = destino.with_suffix(".part")
    digest = hashlib.sha256()
    recebidos = 0
    try:
        with build_opener(_SemRedirect).open(Request(manifesto["url"]), timeout=60) as resposta, temporario.open("xb") as saida:
            while bloco := resposta.read(1024 * 1024):
                recebidos += len(bloco)
                if recebidos > manifesto["tamanho_bytes"] or recebidos > _MAX_PACOTE:
                    raise AtualizacaoInvalida("Pacote excedeu o tamanho assinado.")
                digest.update(bloco)
                saida.write(bloco)
        if recebidos != manifesto["tamanho_bytes"] or digest.hexdigest() != manifesto["sha256"]:
            raise AtualizacaoInvalida("Tamanho ou SHA-256 do pacote não confere.")
        _validar_zip(temporario)
        os.replace(temporario, destino)
    except Exception:
        temporario.unlink(missing_ok=True)
        raise
    return {"versao": str(manifesto["versao"]), "pacote": str(destino), "sha256": manifesto["sha256"], "pronto": True}


def iniciar_helper_rollback(
    helper_exe: str | Path,
    pacote: str | Path,
    pasta_instalada: str | Path,
    comando_inicio: list[str],
    *,
    health_url: str,
) -> int:
    """Copia o helper para fora da instalação e o inicia de forma desacoplada."""
    helper = Path(helper_exe).resolve(); pacote = Path(pacote).resolve(); atual = Path(pasta_instalada).resolve()
    if not helper.is_file() or not pacote.is_file() or not atual.is_dir():
        raise FileNotFoundError("Helper, pacote ou instalação não encontrados.")
    temp = Path(tempfile.mkdtemp(prefix="dataintelligence_update_")) / helper.name
    shutil.copy2(helper, temp)
    cmd = [
        str(temp), "--current", str(atual), "--package", str(pacote),
        "--health-url", str(health_url), "--start-json", json.dumps(comando_inicio),
    ]
    processo = subprocess.Popen(cmd, close_fds=True, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    return int(processo.pid)


__all__ = ("AtualizacaoInvalida", "iniciar_helper_rollback", "preparar_atualizacao", "validar_manifesto")
