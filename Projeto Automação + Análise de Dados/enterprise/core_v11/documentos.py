"""Armazenamento gerenciado, versionado, cifrado e auditável da V11."""
from __future__ import annotations

from io import BytesIO
import hashlib
import json
import mimetypes
from pathlib import Path
from uuid import uuid4

from auth import banco
from auth.banco import conectar
from core.criptografia import carregar_criptografado, obter_chave_mestra, salvar_criptografado
from enterprise.core_v11.common import dump, escopo, json_objeto, registrar_evento, registrar_historico, texto
from enterprise.core_v11.seguranca import exigir_permissao_contextual
from enterprise.privacidade import registrar_leitura_sensivel

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - dependência obrigatória no release completo
    Image = None
    ImageOps = None

_MIMES_PERMITIDOS = {
    "application/pdf", "image/jpeg", "image/png", "image/webp", "image/gif",
    "text/plain", "text/csv", "application/json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
    "application/vnd.oasis.opendocument.text", "application/vnd.oasis.opendocument.spreadsheet",
}
_EXTENSOES_BLOQUEADAS = {".exe", ".dll", ".bat", ".cmd", ".ps1", ".js", ".vbs", ".msi", ".scr", ".com"}
_CLASSIFICACOES = {"Publico", "Interno", "Confidencial", "Restrito"}


def _chave_midia() -> bytes:
    return obter_chave_mestra(
        variavel_ambiente="DATA_INTELLIGENCE_MEDIA_MASTER_KEY",
        caminho_dpapi=banco.STORAGE_DIR / "segredos" / "media_master.dpapi",
        descricao="Data Intelligence V11 media master key",
    )


def _validar_arquivo(nome: str, dados: bytes, mime_type: str | None, *, imagem: bool = False) -> tuple[str, int | None, int | None]:
    if not dados:
        raise ValueError("O arquivo está vazio.")
    limite = 25 * 1024 * 1024 if imagem else 100 * 1024 * 1024
    if len(dados) > limite:
        raise ValueError(f"O arquivo excede o limite de {limite // 1024 // 1024} MB.")
    extensao = Path(nome).suffix.lower()
    if extensao in _EXTENSOES_BLOQUEADAS:
        raise ValueError("Este tipo de arquivo é bloqueado por segurança.")
    detectado = str(mime_type or mimetypes.guess_type(nome)[0] or "application/octet-stream").lower()
    largura = altura = None
    if imagem or detectado.startswith("image/"):
        if Image is None:
            raise RuntimeError("Pillow é necessário para validar imagens.")
        try:
            with Image.open(BytesIO(dados)) as arquivo:
                arquivo.verify()
            with Image.open(BytesIO(dados)) as arquivo:
                largura, altura = arquivo.size
                detectado = Image.MIME.get(arquivo.format, detectado).lower()
        except (OSError, ValueError) as exc:
            raise ValueError("Imagem inválida ou corrompida.") from exc
        if largura * altura > 40_000_000:
            raise ValueError("A imagem excede o limite de resolução.")
    if detectado not in _MIMES_PERMITIDOS:
        raise ValueError(f"Tipo MIME não permitido: {detectado}.")
    return detectado, largura, altura


def _miniatura(dados: bytes, mime_type: str) -> bytes | None:
    if not mime_type.startswith("image/") or Image is None or ImageOps is None:
        return None
    with Image.open(BytesIO(dados)) as arquivo:
        preparada = ImageOps.exif_transpose(arquivo).convert("RGB")
        preparada.thumbnail((320, 320), Image.Resampling.LANCZOS)
        saida = BytesIO(); preparada.save(saida, "JPEG", quality=86, optimize=True)
        return saida.getvalue()


def registrar_midia_bytes(
    dados: bytes,
    nome_original: str,
    ator: dict,
    *,
    modulo: str,
    recurso_tipo: str,
    recurso_id: int,
    finalidade: str = "Anexo",
    titulo: str | None = None,
    classificacao: str = "Interno",
    mime_type: str | None = None,
    midia_id: int | None = None,
    metadados: dict | None = None,
) -> dict:
    empresa_id, filial_id = escopo(ator)
    exigir_permissao_contextual(ator, modulo, "escrever", {"recurso_tipo": recurso_tipo, "recurso_id": int(recurso_id)})
    classificacao = str(classificacao).strip().capitalize().replace("Público", "Publico")
    if classificacao not in _CLASSIFICACOES:
        raise ValueError("Classificação de mídia inválida.")
    nome_original = Path(str(nome_original)).name[:240]
    detectado, largura, altura = _validar_arquivo(nome_original, bytes(dados), mime_type, imagem=finalidade.lower() in {"avatar", "foto"})
    resumo = hashlib.sha256(dados).hexdigest()
    with conectar() as con:
        if midia_id is None:
            cursor = con.execute(
                """INSERT INTO core_midias
                   (empresa_id,filial_id,recurso_tipo,recurso_id,finalidade,titulo,classificacao,criado_por)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    empresa_id, filial_id, recurso_tipo, int(recurso_id), texto(finalidade, minimo=2, maximo=40),
                    texto(titulo or Path(nome_original).stem, minimo=1, maximo=180), classificacao, int(ator["id"]),
                ),
            )
            midia_id = int(cursor.lastrowid); versao = 1
        else:
            atual = con.execute("SELECT * FROM core_midias WHERE id=? AND empresa_id=? AND ativo=1", (int(midia_id), empresa_id)).fetchone()
            if atual is None:
                raise ValueError("Mídia não encontrada.")
            versao = int(atual["versao_atual"]) + 1
    pasta = banco.STORAGE_DIR / "midias_v11" / str(empresa_id) / str(midia_id)
    caminho = pasta / f"v{versao}_{uuid4().hex}.dimedia"
    thumb = pasta / f"v{versao}_{uuid4().hex}.thumb"
    contexto = f"midia:{empresa_id}:{midia_id}:{versao}".encode()
    salvar_criptografado(caminho, dados, _chave_midia(), contexto=contexto)
    miniatura = _miniatura(dados, detectado)
    if miniatura:
        salvar_criptografado(thumb, miniatura, _chave_midia(), contexto=contexto + b":thumb")
    relativo = caminho.relative_to(banco.STORAGE_DIR).as_posix()
    relativo_thumb = thumb.relative_to(banco.STORAGE_DIR).as_posix() if miniatura else None
    try:
        with conectar() as con:
            con.execute(
                """INSERT INTO core_midia_versoes
                   (midia_id,versao,nome_original,mime_type,tamanho_bytes,largura,altura,hash_sha256,
                    caminho_cifrado,miniatura_caminho_cifrado,metadados_json,criado_por)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(midia_id), versao, nome_original, detectado, len(dados), largura, altura, resumo,
                    relativo, relativo_thumb, dump(json_objeto(metadados)), int(ator["id"]),
                ),
            )
            con.execute("UPDATE core_midias SET versao_atual=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (versao, int(midia_id)))
            registrar_historico(
                con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, recurso_tipo="core_midias",
                recurso_id=int(midia_id), acao="Versão adicionada", ator=ator,
                depois={"versao": versao, "mime_type": detectado, "hash_sha256": resumo, "tamanho_bytes": len(dados)},
            )
            registrar_evento(
                con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="midia.versao_criada",
                recurso_tipo=recurso_tipo, recurso_id=int(recurso_id), ator=ator,
                payload={"midia_id": int(midia_id), "versao": versao, "finalidade": finalidade},
            )
    except Exception:
        caminho.unlink(missing_ok=True); thumb.unlink(missing_ok=True)
        raise
    return {"id": int(midia_id), "versao": versao, "mime_type": detectado, "hash_sha256": resumo, "tamanho_bytes": len(dados)}


def registrar_midia(caminho_origem: str | Path, ator: dict, **kwargs) -> dict:
    origem = Path(caminho_origem).expanduser().resolve()
    if not origem.is_file() or origem.is_symlink():
        raise FileNotFoundError("Arquivo de mídia não encontrado ou não permitido.")
    return registrar_midia_bytes(origem.read_bytes(), origem.name, ator, **kwargs)


def obter_midia(midia_id: int, ator: dict, *, modulo: str, versao: int | None = None) -> dict:
    empresa_id, _ = escopo(ator)
    with conectar() as con:
        midia = con.execute("SELECT * FROM core_midias WHERE id=? AND empresa_id=? AND ativo=1", (int(midia_id), empresa_id)).fetchone()
        if midia is None:
            raise ValueError("Mídia não encontrada.")
        exigir_permissao_contextual(
            ator, modulo, "ler", {"recurso_tipo": midia["recurso_tipo"], "recurso_id": int(midia["recurso_id"])},
        )
        alvo = int(versao or midia["versao_atual"])
        item = con.execute("SELECT * FROM core_midia_versoes WHERE midia_id=? AND versao=?", (int(midia_id), alvo)).fetchone()
    if item is None:
        raise ValueError("Versão de mídia não encontrada.")
    return {**dict(midia), "arquivo": {**dict(item), "metadados": json.loads(item["metadados_json"] or "{}")}}


def carregar_midia_bytes(
    midia_id: int,
    ator: dict,
    *,
    modulo: str,
    versao: int | None = None,
    miniatura: bool = False,
) -> tuple[bytes, dict]:
    empresa_id, filial_id = escopo(ator)
    item = obter_midia(midia_id, ator, modulo=modulo, versao=versao)
    arquivo = item["arquivo"]; alvo_versao = int(arquivo["versao"])
    relativo = arquivo["miniatura_caminho_cifrado"] if miniatura else arquivo["caminho_cifrado"]
    if not relativo:
        relativo = arquivo["caminho_cifrado"]; miniatura = False
    caminho = (banco.STORAGE_DIR / str(relativo)).resolve(); storage = banco.STORAGE_DIR.resolve()
    if storage not in caminho.parents or not caminho.is_file():
        raise FileNotFoundError("Arquivo físico da mídia não está disponível.")
    contexto = f"midia:{empresa_id}:{midia_id}:{alvo_versao}".encode() + (b":thumb" if miniatura else b"")
    dados = carregar_criptografado(caminho, _chave_midia(), contexto=contexto)
    if not miniatura and hashlib.sha256(dados).hexdigest() != arquivo["hash_sha256"]:
        raise ValueError("A integridade da mídia não confere.")
    if item["classificacao"] in {"Confidencial", "Restrito"}:
        registrar_leitura_sensivel(
            ator={**ator, "_empresa_id": empresa_id, "_filial_id": filial_id}, modulo=modulo.upper(),
            entidade="core_midias", entidade_id=int(midia_id), campos=["documentos"], finalidade="Leitura de mídia gerenciada",
        )
    return dados, {"mime_type": "image/jpeg" if miniatura else arquivo["mime_type"], "nome": arquivo["nome_original"], "versao": alvo_versao}


def registrar_documento(
    caminho_origem: str | Path,
    dados: dict,
    ator: dict,
    *,
    modulo: str,
    recurso_tipo: str,
    recurso_id: int,
) -> int:
    empresa_id, filial_id = escopo(ator)
    exigir_permissao_contextual(ator, modulo, "escrever", {"recurso_tipo": recurso_tipo, "recurso_id": int(recurso_id)})
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_documentos_v11
               (empresa_id,filial_id,recurso_tipo,recurso_id,titulo,tipo_documento,classificacao,
                validade,status,retencao_ate,criado_por) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                empresa_id, filial_id, recurso_tipo, int(recurso_id),
                texto(dados.get("titulo"), minimo=1, maximo=180), texto(dados.get("tipo_documento"), maximo=80),
                str(dados.get("classificacao") or "Confidencial")[:40], dados.get("validade"), "Processando",
                dados.get("retencao_ate"), int(ator["id"]),
            ),
        )
        documento_id = int(cursor.lastrowid)
    try:
        midia = registrar_midia(
            caminho_origem, ator, modulo=modulo, recurso_tipo="core_documentos_v11", recurso_id=documento_id,
            finalidade="Documento", titulo=str(dados.get("titulo") or "Documento"),
            classificacao=str(dados.get("classificacao") or "Confidencial"),
        )
        with conectar() as con:
            con.execute(
                """INSERT INTO core_documento_versoes(documento_id,versao,midia_id,metadados_json,criado_por)
                   VALUES (?,?,?,?,?)""",
                (documento_id, 1, int(midia["id"]), dump(json_objeto(dados.get("metadados"))), int(ator["id"])),
            )
            con.execute("UPDATE core_documentos_v11 SET status='Ativo' WHERE id=?", (documento_id,))
            registrar_evento(
                con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="documento.criado",
                recurso_tipo=recurso_tipo, recurso_id=int(recurso_id), ator=ator,
                payload={"documento_id": documento_id, "midia_id": midia["id"]},
            )
        return documento_id
    except Exception:
        with conectar() as con:
            con.execute("UPDATE core_documentos_v11 SET status='Falhou' WHERE id=?", (documento_id,))
        raise


def listar_documentos(recurso_tipo: str, recurso_id: int, ator: dict, *, modulo: str) -> list[dict]:
    empresa_id, _ = escopo(ator)
    exigir_permissao_contextual(ator, modulo, "ler", {"recurso_tipo": recurso_tipo, "recurso_id": int(recurso_id)})
    with conectar() as con:
        rows = con.execute(
            """SELECT d.*,v.midia_id,v.ocr_texto,mv.mime_type,mv.tamanho_bytes,mv.hash_sha256
               FROM core_documentos_v11 d
               LEFT JOIN core_documento_versoes v ON v.documento_id=d.id AND v.versao=d.versao_atual
               LEFT JOIN core_midia_versoes mv ON mv.midia_id=v.midia_id AND mv.versao=d.versao_atual
               WHERE d.empresa_id=? AND d.recurso_tipo=? AND d.recurso_id=? ORDER BY d.id DESC""",
            (empresa_id, recurso_tipo, int(recurso_id)),
        ).fetchall()
    return [dict(x) for x in rows]


def adicionar_versao_documento(documento_id: int, caminho_origem: str | Path, ator: dict, *, modulo: str) -> dict:
    empresa_id, filial_id = escopo(ator)
    with conectar() as con:
        documento = con.execute("SELECT * FROM core_documentos_v11 WHERE id=? AND empresa_id=?", (int(documento_id), empresa_id)).fetchone()
    if documento is None:
        raise ValueError("Documento não encontrado.")
    exigir_permissao_contextual(
        ator, modulo, "escrever", {"recurso_tipo": documento["recurso_tipo"], "recurso_id": int(documento["recurso_id"])},
    )
    nova_versao = int(documento["versao_atual"]) + 1
    midia = registrar_midia(
        caminho_origem, ator, modulo=modulo, recurso_tipo="core_documentos_v11", recurso_id=int(documento_id),
        finalidade="Documento", titulo=documento["titulo"], classificacao=documento["classificacao"],
    )
    with conectar() as con:
        con.execute(
            """INSERT INTO core_documento_versoes(documento_id,versao,midia_id,metadados_json,criado_por)
               VALUES (?,?,?,?,?)""", (int(documento_id), nova_versao, int(midia["id"]), "{}", int(ator["id"])),
        )
        con.execute(
            "UPDATE core_documentos_v11 SET versao_atual=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (nova_versao, int(documento_id)),
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="documento.versao_criada",
            recurso_tipo=documento["recurso_tipo"], recurso_id=int(documento["recurso_id"]), ator=ator,
            payload={"documento_id": int(documento_id), "versao": nova_versao},
        )
    return {"documento_id": int(documento_id), "versao": nova_versao, "midia_id": int(midia["id"])}


def solicitar_assinatura(
    documento_id: int,
    ator: dict,
    *,
    modulo: str,
    pessoa_id: int | None = None,
    usuario_id: int | None = None,
    papel: str = "Signatário",
    provedor: str = "Interno",
    tipo_assinatura: str = "Simples",
    nivel_garantia: str | None = None,
) -> int:
    empresa_id, filial_id = escopo(ator)
    tipo_assinatura = str(tipo_assinatura or "Simples").strip().capitalize()
    if tipo_assinatura not in {"Simples", "Avançada", "Qualificada"}:
        raise ValueError("Tipo de assinatura deve ser Simples, Avançada ou Qualificada.")
    if tipo_assinatura == "Qualificada" and str(provedor or "").strip().lower() in {"", "interno"}:
        raise ValueError("Assinatura qualificada exige provedor/certificado ICP-Brasil homologado.")
    with conectar() as con:
        documento = con.execute("SELECT * FROM core_documentos_v11 WHERE id=? AND empresa_id=?", (int(documento_id), empresa_id)).fetchone()
        if documento is None:
            raise ValueError("Documento não encontrado.")
        exigir_permissao_contextual(
            ator, modulo, "escrever", {"recurso_tipo": documento["recurso_tipo"], "recurso_id": int(documento["recurso_id"])},
        )
        if pessoa_id is None and usuario_id is None:
            raise ValueError("Informe a pessoa ou o usuário signatário.")
        cursor = con.execute(
            """INSERT INTO core_documento_assinaturas
               (documento_id,versao,pessoa_id,usuario_id,papel,provedor,tipo_assinatura,nivel_garantia)
               VALUES (?,?,?,?,?,?,?,?)""",
            (int(documento_id), int(documento["versao_atual"]), pessoa_id, usuario_id,
             texto(papel, maximo=80), texto(provedor, maximo=80), tipo_assinatura,
             texto(nivel_garantia, maximo=120) or None),
        )
        assinatura_id = int(cursor.lastrowid)
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="documento.assinatura_solicitada",
            recurso_tipo="core_documentos_v11", recurso_id=int(documento_id), ator=ator,
            payload={"assinatura_id": assinatura_id, "pessoa_id": pessoa_id, "usuario_id": usuario_id,
                     "tipo_assinatura": tipo_assinatura, "provedor": provedor},
        )
    return assinatura_id


def registrar_evidencia_assinatura(
    assinatura_id: int,
    evidencia_hash: str,
    evidencia: dict,
    ator: dict,
    *,
    modulo: str,
) -> None:
    empresa_id, filial_id = escopo(ator)
    resumo = str(evidencia_hash or "").strip().lower()
    if len(resumo) != 64 or any(ch not in "0123456789abcdef" for ch in resumo):
        raise ValueError("A evidência exige hash SHA-256 hexadecimal.")
    with conectar() as con:
        assinatura = con.execute(
            """SELECT a.*,d.recurso_tipo,d.recurso_id FROM core_documento_assinaturas a
               JOIN core_documentos_v11 d ON d.id=a.documento_id
               WHERE a.id=? AND d.empresa_id=?""", (int(assinatura_id), empresa_id),
        ).fetchone()
        if assinatura is None:
            raise ValueError("Solicitação de assinatura não encontrada.")
        exigir_permissao_contextual(
            ator, modulo, "escrever", {"recurso_tipo": assinatura["recurso_tipo"], "recurso_id": int(assinatura["recurso_id"])},
        )
        if assinatura["status"] == "Assinada":
            raise ValueError("A assinatura já possui evidência final.")
        con.execute(
            """UPDATE core_documento_assinaturas SET evidencia_hash=?,evidencia_json=?,status='Assinada',
               assinado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (resumo, dump(json_objeto(evidencia, campo="Evidência", limite=128 * 1024)), int(assinatura_id)),
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="documento.assinatura_evidenciada",
            recurso_tipo="core_documentos_v11", recurso_id=int(assinatura["documento_id"]), ator=ator,
            payload={"assinatura_id": int(assinatura_id), "tipo_assinatura": assinatura["tipo_assinatura"], "evidencia_hash": resumo},
        )


def registrar_resultado_ocr(documento_id: int, versao: int, texto_extraido: str, ator: dict, *, modulo: str) -> None:
    empresa_id, filial_id = escopo(ator)
    exigir_permissao_contextual(ator, modulo, "escrever", {"recurso_tipo": "core_documentos_v11", "recurso_id": int(documento_id)})
    conteudo = texto(texto_extraido, maximo=2_000_000, campo="Texto OCR")
    with conectar() as con:
        cursor = con.execute(
            """UPDATE core_documento_versoes SET ocr_texto=? WHERE documento_id=? AND versao=?
               AND EXISTS(SELECT 1 FROM core_documentos_v11 d WHERE d.id=core_documento_versoes.documento_id AND d.empresa_id=?)""",
            (conteudo, int(documento_id), int(versao), empresa_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Versão documental não encontrada.")
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, recurso_tipo="core_documentos_v11",
            recurso_id=int(documento_id), acao="OCR registrado", ator=ator, depois={"versao": int(versao), "caracteres": len(conteudo)},
        )


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "adicionar_versao_documento", "carregar_midia_bytes", "listar_documentos", "obter_midia",
    "registrar_documento", "registrar_evidencia_assinatura", "registrar_midia", "registrar_midia_bytes", "registrar_resultado_ocr",
    "solicitar_assinatura",
)
