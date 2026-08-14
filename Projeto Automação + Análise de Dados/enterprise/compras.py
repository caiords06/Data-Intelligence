"""Serviços transacionais de Compras e Suprimentos 2.0.

O processo é orientado por cadeia de custódia: necessidade -> solicitação ->
aprovação -> cotação -> negociação -> pedido -> recebimento -> estoque
e financeiro. Escolha de fornecedor, aprovação e divergências permanecem
decisões humanas; o motor apenas calcula, recomenda e registra evidências.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

import pandas as pd

from enterprise.repositories import conectar
from enterprise.contexto import exigir_permissao, obter_escopo_ator, tem_permissao

from enterprise.domains.compras.base import (
    ACOES_COMPRAS,
    PERFIS_ACOES,
    STATUS_SOLICITACAO,
    STATUS_PEDIDO,
    _texto,
    _centavos,
    _quantidade,
    _data,
    _numero,
    tem_permissao_compras,
    exigir_acao,
    salvar_permissao_acao,
    _evento,
    _notificar,
    _tarefa,
)

def garantir_catalogos(ator: dict) -> dict:
    exigir_permissao(ator, "compras", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        # Migra a tabela V5 apenas como origem; o registro especializado passa
        # a conduzir as próximas etapas sem apagar a informação legada.
        legados = conexao.execute(
            """SELECT * FROM solicitacoes_compra
               WHERE empresa_id=? AND filial_id IS ? ORDER BY id""",
            (empresa_id, filial_id),
        ).fetchall()
        for legado in legados:
            existe = conexao.execute(
                """SELECT id FROM cmp_solicitacoes
                   WHERE empresa_id=? AND origem_recurso_tipo='solicitacoes_compra'
                     AND origem_recurso_id=?""",
                (empresa_id, int(legado["id"])),
            ).fetchone()
            if existe is not None:
                continue
            numero = f"LEG-{int(legado['id']):06d}"
            valor = int(round(float(legado["valor_estimado_centavos"] or 0)))
            solicitacao_id = int(conexao.execute(
                """INSERT INTO cmp_solicitacoes (
                    empresa_id,filial_id,numero,titulo,justificativa,prioridade,
                    centro_custo_id,solicitante_id,valor_estimado_centavos,status,
                    etapa,origem_modulo,origem_recurso_tipo,origem_recurso_id,
                    criado_por
                ) VALUES (?,?,?,?,?,'Normal',?,?,?,?,?,'compras','solicitacoes_compra',?,?)""",
                (empresa_id, filial_id, numero, legado["item"], "Importada da estrutura anterior.",
                 legado["centro_custo_id"], int(legado["criado_por"] or ator["id"]), valor,
                 "Aprovada" if legado["status"] == "Aprovado" else "Em análise",
                 "Aprovação", int(legado["id"]), int(legado["criado_por"] or ator["id"])),
            ).lastrowid)
            quantidade = float(legado["quantidade"] or 1)
            conexao.execute(
                """INSERT INTO cmp_solicitacao_itens (
                    solicitacao_id,descricao,quantidade,unidade,
                    valor_estimado_unitario_centavos,valor_estimado_total_centavos
                ) VALUES (?,?,?,'UN',?,?)""",
                (solicitacao_id, legado["item"], quantidade,
                 round(valor / quantidade) if quantidade else valor, valor),
            )
        return {
            "categorias": [dict(x) for x in conexao.execute(
                "SELECT * FROM cmp_categorias WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)
            ).fetchall()],
            "fornecedores": [dict(x) for x in conexao.execute(
                "SELECT * FROM cmp_fornecedores WHERE empresa_id=? AND ativo=1 ORDER BY razao_social", (empresa_id,)
            ).fetchall()],
            "itens_estoque": [dict(x) for x in conexao.execute(
                "SELECT id,codigo,nome,eh_patrimonio FROM est_itens WHERE empresa_id=? AND status='Ativo' ORDER BY nome", (empresa_id,)
            ).fetchall()],
            "depositos": [dict(x) for x in conexao.execute(
                "SELECT id,codigo,nome FROM est_depositos WHERE empresa_id=? AND filial_id IS ? AND ativo=1 ORDER BY nome", (empresa_id, filial_id)
            ).fetchall()],
            "departamentos": [dict(x) for x in conexao.execute(
                "SELECT id,nome FROM departamentos WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)
            ).fetchall()],
            "centros_custo": [dict(x) for x in conexao.execute(
                "SELECT id,nome,codigo FROM centros_custo WHERE empresa_id=? AND ativo=1 ORDER BY nome", (empresa_id,)
            ).fetchall()],
            "usuarios": [dict(x) for x in conexao.execute(
                """SELECT u.id,u.nome FROM usuarios u JOIN usuarios_empresas ue ON ue.usuario_id=u.id
                   WHERE ue.empresa_id=? AND ue.ativo=1 AND u.ativo=1 ORDER BY u.nome""", (empresa_id,)
            ).fetchall()],
        }


def criar_categoria(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_catalogo")
    empresa_id, _ = obter_escopo_ator(ator)
    codigo = _texto(dados.get("codigo"), 30).upper()
    nome = _texto(dados.get("nome"), 120)
    if not codigo or len(nome) < 2:
        raise ValueError("Informe código e nome da categoria.")
    with conectar() as conexao:
        identificador = int(conexao.execute(
            "INSERT INTO cmp_categorias (empresa_id,codigo,nome,descricao) VALUES (?,?,?,?)",
            (empresa_id, codigo, nome, _texto(dados.get("descricao"), 500) or None),
        ).lastrowid)
        _evento(conexao, ator, "categoria_criada", "cmp_categorias", identificador, depois=dados)
    return identificador


def salvar_regra_aprovacao(dados: dict, ator: dict) -> int:
    """Cria ou atualiza uma alçada sem remover o histórico de aprovações."""
    exigir_acao(ator, "configurar")
    empresa_id, _ = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 120)
    if len(nome) < 3:
        raise ValueError("Informe o nome da alçada.")
    minimo = _centavos(dados.get("valor_minimo") or 0)
    maximo = _centavos(dados["valor_maximo"]) if dados.get("valor_maximo") not in (None, "") else None
    if maximo is not None and maximo < minimo:
        raise ValueError("O valor máximo não pode ser menor que o mínimo.")
    nivel = int(dados.get("nivel") or 1)
    if nivel < 1:
        raise ValueError("O nível deve ser maior que zero.")
    prioridade = _texto(dados.get("prioridade"), 20).title() or None
    if prioridade and prioridade not in {"Baixa", "Normal", "Alta", "Urgente", "Crítica"}:
        raise ValueError("Prioridade de alçada inválida.")
    departamento_id = int(dados["departamento_id"]) if dados.get("departamento_id") else None
    regra_id = int(dados["id"]) if dados.get("id") else None
    with conectar() as conexao:
        if departamento_id and conexao.execute(
            "SELECT 1 FROM departamentos WHERE id=? AND empresa_id=? AND ativo=1",
            (departamento_id, empresa_id),
        ).fetchone() is None:
            raise ValueError("Departamento inválido para esta empresa.")
        if regra_id:
            anterior = conexao.execute(
                "SELECT * FROM cmp_regras_aprovacao WHERE id=? AND empresa_id=?",
                (regra_id, empresa_id),
            ).fetchone()
            if anterior is None:
                raise ValueError("Alçada não encontrada.")
            conexao.execute(
                """UPDATE cmp_regras_aprovacao SET nome=?,valor_minimo_centavos=?,
                   valor_maximo_centavos=?,prioridade=?,departamento_id=?,
                   exige_financeiro=?,exige_diretor=?,nivel=?,ativo=? WHERE id=?""",
                (nome, minimo, maximo, prioridade, departamento_id,
                 int(bool(dados.get("exige_financeiro"))), int(bool(dados.get("exige_diretor"))),
                 nivel, int(bool(dados.get("ativo", True))), regra_id),
            )
            identificador = regra_id
            antes = dict(anterior)
        else:
            identificador = int(conexao.execute(
                """INSERT INTO cmp_regras_aprovacao (
                    empresa_id,nome,valor_minimo_centavos,valor_maximo_centavos,
                    prioridade,departamento_id,exige_financeiro,exige_diretor,nivel,ativo
                ) VALUES (?,?,?,?,?,?,?,?,?,1)""",
                (empresa_id, nome, minimo, maximo, prioridade, departamento_id,
                 int(bool(dados.get("exige_financeiro"))), int(bool(dados.get("exige_diretor"))), nivel),
            ).lastrowid)
            antes = None
        _evento(conexao, ator, "alcada_configurada", "cmp_regras_aprovacao", identificador,
                antes=antes, depois={"nome": nome, "minimo": minimo, "maximo": maximo,
                                      "prioridade": prioridade, "nivel": nivel})
    return identificador


def criar_fornecedor(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_fornecedores")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _texto(dados.get("razao_social") or dados.get("nome"), 180)
    documento = _texto(dados.get("cnpj_cpf") or dados.get("documento"), 30) or None
    if len(nome) < 2:
        raise ValueError("Informe a razão social do fornecedor.")
    with conectar() as conexao:
        estoque_id = conexao.execute(
            "SELECT id FROM est_fornecedores WHERE empresa_id=? AND documento IS ?", (empresa_id, documento)
        ).fetchone() if documento else None
        if estoque_id is None:
            estoque_id = conexao.execute(
                """INSERT INTO est_fornecedores
                   (empresa_id,nome,documento,email,telefone,prazo_medio_dias,avaliacao)
                   VALUES (?,?,?,?,?,?,0)""",
                (empresa_id, nome, documento, _texto(dados.get("email"), 180) or None,
                 _texto(dados.get("telefone"), 50) or None, int(dados.get("prazo_medio_dias") or 0)),
            )
            estoque_fornecedor_id = int(estoque_id.lastrowid)
        else:
            estoque_fornecedor_id = int(estoque_id["id"])
        parte = conexao.execute(
            "SELECT id FROM fin_partes WHERE empresa_id=? AND documento IS ?", (empresa_id, documento)
        ).fetchone() if documento else None
        if parte is None:
            parte_id = int(conexao.execute(
                """INSERT INTO fin_partes (
                    empresa_id,filial_id,tipo,nome,documento,email,telefone,chave_pix,
                    criado_por,atualizado_por
                ) VALUES (?,?,'Fornecedor',?,?,?,?,?,?,?)""",
                (empresa_id, filial_id, nome, documento, _texto(dados.get("email"), 180) or None,
                 _texto(dados.get("telefone"), 50) or None, _texto(dados.get("pix"), 150) or None,
                 int(ator["id"]), int(ator["id"])),
            ).lastrowid)
        else:
            parte_id = int(parte["id"])
        codigo = _texto(dados.get("codigo"), 40).upper() or _numero("FOR")
        identificador = int(conexao.execute(
            """INSERT INTO cmp_fornecedores (
                empresa_id,codigo,razao_social,nome_fantasia,cnpj_cpf,
                inscricao_estadual,inscricao_municipal,endereco,cidade,uf,
                telefone,email,site,categorias,dados_bancarios,pix,
                estoque_fornecedor_id,financeiro_parte_id,criado_por,atualizado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, codigo, nome, _texto(dados.get("nome_fantasia"), 180) or None,
             documento, _texto(dados.get("inscricao_estadual"), 40) or None,
             _texto(dados.get("inscricao_municipal"), 40) or None,
             _texto(dados.get("endereco"), 300) or None, _texto(dados.get("cidade"), 100) or None,
             _texto(dados.get("uf"), 2).upper() or None, _texto(dados.get("telefone"), 50) or None,
             _texto(dados.get("email"), 180) or None, _texto(dados.get("site"), 200) or None,
             _texto(dados.get("categorias"), 500) or None, _texto(dados.get("dados_bancarios"), 500) or None,
             _texto(dados.get("pix"), 150) or None, estoque_fornecedor_id, parte_id,
             int(ator["id"]), int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "fornecedor_criado", "cmp_fornecedores", identificador, depois=dados)
    return identificador


def homologar_fornecedor(fornecedor_id: int, status: str, restricoes: str, ator: dict) -> None:
    exigir_acao(ator, "homologar_fornecedor")
    if status not in {"Em análise", "Homologado", "Homologado com restrições", "Bloqueado", "Inativo"}:
        raise ValueError("Status de homologação inválido.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        fornecedor = conexao.execute(
            "SELECT * FROM cmp_fornecedores WHERE id=? AND empresa_id=?", (int(fornecedor_id), empresa_id)
        ).fetchone()
        if fornecedor is None:
            raise ValueError("Fornecedor não encontrado.")
        conexao.execute(
            """UPDATE cmp_fornecedores SET status_homologacao=?,restricoes=?,
               ativo=?,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (status, _texto(restricoes, 1000) or None, int(status != "Inativo"), int(ator["id"]), int(fornecedor_id)),
        )
        if fornecedor["financeiro_parte_id"]:
            conexao.execute(
                "UPDATE fin_partes SET status=? WHERE id=?",
                ("Bloqueado" if status == "Bloqueado" else "Inativo" if status == "Inativo" else "Ativo",
                 int(fornecedor["financeiro_parte_id"])),
            )
        _evento(conexao, ator, "fornecedor_homologado", "cmp_fornecedores", fornecedor_id,
                antes={"status": fornecedor["status_homologacao"]},
                depois={"status": status, "restricoes": restricoes})


def atualizar_fornecedor(fornecedor_id: int, dados: dict, ator: dict) -> None:
    exigir_acao(ator, "gerenciar_fornecedores")
    empresa_id, _ = obter_escopo_ator(ator)
    permitidos = {
        "razao_social": lambda v: _texto(v, 180),
        "nome_fantasia": lambda v: _texto(v, 180) or None,
        "email": lambda v: _texto(v, 180) or None,
        "telefone": lambda v: _texto(v, 50) or None,
        "categorias": lambda v: _texto(v, 400) or None,
    }
    alteracoes = {k: permitidos[k](v) for k, v in dados.items() if k in permitidos}
    if not alteracoes:
        raise ValueError("Nenhuma alteração válida foi informada.")
    if "razao_social" in alteracoes and len(alteracoes["razao_social"]) < 2:
        raise ValueError("A razão social precisa ter ao menos dois caracteres.")
    with conectar() as conexao:
        antes = conexao.execute("SELECT * FROM cmp_fornecedores WHERE id=? AND empresa_id=?", (int(fornecedor_id), empresa_id)).fetchone()
        if antes is None:
            raise ValueError("Fornecedor não encontrado.")
        campos = dict(alteracoes); campos["atualizado_por"] = int(ator["id"])
        sql = ", ".join(f"{k}=?" for k in campos)
        conexao.execute(f"UPDATE cmp_fornecedores SET {sql},atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (*campos.values(), int(fornecedor_id)))
        _evento(conexao, ator, "fornecedor_atualizado", "cmp_fornecedores", int(fornecedor_id), antes=dict(antes), depois=alteracoes)


def adicionar_contato_fornecedor(fornecedor_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_fornecedores")
    empresa_id, _ = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 120)
    if len(nome) < 2:
        raise ValueError("Informe o nome do contato.")
    with conectar() as conexao:
        if conexao.execute("SELECT 1 FROM cmp_fornecedores WHERE id=? AND empresa_id=?", (int(fornecedor_id), empresa_id)).fetchone() is None:
            raise ValueError("Fornecedor não encontrado.")
        identificador = int(conexao.execute(
            """INSERT INTO cmp_fornecedor_contatos
               (fornecedor_id,tipo,nome,cargo,email,telefone,principal)
               VALUES (?,?,?,?,?,?,?)""",
            (int(fornecedor_id), _texto(dados.get("tipo"), 60) or "Comercial", nome,
             _texto(dados.get("cargo"), 100) or None, _texto(dados.get("email"), 180) or None,
             _texto(dados.get("telefone"), 50) or None, int(bool(dados.get("principal")))),
        ).lastrowid)
        _evento(conexao, ator, "contato_criado", "cmp_fornecedor_contatos", identificador, depois=dados)
    return identificador


def avaliar_fornecedor(fornecedor_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "avaliar_fornecedor")
    empresa_id, filial_id = obter_escopo_ator(ator)
    notas = []
    for campo in ("preco", "prazo", "qualidade", "atendimento", "conformidade"):
        try:
            nota = float(str(dados.get(campo, 0)).replace(",", "."))
        except ValueError as erro:
            raise ValueError("As notas devem ser numéricas entre zero e dez.") from erro
        if not 0 <= nota <= 10:
            raise ValueError("As notas devem ficar entre zero e dez.")
        notas.append(nota)
    score = round(sum(notas) / len(notas), 2)
    with conectar() as conexao:
        fornecedor = conexao.execute("SELECT * FROM cmp_fornecedores WHERE id=? AND empresa_id=?", (int(fornecedor_id), empresa_id)).fetchone()
        if fornecedor is None:
            raise ValueError("Fornecedor não encontrado.")
        identificador = int(conexao.execute(
            """INSERT INTO cmp_fornecedor_avaliacoes (
                empresa_id,filial_id,fornecedor_id,pedido_id,recebimento_id,
                preco,prazo,qualidade,atendimento,conformidade,score,comentario,
                avaliado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, int(fornecedor_id),
             int(dados["pedido_id"]) if dados.get("pedido_id") else None,
             int(dados["recebimento_id"]) if dados.get("recebimento_id") else None,
             *notas, score, _texto(dados.get("comentario"), 1000) or None, int(ator["id"])),
        ).lastrowid)
        media = conexao.execute("SELECT AVG(score) media FROM cmp_fornecedor_avaliacoes WHERE fornecedor_id=?", (int(fornecedor_id),)).fetchone()["media"]
        conexao.execute("UPDATE cmp_fornecedores SET score=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (round(float(media or 0), 2), int(fornecedor_id)))
        if fornecedor["estoque_fornecedor_id"]:
            conexao.execute("UPDATE est_fornecedores SET avaliacao=? WHERE id=?", (round(float(media or 0), 2), int(fornecedor["estoque_fornecedor_id"])))
        _evento(conexao, ator, "fornecedor_avaliado", "cmp_fornecedor_avaliacoes", identificador, depois={**dados, "score": score})
    return identificador


def criar_solicitacao(dados: dict, itens: list[dict], ator: dict, *, enviar=False) -> int:
    exigir_acao(ator, "criar_solicitacao")
    if not itens:
        raise ValueError("Inclua pelo menos um produto ou serviço.")
    titulo = _texto(dados.get("titulo"), 180)
    justificativa = _texto(dados.get("justificativa"), 1500)
    if len(titulo) < 3 or len(justificativa) < 5:
        raise ValueError("Informe título e justificativa da compra.")
    prioridade = _texto(dados.get("prioridade"), 20).title() or "Normal"
    if prioridade not in {"Baixa", "Normal", "Alta", "Urgente", "Crítica"}:
        raise ValueError("Prioridade inválida.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    preparados = []
    total = 0
    for item in itens:
        descricao = _texto(item.get("descricao"), 300)
        if len(descricao) < 2:
            raise ValueError("Descreva cada item solicitado.")
        quantidade = _quantidade(item.get("quantidade"))
        unitario = _centavos(item.get("valor_estimado_unitario") or 0)
        valor_total = round(quantidade * unitario)
        total += valor_total
        preparados.append((item, descricao, quantidade, unitario, valor_total))
    numero = _numero("SOL")
    with conectar() as conexao:
        solicitacao_id = int(conexao.execute(
            """INSERT INTO cmp_solicitacoes (
                empresa_id,filial_id,numero,tipo,titulo,justificativa,prioridade,
                necessario_em,departamento_id,centro_custo_id,solicitante_id,
                gestor_id,valor_estimado_centavos,status,etapa,origem_modulo,
                origem_recurso_tipo,origem_recurso_id,recorrente,recorrencia,
                proxima_recorrencia,criado_por,atualizado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'Rascunho','Necessidade',?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, numero, _texto(dados.get("tipo"), 30) or "Produto",
             titulo, justificativa, prioridade, _data(dados.get("necessario_em")),
             int(dados["departamento_id"]) if dados.get("departamento_id") else None,
             int(dados["centro_custo_id"]) if dados.get("centro_custo_id") else None,
             int(ator["id"]), int(dados["gestor_id"]) if dados.get("gestor_id") else None,
             total, _texto(dados.get("origem_modulo"), 60) or None,
             _texto(dados.get("origem_recurso_tipo"), 80) or None,
             int(dados["origem_recurso_id"]) if dados.get("origem_recurso_id") else None,
             int(bool(dados.get("recorrente"))), _texto(dados.get("recorrencia"), 80) or None,
             _data(dados.get("proxima_recorrencia")), int(ator["id"]), int(ator["id"])),
        ).lastrowid)
        for item, descricao, quantidade, unitario, valor_total in preparados:
            conexao.execute(
                """INSERT INTO cmp_solicitacao_itens (
                    solicitacao_id,estoque_item_id,catalogo_item_id,categoria_id,
                    descricao,especificacao,marca_sugerida,modelo_sugerido,
                    quantidade,unidade,valor_estimado_unitario_centavos,
                    valor_estimado_total_centavos,observacao
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (solicitacao_id, int(item["estoque_item_id"]) if item.get("estoque_item_id") else None,
                 int(item["catalogo_item_id"]) if item.get("catalogo_item_id") else None,
                 int(item["categoria_id"]) if item.get("categoria_id") else None,
                 descricao, _texto(item.get("especificacao"), 1000) or None,
                 _texto(item.get("marca_sugerida"), 120) or None,
                 _texto(item.get("modelo_sugerido"), 120) or None, quantidade,
                 _texto(item.get("unidade"), 20).upper() or "UN", unitario, valor_total,
                 _texto(item.get("observacao"), 500) or None),
            )
        _evento(conexao, ator, "solicitacao_criada", "cmp_solicitacoes", solicitacao_id,
                depois={"numero": numero, "titulo": titulo, "valor_centavos": total})
    if enviar:
        enviar_solicitacao(solicitacao_id, ator)
    return solicitacao_id


def _regra_aprovacao(
    conexao,
    empresa_id: int,
    valor_centavos: int,
    departamento_id=None,
    prioridade=None,
):
    return conexao.execute(
        """SELECT * FROM cmp_regras_aprovacao
           WHERE empresa_id=? AND ativo=1
             AND valor_minimo_centavos<=?
             AND (valor_maximo_centavos IS NULL OR valor_maximo_centavos>=?)
             AND (departamento_id IS NULL OR departamento_id IS ?)
             AND (prioridade IS NULL OR prioridade=?)
           ORDER BY CASE WHEN departamento_id IS NULL THEN 1 ELSE 0 END,
                    CASE WHEN prioridade IS NULL THEN 1 ELSE 0 END,
                    nivel DESC LIMIT 1""",
        (empresa_id, valor_centavos, valor_centavos, departamento_id, prioridade),
    ).fetchone()


def _perfil_aprovacao_compras_valido(ator: dict, perfil_exigido: str) -> bool:
    if str(ator.get("perfil", "")).lower() == "admin":
        return True
    perfil = str(ator.get("perfil_acesso") or "").lower()
    exigido = str(perfil_exigido or "").lower()
    if exigido == "gestor":
        return "gestor" in perfil or perfil in {"diretoria", "rh_diretoria"}
    if exigido == "financeiro":
        return perfil.startswith("financeiro") or perfil in {"compras_plus", "compras_gestor", "diretoria"}
    if exigido in {"diretor", "diretoria"}:
        return perfil in {"diretoria", "rh_diretoria"}
    return perfil == exigido


def _criar_etapas_solicitacao(conexao, solicitacao, regra, ator):
    etapas = ["Gestor"]
    if regra and int(regra["exige_financeiro"] or 0):
        etapas.append("Financeiro")
    if regra and int(regra["exige_diretor"] or 0):
        etapas.append("Diretoria")
    # Evita duplicidade ao reenviar após solicitação de alteração.
    conexao.execute("DELETE FROM cmp_aprovacoes_solicitacao WHERE solicitacao_id=?", (int(solicitacao["id"]),))
    for ordem, perfil in enumerate(etapas, 1):
        conexao.execute(
            """INSERT INTO cmp_aprovacoes_solicitacao
               (empresa_id,filial_id,solicitacao_id,ordem,perfil_aprovador)
               VALUES (?,?,?,?,?)""",
            (int(solicitacao["empresa_id"]), solicitacao["filial_id"], int(solicitacao["id"]), ordem, perfil),
        )
    return etapas


def enviar_solicitacao(solicitacao_id: int, ator: dict) -> int:
    exigir_acao(ator, "enviar_solicitacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        solicitacao = conexao.execute(
            "SELECT * FROM cmp_solicitacoes WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (int(solicitacao_id), empresa_id, filial_id),
        ).fetchone()
        if solicitacao is None or solicitacao["status"] not in {"Rascunho", "Alteração solicitada", "Enviada"}:
            raise ValueError("A solicitação não está disponível para envio.")
        regra = _regra_aprovacao(
            conexao, empresa_id, int(solicitacao["valor_estimado_centavos"]),
            solicitacao["departamento_id"], solicitacao["prioridade"],
        )
        etapas = _criar_etapas_solicitacao(conexao, solicitacao, regra, ator)
        titulo = f"Aprovar {solicitacao['numero']} · {solicitacao['titulo']}"
        aprovacao_id = int(conexao.execute(
            """INSERT INTO aprovacoes (
                empresa_id,filial_id,solicitante_id,modulo,recurso_tipo,
                recurso_id,titulo,valor,status,observacao
            ) VALUES (?,?,?,'compras','cmp_solicitacoes',?,?,?,'Pendente',?)""",
            (empresa_id, filial_id, int(solicitacao["solicitante_id"]), int(solicitacao_id),
             titulo, int(solicitacao["valor_estimado_centavos"]) / 100,
             (f"Alçada: {regra['nome']} · Etapas: {' → '.join(etapas)}" if regra else f"Alçada padrão · Etapas: {' → '.join(etapas)}")),
        ).lastrowid)
        conexao.execute(
            """UPDATE cmp_solicitacoes SET status='Aguardando aprovação',
               etapa='Aprovação',aprovacao_id=?,atualizado_por=?,
               atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (aprovacao_id, int(ator["id"]), int(solicitacao_id)),
        )
        _notificar(conexao, ator, "Solicitação aguardando aprovação", titulo, "aviso", "cmp_solicitacoes", solicitacao_id)
        _evento(conexao, ator, "solicitacao_enviada", "cmp_solicitacoes", solicitacao_id,
                antes={"status": solicitacao["status"]}, depois={"status": "Aguardando aprovação", "aprovacao_id": aprovacao_id})
    return aprovacao_id


def decidir_solicitacao(solicitacao_id: int, decisao: str, comentario: str, ator: dict) -> None:
    exigir_acao(ator, "aprovar_solicitacao")
    if decisao not in {"Aprovar", "Rejeitar", "Solicitar alteração"}:
        raise ValueError("Decisão de aprovação inválida.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        solicitacao = conexao.execute(
            "SELECT * FROM cmp_solicitacoes WHERE id=? AND empresa_id=? AND (filial_id=? OR ? IS NULL)",
            (int(solicitacao_id), empresa_id, filial_id, filial_id),
        ).fetchone()
        if solicitacao is None or solicitacao["status"] != "Aguardando aprovação":
            raise ValueError("A solicitação não está aguardando aprovação.")
        etapa = conexao.execute(
            """SELECT * FROM cmp_aprovacoes_solicitacao
               WHERE solicitacao_id=? AND status='Pendente'
               ORDER BY ordem LIMIT 1""",
            (int(solicitacao_id),),
        ).fetchone()
        if etapa is None:
            # Compatibilidade com solicitações criadas antes da migração.
            regra = _regra_aprovacao(conexao, empresa_id, int(solicitacao["valor_estimado_centavos"]), solicitacao["departamento_id"], solicitacao["prioridade"])
            _criar_etapas_solicitacao(conexao, solicitacao, regra, ator)
            etapa = conexao.execute(
                "SELECT * FROM cmp_aprovacoes_solicitacao WHERE solicitacao_id=? AND status='Pendente' ORDER BY ordem LIMIT 1",
                (int(solicitacao_id),),
            ).fetchone()
        if not _perfil_aprovacao_compras_valido(ator, etapa["perfil_aprovador"]):
            raise PermissionError(f"Esta etapa exige aprovação de: {etapa['perfil_aprovador']}.")

        status_etapa = {"Aprovar": "Aprovado", "Rejeitar": "Rejeitado", "Solicitar alteração": "Alteração solicitada"}[decisao]
        conexao.execute(
            """UPDATE cmp_aprovacoes_solicitacao SET status=?,aprovador_id=?,comentario=?,decidido_em=CURRENT_TIMESTAMP WHERE id=?""",
            (status_etapa, int(ator["id"]), _texto(comentario, 1000), int(etapa["id"])),
        )
        proxima = conexao.execute(
            "SELECT * FROM cmp_aprovacoes_solicitacao WHERE solicitacao_id=? AND status='Pendente' ORDER BY ordem LIMIT 1",
            (int(solicitacao_id),),
        ).fetchone()
        if decisao == "Aprovar" and proxima is not None:
            novo, central = "Aguardando aprovação", "Pendente"
            etapa_texto = f"Aprovação · aguardando {proxima['perfil_aprovador']}"
        elif decisao == "Aprovar":
            novo, central, etapa_texto = "Aprovada", "Aprovado", "Cotação"
        elif decisao == "Rejeitar":
            novo, central, etapa_texto = "Rejeitada", "Rejeitado", "Aprovação"
        else:
            novo, central, etapa_texto = "Alteração solicitada", "Alteração solicitada", "Aprovação"

        conexao.execute(
            """UPDATE cmp_solicitacoes SET status=?,etapa=?,valor_aprovado_centavos=?,
               atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (novo, etapa_texto, int(solicitacao["valor_estimado_centavos"]) if novo == "Aprovada" else 0, int(ator["id"]), int(solicitacao_id)),
        )
        if solicitacao["aprovacao_id"]:
            conexao.execute(
                """UPDATE aprovacoes SET status=?,observacao=?,responsavel_id=?,
                   decidido_em=CASE WHEN ?!='Pendente' THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=?""",
                (central, _texto(comentario, 1000), int(ator["id"]), central, int(solicitacao["aprovacao_id"])),
            )
        _evento(conexao, ator, "solicitacao_decidida", "cmp_solicitacoes", solicitacao_id,
                antes={"status": solicitacao["status"]}, depois={"status": novo, "etapa_aprovacao": etapa["perfil_aprovador"]}, observacao=comentario)

def criar_cotacao(solicitacao_id: int, fornecedor_ids: list[int], dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar_cotacao")
    if not fornecedor_ids:
        raise ValueError("Selecione ao menos um fornecedor para a cotação.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        solicitacao = conexao.execute(
            "SELECT * FROM cmp_solicitacoes WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (int(solicitacao_id), empresa_id, filial_id),
        ).fetchone()
        if solicitacao is None or solicitacao["status"] not in {"Aprovada", "Em cotação"}:
            raise ValueError("Somente solicitação aprovada pode iniciar cotação.")
        fornecedores = []
        for fornecedor_id in dict.fromkeys(map(int, fornecedor_ids)):
            fornecedor = conexao.execute(
                "SELECT * FROM cmp_fornecedores WHERE id=? AND empresa_id=? AND ativo=1",
                (fornecedor_id, empresa_id),
            ).fetchone()
            if fornecedor is None or fornecedor["status_homologacao"] in {"Bloqueado", "Inativo"}:
                raise ValueError("Um fornecedor selecionado está bloqueado, inativo ou fora do contexto.")
            fornecedores.append(fornecedor)
        numero = _numero("COT")
        cotacao_id = int(conexao.execute(
            """INSERT INTO cmp_cotacoes (
                empresa_id,filial_id,numero,solicitacao_id,comprador_id,
                resposta_ate,condicoes_desejadas,valor_referencia_centavos
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, numero, int(solicitacao_id), int(ator["id"]),
             _data(dados.get("resposta_ate")), _texto(dados.get("condicoes_desejadas"), 1000) or None,
             int(solicitacao["valor_estimado_centavos"])),
        ).lastrowid)
        for fornecedor in fornecedores:
            conexao.execute(
                "INSERT INTO cmp_cotacao_fornecedores (cotacao_id,fornecedor_id) VALUES (?,?)",
                (cotacao_id, int(fornecedor["id"])),
            )
        conexao.execute(
            "UPDATE cmp_solicitacoes SET status='Em cotação',etapa='Cotação',comprador_id=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (int(ator["id"]), int(solicitacao_id)),
        )
        _evento(conexao, ator, "cotacao_criada", "cmp_cotacoes", cotacao_id,
                depois={"numero": numero, "fornecedores": fornecedor_ids})
    return cotacao_id


def _recalcular_scores(conexao, cotacao_id: int) -> None:
    propostas = conexao.execute(
        """SELECT cf.*,f.score fornecedor_score FROM cmp_cotacao_fornecedores cf
           JOIN cmp_fornecedores f ON f.id=cf.fornecedor_id
           WHERE cf.cotacao_id=? AND cf.status IN ('Respondida','Em negociação','Selecionada')
             AND cf.valor_total_centavos>0""", (int(cotacao_id),)
    ).fetchall()
    if not propostas:
        return
    menor_valor = min(int(x["valor_total_centavos"]) for x in propostas)
    prazos = [int(x["prazo_entrega_dias"]) for x in propostas if int(x["prazo_entrega_dias"]) > 0]
    menor_prazo = min(prazos) if prazos else 1
    for proposta in propostas:
        score_preco = min(10, 10 * menor_valor / max(1, int(proposta["valor_total_centavos"])))
        prazo = int(proposta["prazo_entrega_dias"] or 0)
        score_prazo = min(10, 10 * menor_prazo / max(1, prazo)) if prazo else 0
        score_qualidade = float(proposta["fornecedor_score"] or 0)
        total = round(score_preco * 0.5 + score_prazo * 0.25 + score_qualidade * 0.25, 2)
        conexao.execute(
            "UPDATE cmp_cotacao_fornecedores SET score_preco=?,score_prazo=?,score_qualidade=?,score_total=? WHERE id=?",
            (round(score_preco, 2), round(score_prazo, 2), score_qualidade, total, int(proposta["id"])),
        )


def registrar_proposta(cotacao_id: int, fornecedor_id: int, dados: dict, itens: list[dict], ator: dict) -> int:
    exigir_acao(ator, "registrar_proposta")
    empresa_id, filial_id = obter_escopo_ator(ator)
    if not itens:
        raise ValueError("Informe os itens e valores da proposta.")
    with conectar() as conexao:
        cotacao = conexao.execute(
            "SELECT * FROM cmp_cotacoes WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (int(cotacao_id), empresa_id, filial_id),
        ).fetchone()
        proposta = conexao.execute(
            """SELECT cf.* FROM cmp_cotacao_fornecedores cf
               WHERE cf.cotacao_id=? AND cf.fornecedor_id=?""",
            (int(cotacao_id), int(fornecedor_id)),
        ).fetchone()
        if cotacao is None or cotacao["status"] != "Em andamento" or proposta is None:
            raise ValueError("Cotação ou fornecedor indisponível para proposta.")
        conexao.execute("DELETE FROM cmp_cotacao_itens WHERE cotacao_fornecedor_id=?", (int(proposta["id"]),))
        subtotal = 0
        for linha in itens:
            solicitacao_item_id = int(linha.get("solicitacao_item_id") or 0)
            solicitado = conexao.execute(
                """SELECT si.* FROM cmp_solicitacao_itens si
                   JOIN cmp_cotacoes c ON c.solicitacao_id=si.solicitacao_id
                   WHERE c.id=? AND si.id=?""", (int(cotacao_id), solicitacao_item_id)
            ).fetchone()
            if solicitado is None:
                raise ValueError("Um item da proposta não pertence à solicitação.")
            quantidade = _quantidade(linha.get("quantidade") or solicitado["quantidade"])
            unitario = _centavos(linha.get("valor_unitario"))
            total = round(quantidade * unitario)
            subtotal += total
            conexao.execute(
                """INSERT INTO cmp_cotacao_itens (
                    cotacao_fornecedor_id,solicitacao_item_id,quantidade,
                    valor_unitario_centavos,valor_total_centavos,marca,modelo,observacao
                ) VALUES (?,?,?,?,?,?,?,?)""",
                (int(proposta["id"]), solicitacao_item_id, quantidade, unitario, total,
                 _texto(linha.get("marca"), 120) or None, _texto(linha.get("modelo"), 120) or None,
                 _texto(linha.get("observacao"), 500) or None),
            )
        frete = _centavos(dados.get("frete") or 0)
        impostos = _centavos(dados.get("impostos") or 0)
        desconto = _centavos(dados.get("desconto") or 0)
        total_final = max(0, subtotal + frete + impostos - desconto)
        conexao.execute(
            """UPDATE cmp_cotacao_fornecedores SET status='Respondida',
               proposta_em=CURRENT_TIMESTAMP,validade_proposta=?,prazo_entrega_dias=?,
               frete_centavos=?,impostos_centavos=?,desconto_centavos=?,
               valor_total_centavos=?,forma_pagamento=?,parcelamento=?,garantia=?,
               condicoes_comerciais=? WHERE id=?""",
            (_data(dados.get("validade_proposta")), int(dados.get("prazo_entrega_dias") or 0),
             frete, impostos, desconto, total_final, _texto(dados.get("forma_pagamento"), 120) or None,
             _texto(dados.get("parcelamento"), 120) or None, _texto(dados.get("garantia"), 200) or None,
             _texto(dados.get("condicoes_comerciais"), 1000) or None, int(proposta["id"])),
        )
        _recalcular_scores(conexao, cotacao_id)
        _evento(conexao, ator, "proposta_registrada", "cmp_cotacao_fornecedores", proposta["id"],
                depois={"valor_centavos": total_final, "fornecedor_id": fornecedor_id})
    return int(proposta["id"])


def registrar_negociacao(proposta_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "negociar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        proposta = conexao.execute(
            """SELECT cf.*,c.empresa_id,c.filial_id FROM cmp_cotacao_fornecedores cf
               JOIN cmp_cotacoes c ON c.id=cf.cotacao_id
               WHERE cf.id=? AND c.empresa_id=? AND c.filial_id IS ?""",
            (int(proposta_id), empresa_id, filial_id),
        ).fetchone()
        if proposta is None or proposta["status"] not in {"Respondida", "Em negociação"}:
            raise ValueError("Proposta indisponível para negociação.")
        anterior = int(proposta["valor_total_centavos"])
        novo = _centavos(dados.get("valor_novo"))
        if novo <= 0:
            raise ValueError("Informe o novo valor negociado.")
        rodada = int(conexao.execute("SELECT COUNT(*) n FROM cmp_negociacoes WHERE cotacao_fornecedor_id=?", (int(proposta_id),)).fetchone()["n"]) + 1
        identificador = int(conexao.execute(
            """INSERT INTO cmp_negociacoes (
                cotacao_fornecedor_id,rodada,proposta_anterior_centavos,
                proposta_nova_centavos,desconto_obtido_centavos,prazo_anterior_dias,
                prazo_novo_dias,condicoes,observacao,responsavel_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (int(proposta_id), rodada, anterior, novo, anterior - novo,
             int(proposta["prazo_entrega_dias"] or 0), int(dados.get("prazo_novo_dias") or proposta["prazo_entrega_dias"] or 0),
             _texto(dados.get("condicoes"), 1000) or None, _texto(dados.get("observacao"), 1000) or None,
             int(ator["id"])),
        ).lastrowid)
        conexao.execute(
            """UPDATE cmp_cotacao_fornecedores SET status='Em negociação',
               valor_total_centavos=?,prazo_entrega_dias=? WHERE id=?""",
            (novo, int(dados.get("prazo_novo_dias") or proposta["prazo_entrega_dias"] or 0), int(proposta_id)),
        )
        _recalcular_scores(conexao, int(proposta["cotacao_id"]))
        _evento(conexao, ator, "negociacao_registrada", "cmp_negociacoes", identificador,
                antes={"valor_centavos": anterior}, depois={"valor_centavos": novo})
    return identificador


def selecionar_fornecedor(cotacao_id: int, fornecedor_id: int, motivo: str, ator: dict) -> None:
    exigir_acao(ator, "selecionar_fornecedor")
    if len(_texto(motivo, 1000)) < 5:
        raise ValueError("Justifique a escolha do fornecedor.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cotacao = conexao.execute(
            "SELECT * FROM cmp_cotacoes WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (int(cotacao_id), empresa_id, filial_id),
        ).fetchone()
        proposta = conexao.execute(
            """SELECT * FROM cmp_cotacao_fornecedores WHERE cotacao_id=?
               AND fornecedor_id=? AND status IN ('Respondida','Em negociação')""",
            (int(cotacao_id), int(fornecedor_id)),
        ).fetchone()
        if cotacao is None or cotacao["status"] != "Em andamento" or proposta is None:
            raise ValueError("A proposta não pode ser selecionada.")
        conexao.execute("UPDATE cmp_cotacao_fornecedores SET selecionado=0,status=CASE WHEN status='Selecionada' THEN 'Respondida' ELSE status END WHERE cotacao_id=?", (int(cotacao_id),))
        conexao.execute("UPDATE cmp_cotacao_fornecedores SET selecionado=1,status='Selecionada' WHERE id=?", (int(proposta["id"]),))
        saving = int(cotacao["valor_referencia_centavos"]) - int(proposta["valor_total_centavos"])
        conexao.execute(
            """UPDATE cmp_cotacoes SET status='Encerrada',fornecedor_selecionado_id=?,
               motivo_escolha=?,valor_selecionado_centavos=?,saving_centavos=?,
               encerrado_em=CURRENT_TIMESTAMP WHERE id=?""",
            (int(fornecedor_id), _texto(motivo, 1000), int(proposta["valor_total_centavos"]), saving, int(cotacao_id)),
        )
        conexao.execute("UPDATE cmp_solicitacoes SET status='Cotada',etapa='Escolha do fornecedor',atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(cotacao["solicitacao_id"]),))
        _evento(conexao, ator, "fornecedor_selecionado", "cmp_cotacoes", cotacao_id,
                depois={"fornecedor_id": fornecedor_id, "valor_centavos": proposta["valor_total_centavos"], "saving_centavos": saving}, observacao=motivo)


def criar_pedido(cotacao_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "criar_pedido")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cotacao = conexao.execute(
            """SELECT c.*,s.departamento_id,s.centro_custo_id FROM cmp_cotacoes c
               JOIN cmp_solicitacoes s ON s.id=c.solicitacao_id
               WHERE c.id=? AND c.empresa_id=? AND c.filial_id IS ?""",
            (int(cotacao_id), empresa_id, filial_id),
        ).fetchone()
        if cotacao is None or cotacao["status"] != "Encerrada" or not cotacao["fornecedor_selecionado_id"]:
            raise ValueError("Finalize a cotação e selecione o fornecedor antes do pedido.")
        existente = conexao.execute("SELECT id FROM cmp_pedidos WHERE cotacao_id=? AND status!='Cancelado'", (int(cotacao_id),)).fetchone()
        if existente:
            raise ValueError("Esta cotação já possui pedido ativo.")
        proposta = conexao.execute(
            "SELECT * FROM cmp_cotacao_fornecedores WHERE cotacao_id=? AND selecionado=1",
            (int(cotacao_id),),
        ).fetchone()
        itens = conexao.execute(
            """SELECT ci.*,si.descricao,si.estoque_item_id,si.unidade FROM cmp_cotacao_itens ci
               JOIN cmp_solicitacao_itens si ON si.id=ci.solicitacao_item_id
               WHERE ci.cotacao_fornecedor_id=? ORDER BY ci.id""", (int(proposta["id"]),)
        ).fetchall()
        if not itens:
            raise ValueError("A proposta selecionada não possui itens.")
        subtotal = sum(int(x["valor_total_centavos"]) for x in itens)
        numero = _numero("PC")
        valor_total = int(proposta["valor_total_centavos"])
        aprovacao_id = int(conexao.execute(
            """INSERT INTO aprovacoes (
                empresa_id,filial_id,solicitante_id,modulo,recurso_tipo,
                recurso_id,titulo,valor,status
            ) VALUES (?,?,?,'compras','cmp_pedidos',0,?,?,'Pendente')""",
            (empresa_id, filial_id, int(ator["id"]), f"Aprovar pedido {numero}", valor_total / 100),
        ).lastrowid)
        pedido_id = int(conexao.execute(
            """INSERT INTO cmp_pedidos (
                empresa_id,filial_id,numero,solicitacao_id,cotacao_id,fornecedor_id,
                comprador_id,departamento_id,centro_custo_id,entrega_endereco,
                entrega_contato,previsao_entrega,condicao_pagamento,vencimento,
                parcelas,subtotal_centavos,frete_centavos,impostos_centavos,
                desconto_centavos,valor_total_centavos,status,aprovacao_id,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'Aguardando aprovação',?,?)""",
            (empresa_id, filial_id, numero, int(cotacao["solicitacao_id"]), int(cotacao_id),
             int(cotacao["fornecedor_selecionado_id"]), int(ator["id"]), cotacao["departamento_id"],
             cotacao["centro_custo_id"], _texto(dados.get("entrega_endereco"), 500) or None,
             _texto(dados.get("entrega_contato"), 180) or None, _data(dados.get("previsao_entrega")),
             _texto(dados.get("condicao_pagamento"), 180) or proposta["forma_pagamento"],
             _data(dados.get("vencimento")), int(dados.get("parcelas") or 1), subtotal,
             int(proposta["frete_centavos"]), int(proposta["impostos_centavos"]),
             int(proposta["desconto_centavos"]), valor_total, aprovacao_id, int(ator["id"])),
        ).lastrowid)
        conexao.execute("UPDATE aprovacoes SET recurso_id=? WHERE id=?", (pedido_id, aprovacao_id))
        for item in itens:
            conexao.execute(
                """INSERT INTO cmp_pedido_itens (
                    pedido_id,solicitacao_item_id,estoque_item_id,descricao,
                    quantidade,unidade,valor_unitario_centavos,valor_total_centavos
                ) VALUES (?,?,?,?,?,?,?,?)""",
                (pedido_id, int(item["solicitacao_item_id"]), item["estoque_item_id"], item["descricao"],
                 float(item["quantidade"]), item["unidade"], int(item["valor_unitario_centavos"]),
                 int(item["valor_total_centavos"])),
            )
        conexao.execute("UPDATE cmp_solicitacoes SET status='Pedido criado',etapa='Pedido de compra',atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(cotacao["solicitacao_id"]),))
        _evento(conexao, ator, "pedido_criado", "cmp_pedidos", pedido_id,
                depois={"numero": numero, "valor_centavos": valor_total, "aprovacao_id": aprovacao_id})
    return pedido_id


def aprovar_pedido(pedido_id: int, aprovar: bool, comentario: str, ator: dict) -> None:
    exigir_acao(ator, "aprovar_pedido")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        pedido = conexao.execute("SELECT * FROM cmp_pedidos WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(pedido_id), empresa_id, filial_id)).fetchone()
        if pedido is None or pedido["status"] != "Aguardando aprovação":
            raise ValueError("Pedido não está aguardando aprovação.")
        novo = "Aprovado" if aprovar else "Cancelado"
        conexao.execute("UPDATE cmp_pedidos SET status=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (novo, int(pedido_id)))
        conexao.execute(
            """UPDATE aprovacoes SET status=?,observacao=?,responsavel_id=?,decidido_em=CURRENT_TIMESTAMP WHERE id=?""",
            ("Aprovado" if aprovar else "Rejeitado", _texto(comentario, 1000), int(ator["id"]), int(pedido["aprovacao_id"])),
        )
        _evento(conexao, ator, "pedido_aprovado" if aprovar else "pedido_rejeitado", "cmp_pedidos", pedido_id,
                antes={"status": pedido["status"]}, depois={"status": novo}, observacao=comentario)


def enviar_pedido(pedido_id: int, ator: dict) -> None:
    exigir_acao(ator, "enviar_pedido")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        pedido = conexao.execute("SELECT * FROM cmp_pedidos WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(pedido_id), empresa_id, filial_id)).fetchone()
        if pedido is None or pedido["status"] != "Aprovado":
            raise ValueError("Somente pedido aprovado pode ser enviado.")
        conexao.execute("UPDATE cmp_pedidos SET status='Enviado ao fornecedor',enviado_em=CURRENT_TIMESTAMP,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(pedido_id),))
        _evento(conexao, ator, "pedido_enviado", "cmp_pedidos", pedido_id,
                antes={"status": pedido["status"]}, depois={"status": "Enviado ao fornecedor"})


def atualizar_status_pedido(pedido_id: int, status: str, ator: dict) -> None:
    exigir_acao(ator, "enviar_pedido")
    if status not in STATUS_PEDIDO:
        raise ValueError("Status de pedido inválido.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        pedido = conexao.execute("SELECT * FROM cmp_pedidos WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(pedido_id), empresa_id, filial_id)).fetchone()
        if pedido is None:
            raise ValueError("Pedido não encontrado.")
        if pedido["status"] in {"Recebido", "Encerrado", "Cancelado"}:
            raise ValueError("Pedido em estado terminal não pode ser reaberto.")
        conexao.execute("UPDATE cmp_pedidos SET status=?,confirmado_em=CASE WHEN ?='Confirmado pelo fornecedor' THEN CURRENT_TIMESTAMP ELSE confirmado_em END,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (status, status, int(pedido_id)))
        _evento(conexao, ator, "pedido_status_alterado", "cmp_pedidos", pedido_id,
                antes={"status": pedido["status"]}, depois={"status": status})


def registrar_recebimento(pedido_id: int, dados: dict, itens: list[dict], ator: dict) -> int:
    exigir_acao(ator, "receber")
    if not itens:
        raise ValueError("Informe os itens recebidos.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    numero = _numero("REC")
    integracao_itens = []
    with conectar() as conexao:
        pedido = conexao.execute(
            "SELECT p.*,f.estoque_fornecedor_id FROM cmp_pedidos p JOIN cmp_fornecedores f ON f.id=p.fornecedor_id WHERE p.id=? AND p.empresa_id=? AND p.filial_id IS ?",
            (int(pedido_id), empresa_id, filial_id),
        ).fetchone()
        if pedido is None or pedido["status"] not in {"Enviado ao fornecedor", "Confirmado pelo fornecedor", "Em produção", "Em transporte", "Parcialmente recebido"}:
            raise ValueError("Pedido não está disponível para recebimento.")
        recebimento_id = int(conexao.execute(
            """INSERT INTO cmp_recebimentos (
                empresa_id,filial_id,numero,pedido_id,fornecedor_id,deposito_id,
                localizacao_id,nota_fiscal,chave_nfe,documento_valor_centavos,
                recebido_em,recebido_por,status,observacao
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'Em conferência',?)""",
            (empresa_id, filial_id, numero, int(pedido_id), int(pedido["fornecedor_id"]),
             int(dados["deposito_id"]) if dados.get("deposito_id") else None,
             int(dados["localizacao_id"]) if dados.get("localizacao_id") else None,
             _texto(dados.get("nota_fiscal"), 100) or None, _texto(dados.get("chave_nfe"), 100) or None,
             _centavos(dados.get("documento_valor") or 0), _data(dados.get("recebido_em") or date.today().isoformat(), obrigatoria=True),
             int(ator["id"]), _texto(dados.get("observacao"), 1000) or None),
        ).lastrowid)
        possui_divergencia = False
        for linha in itens:
            pedido_item = conexao.execute(
                "SELECT * FROM cmp_pedido_itens WHERE id=? AND pedido_id=?",
                (int(linha.get("pedido_item_id") or 0), int(pedido_id)),
            ).fetchone()
            if pedido_item is None:
                raise ValueError("Um item recebido não pertence ao pedido.")
            recebido = _quantidade(linha.get("quantidade_recebida"), permite_zero=True)
            aceito = _quantidade(linha.get("quantidade_aceita"), permite_zero=True)
            recusado = _quantidade(linha.get("quantidade_recusada") or recebido - aceito, permite_zero=True)
            if aceito + recusado > recebido + 1e-9:
                raise ValueError("Aceito e recusado não podem superar a quantidade recebida.")
            pendente = float(pedido_item["quantidade"]) - float(pedido_item["quantidade_recebida"])
            if recebido > pendente + 1e-9:
                raise ValueError("A quantidade recebida supera o saldo pendente do pedido.")
            custo = int(pedido_item["valor_unitario_centavos"])
            recebimento_item_id = int(conexao.execute(
                """INSERT INTO cmp_recebimento_itens (
                    recebimento_id,pedido_item_id,quantidade_recebida,
                    quantidade_aceita,quantidade_recusada,custo_unitario_centavos,
                    lote_numero,fabricacao,validade,seriais_json,motivo_recusa
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (recebimento_id, int(pedido_item["id"]), recebido, aceito, recusado, custo,
                 _texto(linha.get("lote_numero"), 100) or None, _data(linha.get("fabricacao")),
                 _data(linha.get("validade")), json.dumps(linha.get("seriais") or [], ensure_ascii=False),
                 _texto(linha.get("motivo_recusa"), 500) or None),
            ).lastrowid)
            conexao.execute("UPDATE cmp_pedido_itens SET quantidade_recebida=quantidade_recebida+? WHERE id=?", (aceito, int(pedido_item["id"])))
            # Recebimento parcial é um estado válido do pedido. Ele só vira
            # divergência quando existe quantidade efetivamente recusada; o saldo
            # não entregue permanece pendente para um próximo recebimento.
            if recusado > 0:
                possui_divergencia = True
                tipo = "Produto danificado"
                conexao.execute(
                    """INSERT INTO cmp_divergencias (
                        empresa_id,filial_id,recebimento_id,pedido_item_id,tipo,
                        descricao,severidade
                    ) VALUES (?,?,?,?,?,?,?)""",
                    (empresa_id, filial_id, recebimento_id, int(pedido_item["id"]), tipo,
                     _texto(linha.get("motivo_recusa"), 500) or f"Recebido {recebido:g}; aceito {aceito:g}; pendente {pendente:g}.",
                     "Alta"),
                )
            if aceito > 0 and pedido_item["estoque_item_id"]:
                integracao_itens.append({
                    "item_id": int(pedido_item["estoque_item_id"]), "quantidade": aceito,
                    "custo_unitario": custo / 100, "lote_numero": linha.get("lote_numero"),
                    "fabricacao": linha.get("fabricacao"), "validade": linha.get("validade"),
                    "seriais": linha.get("seriais") or [],
                })
        conexao.execute("UPDATE cmp_recebimentos SET possui_divergencia=?,status=? WHERE id=?", (int(possui_divergencia), "Recebido com divergência" if possui_divergencia else "Conferido", recebimento_id))
        saldo = conexao.execute("SELECT COALESCE(SUM(quantidade-quantidade_recebida),0) pendente FROM cmp_pedido_itens WHERE pedido_id=?", (int(pedido_id),)).fetchone()["pendente"]
        novo_status = "Recebido" if float(saldo or 0) <= 1e-9 else "Parcialmente recebido"
        conexao.execute("UPDATE cmp_pedidos SET status=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (novo_status, int(pedido_id)))
        if novo_status == "Recebido":
            conexao.execute("UPDATE cmp_solicitacoes SET status='Recebida',etapa='Financeiro',atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(pedido["solicitacao_id"]),))
        if possui_divergencia:
            _notificar(conexao, ator, "Divergência no recebimento", f"{numero} exige tratamento humano.", "critico", "cmp_recebimentos", recebimento_id)
        _evento(conexao, ator, "recebimento_registrado", "cmp_recebimentos", recebimento_id,
                depois={"numero": numero, "divergencia": possui_divergencia, "pedido_status": novo_status})

    if integracao_itens and dados.get("deposito_id"):
        try:
            from enterprise.estoque import criar_operacao, confirmar_operacao, tem_permissao_estoque
            if not tem_permissao_estoque(ator, "registrar_entrada"):
                raise PermissionError("Usuário sem alçada de entrada no Estoque.")
            operacao_id = criar_operacao(
                {"tipo": "Recebimento de compra", "deposito_destino_id": int(dados["deposito_id"]),
                 "localizacao_destino_id": int(dados["localizacao_id"]) if dados.get("localizacao_id") else None,
                 "fornecedor_id": int(pedido["estoque_fornecedor_id"]) if pedido["estoque_fornecedor_id"] else None,
                 "documento_numero": dados.get("nota_fiscal"), "motivo": f"Recebimento {numero}",
                 "origem_modulo": "compras", "origem_recurso_tipo": "cmp_recebimentos", "origem_recurso_id": recebimento_id},
                integracao_itens, ator,
            )
            confirmar_operacao(operacao_id, ator)
            with conectar() as conexao:
                conexao.execute("UPDATE cmp_recebimentos SET estoque_operacao_id=? WHERE id=?", (operacao_id, recebimento_id))
                _evento(conexao, ator, "recebimento_integrado_estoque", "cmp_recebimentos", recebimento_id, depois={"estoque_operacao_id": operacao_id})
        except (ValueError, PermissionError) as erro:
            with conectar() as conexao:
                _tarefa(conexao, ator, "estoque", f"Integrar recebimento {numero}", str(erro), "cmp_recebimentos", recebimento_id, "Alta")
                _notificar(conexao, ator, "Integração com Estoque pendente", str(erro), "aviso", "cmp_recebimentos", recebimento_id)
    with conectar() as conexao:
        _tarefa(conexao, ator, "financeiro", f"Gerar conta a pagar do {numero}", f"Pedido {pedido['numero']} recebido. Conferir nota fiscal e vencimento.", "cmp_recebimentos", recebimento_id, "Alta")
    return recebimento_id


def integrar_recebimento_financeiro(recebimento_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "integrar_financeiro")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        recebimento = conexao.execute(
            """SELECT r.*,p.numero pedido_numero,p.valor_total_centavos,p.parcelas,
                      p.centro_custo_id,p.departamento_id,f.razao_social,f.financeiro_parte_id
               FROM cmp_recebimentos r JOIN cmp_pedidos p ON p.id=r.pedido_id
               JOIN cmp_fornecedores f ON f.id=r.fornecedor_id
               WHERE r.id=? AND r.empresa_id=? AND r.filial_id IS ?""",
            (int(recebimento_id), empresa_id, filial_id),
        ).fetchone()
        if recebimento is None:
            raise ValueError("Recebimento não encontrado.")
        if recebimento["financeiro_lancamento_id"]:
            raise ValueError("Este recebimento já foi integrado ao Financeiro.")
        recebido = dict(recebimento)
    from enterprise.financeiro import criar_lancamento
    ids = criar_lancamento({
        "natureza": "Conta a pagar", "descricao": f"Pedido {recebido['pedido_numero']} · {recebido['razao_social']}",
        "valor": (int(recebido["documento_valor_centavos"] or 0) or int(recebido["valor_total_centavos"])) / 100,
        "competencia": recebido["recebido_em"], "vencimento": dados.get("vencimento"),
        "parcelas": int(dados.get("parcelas") or recebido["parcelas"] or 1),
        "departamento_id": recebido["departamento_id"], "centro_custo_id": recebido["centro_custo_id"],
        "parte_id": recebido["financeiro_parte_id"], "nota_fiscal": recebido["nota_fiscal"],
        "documento_numero": recebido["pedido_numero"], "origem_modulo": "compras",
        "origem_recurso_tipo": "cmp_recebimentos", "origem_recurso_id": int(recebimento_id),
        "observacoes": f"Gerado pelo recebimento {recebido['numero']}",
    }, ator)
    with conectar() as conexao:
        conexao.execute("UPDATE cmp_recebimentos SET financeiro_lancamento_id=? WHERE id=?", (int(ids[0]), int(recebimento_id)))
        _evento(conexao, ator, "recebimento_integrado_financeiro", "cmp_recebimentos", recebimento_id, depois={"lancamentos": ids})
    return int(ids[0])


def registrar_divergencia_manual(recebimento_id: int, dados: dict, ator: dict) -> int:
    """Registra diferenças de preço, produto, documento, prazo ou conferência."""
    exigir_acao(ator, "resolver_divergencia")
    empresa_id, filial_id = obter_escopo_ator(ator)
    tipo = _texto(dados.get("tipo"), 80)
    descricao = _texto(dados.get("descricao"), 1000)
    severidade = _texto(dados.get("severidade"), 20).title() or "Média"
    if tipo not in {"Quantidade diferente", "Preço divergente", "Produto incorreto",
                    "Produto danificado", "Documento divergente", "Atraso", "Outro"}:
        raise ValueError("Tipo de divergência inválido.")
    if len(descricao) < 5:
        raise ValueError("Descreva a divergência encontrada.")
    if severidade not in {"Baixa", "Média", "Alta", "Crítica"}:
        raise ValueError("Severidade inválida.")
    pedido_item_id = int(dados["pedido_item_id"]) if dados.get("pedido_item_id") else None
    with conectar() as conexao:
        recebimento = conexao.execute(
            "SELECT * FROM cmp_recebimentos WHERE id=? AND empresa_id=? AND filial_id IS ?",
            (int(recebimento_id), empresa_id, filial_id),
        ).fetchone()
        if recebimento is None:
            raise ValueError("Recebimento não encontrado.")
        if pedido_item_id and conexao.execute(
            "SELECT 1 FROM cmp_pedido_itens WHERE id=? AND pedido_id=?",
            (pedido_item_id, int(recebimento["pedido_id"])),
        ).fetchone() is None:
            raise ValueError("O item não pertence ao pedido recebido.")
        identificador = int(conexao.execute(
            """INSERT INTO cmp_divergencias (
                empresa_id,filial_id,recebimento_id,pedido_item_id,tipo,
                descricao,severidade,responsavel_id
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, int(recebimento_id), pedido_item_id, tipo,
             descricao, severidade, int(dados["responsavel_id"]) if dados.get("responsavel_id") else None),
        ).lastrowid)
        conexao.execute(
            "UPDATE cmp_recebimentos SET possui_divergencia=1,status='Recebido com divergência' WHERE id=?",
            (int(recebimento_id),),
        )
        _notificar(conexao, ator, "Divergência no recebimento", descricao, "critico",
                   "cmp_divergencias", identificador)
        _evento(conexao, ator, "divergencia_registrada", "cmp_divergencias", identificador,
                depois={"recebimento_id": recebimento_id, "tipo": tipo,
                         "severidade": severidade, "descricao": descricao})
    return identificador


def resolver_divergencia(divergencia_id: int, resolucao: str, ator: dict) -> None:
    exigir_acao(ator, "resolver_divergencia")
    if len(_texto(resolucao, 1000)) < 3:
        raise ValueError("Descreva a resolução da divergência.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        divergencia = conexao.execute("SELECT * FROM cmp_divergencias WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(divergencia_id), empresa_id, filial_id)).fetchone()
        if divergencia is None or divergencia["status"] != "Aberta":
            raise ValueError("Divergência indisponível.")
        conexao.execute("UPDATE cmp_divergencias SET status='Resolvida',resolucao=?,responsavel_id=?,resolvida_em=CURRENT_TIMESTAMP WHERE id=?", (_texto(resolucao, 1000), int(ator["id"]), int(divergencia_id)))
        pendentes = conexao.execute("SELECT COUNT(*) n FROM cmp_divergencias WHERE recebimento_id=? AND status='Aberta'", (int(divergencia["recebimento_id"]),)).fetchone()["n"]
        if not pendentes:
            conexao.execute("UPDATE cmp_recebimentos SET possui_divergencia=0,status='Conferido' WHERE id=?", (int(divergencia["recebimento_id"]),))
        _evento(conexao, ator, "divergencia_resolvida", "cmp_divergencias", divergencia_id, depois={"resolucao": resolucao})


def criar_contrato(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_contratos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    objeto = _texto(dados.get("objeto"), 500)
    if len(objeto) < 3:
        raise ValueError("Informe o objeto do contrato.")
    inicio = _data(dados.get("inicio"), obrigatoria=True)
    termino = _data(dados.get("termino"), obrigatoria=True)
    if termino < inicio:
        raise ValueError("O término não pode ser anterior ao início.")
    numero = _texto(dados.get("numero"), 60).upper() or _numero("CTR")
    with conectar() as conexao:
        fornecedor = conexao.execute("SELECT id FROM cmp_fornecedores WHERE id=? AND empresa_id=? AND ativo=1", (int(dados.get("fornecedor_id") or 0), empresa_id)).fetchone()
        if fornecedor is None:
            raise ValueError("Selecione um fornecedor ativo.")
        identificador = int(conexao.execute(
            """INSERT INTO cmp_contratos (
                empresa_id,filial_id,numero,fornecedor_id,objeto,responsavel_id,
                departamento_id,inicio,termino,valor_centavos,periodicidade,
                indice_reajuste,percentual_reajuste,renovacao_automatica,
                prazo_cancelamento_dias,status,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, filial_id, numero, int(fornecedor["id"]), objeto,
             int(dados["responsavel_id"]) if dados.get("responsavel_id") else int(ator["id"]),
             int(dados["departamento_id"]) if dados.get("departamento_id") else None,
             inicio, termino, _centavos(dados.get("valor") or 0),
             _texto(dados.get("periodicidade"), 80) or None,
             _texto(dados.get("indice_reajuste"), 80) or None,
             float(str(dados.get("percentual_reajuste") or 0).replace(",", ".")),
             int(bool(dados.get("renovacao_automatica"))), int(dados.get("prazo_cancelamento_dias") or 0),
             _texto(dados.get("status"), 30) or "Ativo", int(ator["id"])),
        ).lastrowid)
        _evento(conexao, ator, "contrato_criado", "cmp_contratos", identificador, depois={**dados, "numero": numero})
    return identificador


def adicionar_aditivo(contrato_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_contratos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        contrato = conexao.execute("SELECT * FROM cmp_contratos WHERE id=? AND empresa_id=? AND filial_id IS ?", (int(contrato_id), empresa_id, filial_id)).fetchone()
        if contrato is None:
            raise ValueError("Contrato não encontrado.")
        valor_novo = _centavos(dados.get("valor_novo") or int(contrato["valor_centavos"]) / 100)
        termino_novo = _data(dados.get("termino_novo")) or contrato["termino"]
        identificador = int(conexao.execute(
            """INSERT INTO cmp_contrato_aditivos (
                contrato_id,numero,tipo,descricao,valor_anterior_centavos,
                valor_novo_centavos,termino_anterior,termino_novo,criado_por
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            (int(contrato_id), _texto(dados.get("numero"), 60) or _numero("ADT"),
             _texto(dados.get("tipo"), 80) or "Alteração", _texto(dados.get("descricao"), 1000),
             int(contrato["valor_centavos"]), valor_novo, contrato["termino"], termino_novo, int(ator["id"])),
        ).lastrowid)
        conexao.execute("UPDATE cmp_contratos SET valor_centavos=?,termino=? WHERE id=?", (valor_novo, termino_novo, int(contrato_id)))
        _evento(conexao, ator, "aditivo_criado", "cmp_contrato_aditivos", identificador,
                antes={"valor_centavos": contrato["valor_centavos"], "termino": contrato["termino"]},
                depois={"valor_centavos": valor_novo, "termino": termino_novo})
    return identificador


def criar_item_catalogo(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerenciar_catalogo")
    empresa_id, _ = obter_escopo_ator(ator)
    descricao = _texto(dados.get("descricao"), 300)
    if len(descricao) < 2:
        raise ValueError("Informe a descrição do item de catálogo.")
    with conectar() as conexao:
        fornecedor = conexao.execute("SELECT * FROM cmp_fornecedores WHERE id=? AND empresa_id=? AND status_homologacao IN ('Homologado','Homologado com restrições')", (int(dados.get("fornecedor_id") or 0), empresa_id)).fetchone()
        if fornecedor is None:
            raise ValueError("O catálogo exige fornecedor homologado.")
        identificador = int(conexao.execute(
            """INSERT INTO cmp_catalogo (
                empresa_id,fornecedor_id,estoque_item_id,categoria_id,codigo,
                descricao,especificacao,unidade,preco_centavos,prazo_dias,
                validade_preco,homologado
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
            (empresa_id, int(fornecedor["id"]), int(dados["estoque_item_id"]) if dados.get("estoque_item_id") else None,
             int(dados["categoria_id"]) if dados.get("categoria_id") else None,
             _texto(dados.get("codigo"), 60).upper() or _numero("CAT"), descricao,
             _texto(dados.get("especificacao"), 1000) or None, _texto(dados.get("unidade"), 20).upper() or "UN",
             _centavos(dados.get("preco") or 0), int(dados.get("prazo_dias") or 0),
             _data(dados.get("validade_preco"))),
        ).lastrowid)
        _evento(conexao, ator, "catalogo_item_criado", "cmp_catalogo", identificador, depois=dados)
    return identificador


def registrar_documento_fornecedor(
    fornecedor_id: int,
    dados: dict,
    caminho_origem: str | Path,
    ator: dict,
) -> int:
    """Armazena o arquivo no repositório corporativo e o vincula ao fornecedor."""
    exigir_acao(ator, "gerenciar_fornecedores")
    empresa_id, _ = obter_escopo_ator(ator)
    tipo = _texto(dados.get("tipo"), 100)
    if len(tipo) < 2:
        raise ValueError("Informe o tipo do documento.")
    validade = _data(dados.get("validade"))
    with conectar() as conexao:
        fornecedor = conexao.execute(
            "SELECT * FROM cmp_fornecedores WHERE id=? AND empresa_id=? AND ativo=1",
            (int(fornecedor_id), empresa_id),
        ).fetchone()
        if fornecedor is None:
            raise ValueError("Fornecedor não encontrado.")
    from enterprise.ferramentas import registrar_documento
    documento_id = registrar_documento(
        str(caminho_origem),
        _texto(dados.get("titulo"), 180) or f"{tipo} · {fornecedor['razao_social']}",
        "compras",
        _texto(dados.get("classificacao"), 30) or "Interno",
        ator,
    )
    try:
        with conectar() as conexao:
            identificador = int(conexao.execute(
                """INSERT INTO cmp_fornecedor_documentos (
                    fornecedor_id,documento_id,tipo,numero,emissao,validade,
                    status,observacao
                ) VALUES (?,?,?,?,?,?,?,?)""",
                (int(fornecedor_id), documento_id, tipo,
                 _texto(dados.get("numero"), 80) or None,
                 _data(dados.get("emissao")), validade,
                 _texto(dados.get("status"), 40) or "Válido",
                 _texto(dados.get("observacao"), 500) or None),
            ).lastrowid)
            _evento(
                conexao, ator, "documento_fornecedor_registrado",
                "cmp_fornecedor_documentos", identificador,
                depois={"fornecedor_id": fornecedor_id, "documento_id": documento_id,
                         "tipo": tipo, "validade": validade},
            )
        return identificador
    except Exception:
        from enterprise.ferramentas import arquivar_documento
        arquivar_documento(documento_id, ator)
        raise


def adicionar_comentario(recurso_tipo: str, recurso_id: int, comentario: str, ator: dict) -> int:
    exigir_permissao(ator, "compras", "ler")
    texto = _texto(comentario, 2000)
    if len(texto) < 2:
        raise ValueError("Informe um comentário.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        identificador = int(conexao.execute(
            "INSERT INTO cmp_comentarios (empresa_id,recurso_tipo,recurso_id,usuario_id,comentario) VALUES (?,?,?,?,?)",
            (empresa_id, _texto(recurso_tipo, 80), int(recurso_id), int(ator["id"]), texto),
        ).lastrowid)
        _evento(conexao, ator, "comentario_adicionado", "cmp_comentarios", identificador, depois={"recurso": recurso_tipo, "id": recurso_id})
    return identificador

# V9.5: consultas/inteligência e relatórios vivem em componentes internos menores.
from enterprise.domains.compras.inteligencia import (
    gerar_alertas_compras, resolver_alerta, resumo_compras, listar_secao,
    obter_itens_solicitacao, obter_itens_pedido, obter_fornecedores_cotacao, analisar_compras,
)
from enterprise.domains.compras.relatorios import (
    exportar_dataframe_compras, gerar_pdf_pedido, gerar_relatorio_compras,
    agendar_relatorio, listar_historico,
)

# V9.1+: em estações Central/Cliente, as APIs transacionais públicas desta fachada
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
