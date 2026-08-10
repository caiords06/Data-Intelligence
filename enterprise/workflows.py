"""Motor seguro de regras empresariais sem execução de código arbitrário."""

from __future__ import annotations

import json

from auth.banco import conectar
from enterprise.catalogo import MODULOS
from enterprise.contexto import exigir_permissao, garantir_contexto_sessao

ACOES_PERMITIDAS = {"notificar", "criar_tarefa", "solicitar_aprovacao"}
OPERADORES = {
    "igual",
    "diferente",
    "maior",
    "maior_igual",
    "menor",
    "menor_igual",
    "contem",
}


def criar_workflow(
    nome: str,
    evento_modulo: str,
    evento_tipo: str,
    condicoes: dict,
    acoes: list[dict],
    ator: dict,
) -> int:
    if not ator or ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem criar workflows.")
    nome = str(nome).strip()
    if len(nome) < 3 or len(nome) > 120:
        raise ValueError("Nome de workflow inválido.")
    if evento_modulo not in MODULOS:
        raise ValueError("Módulo de evento inválido.")
    evento_tipo = str(evento_tipo).strip()
    if not evento_tipo:
        raise ValueError("Tipo de evento obrigatório.")
    _validar_condicoes(condicoes)
    _validar_acoes(acoes)
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO workflows (
                empresa_id, nome, evento_modulo, evento_tipo,
                condicoes_json, acoes_json, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                empresa_id,
                nome,
                evento_modulo,
                evento_tipo,
                json.dumps(condicoes, ensure_ascii=False),
                json.dumps(acoes, ensure_ascii=False),
                ator["id"],
            ),
        )
        return int(cursor.lastrowid)


def listar_workflows(ator: dict) -> list[dict]:
    if not ator or ator.get("perfil") != "admin":
        raise PermissionError("Somente administradores podem consultar workflows.")
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        registros = conexao.execute(
            "SELECT * FROM workflows WHERE empresa_id = ? ORDER BY id DESC",
            (empresa_id,),
        ).fetchall()
    resultado = []
    for item in registros:
        registro = dict(item)
        registro["condicoes"] = json.loads(registro.pop("condicoes_json"))
        registro["acoes"] = json.loads(registro.pop("acoes_json"))
        resultado.append(registro)
    return resultado


def executar_workflows(
    evento_modulo: str,
    evento_tipo: str,
    payload: dict,
    ator: dict,
    *,
    recurso_tipo: str | None = None,
    recurso_id: int | None = None,
) -> list[int]:
    empresa_id, _ = garantir_contexto_sessao()
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT * FROM workflows
            WHERE empresa_id = ? AND evento_modulo = ?
              AND evento_tipo = ? AND ativo = 1
            ORDER BY id
            """,
            (empresa_id, evento_modulo, evento_tipo),
        ).fetchall()
        executados = []
        for registro in registros:
            condicoes = json.loads(registro["condicoes_json"])
            if not _condicoes_atendidas(condicoes, payload):
                continue
            acoes = json.loads(registro["acoes_json"])
            _executar_acoes(
                conexao,
                empresa_id,
                evento_modulo,
                acoes,
                payload,
                ator,
                recurso_tipo,
                recurso_id,
            )
            conexao.execute(
                """
                INSERT INTO atividades (
                    usuario_id, empresa_id, modulo, acao, descricao,
                    recurso_tipo, recurso_id
                ) VALUES (?, ?, ?, 'workflow_executado', ?, ?, ?)
                """,
                (
                    ator.get("id"),
                    empresa_id,
                    evento_modulo,
                    f'Workflow executado: {registro["nome"]}',
                    recurso_tipo,
                    recurso_id,
                ),
            )
            executados.append(int(registro["id"]))
    return executados


def _validar_condicoes(condicoes):
    if not isinstance(condicoes, dict):
        raise ValueError("Condições devem formar um objeto.")
    regras = condicoes.get("todos", [])
    if not isinstance(regras, list):
        raise ValueError("A lista de condições é inválida.")
    for regra in regras:
        if not isinstance(regra, dict) or not str(regra.get("campo", "")).strip():
            raise ValueError("Toda condição precisa de um campo.")
        if regra.get("operador", "igual") not in OPERADORES:
            raise ValueError("Operador de condição não permitido.")


def _validar_acoes(acoes):
    if not isinstance(acoes, list) or not acoes:
        raise ValueError("Informe ao menos uma ação.")
    for acao in acoes:
        if not isinstance(acao, dict) or acao.get("tipo") not in ACOES_PERMITIDAS:
            raise ValueError("Ação de workflow não permitida.")


def _condicoes_atendidas(condicoes, payload):
    for regra in condicoes.get("todos", []):
        atual = payload.get(regra["campo"])
        esperado = regra.get("valor")
        operador = regra.get("operador", "igual")
        if operador == "igual" and atual != esperado:
            return False
        if operador == "diferente" and atual == esperado:
            return False
        if operador == "contem" and str(esperado).casefold() not in str(atual).casefold():
            return False
        if operador in {"maior", "maior_igual", "menor", "menor_igual"}:
            try:
                esquerdo, direito = float(atual), float(esperado)
            except (TypeError, ValueError):
                return False
            comparacoes = {
                "maior": esquerdo > direito,
                "maior_igual": esquerdo >= direito,
                "menor": esquerdo < direito,
                "menor_igual": esquerdo <= direito,
            }
            if not comparacoes[operador]:
                return False
    return True


class _ValoresSeguros(dict):
    def __missing__(self, chave):
        return "{" + chave + "}"


def _texto_template(texto, payload):
    return str(texto or "").format_map(_ValoresSeguros(payload))[:500]


def _executar_acoes(
    conexao,
    empresa_id,
    evento_modulo,
    acoes,
    payload,
    ator,
    recurso_tipo,
    recurso_id,
):
    for acao in acoes:
        tipo = acao["tipo"]
        if tipo == "notificar":
            nivel = acao.get("nivel", "info")
            if nivel not in {"info", "sucesso", "aviso", "critico"}:
                nivel = "info"
            conexao.execute(
                """
                INSERT INTO notificacoes (
                    usuario_id, empresa_id, modulo, titulo, mensagem, nivel,
                    recurso_tipo, recurso_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    acao.get("usuario_id"),
                    empresa_id,
                    acao.get("modulo", evento_modulo),
                    _texto_template(acao.get("titulo", "Alerta automático"), payload),
                    _texto_template(acao.get("mensagem", ""), payload),
                    nivel,
                    recurso_tipo,
                    recurso_id,
                ),
            )
        elif tipo == "criar_tarefa":
            modulo = acao.get("modulo", evento_modulo)
            if modulo not in MODULOS:
                continue
            conexao.execute(
                """
                INSERT INTO tarefas (
                    empresa_id, modulo, titulo, descricao, prioridade,
                    recurso_tipo, recurso_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    empresa_id,
                    modulo,
                    _texto_template(acao.get("titulo", "Tarefa automática"), payload),
                    _texto_template(acao.get("descricao", ""), payload),
                    acao.get("prioridade", "Média"),
                    recurso_tipo,
                    recurso_id,
                ),
            )
        elif tipo == "solicitar_aprovacao":
            campo_valor = str(acao.get("campo_valor", "valor"))
            try:
                valor = max(0.0, float(payload.get(campo_valor, 0) or 0))
            except (TypeError, ValueError):
                valor = 0.0
            conexao.execute(
                """
                INSERT INTO aprovacoes (
                    empresa_id, solicitante_id, modulo, recurso_tipo,
                    recurso_id, titulo, valor
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    empresa_id,
                    ator["id"],
                    evento_modulo,
                    recurso_tipo or "workflow",
                    recurso_id or 0,
                    _texto_template(acao.get("titulo", "Aprovação automática"), payload),
                    valor,
                ),
            )
