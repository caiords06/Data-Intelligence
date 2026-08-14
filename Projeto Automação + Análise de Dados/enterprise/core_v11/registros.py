"""Registros operacionais e BPM configuráveis compartilhados pelos módulos."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from uuid import uuid4

from auth.banco import conectar
from enterprise.core_v11.common import dump, escopo, indexar_recurso, json_objeto, load, registrar_evento, registrar_historico, texto
from enterprise.core_v11.metadados import obter_campos_valores, salvar_campos_valores
from enterprise.core_v11.provisionamento import provisionar_empresa_v11
from enterprise.core_v11.seguranca import exigir_permissao_contextual

PRIORIDADES = {"Baixa", "Media", "Alta", "Critica"}
ESTADOS = {"Ativo", "Arquivado", "Lixeira"}


def _centavos(valor) -> int:
    if valor in (None, ""):
        return 0
    bruto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(bruto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor monetário inválido.") from exc
    if not numero.is_finite():
        raise ValueError("Valor monetário deve ser finito.")
    return int(numero * 100)


def _tipo(con, empresa_id: int, modulo: str, codigo_tipo: str):
    return con.execute(
        """SELECT * FROM v11_tipos_registro WHERE empresa_id=? AND modulo=? AND codigo=? AND ativo=1""",
        (int(empresa_id), str(modulo), str(codigo_tipo)),
    ).fetchone()


def listar_tipos(ator: dict, *, modulo: str | None = None) -> list[dict]:
    empresa_id, _ = escopo(ator)
    filtros = ["empresa_id=?", "ativo=1"]; parametros: list = [empresa_id]
    if modulo:
        escopo(ator, modulo, "ler"); filtros.append("modulo=?"); parametros.append(str(modulo))
    with conectar() as con:
        rows = con.execute(
            f"SELECT * FROM v11_tipos_registro WHERE {' AND '.join(filtros)} ORDER BY modulo,nome",
            tuple(parametros),
        ).fetchall()
    return [
        {**dict(x), "schema": load(x["schema_json"], {}), "configuracao": load(x["configuracao_json"], {})}
        for x in rows
    ]


def salvar_tipo(dados: dict, ator: dict) -> int:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("A configuração de tipos exige administrador.")
    empresa_id, _ = escopo(ator)
    modulo = str(dados.get("modulo") or "").strip().lower(); escopo(ator, modulo, "ler")
    codigo_tipo = str(dados.get("codigo") or "").strip().lower()
    if not codigo_tipo.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Código do tipo inválido.")
    schema = json_objeto(dados.get("schema"), campo="Schema")
    configuracao = json_objeto(dados.get("configuracao"), campo="Configuração")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO v11_tipos_registro
               (empresa_id,modulo,codigo,nome,descricao,icone,schema_json,configuracao_json,fluxo_codigo,criado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(empresa_id,modulo,codigo) DO UPDATE SET
               nome=excluded.nome,descricao=excluded.descricao,icone=excluded.icone,
               schema_json=excluded.schema_json,configuracao_json=excluded.configuracao_json,
               fluxo_codigo=excluded.fluxo_codigo,versao_schema=v11_tipos_registro.versao_schema+1,
               atualizado_em=CURRENT_TIMESTAMP RETURNING id""",
            (
                empresa_id, modulo, codigo_tipo, texto(dados.get("nome"), minimo=2, maximo=120, campo="Nome"),
                texto(dados.get("descricao"), maximo=1000), texto(dados.get("icone"), maximo=20),
                dump(schema), dump(configuracao), str(dados.get("fluxo_codigo") or "")[:80] or None, int(ator["id"]),
            ),
        )
        row = cursor.fetchone()
    return int(row["id"] if hasattr(row, "keys") else row[0])


def _validar_schema(schema: dict, dados: dict) -> None:
    campos = schema.get("campos") or []
    if not isinstance(campos, list):
        raise ValueError("Schema do tipo está corrompido.")
    for campo in campos:
        if not isinstance(campo, dict):
            continue
        chave = str(campo.get("codigo") or "")
        valor = dados.get(chave)
        if campo.get("obrigatorio") and valor in (None, "", []):
            raise ValueError(f"O campo {campo.get('rotulo') or chave} é obrigatório.")
        if campo.get("tipo") == "opcao" and valor not in (None, "") and valor not in (campo.get("opcoes") or []):
            raise ValueError(f"Opção inválida para {campo.get('rotulo') or chave}.")


def _validar_referencias(con, empresa_id: int, dados: dict) -> None:
    referencias = (
        ("responsavel_id", "usuarios", "id"), ("departamento_id", "departamentos", "id"),
        ("centro_custo_id", "centros_custo", "id"), ("pessoa_id", "core_pessoas", "id"),
    )
    for campo, tabela, coluna in referencias:
        valor = dados.get(campo)
        if valor in (None, ""):
            continue
        if tabela == "usuarios":
            existe = con.execute(
                """SELECT 1 FROM usuarios_empresas WHERE usuario_id=? AND empresa_id=? AND ativo=1""",
                (int(valor), empresa_id),
            ).fetchone()
        else:
            existe = con.execute(f"SELECT 1 FROM {tabela} WHERE {coluna}=? AND empresa_id=?", (int(valor), empresa_id)).fetchone()
        if existe is None:
            raise ValueError(f"{campo} não pertence à empresa ativa.")


def _criar_instancia_fluxo(con, registro_id: int, tipo: dict, ator: dict, empresa_id: int) -> str | None:
    fluxo_codigo = tipo.get("fluxo_codigo")
    if not fluxo_codigo:
        return None
    modelo = con.execute(
        """SELECT * FROM v11_fluxos_modelos WHERE empresa_id=? AND codigo=? AND ativo=1
           ORDER BY versao DESC LIMIT 1""", (empresa_id, fluxo_codigo),
    ).fetchone()
    if modelo is None:
        return None
    etapas = load(modelo["etapas_json"], [])
    if not etapas:
        return None
    primeira = etapas[0]
    cursor = con.execute(
        """INSERT INTO v11_fluxos_instancias
           (empresa_id,modelo_id,recurso_tipo,recurso_id,etapa_atual,contexto_json,iniciado_por)
           VALUES (?,?,?,?,?,?,?)""",
        (empresa_id, int(modelo["id"]), "v11_registros_operacionais", int(registro_id), primeira["codigo"], "{}", int(ator["id"])),
    )
    instancia_id = int(cursor.lastrowid)
    for etapa in etapas:
        con.execute(
            """INSERT INTO v11_fluxos_etapas_instancias
               (instancia_id,codigo,titulo,modulo,ordem,status,requer_aprovacao,dados_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                instancia_id, etapa["codigo"], etapa["titulo"], etapa["modulo"], int(etapa["ordem"]),
                "Em andamento" if etapa["codigo"] == primeira["codigo"] else "Pendente",
                int(bool(etapa.get("requer_aprovacao"))), dump(etapa),
            ),
        )
    _materializar_pendencia_etapa(con, instancia_id, int(registro_id), primeira, ator, empresa_id)
    return str(primeira["codigo"])


def _materializar_pendencia_etapa(con, instancia_id: int, registro_id: int, etapa: dict, ator: dict, empresa_id: int) -> None:
    filial_id = ator.get("_filial_id")
    con.execute(
        """INSERT INTO tarefas
           (empresa_id,filial_id,modulo,titulo,descricao,responsavel_id,prioridade,status,recurso_tipo,recurso_id,criado_por)
           VALUES (?,?,?,?,?,?,?,'Pendente','v11_fluxos_instancias',?,?)""",
        (
            empresa_id, filial_id, etapa["modulo"], etapa["titulo"],
            f"Etapa do fluxo operacional do registro #{registro_id}", None, "Alta" if etapa.get("requer_aprovacao") else "Média",
            instancia_id, int(ator["id"]),
        ),
    )
    if etapa.get("requer_aprovacao"):
        con.execute(
            """INSERT INTO aprovacoes
               (empresa_id,filial_id,solicitante_id,modulo,recurso_tipo,recurso_id,titulo,status)
               VALUES (?,?,?,?,?,?,?,'Pendente')""",
            (empresa_id, filial_id, int(ator["id"]), etapa["modulo"], "v11_fluxos_instancias", instancia_id, etapa["titulo"]),
        )


def criar_registro(modulo: str, codigo_tipo: str, dados: dict, ator: dict) -> dict:
    modulo = str(modulo).strip().lower()
    empresa_id, filial_id = escopo(ator, modulo, "escrever")
    provisionar_empresa_v11(empresa_id, ator)
    dados_extras = json_objeto(dados.get("dados"), campo="Dados do registro")
    with conectar() as con:
        tipo_row = _tipo(con, empresa_id, modulo, codigo_tipo)
        if tipo_row is None:
            raise ValueError("Tipo de registro não configurado para este módulo.")
        tipo = dict(tipo_row); _validar_schema(load(tipo["schema_json"], {}), dados_extras)
        _validar_referencias(con, empresa_id, dados)
        prioridade = str(dados.get("prioridade") or "Media").strip().capitalize().replace("Média", "Media").replace("Crítica", "Critica")
        if prioridade not in PRIORIDADES:
            raise ValueError("Prioridade inválida.")
        identificador = f"{modulo[:4].upper()}-{uuid4().hex[:12].upper()}"
        cursor = con.execute(
            """INSERT INTO v11_registros_operacionais
               (empresa_id,filial_id,tipo_id,modulo,codigo,titulo,descricao,status,prioridade,
                responsavel_id,equipe,departamento_id,centro_custo_id,pessoa_id,valor_centavos,
                moeda,inicio,vencimento,dados_json,criado_por,atualizado_por)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                empresa_id, filial_id, int(tipo["id"]), modulo, identificador,
                texto(dados.get("titulo"), minimo=2, maximo=240, campo="Título"),
                texto(dados.get("descricao"), maximo=10000), str(dados.get("status") or "Rascunho")[:80], prioridade,
                int(dados["responsavel_id"]) if dados.get("responsavel_id") not in (None, "") else None,
                texto(dados.get("equipe"), maximo=120), int(dados["departamento_id"]) if dados.get("departamento_id") not in (None, "") else None,
                int(dados["centro_custo_id"]) if dados.get("centro_custo_id") not in (None, "") else None,
                int(dados["pessoa_id"]) if dados.get("pessoa_id") not in (None, "") else None,
                _centavos(dados.get("valor")), str(dados.get("moeda") or "BRL")[:3].upper(),
                dados.get("inicio"), dados.get("vencimento"), dump(dados_extras), int(ator["id"]), int(ator["id"]),
            ),
        )
        registro_id = int(cursor.lastrowid)
        etapa = _criar_instancia_fluxo(con, registro_id, tipo, ator, empresa_id)
        if etapa:
            con.execute("UPDATE v11_registros_operacionais SET etapa=?,status='Em andamento' WHERE id=?", (etapa, registro_id))
        resumo = {"id": registro_id, "codigo": identificador, "titulo": dados.get("titulo"), "tipo": codigo_tipo, "etapa": etapa, "versao_registro": 1}
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo,
            recurso_tipo="v11_registros_operacionais", recurso_id=registro_id, acao="Criado", ator=ator, depois=resumo,
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo, tipo=f"{codigo_tipo}.criado",
            recurso_tipo="v11_registros_operacionais", recurso_id=registro_id, ator=ator, payload=resumo,
        )
        indexar_recurso(
            con, empresa_id=empresa_id, recurso_tipo="v11_registros_operacionais", recurso_id=registro_id,
            modulo=modulo, titulo=str(dados.get("titulo")), subtitulo=f"{tipo['nome']} · {identificador}",
            termos=f"{dados.get('titulo','')} {dados.get('descricao','')} {identificador} {json.dumps(dados_extras, ensure_ascii=False)}",
        )
    if dados.get("campos_personalizados"):
        salvar_campos_valores(
            "v11_registros_operacionais", registro_id, json_objeto(dados["campos_personalizados"]), ator, modulo=modulo,
        )
    from enterprise.workflows import executar_workflows
    executar_workflows(
        modulo, "registro_v11_criado", {**dados_extras, **resumo}, ator,
        recurso_tipo="v11_registros_operacionais", recurso_id=registro_id,
    )
    return resumo


def listar_registros(
    ator: dict,
    *,
    modulo: str | None = None,
    tipo: str | None = None,
    status: str | None = None,
    pesquisa: str = "",
    pagina: int = 1,
    tamanho: int = 50,
    estado: str = "Ativo",
) -> dict:
    empresa_id, filial_id = escopo(ator)
    if modulo:
        escopo(ator, modulo, "ler")
    pagina = max(1, int(pagina)); tamanho = max(1, min(int(tamanho), 200))
    estado = str(estado or "Ativo").strip().title()
    if estado not in ESTADOS | {"Todos"}:
        raise ValueError("Estado do registro inválido.")
    filtros = ["r.empresa_id=?", "(r.filial_id=? OR ? IS NULL OR r.filial_id IS NULL)"]
    parametros: list = [empresa_id, filial_id, filial_id]
    if estado != "Todos":
        filtros.append("r.estado_registro=?"); parametros.append(estado)
    if modulo:
        filtros.append("r.modulo=?"); parametros.append(str(modulo))
    if tipo:
        filtros.append("t.codigo=?"); parametros.append(str(tipo))
    if status:
        filtros.append("r.status=?"); parametros.append(str(status))
    if pesquisa:
        filtros.append("(r.titulo LIKE ? OR r.descricao LIKE ? OR r.codigo LIKE ?)")
        termo = f"%{str(pesquisa).strip()}%"; parametros.extend((termo, termo, termo))
    where = " AND ".join(filtros)
    with conectar() as con:
        total = int(con.execute(
            f"SELECT COUNT(*) total FROM v11_registros_operacionais r JOIN v11_tipos_registro t ON t.id=r.tipo_id WHERE {where}",
            tuple(parametros),
        ).fetchone()["total"])
        rows = con.execute(
            f"""SELECT r.*,t.codigo tipo_codigo,t.nome tipo_nome,u.nome responsavel_nome,d.nome departamento_nome,c.nome centro_custo_nome
                FROM v11_registros_operacionais r JOIN v11_tipos_registro t ON t.id=r.tipo_id
                LEFT JOIN usuarios u ON u.id=r.responsavel_id LEFT JOIN departamentos d ON d.id=r.departamento_id
                LEFT JOIN centros_custo c ON c.id=r.centro_custo_id WHERE {where}
                ORDER BY r.atualizado_em DESC,r.id DESC LIMIT ? OFFSET ?""",
            (*parametros, tamanho, (pagina - 1) * tamanho),
        ).fetchall()
    itens = []
    for row in rows:
        item = dict(row); item["dados"] = load(item.pop("dados_json"), {}); item["valor"] = int(item["valor_centavos"] or 0) / 100
        itens.append(item)
    return {"itens": itens, "total": total, "pagina": pagina, "tamanho": tamanho}


def obter_registro(registro_id: int, ator: dict) -> dict:
    empresa_id, filial_id = escopo(ator)
    with conectar() as con:
        row = con.execute(
            """SELECT r.*,t.codigo tipo_codigo,t.nome tipo_nome,t.schema_json,t.configuracao_json
               FROM v11_registros_operacionais r JOIN v11_tipos_registro t ON t.id=r.tipo_id
               WHERE r.id=? AND r.empresa_id=? AND (r.filial_id=? OR ? IS NULL OR r.filial_id IS NULL)""",
            (int(registro_id), empresa_id, filial_id, filial_id),
        ).fetchone()
        if row is None:
            raise ValueError("Registro operacional não encontrado.")
        exigir_permissao_contextual(ator, row["modulo"], "ler", {"recurso_tipo": "v11_registros_operacionais", "recurso_id": int(registro_id)})
        fluxo = con.execute(
            "SELECT * FROM v11_fluxos_instancias WHERE empresa_id=? AND recurso_tipo='v11_registros_operacionais' AND recurso_id=?",
            (empresa_id, int(registro_id)),
        ).fetchone()
        etapas = [] if fluxo is None else con.execute(
            "SELECT * FROM v11_fluxos_etapas_instancias WHERE instancia_id=? ORDER BY ordem", (int(fluxo["id"]),),
        ).fetchall()
        relacoes = con.execute(
            "SELECT * FROM v11_registro_relacoes WHERE empresa_id=? AND origem_tipo='v11_registros_operacionais' AND origem_id=?",
            (empresa_id, int(registro_id)),
        ).fetchall()
        historico = con.execute(
            "SELECT * FROM core_historico WHERE empresa_id=? AND recurso_tipo='v11_registros_operacionais' AND recurso_id=? ORDER BY id DESC LIMIT 200",
            (empresa_id, int(registro_id)),
        ).fetchall()
    item = dict(row); item["dados"] = load(item.pop("dados_json"), {}); item["schema"] = load(item.pop("schema_json"), {}); item["configuracao"] = load(item.pop("configuracao_json"), {})
    item["valor"] = int(item["valor_centavos"] or 0) / 100
    item["campos_personalizados"] = obter_campos_valores("v11_registros_operacionais", int(registro_id), ator)
    item["fluxo"] = None if fluxo is None else {**dict(fluxo), "contexto": load(fluxo["contexto_json"], {}), "etapas": [dict(x) for x in etapas]}
    item["relacoes"] = [{**dict(x), "dados": load(x["dados_json"], {})} for x in relacoes]
    item["historico"] = [{**dict(x), "antes": load(x["antes_json"], {}), "depois": load(x["depois_json"], {})} for x in historico]
    return item


def atualizar_registro(registro_id: int, dados: dict, ator: dict, *, expected_version: int) -> int:
    atual = obter_registro(registro_id, ator); modulo = atual["modulo"]
    empresa_id, filial_id = escopo(ator); exigir_permissao_contextual(ator, modulo, "escrever", {"recurso_tipo": "v11_registros_operacionais", "recurso_id": int(registro_id)})
    permitidos = {"titulo", "descricao", "status", "prioridade", "responsavel_id", "equipe", "departamento_id", "centro_custo_id", "pessoa_id", "inicio", "vencimento", "dados_json"}
    valores = {k: v for k, v in dados.items() if k in permitidos}
    if "dados_json" in valores:
        valores["dados_json"] = dump(json_objeto(valores["dados_json"]))
    if "titulo" in valores:
        valores["titulo"] = texto(valores["titulo"], minimo=2, maximo=240, campo="Título")
    if not valores:
        raise ValueError("Nenhuma alteração válida informada.")
    with conectar() as con:
        _validar_referencias(con, empresa_id, valores)
        colunas = ",".join(f"{k}=?" for k in valores)
        cursor = con.execute(
            f"""UPDATE v11_registros_operacionais SET {colunas},versao_registro=versao_registro+1,
                atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND empresa_id=? AND versao_registro=?""",
            (*valores.values(), int(ator["id"]), int(registro_id), empresa_id, int(expected_version)),
        )
        if cursor.rowcount != 1:
            raise ValueError("O registro foi alterado por outro usuário. Atualize a página.")
        nova = int(expected_version) + 1
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo,
            recurso_tipo="v11_registros_operacionais", recurso_id=int(registro_id), acao="Atualizado", ator=ator,
            antes={k: atual.get(k) for k in valores}, depois={**valores, "versao_registro": nova},
        )
        indexar_recurso(
            con, empresa_id=empresa_id, recurso_tipo="v11_registros_operacionais", recurso_id=int(registro_id), modulo=modulo,
            titulo=str(valores.get("titulo", atual["titulo"])), subtitulo=atual["codigo"],
            termos=f"{valores.get('titulo', atual['titulo'])} {valores.get('descricao', atual.get('descricao') or '')} {atual['codigo']}",
        )
    return nova


def alterar_estado_registro(
    registro_id: int,
    estado: str,
    ator: dict,
    *,
    expected_version: int,
) -> int:
    """Arquiva, envia à lixeira ou restaura sem apagar evidências e relações."""
    estado = str(estado or "").strip().title()
    if estado not in ESTADOS:
        raise ValueError("Estado deve ser Ativo, Arquivado ou Lixeira.")
    atual = obter_registro(registro_id, ator)
    modulo = str(atual["modulo"])
    empresa_id, filial_id = escopo(ator)
    exigir_permissao_contextual(
        ator, modulo, "escrever",
        {"recurso_tipo": "v11_registros_operacionais", "recurso_id": int(registro_id)},
    )
    if str(atual.get("estado_registro")) == estado:
        return int(atual["versao_registro"])
    with conectar() as con:
        cursor = con.execute(
            """UPDATE v11_registros_operacionais
               SET estado_registro=?,versao_registro=versao_registro+1,
                   atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP
               WHERE id=? AND empresa_id=? AND versao_registro=?""",
            (estado, int(ator["id"]), int(registro_id), empresa_id, int(expected_version)),
        )
        if cursor.rowcount != 1:
            raise ValueError("O registro foi alterado por outro usuário. Atualize a página.")
        nova = int(expected_version) + 1
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo,
            recurso_tipo="v11_registros_operacionais", recurso_id=int(registro_id),
            acao="Restaurado" if estado == "Ativo" else ("Removido" if estado == "Lixeira" else "Arquivado"),
            ator=ator, antes={"estado_registro": atual.get("estado_registro")},
            depois={"estado_registro": estado, "versao_registro": nova},
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=modulo,
            tipo=f"registro.{estado.lower()}", recurso_tipo="v11_registros_operacionais",
            recurso_id=int(registro_id), ator=ator,
            payload={"estado_anterior": atual.get("estado_registro"), "estado": estado},
        )
        if estado == "Lixeira":
            con.execute(
                "DELETE FROM core_busca_indice WHERE empresa_id=? AND recurso_tipo='v11_registros_operacionais' AND recurso_id=?",
                (empresa_id, int(registro_id)),
            )
        else:
            indexar_recurso(
                con, empresa_id=empresa_id, recurso_tipo="v11_registros_operacionais",
                recurso_id=int(registro_id), modulo=modulo, titulo=str(atual["titulo"]),
                subtitulo=str(atual["codigo"]),
                termos=f"{atual['titulo']} {atual.get('descricao') or ''} {atual['codigo']}",
            )
    return nova


def avancar_fluxo(registro_id: int, ator: dict, *, expected_version: int, aprovar: bool = False, observacao: str = "") -> dict:
    registro = obter_registro(registro_id, ator); fluxo = registro.get("fluxo")
    if not fluxo:
        raise ValueError("O registro não possui fluxo configurado.")
    empresa_id, filial_id = escopo(ator)
    atual = next((x for x in fluxo["etapas"] if x["codigo"] == fluxo["etapa_atual"]), None)
    if atual is None or atual["status"] != "Em andamento":
        raise ValueError("Etapa atual inconsistente.")
    acao = "aprovar" if atual["requer_aprovacao"] else "escrever"
    exigir_permissao_contextual(ator, atual["modulo"], acao, {"recurso_tipo": "v11_registros_operacionais", "recurso_id": int(registro_id)})
    if atual["requer_aprovacao"] and not aprovar:
        raise ValueError("Esta etapa exige aprovação humana explícita.")
    proximas = [x for x in fluxo["etapas"] if int(x["ordem"]) > int(atual["ordem"])]
    proxima = min(proximas, key=lambda x: int(x["ordem"])) if proximas else None
    with conectar() as con:
        versao = con.execute("SELECT versao_registro FROM v11_registros_operacionais WHERE id=? AND empresa_id=?", (int(registro_id), empresa_id)).fetchone()
        if versao is None or int(versao["versao_registro"]) != int(expected_version):
            raise ValueError("O fluxo foi alterado por outro usuário. Atualize a página.")
        con.execute(
            """UPDATE v11_fluxos_etapas_instancias SET status='Concluída',concluido_em=CURRENT_TIMESTAMP,
               concluido_por=? WHERE id=? AND status='Em andamento'""", (int(ator["id"]), int(atual["id"])),
        )
        con.execute(
            """UPDATE tarefas SET status='Concluída',atualizado_em=CURRENT_TIMESTAMP
               WHERE recurso_tipo='v11_fluxos_instancias' AND recurso_id=? AND status NOT IN ('Concluída','Cancelada')""",
            (int(fluxo["id"]),),
        )
        if atual["requer_aprovacao"]:
            con.execute(
                """UPDATE aprovacoes SET status='Aprovado',responsavel_id=?,observacao=?,decidido_em=CURRENT_TIMESTAMP,
                   versao_registro=versao_registro+1 WHERE recurso_tipo='v11_fluxos_instancias' AND recurso_id=? AND status='Pendente'""",
                (int(ator["id"]), texto(observacao, maximo=2000), int(fluxo["id"])),
            )
        if proxima:
            con.execute("UPDATE v11_fluxos_etapas_instancias SET status='Em andamento',iniciado_em=CURRENT_TIMESTAMP WHERE id=?", (int(proxima["id"]),))
            con.execute("UPDATE v11_fluxos_instancias SET etapa_atual=? WHERE id=?", (proxima["codigo"], int(fluxo["id"])))
            con.execute(
                """UPDATE v11_registros_operacionais SET etapa=?,status='Em andamento',versao_registro=versao_registro+1,
                   atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
                (proxima["codigo"], int(ator["id"]), int(registro_id)),
            )
            _materializar_pendencia_etapa(con, int(fluxo["id"]), int(registro_id), proxima, ator, empresa_id)
            estado = "Em andamento"; etapa = proxima["codigo"]
        else:
            con.execute("UPDATE v11_fluxos_instancias SET status='Concluído',concluido_em=CURRENT_TIMESTAMP WHERE id=?", (int(fluxo["id"]),))
            con.execute(
                """UPDATE v11_registros_operacionais SET etapa=NULL,status='Concluído',conclusao=CURRENT_TIMESTAMP,
                   versao_registro=versao_registro+1,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
                (int(ator["id"]), int(registro_id)),
            )
            estado = "Concluído"; etapa = None
        registrar_historico(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=registro["modulo"],
            recurso_tipo="v11_registros_operacionais", recurso_id=int(registro_id), acao="Etapa concluída", ator=ator,
            antes={"etapa": atual["codigo"]}, depois={"etapa": etapa, "status": estado, "observacao": observacao},
        )
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo=registro["modulo"], tipo="fluxo.etapa_concluida",
            recurso_tipo="v11_registros_operacionais", recurso_id=int(registro_id), ator=ator,
            payload={"etapa_concluida": atual["codigo"], "proxima_etapa": etapa, "status": estado},
        )
    return {"id": int(registro_id), "status": estado, "etapa": etapa, "versao_registro": int(expected_version) + 1}


def relacionar_registros(
    origem_tipo: str,
    origem_id: int,
    relacao: str,
    destino_tipo: str,
    destino_id: int,
    ator: dict,
    *,
    dados: dict | None = None,
) -> int:
    empresa_id, filial_id = escopo(ator)
    origem_tipo = texto(origem_tipo, minimo=2, maximo=120, campo="Tipo de origem")
    destino_tipo = texto(destino_tipo, minimo=2, maximo=120, campo="Tipo de destino")
    relacao = texto(relacao, minimo=2, maximo=120, campo="Relação")
    with conectar() as con:
        # Registros operacionais são sempre validados no escopo empresarial antes
        # de compor relações. Outros recursos continuam protegidos pelo escopo e
        # pela autorização contextual do caso de uso que cria a relação.
        for tipo_recurso, recurso_id in ((origem_tipo, origem_id), (destino_tipo, destino_id)):
            if tipo_recurso == "v11_registros_operacionais":
                recurso = con.execute(
                    "SELECT modulo FROM v11_registros_operacionais WHERE id=? AND empresa_id=? AND estado_registro='Ativo'",
                    (int(recurso_id), empresa_id),
                ).fetchone()
                if recurso is None:
                    raise ValueError("Um dos registros relacionados não pertence à empresa ativa.")
                exigir_permissao_contextual(
                    ator, str(recurso["modulo"]), "ler",
                    {"recurso_tipo": tipo_recurso, "recurso_id": int(recurso_id)},
                )
        cursor = con.execute(
            """INSERT INTO v11_registro_relacoes
               (empresa_id,origem_tipo,origem_id,relacao,destino_tipo,destino_id,dados_json,criado_por)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(empresa_id,origem_tipo,origem_id,relacao,destino_tipo,destino_id)
               DO UPDATE SET dados_json=excluded.dados_json RETURNING id""",
            (empresa_id, origem_tipo, int(origem_id), relacao, destino_tipo, int(destino_id), dump(json_objeto(dados)), int(ator["id"])),
        )
        row = cursor.fetchone(); relacao_id = int(row["id"] if hasattr(row, "keys") else row[0])
        registrar_evento(
            con, empresa_id=empresa_id, filial_id=filial_id, modulo="automacao", tipo="registros.relacionados",
            recurso_tipo=origem_tipo, recurso_id=int(origem_id), ator=ator,
            payload={"relacao": relacao, "destino_tipo": destino_tipo, "destino_id": int(destino_id)},
        )
    return relacao_id


def resumo_operacional(ator: dict) -> dict:
    empresa_id, filial_id = escopo(ator)
    with conectar() as con:
        modulos = con.execute(
            """SELECT modulo,COUNT(*) total,SUM(valor_centavos) valor_centavos,
               SUM(CASE WHEN status='Concluído' THEN 1 ELSE 0 END) concluidos
               FROM v11_registros_operacionais WHERE empresa_id=? AND (filial_id=? OR ? IS NULL OR filial_id IS NULL)
               AND estado_registro='Ativo' GROUP BY modulo ORDER BY modulo""",
            (empresa_id, filial_id, filial_id),
        ).fetchall()
        pendencias = con.execute(
            """SELECT COUNT(*) total FROM v11_fluxos_etapas_instancias e JOIN v11_fluxos_instancias i ON i.id=e.instancia_id
               WHERE i.empresa_id=? AND e.status='Em andamento'""", (empresa_id,),
        ).fetchone()
    return {"modulos": [dict(x) for x in modulos], "etapas_em_andamento": int(pendencias["total"] or 0)}


from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo

__all__ = (
    "ESTADOS", "PRIORIDADES", "alterar_estado_registro", "atualizar_registro", "avancar_fluxo", "criar_registro",
    "listar_registros", "listar_tipos", "obter_registro", "relacionar_registros", "resumo_operacional", "salvar_tipo",
)
