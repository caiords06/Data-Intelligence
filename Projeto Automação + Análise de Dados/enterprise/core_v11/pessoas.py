"""Cadastro mestre de pessoas e papéis empresariais."""
from __future__ import annotations

import base64
import hashlib

from auth import banco
from auth.banco import conectar
from core.criptografia import criptografar_bytes, descriptografar_bytes, obter_chave_mestra
from enterprise.core_v11.common import dump, escopo, indexar_recurso, json_objeto, load, registrar_evento, registrar_historico, texto
from enterprise.privacidade import mascarar_cpf, mascarar_email, registrar_leitura_sensivel


def _chave_pii() -> bytes:
    return obter_chave_mestra(
        variavel_ambiente="DATA_INTELLIGENCE_PII_MASTER_KEY",
        caminho_dpapi=banco.STORAGE_DIR / "segredos" / "pii_master.dpapi",
        descricao="Data Intelligence V11 PII master key",
    )


def _cifrar(dados: dict, *, empresa_id: int) -> str | None:
    if not dados:
        return None
    pacote = criptografar_bytes(dump(dados).encode("utf-8"), _chave_pii(), contexto=f"pessoa:{empresa_id}".encode())
    return base64.b64encode(pacote).decode("ascii")


def _decifrar(valor: str | None, *, empresa_id: int) -> dict:
    if not valor:
        return {}
    bruto = descriptografar_bytes(
        base64.b64decode(valor, validate=True), _chave_pii(), contexto=f"pessoa:{empresa_id}".encode(),
    )
    return load(bruto.decode("utf-8"), {})


def _documento(valor: str | None) -> tuple[str | None, str | None]:
    original = str(valor or "").strip()
    normalizado = "".join(item for item in original if item.isalnum()).upper()
    if not normalizado:
        return None, None
    resumo = hashlib.sha256(normalizado.encode("utf-8")).hexdigest()
    mascarado = mascarar_cpf(normalizado) if len(normalizado) == 11 and normalizado.isdigit() else "***" + normalizado[-4:]
    return resumo, mascarado


def criar_pessoa(dados: dict, ator: dict, *, modulo: str = "rh") -> int:
    empresa_id, filial_id = escopo(ator, modulo, "escrever")
    tipo = str(dados.get("tipo") or "Fisica").strip().title()
    if tipo not in {"Fisica", "Juridica"}:
        raise ValueError("Tipo de pessoa inválido.")
    nome = texto(dados.get("nome"), minimo=2, maximo=180, campo="Nome")
    documento_hash, documento_mascarado = _documento(dados.get("documento"))
    publicos = json_objeto(dados.get("dados_publicos"), campo="Dados públicos")
    sensiveis = json_objeto(dados.get("dados_sensiveis"), campo="Dados sensíveis")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_pessoas
               (empresa_id,tipo,nome,nome_social_fantasia,documento_tipo,documento_hash,
                documento_mascarado,email_corporativo,telefone_corporativo,dados_publicos_json,
                dados_sensiveis_cifrados,classificacao,criado_por,atualizado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                empresa_id, tipo, nome, texto(dados.get("nome_social_fantasia"), maximo=180),
                texto(dados.get("documento_tipo"), maximo=30), documento_hash, documento_mascarado,
                texto(dados.get("email_corporativo"), maximo=180), texto(dados.get("telefone_corporativo"), maximo=40),
                dump(publicos), _cifrar(sensiveis, empresa_id=empresa_id),
                str(dados.get("classificacao") or "Confidencial")[:40], int(ator["id"]), int(ator["id"]),
            ),
        )
        pessoa_id = int(cursor.lastrowid)
        depois = {"id": pessoa_id, "tipo": tipo, "nome": nome, "documento_mascarado": documento_mascarado}
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo,
            recurso_tipo="core_pessoas", recurso_id=pessoa_id, acao="Criado", ator=ator, depois=depois,
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo="pessoa.criada",
            recurso_tipo="core_pessoas", recurso_id=pessoa_id, ator=ator, payload=depois,
        )
        indexar_recurso(
            con, empresa_id=empresa_id, recurso_tipo="core_pessoas", recurso_id=pessoa_id,
            modulo=modulo, titulo=nome, subtitulo=tipo,
            termos=" ".join(filter(None, (nome, documento_mascarado, dados.get("email_corporativo")))),
            classificacao=str(dados.get("classificacao") or "Confidencial"),
        )
    return pessoa_id


def vincular_papel(
    pessoa_id: int,
    papel: str,
    ator: dict,
    *,
    origem_tipo: str | None = None,
    origem_id: int | None = None,
    dados: dict | None = None,
) -> int:
    empresa_id, filial_id = escopo(ator, "rh", "escrever")
    papel = texto(papel, minimo=2, maximo=60, campo="Papel").lower()
    with conectar() as con:
        pessoa = con.execute("SELECT id FROM core_pessoas WHERE id=? AND empresa_id=?", (int(pessoa_id), empresa_id)).fetchone()
        if pessoa is None:
            raise ValueError("Pessoa não encontrada no contexto atual.")
        cursor = con.execute(
            """INSERT INTO core_papeis_pessoa
               (empresa_id,pessoa_id,papel,origem_tipo,origem_id,dados_json,criado_por)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(empresa_id,pessoa_id,papel,origem_tipo,origem_id) DO UPDATE SET
               ativo=1,dados_json=excluded.dados_json,fim=NULL""",
            (empresa_id, int(pessoa_id), papel, origem_tipo, origem_id, dump(json_objeto(dados)), int(ator["id"])),
        )
        identificador = int(cursor.lastrowid or 0)
        if not identificador:
            row = con.execute(
                """SELECT id FROM core_papeis_pessoa WHERE empresa_id=? AND pessoa_id=? AND papel=?
                   AND COALESCE(origem_tipo,'')=COALESCE(?, '') AND COALESCE(origem_id,0)=COALESCE(?,0)""",
                (empresa_id, int(pessoa_id), papel, origem_tipo, origem_id),
            ).fetchone()
            identificador = int(row["id"])
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="rh", tipo="pessoa.papel_vinculado",
            recurso_tipo="core_pessoas", recurso_id=int(pessoa_id), ator=ator,
            payload={"papel": papel, "origem_tipo": origem_tipo, "origem_id": origem_id},
        )
    return identificador


def listar_pessoas(
    ator: dict,
    *,
    papel: str | None = None,
    pesquisa: str = "",
    pagina: int = 1,
    tamanho: int = 50,
) -> dict:
    empresa_id, _ = escopo(ator, "rh", "ler")
    pagina = max(1, int(pagina)); tamanho = max(1, min(int(tamanho), 200))
    filtros = ["p.empresa_id=?", "p.ativo=1"]
    parametros: list = [empresa_id]
    join = ""
    if papel:
        join = "JOIN core_papeis_pessoa pp ON pp.pessoa_id=p.id AND pp.empresa_id=p.empresa_id AND pp.ativo=1"
        filtros.append("pp.papel=?"); parametros.append(str(papel).lower())
    termo = str(pesquisa or "").strip()
    if termo:
        filtros.append("(p.nome LIKE ? OR p.nome_social_fantasia LIKE ? OR p.email_corporativo LIKE ?)")
        busca = f"%{termo}%"; parametros.extend((busca, busca, busca))
    where = " AND ".join(filtros)
    with conectar() as con:
        total = int(con.execute(f"SELECT COUNT(DISTINCT p.id) total FROM core_pessoas p {join} WHERE {where}", tuple(parametros)).fetchone()["total"])
        rows = con.execute(
            f"""SELECT DISTINCT p.id,p.tipo,p.nome,p.nome_social_fantasia,p.documento_mascarado,
                p.email_corporativo,p.telefone_corporativo,p.classificacao,p.versao_registro
                FROM core_pessoas p {join} WHERE {where} ORDER BY p.nome LIMIT ? OFFSET ?""",
            (*parametros, tamanho, (pagina - 1) * tamanho),
        ).fetchall()
    return {"itens": [dict(x) for x in rows], "total": total, "pagina": pagina, "tamanho": tamanho}


def obter_pessoa(pessoa_id: int, ator: dict, *, incluir_sensiveis: bool = False) -> dict:
    empresa_id, filial_id = escopo(ator, "rh", "ler")
    with conectar() as con:
        row = con.execute("SELECT * FROM core_pessoas WHERE id=? AND empresa_id=? AND ativo=1", (int(pessoa_id), empresa_id)).fetchone()
        if row is None:
            raise ValueError("Pessoa não encontrada.")
        papeis = con.execute("SELECT papel,origem_tipo,origem_id,dados_json FROM core_papeis_pessoa WHERE pessoa_id=? AND ativo=1", (int(pessoa_id),)).fetchall()
    item = dict(row)
    item["dados_publicos"] = load(item.pop("dados_publicos_json"), {})
    cifrado = item.pop("dados_sensiveis_cifrados")
    item["dados_sensiveis"] = _decifrar(cifrado, empresa_id=empresa_id) if incluir_sensiveis else None
    item["papeis"] = [{**dict(p), "dados": load(p["dados_json"], {})} for p in papeis]
    if incluir_sensiveis:
        registrar_leitura_sensivel(
            ator={**ator, "_empresa_id": empresa_id, "_filial_id": filial_id}, modulo="RH",
            entidade="core_pessoas", entidade_id=int(pessoa_id),
            campos=["cpf", "rg", "nascimento", "endereco", "telefone", "email_pessoal"],
            finalidade="Consulta de cadastro mestre de pessoa",
        )
    return item


def sincronizar_colaborador(colaborador_id: int, ator: dict) -> int:
    empresa_id, _ = escopo(ator, "rh", "ler")
    with conectar() as con:
        row = con.execute("SELECT * FROM rh_colaboradores WHERE id=? AND empresa_id=?", (int(colaborador_id), empresa_id)).fetchone()
    if row is None:
        raise ValueError("Colaborador não encontrado.")
    if row["pessoa_id"]:
        return int(row["pessoa_id"])
    pessoa_id = criar_pessoa(
        {
            "tipo": "Fisica", "nome": row["nome_completo"], "nome_social_fantasia": row["nome_social"],
            "documento_tipo": "CPF", "documento": row["cpf"], "email_corporativo": row["email_corporativo"],
            "telefone_corporativo": row["telefone"],
            "dados_sensiveis": {
                "rg": row["rg"], "nascimento": row["nascimento"], "email_pessoal": mascarar_email(row["email_pessoal"]),
                "endereco": row["endereco"], "contato_emergencia": row["contato_emergencia"],
            },
        },
        ator,
    )
    with conectar() as con:
        con.execute("UPDATE rh_colaboradores SET pessoa_id=? WHERE id=?", (pessoa_id, int(colaborador_id)))
        if row["usuario_id"]:
            con.execute("UPDATE usuarios SET pessoa_id=? WHERE id=?", (pessoa_id, int(row["usuario_id"])))
    vincular_papel(pessoa_id, "colaborador", ator, origem_tipo="rh_colaboradores", origem_id=int(colaborador_id))
    return pessoa_id


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo


__all__ = ("criar_pessoa", "listar_pessoas", "obter_pessoa", "sincronizar_colaborador", "vincular_papel")
