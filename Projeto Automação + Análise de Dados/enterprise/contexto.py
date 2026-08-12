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
    """Valida e normaliza o escopo ativo da sessão.

    Usuários comuns só podem usar empresas às quais estejam vinculados. Quando
    o vínculo possui ``filial_id``, ele também restringe a sessão àquela filial;
    vínculo com filial nula representa acesso corporativo à empresa.
    """
    if not SESSAO.autenticado():
        raise PermissionError("Usuário não autenticado.")
    with conectar() as conexao:
        usuario_id = int(SESSAO.usuario["id"])
        estado_usuario = conexao.execute(
            "SELECT ativo, perfil, perfil_acesso, sessao_epoch, email_corporativo FROM usuarios WHERE id=?",
            (usuario_id,),
        ).fetchone()
        if estado_usuario is None or not bool(estado_usuario["ativo"]):
            SESSAO.encerrar()
            raise PermissionError("Sua sessão foi revogada porque a conta está inativa.")
        epoch_atual = int(estado_usuario["sessao_epoch"] or 0)
        epoch_sessao = int(SESSAO.usuario.get("sessao_epoch", 0) or 0)
        if epoch_atual != epoch_sessao:
            SESSAO.encerrar()
            raise PermissionError(
                "Sua sessão foi encerrada porque credenciais ou permissões foram alteradas. Entre novamente."
            )
        administrador = SESSAO.eh_admin()

        vinculo_atual = None
        empresa_atual_valida = None
        if SESSAO.empresa_id is not None:
            if administrador:
                empresa_atual_valida = conexao.execute(
                    "SELECT id FROM empresas WHERE id=? AND ativo=1",
                    (int(SESSAO.empresa_id),),
                ).fetchone()
            else:
                vinculo_atual = conexao.execute(
                    """
                    SELECT ue.empresa_id, ue.filial_id
                    FROM usuarios_empresas ue
                    JOIN empresas e ON e.id=ue.empresa_id
                    WHERE ue.usuario_id=? AND ue.empresa_id=?
                      AND ue.ativo=1 AND e.ativo=1
                    """,
                    (usuario_id, int(SESSAO.empresa_id)),
                ).fetchone()
                empresa_atual_valida = vinculo_atual

        if empresa_atual_valida is None:
            if administrador:
                empresa = conexao.execute(
                    "SELECT id FROM empresas WHERE ativo=1 ORDER BY id LIMIT 1"
                ).fetchone()
                vinculo_atual = None
            else:
                empresa = conexao.execute(
                    """
                    SELECT e.id, ue.filial_id
                    FROM usuarios_empresas ue
                    JOIN empresas e ON e.id=ue.empresa_id
                    WHERE ue.usuario_id=? AND ue.ativo=1 AND e.ativo=1
                    ORDER BY e.id LIMIT 1
                    """,
                    (usuario_id,),
                ).fetchone()
                vinculo_atual = empresa
            if empresa is None:
                raise PermissionError("O usuário não está vinculado a uma empresa ativa.")
            SESSAO.empresa_id = int(empresa["id"])
            SESSAO.filial_id = None

        filial_restrita = None
        if not administrador:
            if vinculo_atual is None:
                vinculo_atual = conexao.execute(
                    "SELECT empresa_id, filial_id FROM usuarios_empresas "
                    "WHERE usuario_id=? AND empresa_id=? AND ativo=1",
                    (usuario_id, int(SESSAO.empresa_id)),
                ).fetchone()
            if vinculo_atual is None:
                raise PermissionError("O usuário não possui vínculo com a empresa ativa.")
            filial_restrita = vinculo_atual["filial_id"]

        # Vínculo a uma filial específica restringe o contexto. Filial nula
        # representa acesso corporativo e permite escolher qualquer filial da empresa.
        if filial_restrita is not None:
            filial = conexao.execute(
                "SELECT id FROM filiais WHERE id=? AND empresa_id=? AND ativo=1",
                (int(filial_restrita), int(SESSAO.empresa_id)),
            ).fetchone()
            if filial is None:
                raise PermissionError("A filial vinculada ao usuário está inativa ou inválida.")
            SESSAO.filial_id = int(filial["id"])
        else:
            filial_valida = None
            if SESSAO.filial_id is not None:
                filial_valida = conexao.execute(
                    "SELECT id FROM filiais WHERE id=? AND empresa_id=? AND ativo=1",
                    (int(SESSAO.filial_id), int(SESSAO.empresa_id)),
                ).fetchone()
            if filial_valida is None:
                filial = conexao.execute(
                    "SELECT id FROM filiais WHERE empresa_id=? AND ativo=1 ORDER BY id LIMIT 1",
                    (int(SESSAO.empresa_id),),
                ).fetchone()
                SESSAO.filial_id = int(filial["id"]) if filial else None

    return int(SESSAO.empresa_id), (
        int(SESSAO.filial_id) if SESSAO.filial_id is not None else None
    )


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


def obter_escopo_ator(ator: dict | None) -> tuple[int, int | None]:
    """Resolve um escopo congelado para operações síncronas/assíncronas.

    Quando o ator traz ``_empresa_id``/``_filial_id``, o contexto é validado no
    banco e não depende de alterações posteriores em ``SESSAO``.
    """
    empresa_id = ator.get("_empresa_id") if ator else None
    filial_id = ator.get("_filial_id") if ator else None
    if empresa_id is None:
        return garantir_contexto_sessao()
    if not ator or not ator.get("id"):
        raise PermissionError("Ator inválido para o contexto empresarial.")
    with conectar() as conexao:
        empresa = conexao.execute(
            "SELECT id FROM empresas WHERE id=? AND ativo=1",
            (int(empresa_id),),
        ).fetchone()
        if empresa is None:
            raise PermissionError("O contexto empresarial do trabalho não está mais ativo.")

        filial_restrita = None
        if str(ator.get("perfil", "")).lower() != "admin":
            vinculo = conexao.execute(
                "SELECT filial_id FROM usuarios_empresas "
                "WHERE usuario_id=? AND empresa_id=? AND ativo=1",
                (int(ator["id"]), int(empresa_id)),
            ).fetchone()
            if vinculo is None:
                raise PermissionError("O usuário não possui acesso ao contexto do trabalho.")
            filial_restrita = vinculo["filial_id"]
            if filial_restrita is not None:
                if filial_id is None or int(filial_id) != int(filial_restrita):
                    raise PermissionError("O usuário não possui acesso à filial do trabalho.")

        if filial_id is not None:
            filial = conexao.execute(
                "SELECT id FROM filiais WHERE id=? AND empresa_id=? AND ativo=1",
                (int(filial_id), int(empresa_id)),
            ).fetchone()
            if filial is None:
                raise PermissionError("A filial do trabalho não pertence à empresa informada.")
        elif filial_restrita is not None:
            filial_id = int(filial_restrita)

    return int(empresa_id), int(filial_id) if filial_id is not None else None


def validar_usuario_no_escopo(
    usuario_id: int,
    empresa_id: int,
    filial_id: int | None,
) -> None:
    """Garante que um usuário possa ser referenciado no escopo informado."""
    with conectar() as conexao:
        usuario = conexao.execute(
            "SELECT id, perfil, ativo FROM usuarios WHERE id=?",
            (int(usuario_id),),
        ).fetchone()
        if usuario is None or not bool(usuario["ativo"]):
            raise ValueError("O usuário informado não existe ou está inativo.")
        if str(usuario["perfil"]).lower() == "admin":
            vinculo = conexao.execute(
                "SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
                (int(usuario_id), int(empresa_id)),
            ).fetchone()
            if vinculo is None:
                raise ValueError("O administrador não possui vínculo com esta empresa.")
            return
        vinculo = conexao.execute(
            "SELECT filial_id FROM usuarios_empresas "
            "WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(usuario_id), int(empresa_id)),
        ).fetchone()
        if vinculo is None:
            raise ValueError("O responsável não possui acesso à empresa atual.")
        filial_vinculo = vinculo["filial_id"]
        if filial_vinculo is not None and (
            filial_id is None or int(filial_vinculo) != int(filial_id)
        ):
            raise ValueError("O responsável não possui acesso à filial atual.")


def tem_permissao(ator: dict | None, modulo: str, acao: str = "ler") -> bool:
    if modulo not in MODULOS or acao not in ACOES_PERMISSAO:
        return False
    if not ator or not ator.get("id") or not ator.get("ativo", True):
        return False
    if ator.get("perfil") == "admin":
        return True
    try:
        empresa_id, _ = obter_escopo_ator(ator)
    except (PermissionError, RuntimeError):
        return False
    coluna = ACOES_PERMISSAO[acao]
    with conectar() as conexao:
        vinculo = conexao.execute(
            "SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(ator["id"]), empresa_id),
        ).fetchone()
        if vinculo is None:
            return False
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
        vinculo = conexao.execute(
            "SELECT 1 FROM usuarios_empresas "
            "WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(usuario_id), empresa_id),
        ).fetchone()
        if vinculo is None:
            raise PermissionError(
                "O usuário não possui vínculo com a empresa selecionada."
            )
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
        vinculo = conexao.execute(
            "SELECT 1 FROM usuarios_empresas "
            "WHERE usuario_id=? AND empresa_id=? AND ativo=1",
            (int(usuario_id), empresa_id),
        ).fetchone()
        if vinculo is None:
            raise PermissionError(
                "O usuário não possui vínculo com a empresa selecionada."
            )
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
        conexao.execute(
            "UPDATE usuarios SET sessao_epoch=COALESCE(sessao_epoch,0)+1 WHERE id=?",
            (int(usuario_id),),
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
