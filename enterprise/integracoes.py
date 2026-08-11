"""Integration Hub: metadados seguros para conectores externos futuros."""

from __future__ import annotations

import json

from auth.banco import conectar, registrar_auditoria
from enterprise.contexto import obter_escopo_ator

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
_ESQUEMAS_COFRE = ("cofre://", "keyring://", "env://")


def _contem_segredo(valor, caminho="configuracao"):
    if isinstance(valor, dict):
        for chave, item in valor.items():
            chave_texto = str(chave).casefold()
            if any(marcador in chave_texto for marcador in _MARCADORES_SECRETOS):
                return f"{caminho}.{chave}"
            encontrado = _contem_segredo(item, f"{caminho}.{chave}")
            if encontrado:
                return encontrado
    elif isinstance(valor, (list, tuple)):
        for indice, item in enumerate(valor):
            encontrado = _contem_segredo(item, f"{caminho}[{indice}]")
            if encontrado:
                return encontrado
    return None


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
    segredo = _contem_segredo(configuracao)
    if segredo:
        raise ValueError(
            f"Não armazene segredos em {segredo}. Use uma referência ao cofre."
        )
    referencia_credencial = str(referencia_credencial).strip()
    if referencia_credencial and not referencia_credencial.startswith(_ESQUEMAS_COFRE):
        raise ValueError(
            "A referência deve usar cofre://, keyring:// ou env://."
        )
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO integracoes (
                empresa_id, filial_id, provedor, nome, referencia_credencial,
                configuracao_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                empresa_id,
                filial_id,
                provedor,
                nome,
                referencia_credencial or None,
                json.dumps(configuracao, ensure_ascii=False),
            ),
        )
        integracao_id = int(cursor.lastrowid)
    registrar_auditoria(
        "integracao_registrada",
        usuario_id=ator["id"],
        empresa_id=empresa_id,
        filial_id=filial_id,
        modulo="integracoes",
        entidade="integracoes",
        entidade_id=integracao_id,
        detalhes=f"integracao_id={integracao_id};provedor={provedor}",
    )
    return integracao_id


def listar_integracoes(ator: dict) -> list[dict]:
    _exigir_admin(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT id, provedor, nome, referencia_credencial, configuracao_json,
                   ativo, ultima_sincronizacao, criado_em
            FROM integracoes WHERE empresa_id = ? AND (filial_id = ? OR ? IS NULL) ORDER BY nome
            """,
            (empresa_id, filial_id, filial_id),
        ).fetchall()
    resultado = []
    for item in registros:
        registro = dict(item)
        registro["configuracao"] = json.loads(registro.pop("configuracao_json"))
        resultado.append(registro)
    return resultado


def definir_integracao_ativa(integracao_id: int, ativa: bool, ator: dict) -> None:
    _exigir_admin(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE integracoes SET ativo = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)
            """,
            (int(bool(ativa)), int(integracao_id), empresa_id, filial_id, filial_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Integração não encontrada.")

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
