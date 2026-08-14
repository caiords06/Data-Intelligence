"""Funcionário 360°: visão única, contextual e auditável do colaborador."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from auth.banco import conectar
from enterprise.contexto import obter_escopo_ator, tem_permissao
from enterprise.core_v11.common import escopo, registrar_evento, registrar_historico, texto
from enterprise.core_v11.documentos import carregar_midia_bytes, listar_documentos, registrar_midia_bytes
from enterprise.core_v11.pessoas import sincronizar_colaborador
from enterprise.privacidade import registrar_leitura_sensivel
from enterprise.rh import obter_colaborador, tem_permissao_rh

VISOES = {"meu_perfil", "gestor", "rh", "ti", "auditor"}
SECOES_POR_VISAO = {
    "meu_perfil": {
        "identidade", "profissional", "contatos", "linha_tempo", "documentos", "jornada",
        "beneficios", "remuneracao", "equipamentos", "acessos", "treinamentos", "desempenho",
        "tarefas", "chamados", "solicitacoes", "custos",
    },
    "gestor": {
        "identidade", "profissional", "contatos", "linha_tempo", "jornada", "equipamentos",
        "treinamentos", "desempenho", "tarefas", "chamados", "solicitacoes", "custos",
    },
    "rh": {
        "identidade", "dados_pessoais", "profissional", "contatos", "linha_tempo", "documentos",
        "jornada", "beneficios", "remuneracao", "equipamentos", "acessos", "treinamentos",
        "desempenho", "tarefas", "chamados", "solicitacoes", "ocorrencias", "custos",
    },
    "ti": {"identidade", "profissional", "contatos", "equipamentos", "acessos", "tarefas", "chamados"},
    "auditor": {
        "identidade", "dados_pessoais", "profissional", "contatos", "linha_tempo", "documentos",
        "jornada", "beneficios", "remuneracao", "equipamentos", "acessos", "treinamentos",
        "desempenho", "tarefas", "chamados", "solicitacoes", "ocorrencias", "custos", "auditoria",
    },
}


def _centavos(valor) -> int:
    try:
        numero = Decimal(str(valor or "0").replace("R$", "").replace(".", "").replace(",", ".").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor monetário inválido.") from exc
    if not numero.is_finite() or numero < 0:
        raise ValueError("Valor monetário inválido.")
    return int((numero * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _contexto_colaborador(colaborador_id: int, ator: dict) -> tuple[dict, set[str]]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as con:
        alvo = con.execute(
            """SELECT id,empresa_id,filial_id,usuario_id,gestor_id FROM rh_colaboradores
               WHERE id=? AND empresa_id=? AND (filial_id=? OR ? IS NULL)""",
            (int(colaborador_id), empresa_id, filial_id, filial_id),
        ).fetchone()
        if alvo is None:
            raise ValueError("Colaborador não encontrado no contexto atual.")
        gestor = con.execute(
            "SELECT id FROM rh_colaboradores WHERE empresa_id=? AND usuario_id=? LIMIT 1",
            (empresa_id, int(ator["id"])),
        ).fetchone()
    alvo = dict(alvo)
    perfil = str(ator.get("perfil_acesso") or "").lower()
    visoes: set[str] = set()
    if int(alvo.get("usuario_id") or 0) == int(ator["id"]):
        visoes.add("meu_perfil")
    if gestor is not None and int(alvo.get("gestor_id") or 0) == int(gestor["id"]):
        visoes.add("gestor")
    if str(ator.get("perfil") or "").lower() == "admin" or perfil in {"rh", "rh_plus", "rh_diretoria", "rh_analista"}:
        visoes.add("rh")
    if str(ator.get("perfil") or "").lower() == "admin" or perfil == "rh_auditor":
        visoes.add("auditor")
    if str(ator.get("perfil") or "").lower() == "admin" or tem_permissao(ator, "ti", "ler"):
        visoes.add("ti")
    if not visoes:
        raise PermissionError("Seu perfil não pode visualizar este colaborador.")
    return alvo, visoes


def _escolher_visao(visoes: set[str], solicitada: str | None) -> str:
    if solicitada:
        solicitada = str(solicitada).strip().lower()
        if solicitada not in VISOES or solicitada not in visoes:
            raise PermissionError("A visão solicitada não está autorizada.")
        return solicitada
    for candidato in ("meu_perfil", "rh", "gestor", "ti", "auditor"):
        if candidato in visoes:
            return candidato
    raise PermissionError("Nenhuma visão autorizada.")


def garantir_vinculo(colaborador_id: int, ator: dict) -> dict:
    """Materializa Pessoa/Colaborador/Usuário sem duplicar identidades."""
    empresa_id, _ = escopo(ator)
    with conectar() as con:
        row = con.execute(
            "SELECT pessoa_id,usuario_id,gestor_id FROM rh_colaboradores WHERE id=? AND empresa_id=?",
            (int(colaborador_id), empresa_id),
        ).fetchone()
    if row is None:
        raise ValueError("Colaborador não encontrado.")
    pessoa_id = row["pessoa_id"]
    if not pessoa_id:
        if not tem_permissao_rh(ator, "editar_colaborador", int(colaborador_id)):
            return {"pessoa_id": None, "usuario_id": row["usuario_id"], "sincronizado": False}
        pessoa_id = sincronizar_colaborador(int(colaborador_id), ator)
    with conectar() as con:
        con.execute(
            """INSERT INTO funcionario_360_vinculos
               (empresa_id,colaborador_id,pessoa_id,usuario_id,gestor_colaborador_id)
               VALUES (?,?,?,?,?) ON CONFLICT(empresa_id,colaborador_id) DO UPDATE SET
               pessoa_id=excluded.pessoa_id,usuario_id=excluded.usuario_id,
               gestor_colaborador_id=excluded.gestor_colaborador_id,atualizado_em=CURRENT_TIMESTAMP""",
            (empresa_id, int(colaborador_id), int(pessoa_id), row["usuario_id"], row["gestor_id"]),
        )
    return {"pessoa_id": int(pessoa_id), "usuario_id": row["usuario_id"], "sincronizado": True}


def _listas_360(colaborador_id: int, empresa_id: int, usuario_id: int | None) -> dict:
    cid = int(colaborador_id)
    with conectar() as con:
        consultas = {
            "linha_tempo": ("SELECT * FROM rh_historico_profissional WHERE colaborador_id=? ORDER BY vigencia DESC,id DESC", (cid,)),
            "admissoes": ("SELECT * FROM rh_admissoes WHERE colaborador_id=? ORDER BY id DESC", (cid,)),
            "desligamentos": ("SELECT * FROM rh_desligamentos WHERE colaborador_id=? ORDER BY id DESC", (cid,)),
            "jornada": ("SELECT * FROM rh_pontos WHERE colaborador_id=? ORDER BY data DESC LIMIT 180", (cid,)),
            "ausencias": ("SELECT * FROM rh_ferias_ausencias WHERE colaborador_id=? ORDER BY inicio DESC", (cid,)),
            "beneficios": ("""SELECT cb.*,b.nome,b.tipo,b.custo_empresa_centavos,b.desconto_colaborador_centavos
                              FROM rh_colaborador_beneficios cb JOIN rh_beneficios b ON b.id=cb.beneficio_id
                              WHERE cb.colaborador_id=? ORDER BY cb.inicio DESC""", (cid,)),
            "folha": ("""SELECT e.*,f.competencia,f.status folha_status FROM rh_eventos_folha e
                          JOIN rh_folhas f ON f.id=e.folha_id WHERE e.colaborador_id=? ORDER BY f.competencia DESC,e.id""", (cid,)),
            "contracheques": ("""SELECT c.*,f.competencia FROM rh_contracheques c JOIN rh_folhas f ON f.id=c.folha_id
                                   WHERE c.colaborador_id=? ORDER BY f.competencia DESC""", (cid,)),
            "equipamentos_rh": ("SELECT * FROM rh_equipamentos WHERE colaborador_id=? ORDER BY entregue_em DESC", (cid,)),
            "acessos": ("SELECT * FROM rh_acessos_sistemas WHERE colaborador_id=? ORDER BY solicitado_em DESC", (cid,)),
            "treinamentos": ("""SELECT i.*,t.titulo,t.tipo,t.carga_horaria,t.validade_meses,t.obrigatorio
                                  FROM rh_inscricoes_treinamento i JOIN rh_treinamentos t ON t.id=i.treinamento_id
                                  WHERE i.colaborador_id=? ORDER BY i.inscrito_em DESC""", (cid,)),
            "avaliacoes": ("SELECT * FROM rh_avaliacoes WHERE colaborador_id=? ORDER BY ciclo DESC,id DESC", (cid,)),
            "pdis": ("SELECT * FROM rh_pdis WHERE colaborador_id=? ORDER BY id DESC", (cid,)),
            "feedbacks": ("SELECT * FROM rh_feedbacks WHERE colaborador_id=? ORDER BY criado_em DESC", (cid,)),
            "solicitacoes": ("SELECT * FROM rh_solicitacoes WHERE colaborador_id=? ORDER BY criado_em DESC", (cid,)),
            "ocorrencias": ("SELECT * FROM rh_ocorrencias WHERE colaborador_id=? ORDER BY criado_em DESC", (cid,)),
            "custos": ("SELECT * FROM rh_custos_vinculados WHERE colaborador_id=? ORDER BY criado_em DESC", (cid,)),
        }
        saida = {chave: [dict(x) for x in con.execute(sql, parametros).fetchall()] for chave, (sql, parametros) in consultas.items()}
        saida["equipamentos_ti"] = [dict(x) for x in con.execute(
            "SELECT * FROM ti_ativos WHERE empresa_id=? AND usuario_responsavel_id=? AND ativo=1 ORDER BY nome",
            (empresa_id, int(usuario_id or 0)),
        ).fetchall()]
        saida["chamados"] = [dict(x) for x in con.execute(
            """SELECT * FROM ti_chamados WHERE empresa_id=? AND
               (solicitante_id=? OR tecnico_id=?) ORDER BY criado_em DESC LIMIT 200""",
            (empresa_id, int(usuario_id or 0), int(usuario_id or 0)),
        ).fetchall()]
        saida["tarefas"] = [dict(x) for x in con.execute(
            """SELECT * FROM tarefas WHERE empresa_id=? AND
               (responsavel_id=? OR (recurso_tipo='rh_colaboradores' AND recurso_id=?))
               AND estado_registro='Ativo' ORDER BY criado_em DESC LIMIT 200""",
            (empresa_id, int(usuario_id or 0), cid),
        ).fetchall()]
        saida["auditoria"] = [dict(x) for x in con.execute(
            """SELECT * FROM core_historico WHERE empresa_id=? AND
               ((recurso_tipo='rh_colaboradores' AND recurso_id=?) OR
                (recurso_tipo='funcionario_360_vinculos' AND recurso_id=?))
               ORDER BY criado_em DESC LIMIT 500""", (empresa_id, cid, cid),
        ).fetchall()]
        vinculo = con.execute(
            "SELECT * FROM funcionario_360_vinculos WHERE empresa_id=? AND colaborador_id=?",
            (empresa_id, cid),
        ).fetchone()
        saida["vinculo"] = dict(vinculo) if vinculo else {}
    return saida


def obter_funcionario_360(
    colaborador_id: int,
    ator: dict,
    *,
    visao: str | None = None,
    finalidade: str = "Consulta do Funcionário 360°",
    request_id: str | None = None,
) -> dict:
    alvo, autorizadas = _contexto_colaborador(int(colaborador_id), ator)
    visao_ativa = _escolher_visao(autorizadas, visao)
    vinculo = garantir_vinculo(int(colaborador_id), ator)
    if tem_permissao_rh(ator, "visualizar", int(colaborador_id)):
        perfil = obter_colaborador(int(colaborador_id), ator, finalidade=finalidade, request_id=request_id)
    else:
        # A visão de TI recebe somente atributos corporativos necessários à operação.
        with conectar() as con:
            row = con.execute(
                """SELECT c.id,c.nome_completo,c.nome_social,c.matricula,c.cargo_texto,c.gestor_id,
                   c.departamento_id,c.centro_custo_id,c.filial_id,c.email_corporativo,c.status,c.etapa_jornada,
                   d.nome departamento_nome,cc.nome centro_custo_nome,f.nome filial_nome,g.nome_completo gestor_nome
                   FROM rh_colaboradores c LEFT JOIN departamentos d ON d.id=c.departamento_id
                   LEFT JOIN centros_custo cc ON cc.id=c.centro_custo_id LEFT JOIN filiais f ON f.id=c.filial_id
                   LEFT JOIN rh_colaboradores g ON g.id=c.gestor_id WHERE c.id=? AND c.empresa_id=?""",
                (int(colaborador_id), int(alvo["empresa_id"])),
            ).fetchone()
        perfil = dict(row)
    listas = _listas_360(int(colaborador_id), int(alvo["empresa_id"]), alvo.get("usuario_id"))
    try:
        documentos_v11 = listar_documentos("rh_colaboradores", int(colaborador_id), ator, modulo="rh")
    except PermissionError:
        documentos_v11 = []
    todas = {
        "identidade": {
            "colaborador_id": int(colaborador_id), "pessoa_id": vinculo.get("pessoa_id"),
            "usuario_id": alvo.get("usuario_id"), "nome": perfil.get("nome_completo"),
            "nome_social": perfil.get("nome_social"), "matricula": perfil.get("matricula"),
            "avatar_midia_id": listas["vinculo"].get("avatar_midia_id"),
        },
        "dados_pessoais": {chave: perfil.get(chave) for chave in (
            "cpf", "rg", "nascimento", "estado_civil", "nacionalidade", "endereco", "telefone",
            "email_pessoal", "contato_emergencia", "dependentes",
        )},
        "profissional": {chave: perfil.get(chave) for chave in (
            "cargo_texto", "cargo_catalogo", "gestor_id", "gestor_nome", "departamento_id", "departamento_nome",
            "centro_custo_id", "centro_custo_nome", "filial_id", "filial_nome", "tipo_contrato", "modalidade",
            "jornada_semanal", "admissao", "status", "etapa_jornada",
        )},
        "contatos": {"email_corporativo": perfil.get("email_corporativo"), "telefone": perfil.get("telefone")},
        "linha_tempo": listas["linha_tempo"] + listas["admissoes"] + listas["desligamentos"],
        "documentos": {"legados": perfil.get("documentos", []), "gerenciados": documentos_v11},
        "jornada": {"pontos": listas["jornada"], "ferias_ausencias": listas["ausencias"]},
        "beneficios": listas["beneficios"],
        "remuneracao": {
            "salario_centavos": perfil.get("salario_centavos"), "banco": perfil.get("banco"),
            "agencia": perfil.get("agencia"), "conta": perfil.get("conta"), "chave_pix": perfil.get("chave_pix"),
            "eventos_folha": listas["folha"], "contracheques": listas["contracheques"],
        },
        "equipamentos": {"rh": listas["equipamentos_rh"], "ti": listas["equipamentos_ti"]},
        "acessos": listas["acessos"],
        "treinamentos": listas["treinamentos"],
        "desempenho": {"avaliacoes": listas["avaliacoes"], "feedbacks": listas["feedbacks"], "pdis": listas["pdis"]},
        "tarefas": listas["tarefas"], "chamados": listas["chamados"], "solicitacoes": listas["solicitacoes"],
        "ocorrencias": listas["ocorrencias"], "custos": listas["custos"], "auditoria": listas["auditoria"],
    }
    secoes = {chave: todas[chave] for chave in SECOES_POR_VISAO[visao_ativa]}
    campos_360: list[str] = []
    if "dados_pessoais" in secoes:
        campos_360.extend(("cpf", "rg", "nascimento", "endereco", "telefone", "email_pessoal", "contato_emergencia", "dependentes"))
    if "remuneracao" in secoes:
        campos_360.extend(("salario_centavos", "banco", "agencia", "conta", "chave_pix"))
    if "documentos" in secoes:
        campos_360.append("documentos")
    registrar_leitura_sensivel(
        ator=ator, modulo="RH", entidade="funcionario_360", entidade_id=int(colaborador_id),
        campos=campos_360, finalidade=finalidade, request_id=request_id,
    )
    return {
        "colaborador_id": int(colaborador_id), "visao": visao_ativa,
        "visoes_disponiveis": sorted(autorizadas), "somente_leitura": visao_ativa == "auditor", "secoes": secoes,
    }


def obter_meu_funcionario_360(ator: dict) -> dict:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as con:
        row = con.execute(
            """SELECT id FROM rh_colaboradores WHERE empresa_id=? AND (filial_id=? OR ? IS NULL)
               AND usuario_id=? ORDER BY id LIMIT 1""", (empresa_id, filial_id, filial_id, int(ator["id"])),
        ).fetchone()
    if row is None:
        raise ValueError("Este usuário ainda não está vinculado a um colaborador.")
    return obter_funcionario_360(int(row["id"]), ator, visao="meu_perfil", finalidade="Autoatendimento do colaborador")


def registrar_avatar_bytes(colaborador_id: int, dados: bytes, nome: str, ator: dict, *, mime_type: str | None = None) -> dict:
    _contexto_colaborador(int(colaborador_id), ator)
    if not (tem_permissao_rh(ator, "editar_colaborador", int(colaborador_id)) or
            int(_contexto_colaborador(int(colaborador_id), ator)[0].get("usuario_id") or 0) == int(ator["id"])):
        raise PermissionError("Você não pode alterar o avatar deste colaborador.")
    vinculo = garantir_vinculo(int(colaborador_id), ator)
    if not vinculo.get("pessoa_id"):
        raise PermissionError("O vínculo mestre precisa ser concluído pelo RH antes do avatar.")
    empresa_id, filial_id = escopo(ator)
    with conectar() as con:
        atual = con.execute(
            "SELECT avatar_midia_id FROM funcionario_360_vinculos WHERE empresa_id=? AND colaborador_id=?",
            (empresa_id, int(colaborador_id)),
        ).fetchone()
    midia = registrar_midia_bytes(
        bytes(dados), nome, ator, modulo="rh", recurso_tipo="rh_colaboradores", recurso_id=int(colaborador_id),
        finalidade="Avatar", titulo=f"Avatar do colaborador {colaborador_id}", classificacao="Confidencial",
        mime_type=mime_type, midia_id=atual["avatar_midia_id"] if atual else None,
    )
    with conectar() as con:
        con.execute(
            "UPDATE funcionario_360_vinculos SET avatar_midia_id=?,atualizado_em=CURRENT_TIMESTAMP WHERE empresa_id=? AND colaborador_id=?",
            (int(midia["id"]), empresa_id, int(colaborador_id)),
        )
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="rh", recurso_tipo="rh_colaboradores",
            recurso_id=int(colaborador_id), acao="Avatar atualizado", ator=ator, depois={"midia_id": int(midia["id"]), "versao": midia["versao"]},
        )
    return midia


def registrar_avatar(colaborador_id: int, caminho: str, ator: dict) -> dict:
    from pathlib import Path
    origem = Path(caminho).expanduser().resolve()
    if not origem.is_file() or origem.is_symlink():
        raise FileNotFoundError("Imagem não encontrada ou não permitida.")
    return registrar_avatar_bytes(int(colaborador_id), origem.read_bytes(), origem.name, ator)


def carregar_avatar(colaborador_id: int, ator: dict, *, miniatura: bool = True) -> tuple[bytes, dict]:
    empresa_id, _ = escopo(ator)
    _contexto_colaborador(int(colaborador_id), ator)
    with conectar() as con:
        row = con.execute(
            "SELECT avatar_midia_id FROM funcionario_360_vinculos WHERE empresa_id=? AND colaborador_id=?",
            (empresa_id, int(colaborador_id)),
        ).fetchone()
    if row is None or not row["avatar_midia_id"]:
        raise ValueError("O colaborador não possui avatar.")
    return carregar_midia_bytes(int(row["avatar_midia_id"]), ator, modulo="rh", miniatura=miniatura)


def registrar_acesso(colaborador_id: int, dados: dict, ator: dict) -> int:
    empresa_id, filial_id = escopo(ator, "ti", "escrever")
    _contexto_colaborador(int(colaborador_id), ator)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO rh_acessos_sistemas
               (empresa_id,colaborador_id,sistema_id,sistema_nome,conta,perfil,origem,status,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (empresa_id, int(colaborador_id), dados.get("sistema_id"), texto(dados.get("sistema_nome"), minimo=2, maximo=150),
             texto(dados.get("conta"), maximo=180), texto(dados.get("perfil"), maximo=100),
             texto(dados.get("origem") or "Manual", maximo=40), texto(dados.get("status") or "Solicitado", maximo=40), int(ator["id"])),
        )
        acesso_id = int(cursor.lastrowid)
        registrar_evento(con, empresa_id=empresa_id, filial_id=filial_id, modulo="ti", tipo="colaborador.acesso_solicitado",
                         recurso_tipo="rh_colaboradores", recurso_id=int(colaborador_id), ator=ator,
                         payload={"acesso_id": acesso_id, "sistema": dados.get("sistema_nome")})
    return acesso_id


def registrar_feedback(colaborador_id: int, dados: dict, ator: dict) -> int:
    empresa_id, _ = escopo(ator, "rh", "escrever"); _contexto_colaborador(int(colaborador_id), ator)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO rh_feedbacks(empresa_id,colaborador_id,autor_id,tipo,titulo,conteudo,visibilidade,data_referencia)
               VALUES (?,?,?,?,?,?,?,?)""",
            (empresa_id, int(colaborador_id), int(ator["id"]), texto(dados.get("tipo") or "Feedback", maximo=40),
             texto(dados.get("titulo"), minimo=2, maximo=180), texto(dados.get("conteudo"), minimo=2, maximo=10000),
             texto(dados.get("visibilidade") or "RH_Gestor", maximo=40), dados.get("data_referencia")),
        )
        return int(cursor.lastrowid)


def registrar_custo(colaborador_id: int, dados: dict, ator: dict) -> int:
    empresa_id, _ = escopo(ator, "financeiro", "escrever"); _contexto_colaborador(int(colaborador_id), ator)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO rh_custos_vinculados
               (empresa_id,colaborador_id,centro_custo_id,categoria,referencia,valor_centavos,recorrente,origem_tipo,origem_id,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, int(colaborador_id), dados.get("centro_custo_id"), texto(dados.get("categoria"), minimo=2, maximo=100),
             texto(dados.get("referencia"), maximo=180), _centavos(dados.get("valor")), int(bool(dados.get("recorrente"))),
             texto(dados.get("origem_tipo"), maximo=80), dados.get("origem_id"), int(ator["id"])),
        )
        return int(cursor.lastrowid)


def registrar_ocorrencia(colaborador_id: int, dados: dict, ator: dict) -> int:
    empresa_id, _ = escopo(ator, "rh", "escrever"); _contexto_colaborador(int(colaborador_id), ator)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO rh_ocorrencias
               (empresa_id,colaborador_id,categoria,titulo,descricao,severidade,confidencial,status,responsavel_id,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, int(colaborador_id), texto(dados.get("categoria"), minimo=2, maximo=80),
             texto(dados.get("titulo"), minimo=2, maximo=180), texto(dados.get("descricao"), maximo=10000),
             texto(dados.get("severidade") or "Baixa", maximo=20), int(dados.get("confidencial", True)),
             texto(dados.get("status") or "Aberta", maximo=40), dados.get("responsavel_id"), int(ator["id"])),
        )
        return int(cursor.lastrowid)


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "carregar_avatar", "garantir_vinculo", "obter_funcionario_360", "obter_meu_funcionario_360",
    "registrar_acesso", "registrar_avatar", "registrar_avatar_bytes", "registrar_custo", "registrar_feedback",
    "registrar_ocorrencia",
)
