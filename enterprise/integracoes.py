"""Integration Hub: metadados seguros para conectores externos futuros."""

from __future__ import annotations

import json

from auth.banco import conectar, registrar_auditoria
from enterprise.contexto import garantir_contexto_sessao

PROVEDORES_SUPORTADOS = {
    "google",
    "microsoft",
    "smtp",
    "slack",
    "teams",
    "github",
    "odoo",
    "sap",
    "dynamics",
    "postgresql",
    "sql_server",
    "mysql",
    "api_http",
}
_MARCADORES_SECRETOS = {
    "senha",
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
}


def _exigir_admin(ator):
    if not ator or ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem configurar integrações.")


def registrar_integracao(
    provedor: str,
    nome: str,
    referencia_credencial: str,
    configuracao: dict,
    ator: dict,
) -> int:
    _exigir_admin(ator)
    provedor = str(provedor).strip().lower()
    nome = str(nome).strip()
    if provedor not in PROVEDORES_SUPORTADOS:
        raise ValueError("Provedor de integração não suportado.")
    if len(nome) < 2 or len(nome) > 100:
        raise ValueError("Nome de integração inválido.")
    if not isinstance(configuracao, dict):
        raise ValueError("A configuração precisa ser um objeto.")
    chaves = {str(chave).casefold() for chave in configuracao}
    if any(
        marcador in chave
        for chave in chaves
        for marcador in _MARCADORES_SECRETOS
    ):
        raise ValueError(
            "Não armazene segredos na configuração. Use uma referência ao cofre de credenciais."
        )
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO integracoes (
                empresa_id, provedor, nome, referencia_credencial,
                configuracao_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                empresa_id,
                provedor,
                nome,
                str(referencia_credencial).strip() or None,
                json.dumps(configuracao, ensure_ascii=False),
            ),
        )
        integracao_id = int(cursor.lastrowid)
    registrar_auditoria(
        "integracao_registrada",
        usuario_id=ator["id"],
        detalhes=f"integracao_id={integracao_id};provedor={provedor}",
    )
    return integracao_id


def listar_integracoes(ator: dict) -> list[dict]:
    _exigir_admin(ator)
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id, provedor, nome, referencia_credencial, configuracao_json,
                   ativo, ultima_sincronizacao, criado_em
            FROM integracoes WHERE empresa_id = ? ORDER BY nome
            """,
            (empresa_id,),
        ).fetchall()
    resultado = []
    for item in registros:
        registro = dict(item)
        registro["configuracao"] = json.loads(registro.pop("configuracao_json"))
        resultado.append(registro)
    return resultado


def definir_integracao_ativa(integracao_id: int, ativa: bool, ator: dict) -> None:
    _exigir_admin(ator)
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE integracoes SET ativo = ?
            WHERE id = ? AND empresa_id = ?
            """,
            (int(bool(ativa)), int(integracao_id), empresa_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Integração não encontrada.")
