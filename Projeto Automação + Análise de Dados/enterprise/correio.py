"""Correio corporativo interno da plataforma.

O correio é intencionalmente interno: os endereços corporativos identificam
usuários da organização e as mensagens permanecem no banco/armazenamento da
plataforma. Integrações SMTP/Outlook podem ser acrescentadas como gateways,
sem alterar o modelo interno.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Iterable

from auth import banco as banco_auth
from auth.banco import conectar
from enterprise.contexto import obter_escopo_ator


def _remoto() -> bool:
    from core.nodo import usa_servidor_remoto
    return usa_servidor_remoto()


def _texto(valor, limite: int) -> str:
    return str(valor or "").strip()[:limite]


def _emails(valores: Iterable[str] | str | None) -> list[str]:
    if valores is None:
        return []
    if isinstance(valores, str):
        valores = valores.replace(";", ",").split(",")
    saida: list[str] = []
    for valor in valores:
        email = str(valor or "").strip().lower()
        if email and email not in saida:
            saida.append(email)
    return saida


def listar_contatos(ator: dict, pesquisa: str = "") -> list[dict]:
    if _remoto():
        from enterprise.servidor_cliente import listar_contatos_remoto
        return listar_contatos_remoto(pesquisa)
    empresa_id, _ = obter_escopo_ator(ator)
    termo = f"%{str(pesquisa or '').strip()}%"
    with conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT DISTINCT u.id, u.nome, u.usuario, u.email_corporativo,
                   u.perfil_acesso
            FROM usuarios u
            JOIN usuarios_empresas ue ON ue.usuario_id=u.id
            WHERE ue.empresa_id=? AND ue.ativo=1 AND u.ativo=1
              AND u.email_corporativo IS NOT NULL
              AND (u.nome LIKE ? OR u.email_corporativo LIKE ? OR u.usuario LIKE ?)
            ORDER BY u.nome COLLATE NOCASE
            LIMIT 300
            """,
            (empresa_id, termo, termo, termo),
        ).fetchall()
    return [dict(x) for x in linhas]


def _resolver_destinatarios(conexao, empresa_id: int, emails: list[str]) -> list[dict]:
    if not emails:
        return []
    marcadores = ",".join("?" for _ in emails)
    linhas = conexao.execute(
        f"""
        SELECT DISTINCT u.id, LOWER(u.email_corporativo) email
        FROM usuarios u
        JOIN usuarios_empresas ue ON ue.usuario_id=u.id
        WHERE ue.empresa_id=? AND ue.ativo=1 AND u.ativo=1
          AND LOWER(u.email_corporativo) IN ({marcadores})
        """,
        (empresa_id, *emails),
    ).fetchall()
    por_email = {str(x["email"]): int(x["id"]) for x in linhas}
    faltantes = [email for email in emails if email not in por_email]
    if faltantes:
        raise ValueError(
            "Destinatário(s) não encontrado(s) no diretório corporativo: "
            + ", ".join(faltantes[:8])
        )
    return [{"email": email, "id": por_email[email]} for email in emails]


def _hash_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _copiar_anexos(conexao, mensagem_id: int, anexos: Iterable[str | Path] | None) -> list[Path]:
    if not anexos:
        return []
    pasta = banco_auth.STORAGE_DIR / "correio" / str(mensagem_id)
    pasta.mkdir(parents=True, exist_ok=True)
    criados: list[Path] = []
    for origem_bruta in anexos:
        origem = Path(origem_bruta).expanduser().resolve()
        if not origem.is_file():
            raise ValueError(f"Anexo não encontrado: {origem.name}")
        if origem.stat().st_size > 25 * 1024 * 1024:
            raise ValueError(f"O anexo {origem.name} excede 25 MB.")
        nome = origem.name[:180]
        destino = pasta / nome
        contador = 2
        while destino.exists():
            destino = pasta / f"{origem.stem[:140]} ({contador}){origem.suffix[:20]}"
            contador += 1
        shutil.copy2(origem, destino)
        criados.append(destino)
        digest = _hash_arquivo(destino)
        relativo = destino.relative_to(banco_auth.STORAGE_DIR).as_posix()
        conexao.execute(
            """INSERT INTO correio_anexos
               (mensagem_id,nome,arquivo_relativo,tamanho_bytes,sha256)
               VALUES (?,?,?,?,?)""",
            (mensagem_id, destino.name, relativo, destino.stat().st_size, digest),
        )
    return criados


def enviar_mensagem(
    assunto: str,
    corpo: str,
    para: Iterable[str] | str,
    ator: dict,
    *,
    cc: Iterable[str] | str | None = None,
    cco: Iterable[str] | str | None = None,
    modulo_origem: str | None = None,
    anexos: Iterable[str | Path] | None = None,
    resposta_de_id: int | None = None,
) -> int:
    if _remoto():
        from enterprise.servidor_cliente import enviar_mensagem_remota
        return enviar_mensagem_remota(assunto=assunto, corpo=corpo, para=para, cc=cc, cco=cco, modulo_origem=modulo_origem, anexos=anexos, resposta_de_id=resposta_de_id)
    assunto = _texto(assunto, 240)
    corpo = str(corpo or "").strip()
    if not assunto:
        raise ValueError("Informe o assunto da mensagem.")
    if not corpo:
        raise ValueError("Escreva a mensagem antes de enviar.")
    para_e = _emails(para)
    cc_e = _emails(cc)
    cco_e = _emails(cco)
    if not para_e:
        raise ValueError("Informe pelo menos um destinatário.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    anexos_criados: list[Path] = []
    mensagem_id: int | None = None
    try:
        with conectar() as conexao:
            grupos = {
                "PARA": _resolver_destinatarios(conexao, empresa_id, para_e),
                "CC": _resolver_destinatarios(conexao, empresa_id, cc_e),
                "CCO": _resolver_destinatarios(conexao, empresa_id, cco_e),
            }
            cursor = conexao.execute(
                """INSERT INTO correio_mensagens
                   (empresa_id,filial_id,remetente_id,assunto,corpo,modulo_origem,
                    resposta_de_id,rascunho,enviado_em)
                   VALUES (?,?,?,?,?,?,?,0,CURRENT_TIMESTAMP)""",
                (
                    empresa_id,
                    filial_id,
                    int(ator["id"]),
                    assunto,
                    corpo,
                    _texto(modulo_origem, 60) or None,
                    int(resposta_de_id) if resposta_de_id else None,
                ),
            )
            mensagem_id = int(cursor.lastrowid)
            vistos: set[tuple[int, str]] = set()
            for tipo, pessoas in grupos.items():
                for pessoa in pessoas:
                    chave = (int(pessoa["id"]), tipo)
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    conexao.execute(
                        "INSERT OR IGNORE INTO correio_destinatarios (mensagem_id,usuario_id,tipo) VALUES (?,?,?)",
                        (mensagem_id, int(pessoa["id"]), tipo),
                    )
            conexao.execute(
                """INSERT INTO atividades
                   (usuario_id,empresa_id,filial_id,modulo,acao,descricao,recurso_tipo,recurso_id)
                   VALUES (?,?,?,?, 'email_enviado', ?, 'correio_mensagens', ?)""",
                (
                    int(ator["id"]), empresa_id, filial_id,
                    _texto(modulo_origem, 40) or "core",
                    f"Mensagem interna: {assunto}", mensagem_id,
                ),
            )
            # Anexos são a última etapa física. Se o commit falhar, o bloco
            # externo remove tudo que foi copiado, evitando arquivos órfãos.
            anexos_criados = _copiar_anexos(conexao, mensagem_id, anexos)
    except Exception:
        for arquivo in anexos_criados:
            arquivo.unlink(missing_ok=True)
        if mensagem_id is not None:
            pasta = banco_auth.STORAGE_DIR / "correio" / str(mensagem_id)
            try:
                pasta.rmdir()
            except OSError:
                pass
        raise
    return int(mensagem_id)


def salvar_rascunho(
    assunto: str,
    corpo: str,
    ator: dict,
    *,
    modulo_origem: str | None = None,
) -> int:
    if _remoto():
        from enterprise.servidor_cliente import salvar_rascunho_remoto
        return salvar_rascunho_remoto(assunto, corpo, modulo_origem)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        return int(
            conexao.execute(
                """INSERT INTO correio_mensagens
                   (empresa_id,filial_id,remetente_id,assunto,corpo,modulo_origem,rascunho)
                   VALUES (?,?,?,?,?,?,1)""",
                (
                    empresa_id, filial_id, int(ator["id"]),
                    _texto(assunto, 240) or "(sem assunto)",
                    str(corpo or ""), _texto(modulo_origem, 60) or None,
                ),
            ).lastrowid
        )


def listar_caixa(
    ator: dict,
    caixa: str = "entrada",
    *,
    pesquisa: str = "",
    limite: int = 300,
) -> list[dict]:
    if _remoto():
        from enterprise.servidor_cliente import listar_caixa_remoto
        return listar_caixa_remoto(caixa, pesquisa)
    empresa_id, _ = obter_escopo_ator(ator)
    caixa = str(caixa or "entrada").strip().lower()
    termo = f"%{str(pesquisa or '').strip()}%"
    uid = int(ator["id"])
    limite = max(1, min(int(limite), 1000))
    with conectar() as conexao:
        if caixa == "enviados":
            sql = """
                SELECT m.id,m.assunto,m.corpo,m.modulo_origem,m.enviado_em,m.criado_em,
                       u.nome remetente_nome,u.email_corporativo remetente_email,
                       1 lida,0 estrela
                FROM correio_mensagens m JOIN usuarios u ON u.id=m.remetente_id
                WHERE m.empresa_id=? AND m.remetente_id=? AND m.rascunho=0
                  AND m.excluida_remetente=0
                  AND (m.assunto LIKE ? OR m.corpo LIKE ?)
                ORDER BY m.id DESC LIMIT ?
            """
            params=(empresa_id,uid,termo,termo,limite)
        elif caixa == "rascunhos":
            sql = """
                SELECT m.id,m.assunto,m.corpo,m.modulo_origem,m.enviado_em,m.criado_em,
                       u.nome remetente_nome,u.email_corporativo remetente_email,
                       1 lida,0 estrela
                FROM correio_mensagens m JOIN usuarios u ON u.id=m.remetente_id
                WHERE m.empresa_id=? AND m.remetente_id=? AND m.rascunho=1
                  AND m.excluida_remetente=0
                  AND (m.assunto LIKE ? OR m.corpo LIKE ?)
                ORDER BY m.id DESC LIMIT ?
            """
            params=(empresa_id,uid,termo,termo,limite)
        else:
            arquivada = 1 if caixa == "arquivados" else 0
            excluida = 1 if caixa == "lixeira" else 0
            sql = """
                SELECT m.id,m.assunto,m.corpo,m.modulo_origem,m.enviado_em,m.criado_em,
                       u.nome remetente_nome,u.email_corporativo remetente_email,
                       CASE WHEN d.lida_em IS NULL THEN 0 ELSE 1 END lida,d.estrela
                FROM correio_destinatarios d
                JOIN correio_mensagens m ON m.id=d.mensagem_id
                JOIN usuarios u ON u.id=m.remetente_id
                WHERE m.empresa_id=? AND d.usuario_id=? AND m.rascunho=0
                  AND d.arquivada=? AND d.excluida=?
                  AND (m.assunto LIKE ? OR m.corpo LIKE ? OR u.nome LIKE ?)
                GROUP BY m.id, u.nome, u.email_corporativo, d.lida_em, d.estrela
                ORDER BY m.id DESC LIMIT ?
            """
            params=(empresa_id,uid,arquivada,excluida,termo,termo,termo,limite)
        linhas=conexao.execute(sql,params).fetchall()
    return [dict(x) for x in linhas]


def obter_mensagem(mensagem_id: int, ator: dict) -> dict:
    if _remoto():
        from enterprise.servidor_cliente import obter_mensagem_remoto
        return obter_mensagem_remoto(mensagem_id)
    empresa_id, _ = obter_escopo_ator(ator)
    uid = int(ator["id"])
    with conectar() as conexao:
        linha = conexao.execute(
            """
            SELECT m.*,u.nome remetente_nome,u.email_corporativo remetente_email
            FROM correio_mensagens m JOIN usuarios u ON u.id=m.remetente_id
            WHERE m.id=? AND m.empresa_id=? AND
              (m.remetente_id=? OR EXISTS(
                SELECT 1 FROM correio_destinatarios d WHERE d.mensagem_id=m.id AND d.usuario_id=?
              ))
            """,
            (int(mensagem_id), empresa_id, uid, uid),
        ).fetchone()
        if linha is None:
            raise PermissionError("Mensagem não disponível para este usuário.")
        destinatarios = conexao.execute(
            """SELECT d.tipo,u.nome,u.email_corporativo
               FROM correio_destinatarios d JOIN usuarios u ON u.id=d.usuario_id
               WHERE d.mensagem_id=? AND (d.tipo<>'CCO' OR ?=?)
               ORDER BY d.tipo,u.nome""",
            (int(mensagem_id), uid, int(linha["remetente_id"])),
        ).fetchall()
        anexos = conexao.execute(
            "SELECT id,nome,arquivo_relativo,tamanho_bytes,sha256 FROM correio_anexos WHERE mensagem_id=?",
            (int(mensagem_id),),
        ).fetchall()
        conexao.execute(
            "UPDATE correio_destinatarios SET lida_em=COALESCE(lida_em,CURRENT_TIMESTAMP) WHERE mensagem_id=? AND usuario_id=?",
            (int(mensagem_id), uid),
        )
    resultado=dict(linha)
    resultado["destinatarios"]=[dict(x) for x in destinatarios]
    resultado["anexos"]=[dict(x) for x in anexos]
    return resultado


def atualizar_estado(mensagem_id: int, ator: dict, *, arquivada=None, excluida=None, estrela=None) -> None:
    if _remoto():
        from enterprise.servidor_cliente import atualizar_estado_remoto
        atualizar_estado_remoto(mensagem_id, arquivada=arquivada, excluida=excluida, estrela=estrela)
        return
    empresa_id, _ = obter_escopo_ator(ator)
    uid=int(ator["id"])
    campos=[]; valores=[]
    for nome, valor in (("arquivada",arquivada),("excluida",excluida),("estrela",estrela)):
        if valor is not None:
            campos.append(f"{nome}=?"); valores.append(int(bool(valor)))
    if not campos:
        return
    with conectar() as conexao:
        pertence=conexao.execute(
            """SELECT 1 FROM correio_destinatarios d JOIN correio_mensagens m ON m.id=d.mensagem_id
               WHERE d.mensagem_id=? AND d.usuario_id=? AND m.empresa_id=?""",
            (int(mensagem_id),uid,empresa_id),
        ).fetchone()
        if pertence is None:
            raise PermissionError("Mensagem não disponível para alteração.")
        conexao.execute(
            f"UPDATE correio_destinatarios SET {', '.join(campos)} WHERE mensagem_id=? AND usuario_id=?",
            (*valores,int(mensagem_id),uid),
        )


def contagem_nao_lidas(ator: dict) -> int:
    if _remoto():
        from enterprise.servidor_cliente import contagem_nao_lidas_remoto
        return contagem_nao_lidas_remoto()
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha=conexao.execute(
            """SELECT COUNT(DISTINCT m.id) total
               FROM correio_destinatarios d JOIN correio_mensagens m ON m.id=d.mensagem_id
               WHERE m.empresa_id=? AND d.usuario_id=? AND d.excluida=0 AND d.arquivada=0
                 AND d.lida_em IS NULL AND m.rascunho=0""",
            (empresa_id,int(ator["id"])),
        ).fetchone()
    return int(linha["total"] or 0)
