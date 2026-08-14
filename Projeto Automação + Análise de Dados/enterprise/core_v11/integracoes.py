"""Governança de conectores e referências de credenciais externas."""
from __future__ import annotations

from datetime import date, datetime

from auth.banco import conectar
from enterprise.core_v11.common import escopo, exigir_admin, registrar_evento, texto

COFRES_SUPORTADOS = {"cofre", "keyring", "env", "vault", "aws-secrets-manager", "azure-key-vault", "gcp-secret-manager"}


def registrar_referencia_credencial(dados: dict, ator: dict) -> int:
    exigir_admin(ator); empresa_id, filial_id = escopo(ator)
    provedor = str(dados.get("provedor_cofre") or "").strip().lower()
    if provedor not in COFRES_SUPORTADOS:
        raise ValueError("Provedor de cofre não suportado.")
    referencia = texto(dados.get("referencia"), minimo=4, maximo=500, campo="Referência")
    proibidos = ("password=", "senha=", "token=", "secret=", "api_key=")
    if any(item in referencia.casefold() for item in proibidos):
        raise ValueError("Informe somente a referência do segredo, nunca seu valor.")
    integracao_id = int(dados["integracao_id"]) if dados.get("integracao_id") else None
    if integracao_id:
        with conectar() as con:
            existe = con.execute("SELECT 1 FROM integracoes WHERE id=? AND empresa_id=?", (integracao_id, empresa_id)).fetchone()
        if existe is None:
            raise ValueError("Integração não encontrada.")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO core_credenciais_referencias
               (empresa_id,integracao_id,nome,provedor_cofre,referencia,rotacao_dias,ultima_rotacao,expira_em,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(empresa_id,nome) DO UPDATE SET
               integracao_id=excluded.integracao_id,provedor_cofre=excluded.provedor_cofre,
               referencia=excluded.referencia,rotacao_dias=excluded.rotacao_dias,
               ultima_rotacao=excluded.ultima_rotacao,expira_em=excluded.expira_em,ativo=1 RETURNING id""",
            (empresa_id, integracao_id, texto(dados.get("nome"), minimo=2, maximo=120, campo="Nome"), provedor,
             referencia, int(dados["rotacao_dias"]) if dados.get("rotacao_dias") else None,
             dados.get("ultima_rotacao"), dados.get("expira_em"), int(ator["id"])),
        )
        row = cursor.fetchone(); credencial_id = int(row["id"] if hasattr(row, "keys") else row[0])
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="integracoes", tipo="credencial.referencia_atualizada",
            recurso_tipo="core_credenciais_referencias", recurso_id=credencial_id, ator=ator,
            payload={"provedor": provedor, "integracao_id": integracao_id},
        )
    return credencial_id


def listar_credenciais(ator: dict, *, somente_alertas: bool = False) -> list[dict]:
    exigir_admin(ator); empresa_id, _ = escopo(ator); hoje = date.today().isoformat()
    with conectar() as con:
        rows = con.execute(
            """SELECT c.id,c.integracao_id,c.nome,c.provedor_cofre,c.referencia,c.rotacao_dias,
               c.ultima_rotacao,c.expira_em,c.ativo,c.criado_em,i.nome integracao_nome,i.provedor
               FROM core_credenciais_referencias c LEFT JOIN integracoes i ON i.id=c.integracao_id
               WHERE c.empresa_id=? AND c.ativo=1 ORDER BY c.nome""", (empresa_id,),
        ).fetchall()
    saida = []
    for row in rows:
        item = dict(row); referencia = str(item["referencia"])
        item["referencia_mascarada"] = referencia.split(":", 1)[0] + "://***"
        item.pop("referencia")
        item["alerta_expiracao"] = bool(item.get("expira_em") and str(item["expira_em"])[:10] <= hoje)
        if not somente_alertas or item["alerta_expiracao"]:
            saida.append(item)
    return saida


def registrar_rotacao(credencial_id: int, nova_referencia: str, ator: dict) -> None:
    exigir_admin(ator); empresa_id, filial_id = escopo(ator)
    nova_referencia = texto(nova_referencia, minimo=4, maximo=500, campo="Referência")
    with conectar() as con:
        cursor = con.execute(
            """UPDATE core_credenciais_referencias SET referencia=?,ultima_rotacao=CURRENT_TIMESTAMP
               WHERE id=? AND empresa_id=? AND ativo=1""", (nova_referencia, int(credencial_id), empresa_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Referência de credencial não encontrada.")
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="integracoes", tipo="credencial.rotacionada",
            recurso_tipo="core_credenciais_referencias", recurso_id=int(credencial_id), ator=ator,
            payload={"rotacionada_em": datetime.utcnow().isoformat(timespec="seconds")},
        )


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = ("COFRES_SUPORTADOS", "listar_credenciais", "registrar_referencia_credencial", "registrar_rotacao")
