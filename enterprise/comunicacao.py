"""Correio corporativo interno da plataforma.

Mensagens permanecem no escopo da empresa, usam exclusão individual e mantêm
anexos verificados por hash. O serviço não depende de Outlook/Gmail: integrações
externas podem consumir esta caixa posteriormente sem alterar a interface.
"""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
from pathlib import Path
from uuid import uuid4

from auth import banco
from auth.banco import conectar, registrar_auditoria
from enterprise.contexto import obter_escopo_ator

MAX_ANEXO = 25 * 1024 * 1024
MAX_TOTAL_ANEXOS = 50 * 1024 * 1024


def _hash(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def listar_contatos(ator: dict) -> list[dict]:
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT DISTINCT u.id,u.nome,u.email_corporativo,u.perfil_acesso
            FROM usuarios u
            JOIN usuarios_empresas ue ON ue.usuario_id=u.id
            WHERE ue.empresa_id=? AND ue.ativo=1 AND u.ativo=1
              AND u.email_corporativo IS NOT NULL
            ORDER BY u.nome COLLATE NOCASE
            """,
            (empresa_id,),
        ).fetchall()
    return [dict(item) for item in registros]


def _resolver_destinatarios(conexao, empresa_id: int, valores) -> list[int]:
    entradas = valores if isinstance(valores, (list, tuple, set)) else [valores]
    ids: list[int] = []
    for valor in entradas:
        if valor in (None, ""):
            continue
        if isinstance(valor, int) or str(valor).strip().isdigit():
            filtro, parametro = "u.id=?", int(valor)
        else:
            filtro, parametro = "u.email_corporativo=? COLLATE NOCASE", str(valor).strip()
        registro = conexao.execute(
            f"""
            SELECT u.id FROM usuarios u
            JOIN usuarios_empresas ue ON ue.usuario_id=u.id
            WHERE {filtro} AND ue.empresa_id=? AND ue.ativo=1 AND u.ativo=1
            """,
            (parametro, empresa_id),
        ).fetchone()
        if registro is None:
            raise ValueError(f"Destinatário corporativo não encontrado: {valor}")
        if int(registro["id"]) not in ids:
            ids.append(int(registro["id"]))
    return ids


def enviar_mensagem(dados: dict, ator: dict, *, rascunho: bool = False) -> int:
    empresa_id, filial_id = obter_escopo_ator(ator)
    assunto = " ".join(str(dados.get("assunto") or "").split())[:240]
    corpo = str(dados.get("corpo") or "").strip()[:100_000]
    if not assunto or not corpo:
        raise ValueError("Informe o assunto e o conteúdo da mensagem.")
    anexos = [Path(item).expanduser().resolve() for item in dados.get("anexos", [])]
    total = 0
    for anexo in anexos:
        if not anexo.is_file():
            raise FileNotFoundError(f"Anexo não encontrado: {anexo.name}")
        tamanho = anexo.stat().st_size
        if tamanho > MAX_ANEXO:
            raise ValueError(f"O anexo {anexo.name} excede 25 MB.")
        total += tamanho
    if total > MAX_TOTAL_ANEXOS:
        raise ValueError("Os anexos da mensagem excedem 50 MB.")

    status = "Rascunho" if rascunho else "Enviada"
    with conectar() as conexao:
        para = _resolver_destinatarios(conexao, empresa_id, dados.get("para", []))
        cc = _resolver_destinatarios(conexao, empresa_id, dados.get("cc", []))
        cco = _resolver_destinatarios(conexao, empresa_id, dados.get("cco", []))
        if not rascunho and not para:
            raise ValueError("Informe pelo menos um destinatário.")
        resposta_de = int(dados["resposta_de_id"]) if dados.get("resposta_de_id") else None
        conversa = str(dados.get("conversa_id") or uuid4())
        cursor = conexao.execute(
            """
            INSERT INTO mensagens (
                empresa_id,filial_id,remetente_id,assunto,corpo,prioridade,
                status,resposta_de_id,conversa_id,enviada_em
            ) VALUES (?,?,?,?,?,?,?,?,?,CASE WHEN ?='Enviada' THEN CURRENT_TIMESTAMP END)
            """,
            (
                empresa_id, filial_id, int(ator["id"]), assunto, corpo,
                str(dados.get("prioridade") or "Normal"), status,
                resposta_de, conversa, status,
            ),
        )
        mensagem_id = int(cursor.lastrowid)
        for tipo, usuarios in (("Para", para), ("Cc", cc), ("Cco", cco)):
            for usuario_id in usuarios:
                conexao.execute(
                    "INSERT INTO mensagem_destinatarios (mensagem_id,usuario_id,tipo) VALUES (?,?,?)",
                    (mensagem_id, usuario_id, tipo),
                )

        pasta = banco.STORAGE_DIR / "correio" / str(empresa_id) / str(mensagem_id)
        for origem in anexos:
            pasta.mkdir(parents=True, exist_ok=True)
            nome = f"{uuid4().hex}_{origem.name}"
            destino = pasta / nome
            shutil.copy2(origem, destino)
            relativo = destino.relative_to(banco.STORAGE_DIR).as_posix()
            conexao.execute(
                """
                INSERT INTO mensagem_anexos (
                    mensagem_id,nome_original,caminho_relativo,tamanho_bytes,
                    hash_sha256,mime_type
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    mensagem_id, origem.name, relativo, origem.stat().st_size,
                    _hash(origem), mimetypes.guess_type(origem.name)[0],
                ),
            )
        if status == "Enviada":
            for usuario_id in set(para + cc + cco):
                conexao.execute(
                    """
                    INSERT INTO notificacoes (
                        usuario_id,empresa_id,filial_id,modulo,titulo,mensagem,
                        nivel,recurso_tipo,recurso_id
                    ) VALUES (?,?,?,'comunicacao','Nova mensagem corporativa',?,
                              'info','mensagens',?)
                    """,
                    (usuario_id, empresa_id, filial_id, assunto, mensagem_id),
                )
    registrar_auditoria(
        "mensagem_salva" if rascunho else "mensagem_enviada",
        usuario_id=int(ator["id"]), empresa_id=empresa_id, filial_id=filial_id,
        modulo="comunicacao", entidade="mensagens", entidade_id=mensagem_id,
    )
    return mensagem_id


def listar_mensagens(ator: dict, caixa: str = "entrada", *, termo="", limite=300) -> list[dict]:
    empresa_id, _ = obter_escopo_ator(ator)
    usuario_id = int(ator["id"])
    busca = f"%{str(termo).strip()}%"
    parametros: list[object] = [empresa_id]
    if caixa == "enviadas":
        juncao = ""
        condicao = "m.remetente_id=? AND m.status='Enviada'"
        parametros.append(usuario_id)
    elif caixa == "rascunhos":
        juncao = ""
        condicao = "m.remetente_id=? AND m.status='Rascunho'"
        parametros.append(usuario_id)
    else:
        juncao = "JOIN mensagem_destinatarios md ON md.mensagem_id=m.id"
        estado = {
            "arquivadas": "md.arquivada=1 AND md.excluida=0",
            "lixeira": "md.excluida=1",
        }.get(caixa, "md.arquivada=0 AND md.excluida=0")
        condicao = f"md.usuario_id=? AND {estado} AND m.status='Enviada'"
        parametros.append(usuario_id)
    parametros.extend((busca, busca, max(1, min(int(limite), 1000))))
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT DISTINCT m.*,u.nome AS remetente_nome,u.email_corporativo AS remetente_email,
                   COALESCE((SELECT md2.lida FROM mensagem_destinatarios md2
                             WHERE md2.mensagem_id=m.id AND md2.usuario_id=? LIMIT 1),1) AS lida,
                   (SELECT COUNT(*) FROM mensagem_anexos a WHERE a.mensagem_id=m.id) AS anexos
            FROM mensagens m
            {juncao}
            JOIN usuarios u ON u.id=m.remetente_id
            WHERE m.empresa_id=? AND {condicao}
              AND (m.assunto LIKE ? OR m.corpo LIKE ?)
            ORDER BY COALESCE(m.enviada_em,m.criado_em) DESC
            LIMIT ?
            """,
            (usuario_id, *parametros),
        ).fetchall()
    return [dict(item) for item in registros]


def obter_mensagem(mensagem_id: int, ator: dict) -> dict:
    empresa_id, _ = obter_escopo_ator(ator)
    usuario_id = int(ator["id"])
    with conectar() as conexao:
        mensagem = conexao.execute(
            """
            SELECT m.*,u.nome remetente_nome,u.email_corporativo remetente_email
            FROM mensagens m JOIN usuarios u ON u.id=m.remetente_id
            WHERE m.id=? AND m.empresa_id=? AND (
                m.remetente_id=? OR EXISTS (
                    SELECT 1 FROM mensagem_destinatarios md
                    WHERE md.mensagem_id=m.id AND md.usuario_id=?
                )
            )
            """,
            (int(mensagem_id), empresa_id, usuario_id, usuario_id),
        ).fetchone()
        if mensagem is None:
            raise PermissionError("Mensagem não disponível para este usuário.")
        conexao.execute(
            "UPDATE mensagem_destinatarios SET lida=1,lida_em=CURRENT_TIMESTAMP "
            "WHERE mensagem_id=? AND usuario_id=?",
            (int(mensagem_id), usuario_id),
        )
        destinatarios = conexao.execute(
            """
            SELECT md.tipo,u.id,u.nome,u.email_corporativo
            FROM mensagem_destinatarios md JOIN usuarios u ON u.id=md.usuario_id
            WHERE md.mensagem_id=? ORDER BY md.tipo,u.nome
            """,
            (int(mensagem_id),),
        ).fetchall()
        anexos = conexao.execute(
            "SELECT id,nome_original,caminho_relativo,tamanho_bytes,hash_sha256,mime_type "
            "FROM mensagem_anexos WHERE mensagem_id=? ORDER BY id",
            (int(mensagem_id),),
        ).fetchall()
    resultado = dict(mensagem)
    resultado["destinatarios"] = [dict(item) for item in destinatarios]
    resultado["anexos"] = [dict(item) for item in anexos]
    return resultado


def alterar_estado_mensagem(mensagem_id: int, ator: dict, *, arquivar=None, excluir=None) -> None:
    empresa_id, _ = obter_escopo_ator(ator)
    usuario_id = int(ator["id"])
    campos, valores = [], []
    if arquivar is not None:
        campos.append("arquivada=?")
        valores.append(int(bool(arquivar)))
    if excluir is not None:
        campos.append("excluida=?")
        valores.append(int(bool(excluir)))
    if not campos:
        return
    with conectar() as conexao:
        existe = conexao.execute(
            """
            SELECT 1 FROM mensagem_destinatarios md JOIN mensagens m ON m.id=md.mensagem_id
            WHERE md.mensagem_id=? AND md.usuario_id=? AND m.empresa_id=?
            """,
            (int(mensagem_id), usuario_id, empresa_id),
        ).fetchone()
        if existe is None:
            raise PermissionError("Somente o destinatário pode alterar esta caixa.")
        conexao.execute(
            f"UPDATE mensagem_destinatarios SET {', '.join(campos)} WHERE mensagem_id=? AND usuario_id=?",
            (*valores, int(mensagem_id), usuario_id),
        )
