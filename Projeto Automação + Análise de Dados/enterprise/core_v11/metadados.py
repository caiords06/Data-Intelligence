"""Campos personalizados, etiquetas e configurações sem código por empresa."""
from __future__ import annotations

import base64
import json

from auth import banco
from auth.banco import conectar
from core.criptografia import criptografar_bytes, descriptografar_bytes, obter_chave_mestra
from enterprise.core_v11.common import codigo, dump, escopo, exigir_admin, json_lista, json_objeto, load, registrar_historico, texto

TIPOS_CAMPO = {"texto", "texto_longo", "numero", "moeda", "booleano", "data", "data_hora", "opcao", "lista", "usuario", "pessoa", "arquivo"}


def _chave_campos() -> bytes:
    return obter_chave_mestra(
        variavel_ambiente="DATA_INTELLIGENCE_PII_MASTER_KEY",
        caminho_dpapi=banco.STORAGE_DIR / "segredos" / "pii_master.dpapi",
        descricao="Data Intelligence V11 PII master key",
    )


def definir_campo(dados: dict, ator: dict) -> int:
    exigir_admin(ator); empresa_id, _ = escopo(ator)
    tipo = str(dados.get("tipo") or "texto").strip().lower()
    if tipo not in TIPOS_CAMPO:
        raise ValueError("Tipo de campo personalizado inválido.")
    modulo = codigo(dados.get("modulo"), campo="Módulo")
    recurso_tipo = codigo(dados.get("recurso_tipo"), campo="Tipo de recurso")
    codigo_campo = codigo(dados.get("codigo"), campo="Código do campo")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_campos_definicoes
               (empresa_id,modulo,recurso_tipo,codigo,rotulo,tipo,obrigatorio,sensivel,
                opcoes_json,validacao_json,ordem,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(empresa_id,recurso_tipo,codigo) DO UPDATE SET
               rotulo=excluded.rotulo,tipo=excluded.tipo,obrigatorio=excluded.obrigatorio,
               sensivel=excluded.sensivel,opcoes_json=excluded.opcoes_json,
               validacao_json=excluded.validacao_json,ordem=excluded.ordem,ativo=1
               RETURNING id""",
            (
                empresa_id, modulo, recurso_tipo, codigo_campo,
                texto(dados.get("rotulo"), minimo=2, maximo=120, campo="Rótulo"), tipo,
                int(bool(dados.get("obrigatorio"))), int(bool(dados.get("sensivel"))),
                dump(json_lista(dados.get("opcoes"), campo="Opções")),
                dump(json_objeto(dados.get("validacao"), campo="Validação")), int(dados.get("ordem") or 0), int(ator["id"]),
            ),
        )
        row = cursor.fetchone()
    return int(row["id"] if hasattr(row, "keys") else row[0])


def listar_campos(recurso_tipo: str, ator: dict, *, incluir_inativos: bool = False) -> list[dict]:
    empresa_id, _ = escopo(ator)
    filtro = "" if incluir_inativos else "AND ativo=1"
    with conectar() as con:
        rows = con.execute(
            f"""SELECT * FROM core_campos_definicoes WHERE empresa_id=? AND recurso_tipo=? {filtro}
                ORDER BY ordem,id""",
            (empresa_id, str(recurso_tipo)),
        ).fetchall()
    return [{**dict(x), "opcoes": load(x["opcoes_json"], []), "validacao": load(x["validacao_json"], {})} for x in rows]


def _validar_valor(definicao: dict, valor):
    if definicao["obrigatorio"] and valor in (None, "", []):
        raise ValueError(f"O campo {definicao['rotulo']} é obrigatório.")
    tipo = definicao["tipo"]
    if valor in (None, ""):
        return None
    if tipo in {"numero", "moeda"}:
        try:
            return float(valor)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"O campo {definicao['rotulo']} exige número.") from exc
    if tipo == "booleano":
        return bool(valor)
    if tipo == "opcao" and valor not in load(definicao["opcoes_json"], []):
        raise ValueError(f"Opção inválida para {definicao['rotulo']}.")
    return valor


def salvar_campos_valores(recurso_tipo: str, recurso_id: int, valores: dict, ator: dict, *, modulo: str) -> None:
    empresa_id, filial_id = escopo(ator, modulo, "escrever")
    definicoes = {item["codigo"]: item for item in listar_campos(recurso_tipo, ator)}
    desconhecidos = sorted(set(valores) - set(definicoes))
    if desconhecidos:
        raise ValueError("Campos personalizados desconhecidos: " + ", ".join(desconhecidos))
    with conectar() as con:
        for codigo_campo, valor in valores.items():
            definicao = definicoes[codigo_campo]
            validado = _validar_valor(definicao, valor)
            valor_json = dump(validado)
            valor_cifrado = None
            if definicao["sensivel"]:
                pacote = criptografar_bytes(
                    valor_json.encode("utf-8"), _chave_campos(),
                    contexto=f"campo:{empresa_id}:{definicao['id']}".encode(),
                )
                valor_cifrado = base64.b64encode(pacote).decode("ascii"); valor_json = None
            con.execute(
                """INSERT INTO core_campos_valores
                   (empresa_id,definicao_id,recurso_tipo,recurso_id,valor_json,valor_cifrado,atualizado_por)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(definicao_id,recurso_tipo,recurso_id) DO UPDATE SET
                   valor_json=excluded.valor_json,valor_cifrado=excluded.valor_cifrado,
                   atualizado_por=excluded.atualizado_por,atualizado_em=CURRENT_TIMESTAMP""",
                (empresa_id, int(definicao["id"]), recurso_tipo, int(recurso_id), valor_json, valor_cifrado, int(ator["id"])),
            )
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, recurso_tipo=recurso_tipo,
            recurso_id=int(recurso_id), acao="Campos personalizados atualizados", ator=ator,
            depois={"campos": sorted(valores)},
        )


def obter_campos_valores(recurso_tipo: str, recurso_id: int, ator: dict, *, incluir_sensiveis: bool = False) -> dict:
    empresa_id, _ = escopo(ator)
    with conectar() as con:
        rows = con.execute(
            """SELECT d.codigo,d.rotulo,d.tipo,d.sensivel,v.valor_json,v.valor_cifrado,d.id definicao_id
               FROM core_campos_definicoes d LEFT JOIN core_campos_valores v
               ON v.definicao_id=d.id AND v.recurso_tipo=? AND v.recurso_id=?
               WHERE d.empresa_id=? AND d.recurso_tipo=? AND d.ativo=1 ORDER BY d.ordem,d.id""",
            (recurso_tipo, int(recurso_id), empresa_id, recurso_tipo),
        ).fetchall()
    saida = {}
    for row in rows:
        if row["sensivel"] and row["valor_cifrado"]:
            if not incluir_sensiveis:
                saida[row["codigo"]] = "***"
                continue
            pacote = base64.b64decode(row["valor_cifrado"], validate=True)
            bruto = descriptografar_bytes(
                pacote, _chave_campos(), contexto=f"campo:{empresa_id}:{row['definicao_id']}".encode(),
            )
            saida[row["codigo"]] = json.loads(bruto.decode("utf-8"))
        else:
            saida[row["codigo"]] = json.loads(row["valor_json"]) if row["valor_json"] is not None else None
    return saida


def criar_etiqueta(nome: str, cor: str, ator: dict, *, categoria: str = "") -> int:
    empresa_id, _ = escopo(ator)
    cor = str(cor or "#64748B").upper()
    if len(cor) != 7 or not cor.startswith("#") or any(c not in "0123456789ABCDEF" for c in cor[1:]):
        raise ValueError("Cor deve usar o formato hexadecimal #RRGGBB.")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_etiquetas(empresa_id,nome,cor,categoria,criado_por) VALUES (?,?,?,?,?)
               ON CONFLICT(empresa_id,nome) DO UPDATE SET cor=excluded.cor,categoria=excluded.categoria,ativo=1
               RETURNING id""",
            (empresa_id, texto(nome, minimo=1, maximo=60, campo="Etiqueta"), cor, texto(categoria, maximo=60), int(ator["id"])),
        )
        row = cursor.fetchone()
    return int(row["id"] if hasattr(row, "keys") else row[0])


def aplicar_etiqueta(etiqueta_id: int, recurso_tipo: str, recurso_id: int, ator: dict) -> None:
    empresa_id, _ = escopo(ator)
    with conectar() as con:
        etiqueta = con.execute("SELECT id FROM core_etiquetas WHERE id=? AND empresa_id=? AND ativo=1", (int(etiqueta_id), empresa_id)).fetchone()
        if etiqueta is None:
            raise ValueError("Etiqueta não encontrada.")
        con.execute(
            """INSERT INTO core_recurso_etiquetas(etiqueta_id,recurso_tipo,recurso_id,aplicado_por)
               VALUES (?,?,?,?) ON CONFLICT(etiqueta_id,recurso_tipo,recurso_id) DO NOTHING""",
            (int(etiqueta_id), recurso_tipo, int(recurso_id), int(ator["id"])),
        )


def salvar_configuracao(modulo: str, chave: str, valor: dict, ator: dict, *, filial_id: int | None = None) -> int:
    exigir_admin(ator); empresa_id, _ = escopo(ator)
    modulo = codigo(modulo, campo="Módulo"); chave = codigo(chave, campo="Chave")
    with conectar() as con:
        row = con.execute(
            """SELECT id FROM core_configuracoes WHERE empresa_id=? AND COALESCE(filial_id,0)=COALESCE(?,0)
               AND modulo=? AND chave=?""", (empresa_id, filial_id, modulo, chave),
        ).fetchone()
        if row:
            con.execute(
                "UPDATE core_configuracoes SET valor_json=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                (dump(json_objeto(valor)), int(ator["id"]), int(row["id"])),
            )
            return int(row["id"])
        cursor = con.execute(
            """INSERT INTO core_configuracoes(empresa_id,filial_id,modulo,chave,valor_json,atualizado_por)
               VALUES (?,?,?,?,?,?)""", (empresa_id, filial_id, modulo, chave, dump(json_objeto(valor)), int(ator["id"])),
        )
        return int(cursor.lastrowid)


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "TIPOS_CAMPO", "aplicar_etiqueta", "criar_etiqueta", "definir_campo", "listar_campos",
    "obter_campos_valores", "salvar_campos_valores", "salvar_configuracao",
)
