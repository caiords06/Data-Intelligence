"""Contexto de empresa/filial e permissões por módulo."""

from __future__ import annotations

from auth.banco import conectar
from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS, ORDEM_MODULOS
from enterprise.perfis_acesso import obter_permissoes_perfil


ACOES_PERMISSAO = {
    "ler": "pode_ler",
    "escrever": "pode_escrever",
    "aprovar": "pode_aprovar",
}


def _permissoes_padrao_seguras(perfil_acesso) -> dict[str, dict[str, bool]]:
    try:
        return obter_permissoes_perfil(perfil_acesso)
    except ValueError:
        return {
            modulo: {"ler": False, "escrever": False, "aprovar": False}
            for modulo in ORDEM_MODULOS
        }


def garantir_contexto_sessao() -> tuple[int, int | None]:
    if not SESSAO.autenticado():
        raise PermissionError("Usuário não autenticado.")
    with conectar() as conexao:
        if SESSAO.empresa_id is None:
            empresa = conexao.execute(
                "SELECT id FROM empresas WHERE ativo = 1 ORDER BY id LIMIT 1"
            ).fetchone()
            if empresa is None:
                raise RuntimeError("Nenhuma empresa ativa foi configurada.")
            SESSAO.empresa_id = int(empresa["id"])
        if SESSAO.filial_id is None:
            filial = conexao.execute(
                """
                SELECT id FROM filiais
                WHERE empresa_id = ? AND ativo = 1 ORDER BY id LIMIT 1
                """,
                (SESSAO.empresa_id,),
            ).fetchone()
            SESSAO.filial_id = int(filial["id"]) if filial else None
    return SESSAO.empresa_id, SESSAO.filial_id


def obter_contexto() -> dict:
    empresa_id, filial_id = garantir_contexto_sessao()
    with conectar() as conexao:
        empresa = conexao.execute(
            "SELECT id, nome FROM empresas WHERE id = ?",
            (empresa_id,),
        ).fetchone()
        filial = (
            conexao.execute(
                "SELECT id, nome FROM filiais WHERE id = ?",
                (filial_id,),
            ).fetchone()
            if filial_id
            else None
        )
    return {
        "empresa_id": empresa_id,
        "empresa_nome": empresa["nome"] if empresa else "Empresa",
        "filial_id": filial_id,
        "filial_nome": filial["nome"] if filial else None,
    }


def tem_permissao(ator: dict | None, modulo: str, acao: str = "ler") -> bool:
    if modulo not in MODULOS or acao not in ACOES_PERMISSAO:
        return False
    if not ator or not ator.get("id") or not ator.get("ativo", True):
        return False
    if ator.get("perfil") == "admin":
        return True
    empresa_id, _ = garantir_contexto_sessao()
    coluna = ACOES_PERMISSAO[acao]
    with conectar() as conexao:
        registro = conexao.execute(
            f"""
            SELECT {coluna} AS permitido
            FROM permissoes_modulos
            WHERE usuario_id = ? AND empresa_id = ? AND modulo = ?
            """,
            (int(ator["id"]), empresa_id, modulo),
        ).fetchone()
    if registro is not None:
        return bool(registro["permitido"])
    perfil_acesso = ator.get("perfil_acesso") or "analista"
    return bool(_permissoes_padrao_seguras(perfil_acesso)[modulo][acao])


def exigir_permissao(ator: dict | None, modulo: str, acao: str = "ler") -> None:
    if not tem_permissao(ator, modulo, acao):
        raise PermissionError(
            f"Seu perfil não possui permissão para {acao} no módulo {modulo}."
        )


def listar_modulos_permitidos(ator: dict | None) -> list[str]:
    return [
        modulo
        for modulo in ORDEM_MODULOS
        if tem_permissao(ator, modulo, "ler")
    ]


def obter_permissoes_usuario(usuario_id: int, ator: dict | None) -> dict[str, dict]:
    if not ator or ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem consultar permissões.")
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT perfil, perfil_acesso FROM usuarios WHERE id = ?",
            (int(usuario_id),),
        ).fetchone()
        if usuario is None:
            raise ValueError("Usuário não encontrado.")
        registros = conexao.execute(
            """
            SELECT modulo, pode_ler, pode_escrever, pode_aprovar
            FROM permissoes_modulos WHERE usuario_id = ? AND empresa_id = ?
            """,
            (int(usuario_id), empresa_id),
        ).fetchall()
    existentes = {registro["modulo"]: dict(registro) for registro in registros}
    if usuario["perfil"] == "admin":
        return {
            modulo: {"ler": True, "escrever": True, "aprovar": True}
            for modulo in ORDEM_MODULOS
        }
    padrao = _permissoes_padrao_seguras(
        usuario["perfil_acesso"] or "analista"
    )
    return {
        modulo: {
            "ler": bool(
                existentes.get(modulo, {}).get("pode_ler", padrao[modulo]["ler"])
            ),
            "escrever": bool(
                existentes.get(modulo, {}).get(
                    "pode_escrever", padrao[modulo]["escrever"]
                )
            ),
            "aprovar": bool(
                existentes.get(modulo, {}).get(
                    "pode_aprovar", padrao[modulo]["aprovar"]
                )
            ),
        }
        for modulo in ORDEM_MODULOS
    }


def salvar_permissoes_usuario(
    usuario_id: int,
    permissoes: dict[str, dict],
    ator: dict | None,
) -> None:
    if not ator or ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem alterar permissões.")
    if int(usuario_id) == int(ator["id"]):
        raise ValueError("As permissões do administrador atual não precisam ser alteradas.")
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT perfil_acesso FROM usuarios WHERE id = ?",
            (int(usuario_id),),
        ).fetchone()
        if usuario is None:
            raise ValueError("Usuário não encontrado.")
        padrao = _permissoes_padrao_seguras(
            usuario["perfil_acesso"] or "analista"
        )
        for modulo in ORDEM_MODULOS:
            valores = permissoes.get(modulo, padrao[modulo])
            ler = bool(valores.get("ler"))
            escrever = bool(valores.get("escrever")) and ler
            aprovar = bool(valores.get("aprovar")) and ler
            conexao.execute(
                """
                INSERT INTO permissoes_modulos (
                    usuario_id, empresa_id, modulo,
                    pode_ler, pode_escrever, pode_aprovar
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(usuario_id, empresa_id, modulo) DO UPDATE SET
                    pode_ler = excluded.pode_ler,
                    pode_escrever = excluded.pode_escrever,
                    pode_aprovar = excluded.pode_aprovar,
                    atualizado_em = CURRENT_TIMESTAMP
                """,
                (
                    int(usuario_id),
                    empresa_id,
                    modulo,
                    int(ler),
                    int(escrever),
                    int(aprovar),
                ),
            )


def aplicar_perfil_padrao_usuario(
    usuario_id: int,
    perfil_acesso: str,
    ator: dict | None,
) -> None:
    """Substitui personalizações pelo conjunto padrão do perfil escolhido."""
    salvar_permissoes_usuario(
        usuario_id,
        obter_permissoes_perfil(perfil_acesso),
        ator,
    )
