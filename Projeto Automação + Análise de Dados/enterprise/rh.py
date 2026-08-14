"""Serviços especializados de Recursos Humanos.

O domínio cobre pessoas, admissão, desligamento, jornada, remuneração,
talentos, documentos, solicitações, relatórios e auditoria. Informações
sensíveis são filtradas conforme a ação e o escopo do usuário.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

import pandas as pd

from auth import banco as banco_auth
from enterprise.repositories import conectar
from enterprise.contexto import obter_escopo_ator, tem_permissao


ACOES_RH = {
    "visualizar": "ler",
    "visualizar_dados_pessoais": "ler",
    "visualizar_remuneracao": "ler",
    "visualizar_equipe": "ler",
    "criar_colaborador": "escrever",
    "editar_colaborador": "escrever",
    "admitir": "escrever",
    "desligar": "aprovar",
    "gerir_jornada": "escrever",
    "aprovar_ferias": "aprovar",
    "gerir_beneficios": "escrever",
    "processar_folha": "escrever",
    "fechar_folha": "aprovar",
    "gerir_talentos": "escrever",
    "gerir_documentos": "escrever",
    "aprovar_solicitacao": "aprovar",
    "exportar": "ler",
    "auditar": "aprovar",
}

SECOES_RECURSOS = {
    "colaboradores": "rh_colaboradores",
    "admissoes": "rh_admissoes",
    "desligamentos": "rh_desligamentos",
    "movimentacoes": "rh_historico_profissional",
    "ponto": "rh_pontos",
    "ferias": "rh_ferias_ausencias",
    "beneficios": "rh_colaborador_beneficios",
    "folha": "rh_folhas",
    "cargos": "rh_cargos",
    "recrutamento": "rh_vagas",
    "desempenho": "rh_avaliacoes",
    "treinamentos": "rh_treinamentos",
    "carreira": "rh_pdis",
    "documentos": "rh_documentos",
    "solicitacoes": "rh_solicitacoes",
}

_ESTADOS_REMOCAO_RH = {
    "colaboradores": ("status", "Removido", "Ativo"),
    "admissoes": ("status", "Removida", "Em andamento"),
    "desligamentos": ("status", "Removido", "Em andamento"),
    "ponto": ("status", "Removido", "Registrado"),
    "ferias": ("status", "Removido", "Solicitado"),
    "beneficios": ("status", "Removido", "Ativo"),
    "folha": ("status", "Removida", "Aberta"),
    "cargos": ("ativo", 0, 1),
    "recrutamento": ("status", "Removida", "Rascunho"),
    "desempenho": ("status", "Removida", "Planejada"),
    "treinamentos": ("ativo", 0, 1),
    "carreira": ("status", "Removido", "Ativo"),
    "documentos": ("status", "Removido", "Ativo"),
    "solicitacoes": ("status", "Removida", "Aberta"),
}


def _texto(valor, limite=500) -> str:
    return " ".join(str(valor or "").strip().split())[:limite]


def _data(valor, *, obrigatoria=False) -> str | None:
    if valor in (None, ""):
        if obrigatoria:
            raise ValueError("Informe a data obrigatória.")
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(valor).strip(), formato).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Data inválida. Utilize DD/MM/AAAA ou AAAA-MM-DD.")


def _centavos(valor) -> int:
    if valor in (None, ""):
        return 0
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", texto):
        texto = texto.replace(".", "")
    try:
        numero = Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as erro:
        raise ValueError(f"Valor monetário inválido: {valor}") from erro
    if not numero.is_finite() or numero < 0:
        raise ValueError("O valor monetário não pode ser negativo.")
    return int(numero * 100)


def _moeda(centavos) -> str:
    valor = int(centavos or 0) / 100
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _caminho_relativo_storage(caminho: str | Path) -> str:
    caminho = Path(caminho).expanduser().resolve()
    raiz = banco_auth.STORAGE_DIR.resolve()
    try:
        return caminho.relative_to(raiz).as_posix()
    except ValueError:
        # Apenas arquivos gerados/copiedos pelo RH devem ser persistidos.
        raise ValueError("O arquivo de RH precisa estar dentro do armazenamento corporativo.")


def _resolver_caminho_storage(valor: str | Path) -> Path:
    caminho = Path(str(valor)).expanduser()
    if caminho.is_absolute():
        # Compatibilidade com registros anteriores à V9.
        return caminho.resolve()
    resolvido = (banco_auth.STORAGE_DIR / caminho).resolve()
    raiz = banco_auth.STORAGE_DIR.resolve()
    if resolvido != raiz and raiz not in resolvido.parents:
        raise ValueError("Caminho de documento de RH inválido.")
    return resolvido


def tem_permissao_rh(ator: dict | None, acao: str, colaborador_id: int | None = None) -> bool:
    acao = str(acao).strip().lower()
    basica = ACOES_RH.get(acao)
    if basica is None or not ator or not ator.get("id"):
        return False
    if str(ator.get("perfil", "")).lower() == "admin":
        return True
    try:
        empresa_id, filial_id = obter_escopo_ator(ator)
    except (PermissionError, RuntimeError):
        return False
    with conectar() as conexao:
        especifica = conexao.execute(
            "SELECT permitido FROM rh_permissoes_acoes WHERE usuario_id=? AND empresa_id=? AND acao=?",
            (int(ator["id"]), empresa_id, acao),
        ).fetchone()
        if especifica is not None:
            permitido = bool(especifica["permitido"])
        else:
            permitido = tem_permissao(ator, "rh", basica)
            # Acesso genérico ao módulo não concede automaticamente dados
            # pessoais, bancários ou salariais. Perfis nativos de RH recebem
            # essa base; qualquer outro perfil exige autorização explícita.
            if acao in {"visualizar_dados_pessoais", "visualizar_remuneracao"}:
                permitido = permitido and str(
                    ator.get("perfil_acesso", "")
                ).lower() in {
                    "rh", "rh_plus", "rh_diretoria", "rh_analista", "rh_auditor"
                }
        perfil_acesso = str(ator.get("perfil_acesso", "")).lower()
        if colaborador_id is None:
            return permitido
        if permitido and perfil_acesso not in {"colaborador", "gestor_pessoas"}:
            return True
        # Portal do colaborador: acesso estritamente ao próprio cadastro.
        proprio = conexao.execute(
            "SELECT id FROM rh_colaboradores WHERE id=? AND empresa_id=? AND (filial_id=? OR ? IS NULL) AND usuario_id=?",
            (int(colaborador_id), empresa_id, filial_id, filial_id, int(ator["id"])),
        ).fetchone()
        if proprio and acao in {
            "visualizar", "visualizar_dados_pessoais", "visualizar_remuneracao"
        }:
            return True
        if permitido and perfil_acesso == "gestor_pessoas" and acao in {
            "visualizar", "visualizar_dados_pessoais", "aprovar_ferias",
            "aprovar_solicitacao", "gerir_talentos",
        }:
            gestor = conexao.execute(
                "SELECT id FROM rh_colaboradores WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) AND usuario_id=?",
                (empresa_id, filial_id, filial_id, int(ator["id"])),
            ).fetchone()
            if gestor is not None:
                equipe = conexao.execute(
                    "SELECT 1 FROM rh_colaboradores WHERE id=? AND empresa_id=? AND (filial_id=? OR ? IS NULL) AND gestor_id=?",
                    (int(colaborador_id), empresa_id, filial_id, filial_id, int(gestor["id"])),
                ).fetchone()
                if equipe:
                    return True
    return False


def exigir_acao(ator: dict | None, acao: str, colaborador_id: int | None = None) -> None:
    if not tem_permissao_rh(ator, acao, colaborador_id):
        raise PermissionError(
            f"Seu perfil não possui permissão de RH para {acao.replace('_', ' ')}."
        )


def salvar_permissao_acao(usuario_id: int, acao: str, permitido: bool, ator: dict) -> None:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Somente administradores configuram permissões de RH.")
    acao = str(acao).strip().lower()
    if acao not in ACOES_RH:
        raise ValueError("Ação de RH inválida.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO rh_permissoes_acoes (usuario_id, empresa_id, acao, permitido, atualizado_por)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(usuario_id, empresa_id, acao) DO UPDATE SET
                permitido=excluded.permitido, atualizado_por=excluded.atualizado_por,
                atualizado_em=CURRENT_TIMESTAMP
            """,
            (int(usuario_id), empresa_id, acao, int(bool(permitido)), int(ator["id"])),
        )


def _evento(conexao, ator, acao, entidade, entidade_id, antes=None, depois=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """
        INSERT INTO historico_alteracoes (
            operacao_id, empresa_id, filial_id, usuario_id, modulo,
            entidade, entidade_id, acao, dados_antes, dados_depois
        ) VALUES (?, ?, ?, ?, 'rh', ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()), empresa_id, filial_id, int(ator["id"]), entidade,
            int(entidade_id), acao,
            json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
            json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None,
        ),
    )
    conexao.execute(
        """INSERT INTO atividades (
            usuario_id, empresa_id, filial_id, modulo, acao, descricao, recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, 'rh', ?, ?, ?, ?)""",
        (int(ator["id"]), empresa_id, filial_id, acao, f"RH: {entidade} #{entidade_id}", entidade, int(entidade_id)),
    )


def _notificar(conexao, ator, titulo, mensagem, nivel="aviso", usuario_id=None, recurso=None, recurso_id=None) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    conexao.execute(
        """INSERT INTO notificacoes (
            empresa_id, filial_id, usuario_id, modulo, titulo, mensagem,
            nivel, recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, 'rh', ?, ?, ?, ?, ?)""",
        (empresa_id, filial_id, usuario_id, titulo, mensagem, nivel, recurso, recurso_id),
    )


def _tarefa(conexao, ator, modulo, titulo, descricao, recurso, recurso_id, prioridade="Média") -> int:
    empresa_id, filial_id = obter_escopo_ator(ator)
    cursor = conexao.execute(
        """INSERT INTO tarefas (
            empresa_id, filial_id, modulo, titulo, descricao, prioridade,
            status, recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, ?, ?, ?, 'Pendente', ?, ?)""",
        (empresa_id, filial_id, modulo, titulo, descricao, prioridade, recurso, int(recurso_id)),
    )
    return int(cursor.lastrowid)


def _aprovacao(conexao, ator, recurso, recurso_id, titulo, valor=0) -> int:
    empresa_id, filial_id = obter_escopo_ator(ator)
    cursor = conexao.execute(
        """INSERT INTO aprovacoes (
            empresa_id, filial_id, solicitante_id, modulo, recurso_tipo,
            recurso_id, titulo, valor, status
        ) VALUES (?, ?, ?, 'rh', ?, ?, ?, ?, 'Pendente')""",
        (empresa_id, filial_id, int(ator["id"]), recurso, int(recurso_id), titulo, float(valor)),
    )
    return int(cursor.lastrowid)


def listar_catalogos(ator: dict) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        consulta = lambda sql, params=(empresa_id,): [dict(x) for x in conexao.execute(sql, params).fetchall()]
        return {
            "filiais": consulta("SELECT id, nome FROM filiais WHERE empresa_id=? AND ativo=1 ORDER BY nome"),
            "departamentos": consulta("SELECT id, nome FROM departamentos WHERE empresa_id=? AND ativo=1 ORDER BY nome"),
            "centros_custo": consulta("SELECT id, codigo, nome FROM centros_custo WHERE empresa_id=? AND ativo=1 ORDER BY nome"),
            "cargos": consulta("SELECT * FROM rh_cargos WHERE empresa_id=? AND ativo=1 ORDER BY titulo"),
            "beneficios": consulta("SELECT * FROM rh_beneficios WHERE empresa_id=? AND ativo=1 ORDER BY nome"),
            "colaboradores": consulta(
                "SELECT id, matricula, nome_completo FROM rh_colaboradores WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) AND status NOT IN ('Desligado','Removido') ORDER BY nome_completo",
                (empresa_id, filial_id, filial_id),
            ),
        }


def _sincronizar_legado(conexao, empresa_id: int, filial_id: int | None) -> None:
    """Importa inclusões feitas pela API genérica após a migração."""
    conexao.execute(
        """
        INSERT INTO rh_colaboradores (
            id, empresa_id, filial_id, departamento_id, centro_custo_id,
            matricula, nome_completo, email_corporativo, cargo_texto,
            admissao, salario_centavos, status, etapa_jornada, criado_por,
            atualizado_por, criado_em, atualizado_em, origem_legado_id
        )
        SELECT
            -id, empresa_id, filial_id, departamento_id, centro_custo_id,
            'LEG-' || printf('%06d', id), nome, email, cargo,
            COALESCE(admissao, substr(criado_em, 1, 10)),
            COALESCE(salario_centavos, ROUND(salario * 100)),
            status, CASE WHEN status='Ativo' THEN 'Ativo' ELSE 'Desligamento' END,
            criado_por, criado_por, criado_em, COALESCE(atualizado_em, criado_em), id
        FROM colaboradores legado
        WHERE legado.empresa_id=? AND (legado.filial_id=? OR ? IS NULL)
          AND legado.estado_registro='Ativo'
          AND NOT EXISTS (
              SELECT 1 FROM rh_colaboradores novo
              WHERE novo.origem_legado_id=legado.id
          )
        """,
        (empresa_id, filial_id, filial_id),
    )


def _validar_ref(conexao, tabela, identificador, empresa_id, *, opcional=True):
    if identificador in (None, ""):
        if opcional:
            return None
        raise ValueError("Referência obrigatória não informada.")
    linha = conexao.execute(f"SELECT id FROM {tabela} WHERE id=? AND empresa_id=?", (int(identificador), empresa_id)).fetchone()
    if linha is None:
        raise ValueError("A referência informada não pertence à empresa atual.")
    return int(linha["id"])


def _registro_no_escopo(conexao, tabela: str, identificador: int, empresa_id: int, filial_id: int | None):
    """Obtém um registro de RH respeitando empresa e, quando aplicável, a filial ativa.

    Contexto corporativo (filial_id=None) pode consultar todas as filiais da empresa;
    um contexto de filial nunca pode atravessar para outra filial.
    """
    colunas = {linha["name"] for linha in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()}
    if "empresa_id" not in colunas:
        raise ValueError(f"Tabela de RH sem escopo empresarial: {tabela}.")
    if "filial_id" in colunas:
        return conexao.execute(
            f"SELECT * FROM {tabela} WHERE id=? AND empresa_id=? AND (filial_id=? OR ? IS NULL)",
            (int(identificador), int(empresa_id), filial_id, filial_id),
        ).fetchone()
    return conexao.execute(
        f"SELECT * FROM {tabela} WHERE id=? AND empresa_id=?",
        (int(identificador), int(empresa_id)),
    ).fetchone()


def _exigir_colaborador_escopo(conexao, colaborador_id: int, empresa_id: int, filial_id: int | None):
    registro = _registro_no_escopo(conexao, "rh_colaboradores", colaborador_id, empresa_id, filial_id)
    if registro is None:
        raise ValueError("Colaborador não encontrado no contexto da empresa/filial atual.")
    return registro


def criar_colaborador(dados: dict, ator: dict, *, iniciar_admissao=False) -> int:
    exigir_acao(ator, "criar_colaborador")
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome_completo") or dados.get("nome"), 180)
    cargo = _texto(dados.get("cargo_texto") or dados.get("cargo"), 150)
    if len(nome) < 3 or len(cargo) < 2:
        raise ValueError("Informe o nome completo e o cargo.")
    admissao = _data(dados.get("admissao") or date.today(), obrigatoria=True)
    matricula = _texto(dados.get("matricula"), 40) or f"RH-{datetime.now():%Y%m%d%H%M%S%f}"
    cpf = re.sub(r"\D", "", str(dados.get("cpf") or "")) or None
    if cpf and len(cpf) != 11:
        raise ValueError("O CPF deve possuir 11 dígitos.")
    with conectar() as conexao:
        departamento_id = _validar_ref(conexao, "departamentos", dados.get("departamento_id"), empresa_id)
        centro_id = _validar_ref(conexao, "centros_custo", dados.get("centro_custo_id"), empresa_id)
        cargo_id = _validar_ref(conexao, "rh_cargos", dados.get("cargo_id"), empresa_id)
        cursor = conexao.execute(
            """
            INSERT INTO rh_colaboradores (
                empresa_id, filial_id, departamento_id, centro_custo_id,
                cargo_id, gestor_id, usuario_id, matricula, nome_completo,
                nome_social, cpf, rg, nascimento, estado_civil, nacionalidade,
                endereco, telefone, email_pessoal, email_corporativo,
                contato_emergencia, cargo_texto, tipo_contrato, modalidade,
                jornada_semanal, admissao, experiencia_fim, salario_centavos,
                banco, agencia, conta, chave_pix, status, etapa_jornada,
                criado_por, atualizado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                empresa_id, int(dados.get("filial_id") or filial_id) if (dados.get("filial_id") or filial_id) else None,
                departamento_id, centro_id, cargo_id,
                int(dados["gestor_id"]) if dados.get("gestor_id") else None,
                int(dados["usuario_id"]) if dados.get("usuario_id") else None,
                matricula, nome, _texto(dados.get("nome_social"), 180) or None,
                cpf, _texto(dados.get("rg"), 30) or None, _data(dados.get("nascimento")),
                _texto(dados.get("estado_civil"), 40) or None,
                _texto(dados.get("nacionalidade"), 80) or None,
                _texto(dados.get("endereco"), 600) or None, _texto(dados.get("telefone"), 40) or None,
                _texto(dados.get("email_pessoal"), 180) or None,
                _texto(dados.get("email_corporativo") or dados.get("email"), 180) or None,
                _texto(dados.get("contato_emergencia"), 250) or None, cargo,
                _texto(dados.get("tipo_contrato") or "CLT", 40),
                _texto(dados.get("modalidade") or "Presencial", 40),
                float(dados.get("jornada_semanal") or 44), admissao,
                _data(dados.get("experiencia_fim")), _centavos(dados.get("salario")),
                _texto(dados.get("banco"), 80) or None, _texto(dados.get("agencia"), 30) or None,
                _texto(dados.get("conta"), 40) or None, _texto(dados.get("chave_pix"), 160) or None,
                "Pré-admissão" if iniciar_admissao else _texto(dados.get("status") or "Ativo", 40),
                "Pré-admissão" if iniciar_admissao else "Ativo",
                int(ator["id"]), int(ator["id"]),
            ),
        )
        colaborador_id = int(cursor.lastrowid)
        _evento(conexao, ator, "colaborador_criado", "rh_colaboradores", colaborador_id, depois={"matricula": matricula, "nome": nome})
        if iniciar_admissao:
            conexao.execute(
                "INSERT INTO rh_admissoes (empresa_id, filial_id, colaborador_id, criado_por) VALUES (?, ?, ?, ?)",
                (empresa_id, filial_id, colaborador_id, int(ator["id"])),
            )
    return colaborador_id


def listar_colaboradores(ator: dict, *, pesquisa="", status="Todos", pagina=1, por_pagina=50) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    filtros = ["c.empresa_id=?", "(c.filial_id=? OR ? IS NULL)"]
    parametros = [empresa_id, filial_id, filial_id]
    perfil_acesso = str(ator.get("perfil_acesso", "")).lower()
    if perfil_acesso == "colaborador":
        filtros.append("c.usuario_id=?")
        parametros.append(int(ator["id"]))
    elif perfil_acesso == "gestor_pessoas":
        filtros.append("(c.usuario_id=? OR c.gestor_id=(SELECT id FROM rh_colaboradores WHERE empresa_id=? AND usuario_id=? LIMIT 1))")
        parametros.extend((int(ator["id"]), empresa_id, int(ator["id"])))
    if pesquisa:
        filtros.append("(c.nome_completo LIKE ? OR c.matricula LIKE ? OR c.cargo_texto LIKE ?)")
        termo = f"%{_texto(pesquisa, 120)}%"
        parametros += [termo, termo, termo]
    if status == "Todos":
        filtros.append("c.status<>'Removido'")
    else:
        filtros.append("c.status=?")
        parametros.append(status)
    limite = max(1, min(int(por_pagina), 200))
    deslocamento = (max(1, int(pagina)) - 1) * limite
    where = " AND ".join(filtros)
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        total = int(conexao.execute(f"SELECT COUNT(*) total FROM rh_colaboradores c WHERE {where}", parametros).fetchone()["total"])
        linhas = conexao.execute(
            f"""SELECT c.id, c.matricula, c.nome_completo, c.nome_social,
                c.cargo_texto, c.status, c.etapa_jornada, c.admissao,
                c.salario_centavos, d.nome departamento_nome, f.nome filial_nome
                FROM rh_colaboradores c
                LEFT JOIN departamentos d ON d.id=c.departamento_id
                LEFT JOIN filiais f ON f.id=c.filial_id
                WHERE {where} ORDER BY c.nome_completo LIMIT ? OFFSET ?""",
            (*parametros, limite, deslocamento),
        ).fetchall()
    registros = [dict(x) for x in linhas]
    if not tem_permissao_rh(ator, "visualizar_remuneracao"):
        for registro in registros:
            registro["salario_centavos"] = None
    return {"registros": registros, "total": total, "pagina": max(1, int(pagina)), "por_pagina": limite}


def obter_colaborador(
    colaborador_id: int,
    ator: dict,
    *,
    finalidade: str = "Gestão do colaborador",
    request_id: str | None = None,
) -> dict:
    exigir_acao(ator, "visualizar", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linha = conexao.execute(
            """SELECT c.*, d.nome departamento_nome, cc.nome centro_custo_nome,
                f.nome filial_nome, g.nome_completo gestor_nome, ca.titulo cargo_catalogo
                FROM rh_colaboradores c
                LEFT JOIN departamentos d ON d.id=c.departamento_id
                LEFT JOIN centros_custo cc ON cc.id=c.centro_custo_id
                LEFT JOIN filiais f ON f.id=c.filial_id
                LEFT JOIN rh_colaboradores g ON g.id=c.gestor_id
                LEFT JOIN rh_cargos ca ON ca.id=c.cargo_id
                WHERE c.id=? AND c.empresa_id=? AND (c.filial_id=? OR ? IS NULL)""",
            (int(colaborador_id), empresa_id, filial_id, filial_id),
        ).fetchone()
        if linha is None:
            raise ValueError("Colaborador não encontrado no contexto atual.")
        resultado = dict(linha)
        resultado["dependentes"] = [dict(x) for x in conexao.execute("SELECT * FROM rh_dependentes WHERE colaborador_id=? ORDER BY nome", (int(colaborador_id),)).fetchall()]
        resultado["historico"] = [dict(x) for x in conexao.execute("SELECT * FROM rh_historico_profissional WHERE colaborador_id=? ORDER BY vigencia DESC, id DESC", (int(colaborador_id),)).fetchall()]
        resultado["beneficios"] = [dict(x) for x in conexao.execute("""SELECT cb.*, b.nome, b.tipo, b.custo_empresa_centavos, b.desconto_colaborador_centavos
            FROM rh_colaborador_beneficios cb JOIN rh_beneficios b ON b.id=cb.beneficio_id
            WHERE cb.colaborador_id=? ORDER BY cb.inicio DESC""", (int(colaborador_id),)).fetchall()]
        resultado["documentos"] = [dict(x) for x in conexao.execute("SELECT * FROM rh_documentos WHERE colaborador_id=? AND status='Ativo' ORDER BY criado_em DESC", (int(colaborador_id),)).fetchall()]
        resultado["equipamentos"] = [dict(x) for x in conexao.execute("SELECT * FROM rh_equipamentos WHERE colaborador_id=? ORDER BY entregue_em DESC", (int(colaborador_id),)).fetchall()]
    campos_lidos: list[str] = []
    if not tem_permissao_rh(ator, "visualizar_remuneracao", colaborador_id):
        for campo in ("salario_centavos", "banco", "agencia", "conta", "chave_pix"):
            resultado[campo] = None
    else:
        campos_lidos.extend(("salario_centavos", "banco", "agencia", "conta", "chave_pix"))
    if not tem_permissao_rh(ator, "visualizar_dados_pessoais", colaborador_id):
        for campo in ("cpf", "rg", "nascimento", "endereco", "telefone", "email_pessoal", "contato_emergencia"):
            resultado[campo] = None
        resultado["dependentes"] = []
        resultado["documentos"] = []
    else:
        campos_lidos.extend((
            "cpf", "rg", "nascimento", "endereco", "telefone", "email_pessoal",
            "contato_emergencia", "dependentes", "documentos",
        ))
    if campos_lidos:
        from enterprise.privacidade import registrar_leitura_sensivel
        registrar_leitura_sensivel(
            ator=ator, modulo="RH", entidade="colaborador", entidade_id=int(colaborador_id),
            campos=campos_lidos, finalidade=finalidade, request_id=request_id,
        )
    return resultado


def atualizar_colaborador(colaborador_id: int, dados: dict, ator: dict) -> None:
    exigir_acao(ator, "editar_colaborador", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    campos = {
        "nome_completo": lambda x: _texto(x, 180), "nome_social": lambda x: _texto(x, 180) or None,
        "cargo_texto": lambda x: _texto(x, 150), "email_corporativo": lambda x: _texto(x, 180) or None,
        "telefone": lambda x: _texto(x, 40) or None, "status": lambda x: _texto(x, 40),
        "tipo_contrato": lambda x: _texto(x, 40), "modalidade": lambda x: _texto(x, 40),
        "salario": _centavos, "departamento_id": lambda x: int(x) if x else None,
        "centro_custo_id": lambda x: int(x) if x else None, "cargo_id": lambda x: int(x) if x else None,
        "gestor_id": lambda x: int(x) if x else None,
    }
    with conectar() as conexao:
        atual = _registro_no_escopo(conexao, "rh_colaboradores", colaborador_id, empresa_id, filial_id)
        if atual is None:
            raise ValueError("Colaborador não encontrado.")
        alteracoes = {}
        for nome, conversor in campos.items():
            if nome not in dados:
                continue
            coluna = "salario_centavos" if nome == "salario" else nome
            novo = conversor(dados[nome])
            if atual[coluna] != novo:
                alteracoes[coluna] = novo
        if not alteracoes:
            return
        antes = {campo: atual[campo] for campo in alteracoes}
        atribuicoes = ", ".join(f"{campo}=?" for campo in alteracoes)
        conexao.execute(
            f"UPDATE rh_colaboradores SET {atribuicoes}, atualizado_por=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (*alteracoes.values(), int(ator["id"]), int(colaborador_id)),
        )
        conexao.execute(
            """INSERT INTO rh_historico_profissional (
                empresa_id, filial_id, colaborador_id, tipo, vigencia,
                dados_antes, dados_depois, criado_por
            ) VALUES (?, ?, ?, 'Alteração cadastral', ?, ?, ?, ?)""",
            (empresa_id, atual["filial_id"], int(colaborador_id), date.today().isoformat(), json.dumps(antes, ensure_ascii=False), json.dumps(alteracoes, ensure_ascii=False), int(ator["id"])),
        )
        _evento(conexao, ator, "colaborador_atualizado", "rh_colaboradores", colaborador_id, antes, alteracoes)


def alterar_estado_registro_rh(secao: str, registro_id: int, remover: bool, ator: dict) -> None:
    """Move um item de RH para a lixeira ou o restaura, sempre com auditoria."""
    exigir_acao(ator, "editar_colaborador")
    secao = str(secao or "").strip().lower()
    if secao == "movimentacoes":
        raise ValueError("Movimentações profissionais são evidências de auditoria e não podem ser removidas.")
    configuracao = _ESTADOS_REMOCAO_RH.get(secao)
    tabela = SECOES_RECURSOS.get(secao)
    if configuracao is None or tabela is None:
        raise ValueError("Esta seção ainda não possui remoção controlada.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    campo, valor_removido, valor_restaurado = configuracao
    with conectar() as conexao:
        if secao == "beneficios":
            atual = conexao.execute(
                """SELECT cb.* FROM rh_colaborador_beneficios cb
                   JOIN rh_colaboradores c ON c.id=cb.colaborador_id
                   WHERE cb.id=? AND c.empresa_id=? AND (c.filial_id=? OR ? IS NULL)""",
                (int(registro_id), empresa_id, filial_id, filial_id),
            ).fetchone()
        elif secao == "carreira":
            atual = conexao.execute(
                """SELECT p.* FROM rh_pdis p JOIN rh_colaboradores c ON c.id=p.colaborador_id
                   WHERE p.id=? AND c.empresa_id=? AND (c.filial_id=? OR ? IS NULL)""",
                (int(registro_id), empresa_id, filial_id, filial_id),
            ).fetchone()
        else:
            atual = _registro_no_escopo(conexao, tabela, int(registro_id), empresa_id, filial_id)
        if atual is None:
            raise ValueError("Registro de RH não encontrado no contexto atual.")
        novo = valor_removido if remover else valor_restaurado
        if atual[campo] == novo:
            return
        conexao.execute(f"UPDATE {tabela} SET {campo}=? WHERE id=?", (novo, int(registro_id)))
        _evento(
            conexao, ator, "registro_removido" if remover else "registro_restaurado",
            tabela, int(registro_id), antes={campo: atual[campo]}, depois={campo: novo},
        )


def adicionar_dependente(colaborador_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "editar_colaborador", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    nome = _texto(dados.get("nome"), 180)
    parentesco = _texto(dados.get("parentesco"), 60)
    if not nome or not parentesco:
        raise ValueError("Informe o nome e o parentesco.")
    with conectar() as conexao:
        _exigir_colaborador_escopo(conexao, colaborador_id, empresa_id, filial_id)
        cursor = conexao.execute(
            "INSERT INTO rh_dependentes (colaborador_id, nome, parentesco, nascimento, cpf, dependente_ir) VALUES (?, ?, ?, ?, ?, ?)",
            (int(colaborador_id), nome, parentesco, _data(dados.get("nascimento")), _texto(dados.get("cpf"), 20) or None, int(bool(dados.get("dependente_ir")))),
        )
        identificador = int(cursor.lastrowid)
        _evento(conexao, ator, "dependente_adicionado", "rh_dependentes", identificador, depois={"colaborador_id": colaborador_id, "nome": nome})
    return identificador


def iniciar_admissao(dados: dict, ator: dict) -> int:
    colaborador_id = criar_colaborador(dados, ator, iniciar_admissao=True)
    with conectar() as conexao:
        admissao = conexao.execute("SELECT id FROM rh_admissoes WHERE colaborador_id=?", (colaborador_id,)).fetchone()
        admissao_id = int(admissao["id"])
        nome = _texto(dados.get("nome_completo") or dados.get("nome"), 180)
        for modulo, titulo, descricao in (
            ("rh", f"Conferir documentos de {nome}", "Validar documentos pessoais, contrato e benefícios."),
            ("ti", f"Preparar acessos de {nome}", "Criar e-mail, usuário e acessos autorizados."),
            ("estoque", f"Separar equipamentos para {nome}", "Separar equipamentos e registrar termos de entrega."),
            ("administrativo", f"Preparar estrutura de {nome}", "Providenciar crachá, posto e itens administrativos."),
        ):
            _tarefa(conexao, ator, modulo, titulo, descricao, "rh_admissoes", admissao_id, "Alta" if modulo == "rh" else "Média")
        _notificar(conexao, ator, "Nova admissão iniciada", f"O processo de {nome} gerou tarefas integradas.", "info", recurso="rh_admissoes", recurso_id=admissao_id)
    # V10.4.1: registra o fluxo transversal em um objeto único, além das tarefas legadas.
    from enterprise.orquestracao import criar_fluxo_admissao
    criar_fluxo_admissao(colaborador_id, ator)
    return admissao_id


def listar_admissoes(ator: dict) -> list[dict]:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linhas = conexao.execute(
            """SELECT a.*, c.nome_completo, c.matricula, c.cargo_texto
            FROM rh_admissoes a JOIN rh_colaboradores c ON c.id=a.colaborador_id
            WHERE a.empresa_id=? AND (a.filial_id=? OR ? IS NULL)
            ORDER BY CASE WHEN a.status='Concluída' THEN 1 ELSE 0 END, a.id DESC""",
            (empresa_id, filial_id, filial_id),
        ).fetchall()
    return [dict(x) for x in linhas]


def atualizar_admissao(admissao_id: int, etapa: int, checklist: dict, ator: dict, *, concluir=False) -> None:
    exigir_acao(ator, "admitir")
    etapa = max(1, min(int(etapa), 8))
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        atual = _registro_no_escopo(conexao, "rh_admissoes", admissao_id, empresa_id, filial_id)
        if atual is None:
            raise ValueError("Admissão não encontrada.")
        status = "Concluída" if concluir else "Em andamento"
        conexao.execute(
            "UPDATE rh_admissoes SET etapa_atual=?, checklist_json=?, status=?, concluido_em=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (etapa, json.dumps(checklist, ensure_ascii=False), status, datetime.now().isoformat(timespec="seconds") if concluir else None, int(admissao_id)),
        )
        if concluir:
            conexao.execute("UPDATE rh_colaboradores SET status='Ativo', etapa_jornada='Ativo', atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (int(atual["colaborador_id"]),))
        _evento(conexao, ator, "admissao_concluida" if concluir else "admissao_atualizada", "rh_admissoes", admissao_id, depois={"etapa": etapa, "status": status})


def iniciar_desligamento(colaborador_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "desligar", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    tipo = _texto(dados.get("tipo") or "Sem justa causa", 80)
    motivo = _texto(dados.get("motivo"), 1000)
    if len(motivo) < 3:
        raise ValueError("Informe o motivo do desligamento.")
    data_prevista = _data(dados.get("data_prevista"), obrigatoria=True)
    with conectar() as conexao:
        colaborador = _registro_no_escopo(conexao, "rh_colaboradores", colaborador_id, empresa_id, filial_id)
        if colaborador is None or colaborador["status"] == "Desligado":
            raise ValueError("Colaborador não encontrado ou já desligado.")
        cursor = conexao.execute(
            "INSERT INTO rh_desligamentos (empresa_id, filial_id, colaborador_id, tipo, motivo, data_prevista, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (empresa_id, filial_id, int(colaborador_id), tipo, motivo, data_prevista, int(ator["id"])),
        )
        desligamento_id = int(cursor.lastrowid)
        conexao.execute("UPDATE rh_colaboradores SET status='Em desligamento', etapa_jornada='Desligamento' WHERE id=?", (int(colaborador_id),))
        nome = colaborador["nome_completo"]
        for modulo, titulo, descricao in (
            ("rh", f"Preparar rescisão de {nome}", "Documentos, entrevista de saída e arquivamento."),
            ("financeiro", f"Calcular verbas de {nome}", "Calcular rescisão, benefícios e pendências."),
            ("ti", f"Revogar acessos de {nome}", "Desativar e-mail, VPN e sistemas corporativos."),
            ("estoque", f"Recolher equipamentos de {nome}", "Conferir notebook, monitor, celular e crachá."),
            ("administrativo", f"Encerrar estrutura de {nome}", "Encerrar acessos físicos e pendências internas."),
        ):
            _tarefa(conexao, ator, modulo, titulo, descricao, "rh_desligamentos", desligamento_id, "Alta")
        _evento(conexao, ator, "desligamento_iniciado", "rh_desligamentos", desligamento_id, depois={"colaborador": nome, "data": data_prevista})
    # V10.4.1: acompanha revogação de acessos, devolução de ativos e pendências financeiras.
    from enterprise.orquestracao import criar_fluxo_desligamento
    criar_fluxo_desligamento(int(colaborador_id), ator)
    return desligamento_id


def concluir_desligamento(desligamento_id: int, ator: dict, *, forcar=False) -> None:
    exigir_acao(ator, "desligar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = _registro_no_escopo(conexao, "rh_desligamentos", desligamento_id, empresa_id, filial_id)
        if registro is None:
            raise ValueError("Desligamento não encontrado.")
        pendentes = int(conexao.execute(
            "SELECT COUNT(*) total FROM tarefas WHERE recurso_tipo='rh_desligamentos' AND recurso_id=? AND status NOT IN ('Concluída', 'Cancelada')",
            (int(desligamento_id),),
        ).fetchone()["total"])
        if pendentes and not forcar:
            raise ValueError(f"Existem {pendentes} tarefa(s) obrigatória(s) pendente(s).")
        agora = datetime.now().isoformat(timespec="seconds")
        conexao.execute("UPDATE rh_desligamentos SET status='Concluído', concluido_em=? WHERE id=?", (agora, int(desligamento_id)))
        conexao.execute(
            "UPDATE rh_colaboradores SET status='Desligado', etapa_jornada='Desligado', desligamento=?, motivo_desligamento=(SELECT motivo FROM rh_desligamentos WHERE id=?), atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (registro["data_prevista"], int(desligamento_id), int(registro["colaborador_id"])),
        )
        _evento(conexao, ator, "desligamento_concluido", "rh_desligamentos", desligamento_id)


def solicitar_ferias_ausencia(dados: dict, ator: dict) -> int:
    colaborador_id = int(dados.get("colaborador_id") or 0)
    exigir_acao(ator, "gerir_jornada", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    inicio, fim = _data(dados.get("inicio"), obrigatoria=True), _data(dados.get("fim"), obrigatoria=True)
    if fim < inicio:
        raise ValueError("A data final não pode ser anterior à inicial.")
    dias = (datetime.fromisoformat(fim).date() - datetime.fromisoformat(inicio).date()).days + 1
    tipo = _texto(dados.get("tipo") or "Férias", 80)
    with conectar() as conexao:
        _exigir_colaborador_escopo(conexao, colaborador_id, empresa_id, filial_id)
        conflito = conexao.execute(
            """SELECT id FROM rh_ferias_ausencias WHERE colaborador_id=?
               AND status NOT IN ('Rejeitado', 'Cancelado') AND inicio<=? AND fim>=?""",
            (colaborador_id, fim, inicio),
        ).fetchone()
        if conflito:
            raise ValueError("Já existe um afastamento que conflita com esse período.")
        cursor = conexao.execute(
            """INSERT INTO rh_ferias_ausencias (
                empresa_id, filial_id, colaborador_id, tipo, inicio, fim, dias,
                periodo_aquisitivo_inicio, periodo_aquisitivo_fim, saldo_antes,
                saldo_depois, abono_dias, motivo, anexo_caminho, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, colaborador_id, tipo, inicio, fim, dias,
             _data(dados.get("periodo_aquisitivo_inicio")), _data(dados.get("periodo_aquisitivo_fim")),
             float(dados.get("saldo_antes") or 30), float(dados.get("saldo_antes") or 30) - (dias if tipo == "Férias" else 0),
             float(dados.get("abono_dias") or 0), _texto(dados.get("motivo"), 1000) or None,
             _texto(dados.get("anexo_caminho"), 500) or None, int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        aprovacao_id = _aprovacao(conexao, ator, "rh_ferias_ausencias", identificador, f"{tipo} de colaborador #{colaborador_id}")
        conexao.execute("UPDATE rh_ferias_ausencias SET aprovacao_id=? WHERE id=?", (aprovacao_id, identificador))
        _evento(conexao, ator, "afastamento_solicitado", "rh_ferias_ausencias", identificador)
    return identificador


def decidir_ferias_ausencia(registro_id: int, aprovar: bool, observacao: str, ator: dict) -> None:
    exigir_acao(ator, "aprovar_ferias")
    empresa_id, filial_id = obter_escopo_ator(ator)
    status = "Aprovado" if aprovar else "Rejeitado"
    with conectar() as conexao:
        registro = _registro_no_escopo(conexao, "rh_ferias_ausencias", registro_id, empresa_id, filial_id)
        if registro is None:
            raise ValueError("Solicitação não encontrada.")
        conexao.execute("UPDATE rh_ferias_ausencias SET status=?, motivo=COALESCE(NULLIF(?, ''), motivo), atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (status, _texto(observacao, 1000), int(registro_id)))
        if registro["aprovacao_id"]:
            conexao.execute("UPDATE aprovacoes SET status=?, responsavel_id=?, observacao=?, decidido_em=CURRENT_TIMESTAMP WHERE id=? AND status='Pendente'", (status, int(ator["id"]), _texto(observacao, 1000), int(registro["aprovacao_id"])))
        _evento(conexao, ator, "afastamento_decidido", "rh_ferias_ausencias", registro_id, depois={"status": status})


def salvar_beneficio(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_beneficios")
    empresa_id, _ = obter_escopo_ator(ator)
    nome, tipo = _texto(dados.get("nome"), 120), _texto(dados.get("tipo"), 80)
    if not nome or not tipo:
        raise ValueError("Informe o nome e o tipo do benefício.")
    with conectar() as conexao:
        cursor = conexao.execute(
            """INSERT INTO rh_beneficios (
                empresa_id, nome, tipo, fornecedor, custo_empresa_centavos,
                desconto_colaborador_centavos, elegibilidade
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, nome, tipo, _texto(dados.get("fornecedor"), 150) or None,
             _centavos(dados.get("custo_empresa")), _centavos(dados.get("desconto_colaborador")),
             _texto(dados.get("elegibilidade"), 500) or None),
        )
        identificador = int(cursor.lastrowid)
        _evento(conexao, ator, "beneficio_criado", "rh_beneficios", identificador)
    return identificador


def vincular_beneficio(colaborador_id: int, beneficio_id: int, inicio, ator: dict) -> int:
    exigir_acao(ator, "gerir_beneficios", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        _exigir_colaborador_escopo(conexao, colaborador_id, empresa_id, filial_id)
        if _registro_no_escopo(conexao, "rh_beneficios", beneficio_id, empresa_id, filial_id) is None:
            raise ValueError("Benefício não pertence à empresa atual.")
        cursor = conexao.execute(
            "INSERT INTO rh_colaborador_beneficios (colaborador_id, beneficio_id, inicio) VALUES (?, ?, ?)",
            (int(colaborador_id), int(beneficio_id), _data(inicio, obrigatoria=True)),
        )
        identificador = int(cursor.lastrowid)
        _evento(conexao, ator, "beneficio_vinculado", "rh_colaborador_beneficios", identificador)
    return identificador


def abrir_folha(competencia, ator: dict) -> int:
    exigir_acao(ator, "processar_folha")
    empresa_id, filial_id = obter_escopo_ator(ator)
    comp = str(competencia).strip()[:7]
    if not re.fullmatch(r"\d{4}-\d{2}", comp):
        raise ValueError("Competência inválida. Utilize AAAA-MM.")
    with conectar() as conexao:
        existente = conexao.execute("SELECT id FROM rh_folhas WHERE empresa_id=? AND filial_id IS ? AND competencia=?", (empresa_id, filial_id, comp)).fetchone()
        if existente:
            return int(existente["id"])
        cursor = conexao.execute("INSERT INTO rh_folhas (empresa_id, filial_id, competencia) VALUES (?, ?, ?)", (empresa_id, filial_id, comp))
        folha_id = int(cursor.lastrowid)
        colaboradores = conexao.execute("SELECT id, salario_centavos FROM rh_colaboradores WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) AND status='Ativo'", (empresa_id, filial_id, filial_id)).fetchall()
        for colaborador in colaboradores:
            conexao.execute("INSERT INTO rh_eventos_folha (folha_id, colaborador_id, codigo, descricao, natureza, valor_centavos, origem, criado_por) VALUES (?, ?, 'SAL', 'Salário base', 'Provento', ?, 'Cadastro', ?)", (folha_id, int(colaborador["id"]), int(colaborador["salario_centavos"] or 0), int(ator["id"])))
        _recalcular_folha(conexao, folha_id)
        _evento(conexao, ator, "folha_aberta", "rh_folhas", folha_id, depois={"competencia": comp})
    return folha_id


def adicionar_evento_folha(folha_id: int, colaborador_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "processar_folha", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    natureza = _texto(dados.get("natureza"), 20)
    if natureza not in {"Provento", "Desconto", "Encargo"}:
        raise ValueError("Natureza de folha inválida.")
    with conectar() as conexao:
        folha = _registro_no_escopo(conexao, "rh_folhas", folha_id, empresa_id, filial_id)
        colaborador = _exigir_colaborador_escopo(conexao, colaborador_id, empresa_id, filial_id)
        if folha is None or folha["status"] != "Aberta":
            raise ValueError("A folha não está aberta.")
        cursor = conexao.execute(
            "INSERT INTO rh_eventos_folha (folha_id, colaborador_id, codigo, descricao, natureza, valor_centavos, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (int(folha_id), int(colaborador_id), _texto(dados.get("codigo"), 20), _texto(dados.get("descricao"), 180), natureza, _centavos(dados.get("valor")), int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        _recalcular_folha(conexao, int(folha_id))
        _evento(conexao, ator, "evento_folha_adicionado", "rh_eventos_folha", identificador)
    return identificador


def _recalcular_folha(conexao, folha_id: int) -> None:
    totais = conexao.execute("""SELECT
        COALESCE(SUM(CASE WHEN natureza='Provento' THEN valor_centavos ELSE 0 END), 0) proventos,
        COALESCE(SUM(CASE WHEN natureza='Desconto' THEN valor_centavos ELSE 0 END), 0) descontos,
        COALESCE(SUM(CASE WHEN natureza='Encargo' THEN valor_centavos ELSE 0 END), 0) encargos
        FROM rh_eventos_folha WHERE folha_id=?""", (int(folha_id),)).fetchone()
    conexao.execute("UPDATE rh_folhas SET total_proventos_centavos=?, total_descontos_centavos=?, total_liquido_centavos=?, encargos_centavos=? WHERE id=?", (int(totais["proventos"]), int(totais["descontos"]), int(totais["proventos"])-int(totais["descontos"]), int(totais["encargos"]), int(folha_id)))


def fechar_folha(folha_id: int, ator: dict) -> None:
    exigir_acao(ator, "fechar_folha")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        folha = _registro_no_escopo(conexao, "rh_folhas", folha_id, empresa_id, filial_id)
        if folha is None or folha["status"] != "Aberta":
            raise ValueError("A folha não está aberta.")
        _recalcular_folha(conexao, int(folha_id))
        conexao.execute("UPDATE rh_folhas SET status='Fechada', fechada_por=?, fechada_em=CURRENT_TIMESTAMP WHERE id=?", (int(ator["id"]), int(folha_id)))
        _tarefa(conexao, ator, "financeiro", f"Provisionar folha {folha['competencia']}", "Registrar a provisão financeira da folha fechada pelo RH.", "rh_folhas", int(folha_id), "Alta")
        _evento(conexao, ator, "folha_fechada", "rh_folhas", folha_id)


def gerar_contracheque(folha_id: int, colaborador_id: int, ator: dict) -> str:
    exigir_acao(ator, "visualizar_remuneracao", colaborador_id)
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        folha = _registro_no_escopo(conexao, "rh_folhas", folha_id, empresa_id, filial_id)
        colaborador = _registro_no_escopo(conexao, "rh_colaboradores", colaborador_id, empresa_id, filial_id)
        eventos = conexao.execute("SELECT * FROM rh_eventos_folha WHERE folha_id=? AND colaborador_id=? ORDER BY id", (int(folha_id), int(colaborador_id))).fetchall()
    if folha is None or colaborador is None:
        raise ValueError("Folha ou colaborador não encontrado.")
    pasta = banco_auth.STORAGE_DIR / "rh" / "contracheques" / str(empresa_id)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"contracheque_{folha['competencia']}_{colaborador_id}.pdf"
    pdf = canvas.Canvas(str(caminho), pagesize=A4)
    pdf.setTitle("Contracheque")
    pdf.setFont("Helvetica-Bold", 16); pdf.drawString(48, 800, "CONTRACHEQUE")
    pdf.setFont("Helvetica", 10); pdf.drawString(48, 780, f"Competência: {folha['competencia']}")
    pdf.drawString(48, 764, f"Colaborador: {colaborador['nome_completo']} | Matrícula: {colaborador['matricula']}")
    y = 730
    proventos = descontos = 0
    for evento in eventos:
        pdf.drawString(54, y, f"{evento['codigo']}  {evento['descricao']}")
        pdf.drawRightString(545, y, _moeda(evento["valor_centavos"]))
        if evento["natureza"] == "Provento": proventos += int(evento["valor_centavos"])
        elif evento["natureza"] == "Desconto": descontos += int(evento["valor_centavos"])
        y -= 18
    pdf.line(48, y, 548, y); y -= 20
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(48, y, f"Proventos: {_moeda(proventos)}   Descontos: {_moeda(descontos)}")
    pdf.drawRightString(545, y, f"Líquido: {_moeda(proventos-descontos)}")
    pdf.setFont("Helvetica", 8); pdf.drawString(48, 40, "Documento gerado pela Data Intelligence Enterprise Platform. Confira com o RH.")
    pdf.save()
    resumo = hashlib.sha256(caminho.read_bytes()).hexdigest()
    with conectar() as conexao:
        conexao.execute(
            """INSERT INTO rh_contracheques (
                empresa_id, filial_id, folha_id, colaborador_id, caminho,
                hash_sha256, gerado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(folha_id, colaborador_id) DO UPDATE SET
                caminho=excluded.caminho, hash_sha256=excluded.hash_sha256,
                gerado_por=excluded.gerado_por, gerado_em=CURRENT_TIMESTAMP""",
            (empresa_id, folha["filial_id"], int(folha_id), int(colaborador_id), _caminho_relativo_storage(caminho), resumo, int(ator["id"])),
        )
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(caminho, modulo="rh", categoria="contracheque")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar contracheque no servidor")
    return str(caminho)


def vincular_equipamento(colaborador_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "editar_colaborador", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    patrimonio = _texto(dados.get("patrimonio"), 80)
    descricao = _texto(dados.get("descricao"), 180)
    if not patrimonio or not descricao:
        raise ValueError("Informe o patrimônio e a descrição do equipamento.")
    with conectar() as conexao:
        _exigir_colaborador_escopo(conexao, colaborador_id, empresa_id, filial_id)
        cursor = conexao.execute(
            """INSERT INTO rh_equipamentos (
                empresa_id, filial_id, colaborador_id, patrimonio, descricao,
                origem_modulo, origem_recurso_id, entregue_em,
                termo_documento_id, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, int(colaborador_id), patrimonio, descricao,
             _texto(dados.get("origem_modulo"), 40) or None,
             int(dados["origem_recurso_id"]) if dados.get("origem_recurso_id") else None,
             _data(dados.get("entregue_em") or date.today(), obrigatoria=True),
             int(dados["termo_documento_id"]) if dados.get("termo_documento_id") else None,
             int(ator["id"])),
        )
        identificador = int(cursor.lastrowid)
        _evento(conexao, ator, "equipamento_vinculado", "rh_equipamentos", identificador)
    return identificador


def devolver_equipamento(equipamento_id: int, data_devolucao, ator: dict) -> None:
    exigir_acao(ator, "editar_colaborador")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = _registro_no_escopo(conexao, "rh_equipamentos", equipamento_id, empresa_id, filial_id)
        if registro is None:
            raise ValueError("Equipamento não encontrado.")
        conexao.execute("UPDATE rh_equipamentos SET devolvido_em=?, status='Devolvido' WHERE id=?", (_data(data_devolucao, obrigatoria=True), int(equipamento_id)))
        _evento(conexao, ator, "equipamento_devolvido", "rh_equipamentos", equipamento_id)


def registrar_ponto(colaborador_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_jornada", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    dia = _data(dados.get("data") or date.today(), obrigatoria=True)
    def minutos(texto):
        if not texto: return None
        hora = datetime.strptime(str(texto).strip(), "%H:%M")
        return hora.hour * 60 + hora.minute
    entrada, saida = minutos(dados.get("entrada")), minutos(dados.get("saida"))
    intervalo_inicio, intervalo_fim = minutos(dados.get("intervalo_inicio")), minutos(dados.get("intervalo_fim"))
    trabalhados = max(0, (saida or entrada or 0) - (entrada or 0) - max(0, (intervalo_fim or 0)-(intervalo_inicio or 0)))
    extras, atraso = max(0, trabalhados-480), max(0, 480-trabalhados)
    with conectar() as conexao:
        _exigir_colaborador_escopo(conexao, colaborador_id, empresa_id, filial_id)
        cursor = conexao.execute(
            """INSERT INTO rh_pontos (
                empresa_id, filial_id, colaborador_id, data, entrada,
                intervalo_inicio, intervalo_fim, saida, minutos_trabalhados,
                minutos_extras, minutos_atraso, justificativa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(colaborador_id, data) DO UPDATE SET
                entrada=excluded.entrada, intervalo_inicio=excluded.intervalo_inicio,
                intervalo_fim=excluded.intervalo_fim, saida=excluded.saida,
                minutos_trabalhados=excluded.minutos_trabalhados,
                minutos_extras=excluded.minutos_extras, minutos_atraso=excluded.minutos_atraso,
                justificativa=excluded.justificativa, status='Ajustado'
            RETURNING id""",
            (empresa_id, filial_id, int(colaborador_id), dia, dados.get("entrada"), dados.get("intervalo_inicio"), dados.get("intervalo_fim"), dados.get("saida"), trabalhados, extras, atraso, _texto(dados.get("justificativa"), 1000) or None),
        )
        identificador = int(cursor.fetchone()["id"])
        _evento(conexao, ator, "ponto_registrado", "rh_pontos", identificador)
    return identificador


def salvar_cargo(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_talentos")
    empresa_id, _ = obter_escopo_ator(ator)
    codigo, titulo = _texto(dados.get("codigo"), 30), _texto(dados.get("titulo"), 150)
    if not codigo or not titulo:
        raise ValueError("Informe o código e o título do cargo.")
    with conectar() as conexao:
        cursor = conexao.execute("""INSERT INTO rh_cargos (
            empresa_id, departamento_id, codigo, titulo, nivel, descricao,
            responsabilidades, competencias, salario_minimo_centavos,
            salario_referencia_centavos, salario_maximo_centavos
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (empresa_id, int(dados["departamento_id"]) if dados.get("departamento_id") else None,
         codigo, titulo, _texto(dados.get("nivel"), 60) or None, _texto(dados.get("descricao"), 1500) or None,
         _texto(dados.get("responsabilidades"), 1500) or None, _texto(dados.get("competencias"), 1500) or None,
         _centavos(dados.get("salario_minimo")), _centavos(dados.get("salario_referencia")), _centavos(dados.get("salario_maximo"))))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "cargo_criado", "rh_cargos", identificador)
    return identificador


def criar_vaga(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_talentos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    titulo = _texto(dados.get("titulo"), 180)
    if not titulo: raise ValueError("Informe o título da vaga.")
    with conectar() as conexao:
        cursor = conexao.execute("INSERT INTO rh_vagas (empresa_id, filial_id, departamento_id, cargo_id, titulo, quantidade, motivo, responsavel_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (empresa_id, filial_id, int(dados["departamento_id"]) if dados.get("departamento_id") else None, int(dados["cargo_id"]) if dados.get("cargo_id") else None, titulo, int(dados.get("quantidade") or 1), _texto(dados.get("motivo"), 1000) or None, int(dados["responsavel_id"]) if dados.get("responsavel_id") else None))
        identificador = int(cursor.lastrowid)
        aprovacao_id = _aprovacao(conexao, ator, "rh_vagas", identificador, f"Abertura de vaga: {titulo}")
        conexao.execute("UPDATE rh_vagas SET aprovacao_id=? WHERE id=?", (aprovacao_id, identificador))
        _evento(conexao, ator, "vaga_criada", "rh_vagas", identificador)
    return identificador


def adicionar_candidato(vaga_id: int, dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_talentos")
    nome = _texto(dados.get("nome"), 180)
    if not nome: raise ValueError("Informe o nome do candidato.")
    with conectar() as conexao:
        cursor = conexao.execute("INSERT INTO rh_candidatos (vaga_id, nome, email, telefone, curriculo_caminho, etapa, nota, observacao) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (int(vaga_id), nome, _texto(dados.get("email"), 180) or None, _texto(dados.get("telefone"), 40) or None, _texto(dados.get("curriculo_caminho"), 500) or None, _texto(dados.get("etapa") or "Inscrição", 60), float(dados["nota"]) if dados.get("nota") not in (None, "") else None, _texto(dados.get("observacao"), 1000) or None))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "candidato_adicionado", "rh_candidatos", identificador)
    return identificador


def salvar_avaliacao(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_talentos", int(dados.get("colaborador_id") or 0))
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute("""INSERT INTO rh_avaliacoes (
            empresa_id, filial_id, colaborador_id, avaliador_id, ciclo, tipo,
            nota, competencias_json, feedback, status, realizada_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, int(dados["colaborador_id"]), int(dados.get("avaliador_id") or ator["id"]), _texto(dados.get("ciclo"), 80), _texto(dados.get("tipo") or "Gestor", 40), float(dados["nota"]) if dados.get("nota") not in (None, "") else None, json.dumps(dados.get("competencias") or {}, ensure_ascii=False), _texto(dados.get("feedback"), 3000) or None, _texto(dados.get("status") or "Planejada", 40), date.today().isoformat() if dados.get("status") == "Concluída" else None))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "avaliacao_criada", "rh_avaliacoes", identificador)
    return identificador


def salvar_pdi(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_talentos", int(dados.get("colaborador_id") or 0))
    with conectar() as conexao:
        cursor = conexao.execute("INSERT INTO rh_pdis (colaborador_id, titulo, objetivo, acoes_json, inicio, prazo, progresso, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (int(dados["colaborador_id"]), _texto(dados.get("titulo"), 180), _texto(dados.get("objetivo"), 2000), json.dumps(dados.get("acoes") or [], ensure_ascii=False), _data(dados.get("inicio") or date.today(), obrigatoria=True), _data(dados.get("prazo")), int(dados.get("progresso") or 0), _texto(dados.get("status") or "Ativo", 40)))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "pdi_criado", "rh_pdis", identificador)
    return identificador


def salvar_treinamento(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "gerir_talentos")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute("INSERT INTO rh_treinamentos (empresa_id, titulo, tipo, carga_horaria, validade_meses, obrigatorio, custo_centavos) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (empresa_id, _texto(dados.get("titulo"), 180), _texto(dados.get("tipo") or "Interno", 60), float(dados.get("carga_horaria") or 0), int(dados["validade_meses"]) if dados.get("validade_meses") else None, int(bool(dados.get("obrigatorio"))), _centavos(dados.get("custo"))))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "treinamento_criado", "rh_treinamentos", identificador)
    return identificador


def inscrever_treinamento(treinamento_id: int, colaborador_id: int, ator: dict) -> int:
    exigir_acao(ator, "gerir_talentos", colaborador_id)
    with conectar() as conexao:
        cursor = conexao.execute("INSERT INTO rh_inscricoes_treinamento (treinamento_id, colaborador_id) VALUES (?, ?)", (int(treinamento_id), int(colaborador_id)))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "treinamento_inscrito", "rh_inscricoes_treinamento", identificador)
    return identificador


def registrar_documento(colaborador_id: int | None, dados: dict, caminho_origem: str | Path, ator: dict) -> int:
    exigir_acao(ator, "gerir_documentos", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    origem = Path(caminho_origem).expanduser().resolve()
    if not origem.is_file(): raise FileNotFoundError("Arquivo do documento não encontrado.")
    if origem.stat().st_size > 30 * 1024 * 1024: raise ValueError("O documento excede o limite de 30 MB.")
    resumo = hashlib.sha256(origem.read_bytes()).hexdigest()
    pasta = banco_auth.STORAGE_DIR / "rh" / "documentos" / str(empresa_id) / str(colaborador_id or 0)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{datetime.now():%Y%m%d%H%M%S}_{resumo[:10]}{origem.suffix.lower()}"
    shutil.copy2(origem, destino)
    with conectar() as conexao:
        if colaborador_id:
            _exigir_colaborador_escopo(conexao, colaborador_id, empresa_id, filial_id)
        cursor = conexao.execute("""INSERT INTO rh_documentos (
            empresa_id, filial_id, colaborador_id, categoria, titulo, caminho,
            hash_sha256, classificacao, validade, assinatura_status, criado_por
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (empresa_id, filial_id, int(colaborador_id) if colaborador_id else None, _texto(dados.get("categoria") or "Outros", 80), _texto(dados.get("titulo") or origem.stem, 180), _caminho_relativo_storage(destino), resumo, _texto(dados.get("classificacao") or "Confidencial", 40), _data(dados.get("validade")), _texto(dados.get("assinatura_status") or "Não aplicável", 40), int(ator["id"])))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "documento_registrado", "rh_documentos", identificador)
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="rh", categoria="documento")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar documento RH no servidor")
    return identificador


def verificar_documento(documento_id: int, ator: dict) -> dict:
    exigir_acao(ator, "gerir_documentos")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = _registro_no_escopo(conexao, "rh_documentos", documento_id, empresa_id, filial_id)
    if registro is None:
        raise ValueError("Documento não encontrado.")
    caminho = _resolver_caminho_storage(registro["caminho"])
    existe = caminho.is_file()
    hash_atual = hashlib.sha256(caminho.read_bytes()).hexdigest() if existe else None
    return {"existe": existe, "integro": bool(existe and hash_atual == registro["hash_sha256"]), "hash_esperado": registro["hash_sha256"], "hash_atual": hash_atual}


def decidir_solicitacao(solicitacao_id: int, aprovar: bool, resposta: str, ator: dict) -> None:
    exigir_acao(ator, "aprovar_solicitacao")
    empresa_id, filial_id = obter_escopo_ator(ator)
    status = "Aprovada" if aprovar else "Rejeitada"
    with conectar() as conexao:
        registro = _registro_no_escopo(conexao, "rh_solicitacoes", solicitacao_id, empresa_id, filial_id)
        if registro is None:
            raise ValueError("Solicitação não encontrada.")
        conexao.execute("UPDATE rh_solicitacoes SET status=?, resposta=?, responsavel_id=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (status, _texto(resposta, 2000), int(ator["id"]), int(solicitacao_id)))
        if registro["aprovacao_id"]:
            conexao.execute("UPDATE aprovacoes SET status=?, observacao=?, responsavel_id=?, decidido_em=CURRENT_TIMESTAMP WHERE id=? AND status='Pendente'", (status[:-1] + "o" if status.endswith("a") else status, _texto(resposta, 1000), int(ator["id"]), int(registro["aprovacao_id"])))
        _evento(conexao, ator, "solicitacao_decidida", "rh_solicitacoes", solicitacao_id, depois={"status": status})


def criar_solicitacao(dados: dict, ator: dict) -> int:
    colaborador_id = int(dados.get("colaborador_id") or 0)
    exigir_acao(ator, "visualizar", colaborador_id)
    empresa_id, filial_id = obter_escopo_ator(ator)
    titulo = _texto(dados.get("titulo"), 180)
    if not titulo: raise ValueError("Informe o título da solicitação.")
    with conectar() as conexao:
        cursor = conexao.execute("INSERT INTO rh_solicitacoes (empresa_id, filial_id, colaborador_id, tipo, titulo, descricao) VALUES (?, ?, ?, ?, ?, ?)", (empresa_id, filial_id, colaborador_id, _texto(dados.get("tipo") or "Geral", 80), titulo, _texto(dados.get("descricao"), 2000) or None))
        identificador = int(cursor.lastrowid)
        aprovacao_id = _aprovacao(conexao, ator, "rh_solicitacoes", identificador, titulo)
        conexao.execute("UPDATE rh_solicitacoes SET aprovacao_id=? WHERE id=?", (aprovacao_id, identificador))
        _evento(conexao, ator, "solicitacao_criada", "rh_solicitacoes", identificador)
    return identificador


def listar_secao(secao: str, ator: dict, *, limite=500, estado="Ativos") -> list[dict]:
    exigir_acao(ator, "visualizar")
    tabela = SECOES_RECURSOS.get(secao)
    if tabela is None: raise ValueError("Seção de RH inválida.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    consultas = {
        "colaboradores": "SELECT id, matricula, nome_completo, cargo_texto, status, etapa_jornada, admissao, salario_centavos FROM rh_colaboradores WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) ORDER BY nome_completo",
        "admissoes": "SELECT a.id, c.nome_completo, c.cargo_texto, a.etapa_atual, a.status, a.previsao_conclusao FROM rh_admissoes a JOIN rh_colaboradores c ON c.id=a.colaborador_id WHERE a.empresa_id=? AND (a.filial_id=? OR ? IS NULL) ORDER BY a.id DESC",
        "desligamentos": "SELECT d.id, c.nome_completo, d.tipo, d.data_prevista, d.status, d.motivo FROM rh_desligamentos d JOIN rh_colaboradores c ON c.id=d.colaborador_id WHERE d.empresa_id=? AND (d.filial_id=? OR ? IS NULL) ORDER BY d.id DESC",
        "movimentacoes": "SELECT h.id, c.nome_completo, h.tipo, h.vigencia, h.observacao, h.criado_em FROM rh_historico_profissional h JOIN rh_colaboradores c ON c.id=h.colaborador_id WHERE h.empresa_id=? AND (h.filial_id=? OR ? IS NULL) ORDER BY h.id DESC",
        "ponto": "SELECT p.id, c.nome_completo, p.data, p.entrada, p.saida, p.minutos_trabalhados, p.minutos_extras, p.minutos_atraso, p.status FROM rh_pontos p JOIN rh_colaboradores c ON c.id=p.colaborador_id WHERE p.empresa_id=? AND (p.filial_id=? OR ? IS NULL) ORDER BY p.data DESC",
        "ferias": "SELECT f.id, c.nome_completo, f.tipo, f.inicio, f.fim, f.dias, f.status, f.saldo_depois FROM rh_ferias_ausencias f JOIN rh_colaboradores c ON c.id=f.colaborador_id WHERE f.empresa_id=? AND (f.filial_id=? OR ? IS NULL) ORDER BY f.inicio DESC",
        "beneficios": "SELECT cb.id, c.nome_completo, b.nome beneficio, b.tipo, cb.inicio, cb.fim, cb.status, b.custo_empresa_centavos FROM rh_colaborador_beneficios cb JOIN rh_colaboradores c ON c.id=cb.colaborador_id JOIN rh_beneficios b ON b.id=cb.beneficio_id WHERE c.empresa_id=? AND (c.filial_id=? OR ? IS NULL) ORDER BY c.nome_completo",
        "folha": "SELECT id, competencia, status, total_proventos_centavos, total_descontos_centavos, total_liquido_centavos, encargos_centavos, fechada_em FROM rh_folhas WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) ORDER BY competencia DESC",
        "cargos": "SELECT id, codigo, titulo, nivel, salario_minimo_centavos, salario_referencia_centavos, salario_maximo_centavos, ativo FROM rh_cargos WHERE empresa_id=? ORDER BY titulo",
        "recrutamento": "SELECT v.id, v.titulo, v.quantidade, v.status, v.motivo, COUNT(c.id) candidatos FROM rh_vagas v LEFT JOIN rh_candidatos c ON c.vaga_id=v.id WHERE v.empresa_id=? AND (v.filial_id=? OR ? IS NULL) GROUP BY v.id ORDER BY v.id DESC",
        "desempenho": "SELECT a.id, c.nome_completo, a.ciclo, a.tipo, a.nota, a.status, a.realizada_em FROM rh_avaliacoes a JOIN rh_colaboradores c ON c.id=a.colaborador_id WHERE a.empresa_id=? AND (a.filial_id=? OR ? IS NULL) ORDER BY a.id DESC",
        "treinamentos": "SELECT t.id, t.titulo, t.tipo, t.carga_horaria, t.obrigatorio, t.validade_meses, t.ativo, COUNT(i.id) inscritos FROM rh_treinamentos t LEFT JOIN rh_inscricoes_treinamento i ON i.treinamento_id=t.id WHERE t.empresa_id=? GROUP BY t.id ORDER BY t.titulo",
        "carreira": "SELECT p.id, c.nome_completo, p.titulo, p.inicio, p.prazo, p.progresso, p.status FROM rh_pdis p JOIN rh_colaboradores c ON c.id=p.colaborador_id WHERE c.empresa_id=? AND (c.filial_id=? OR ? IS NULL) ORDER BY p.id DESC",
        "documentos": "SELECT d.id, COALESCE(c.nome_completo, 'Corporativo') vinculo, d.categoria, d.titulo, d.versao, d.classificacao, d.validade, d.assinatura_status, d.status FROM rh_documentos d LEFT JOIN rh_colaboradores c ON c.id=d.colaborador_id WHERE d.empresa_id=? AND (d.filial_id=? OR ? IS NULL) ORDER BY d.id DESC",
        "solicitacoes": "SELECT s.id, c.nome_completo, s.tipo, s.titulo, s.status, s.resposta, s.criado_em FROM rh_solicitacoes s JOIN rh_colaboradores c ON c.id=s.colaborador_id WHERE s.empresa_id=? AND (s.filial_id=? OR ? IS NULL) ORDER BY s.id DESC",
    }
    sql = consultas[secao] + " LIMIT ?"
    params = (empresa_id, filial_id, filial_id, max(1, min(int(limite), 2000)))
    if secao in {"cargos", "treinamentos"}:
        params = (empresa_id, max(1, min(int(limite), 2000)))
    with conectar() as conexao:
        linhas = conexao.execute(sql, params).fetchall()
    registros = [dict(x) for x in linhas]
    configuracao_remocao = _ESTADOS_REMOCAO_RH.get(secao)
    if configuracao_remocao:
        campo, valor_removido, _valor_restaurado = configuracao_remocao
        mostrar_lixeira = str(estado or "Ativos").strip().lower() == "lixeira"
        registros = [
            item for item in registros
            if (item.get(campo) == valor_removido) == mostrar_lixeira
        ]
    if secao in {"colaboradores", "folha", "beneficios", "cargos"} and not tem_permissao_rh(ator, "visualizar_remuneracao"):
        for registro in registros:
            for campo in tuple(registro):
                if "centavos" in campo:
                    registro[campo] = None
    return registros


def resumo_rh(ator: dict) -> dict:
    exigir_acao(ator, "visualizar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        linha = conexao.execute("""SELECT COUNT(*) total,
            SUM(CASE WHEN status='Ativo' THEN 1 ELSE 0 END) ativos,
            SUM(CASE WHEN status='Pré-admissão' THEN 1 ELSE 0 END) pre_admissoes,
            SUM(CASE WHEN status='Em desligamento' THEN 1 ELSE 0 END) desligamentos,
            COUNT(DISTINCT departamento_id) departamentos,
            COALESCE(SUM(CASE WHEN status='Ativo' THEN salario_centavos ELSE 0 END), 0) folha_base
            FROM rh_colaboradores WHERE empresa_id=? AND (filial_id=? OR ? IS NULL)
              AND status<>'Removido'""", (empresa_id, filial_id, filial_id)).fetchone()
        ferias = int(conexao.execute("SELECT COUNT(*) total FROM rh_ferias_ausencias WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) AND status='Solicitado'", (empresa_id, filial_id, filial_id)).fetchone()["total"])
        docs = int(conexao.execute("SELECT COUNT(*) total FROM rh_documentos WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) AND validade IS NOT NULL AND validade<=date('now','+30 day') AND status='Ativo'", (empresa_id, filial_id, filial_id)).fetchone()["total"])
        tarefas = int(conexao.execute("SELECT COUNT(*) total FROM tarefas WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) AND modulo='rh' AND status NOT IN ('Concluída','Cancelada')", (empresa_id, filial_id, filial_id)).fetchone()["total"])
        jornada = [dict(x) for x in conexao.execute("SELECT etapa_jornada etapa, COUNT(*) total FROM rh_colaboradores WHERE empresa_id=? AND (filial_id=? OR ? IS NULL) AND status<>'Removido' GROUP BY etapa_jornada ORDER BY etapa_jornada", (empresa_id, filial_id, filial_id)).fetchall()]
    resultado = dict(linha); resultado.update({"ferias_pendentes": ferias, "documentos_vencendo": docs, "tarefas_pendentes": tarefas, "jornada": jornada})
    if not tem_permissao_rh(ator, "visualizar_remuneracao"):
        resultado["folha_base"] = None
    return resultado


def analisar_rh(ator: dict) -> dict:
    resumo = resumo_rh(ator)
    alertas, recomendacoes = [], []
    if resumo["ferias_pendentes"]: alertas.append(f"{resumo['ferias_pendentes']} solicitação(ões) de férias/ausência aguardam decisão.")
    if resumo["documentos_vencendo"]: alertas.append(f"{resumo['documentos_vencendo']} documento(s) vencem nos próximos 30 dias.")
    if resumo["tarefas_pendentes"]: alertas.append(f"{resumo['tarefas_pendentes']} tarefa(s) operacionais de RH estão pendentes.")
    if not alertas: alertas.append("Nenhuma pendência crítica foi identificada no contexto atual.")
    recomendacoes.append("Revise admissões, desligamentos e afastamentos com pendências antes do fechamento mensal.")
    recomendacoes.append("Use os indicadores como apoio à gestão; decisões sensíveis permanecem humanas.")
    return {"resumo": resumo, "alertas": alertas, "recomendacoes": recomendacoes}


def exportar_dataframe_rh(ator: dict) -> pd.DataFrame:
    exigir_acao(ator, "exportar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    perfil_acesso = str(ator.get("perfil_acesso", "")).lower()
    restricao = ""
    params: list = [empresa_id, filial_id, filial_id]
    if perfil_acesso == "colaborador":
        restricao = " AND c.usuario_id=?"
        params.append(int(ator["id"]))
    elif perfil_acesso == "gestor_pessoas":
        restricao = " AND (c.usuario_id=? OR c.gestor_id=(SELECT id FROM rh_colaboradores WHERE empresa_id=? AND usuario_id=? LIMIT 1))"
        params.extend((int(ator["id"]), empresa_id, int(ator["id"])))
    with conectar() as conexao:
        _sincronizar_legado(conexao, empresa_id, filial_id)
        # ``ConexaoCompat`` protege o restante da aplicação de detalhes do
        # driver e, por projeto, não expõe ``cursor()``. O pandas tenta acessar
        # esse método quando recebe uma conexão que não seja sqlite3/SQLAlchemy,
        # fazendo a exportação falhar somente no PostgreSQL. Execute pelo
        # contrato portátil do adapter e entregue ao pandas dados já
        # materializados.
        linhas = conexao.execute(f"""SELECT c.id, c.matricula, c.nome_completo nome,
            c.cargo_texto cargo, d.nome departamento, f.nome filial,
            c.tipo_contrato, c.modalidade, c.admissao, c.status,
            c.etapa_jornada, c.salario_centavos
            FROM rh_colaboradores c
            LEFT JOIN departamentos d ON d.id=c.departamento_id
            LEFT JOIN filiais f ON f.id=c.filial_id
            WHERE c.empresa_id=? AND (c.filial_id=? OR ? IS NULL)
              AND c.status<>'Removido' {restricao}
            ORDER BY c.nome_completo""", tuple(params)).fetchall()
        df = pd.DataFrame([dict(linha) for linha in linhas])
        # Uma consulta vazia ainda precisa preservar o schema do relatório.
        if df.empty:
            df = pd.DataFrame(columns=(
                "id", "matricula", "nome", "cargo", "departamento", "filial",
                "tipo_contrato", "modalidade", "admissao", "status",
                "etapa_jornada", "salario_centavos",
            ))
    if not tem_permissao_rh(ator, "visualizar_remuneracao") and "salario_centavos" in df:
        df = df.drop(columns=["salario_centavos"])
    return df


def gerar_relatorio_rh(tipo: str, formato: str, destino: str | Path, ator: dict) -> str:
    exigir_acao(ator, "exportar")
    tipo = _texto(tipo or "Colaboradores", 60)
    formato = str(formato).lower().lstrip(".")
    destino = Path(destino).expanduser().resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    if tipo.lower() in {"folha", "custos", "remuneração"}:
        registros = listar_secao("folha", ator)
        df = pd.DataFrame(registros)
    elif tipo.lower() in {"férias", "ferias", "ausências"}:
        df = pd.DataFrame(listar_secao("ferias", ator))
    else:
        df = exportar_dataframe_rh(ator)
    if formato == "csv": df.to_csv(destino, index=False, encoding="utf-8-sig")
    elif formato in {"xlsx", "excel"}: df.to_excel(destino, index=False)
    elif formato == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        estilos = getSampleStyleSheet()
        elementos = [Paragraph(f"Relatório de RH · {tipo}", estilos["Title"]),
                     Paragraph(f"Gerado em {datetime.now():%d/%m/%Y %H:%M} · {len(df)} registro(s)", estilos["BodyText"]), Spacer(1, 8)]
        limite_pdf = 5000
        if len(df) > limite_pdf:
            elementos.extend([Paragraph(
                f"ATENÇÃO: o PDF contém {limite_pdf:,} de {len(df):,} registros. Use XLSX/CSV para o conjunto integral.",
                estilos["BodyText"]), Spacer(1, 6)])
        if df.empty:
            elementos.append(Paragraph("Nenhum registro encontrado.", estilos["BodyText"]))
        else:
            quadro = df.fillna("").astype(str)
            dados = [list(quadro.columns)] + [[str(v)[:45] for v in linha] for linha in quadro.head(limite_pdf).itertuples(index=False, name=None)]
            tabela = Table(dados, repeatRows=1)
            tabela.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#312E81")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .25, colors.lightgrey), ("FONTSIZE", (0,0), (-1,-1), 5.5), ("VALIGN", (0,0), (-1,-1), "TOP")]))
            elementos.append(tabela)
        SimpleDocTemplate(str(destino), pagesize=landscape(A4), title=f"Relatório RH - {tipo}", leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18).build(elementos)
    else: raise ValueError("Formato suportado: PDF, XLSX ou CSV.")
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="rh", categoria="relatorio")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar relatório RH no servidor")
    return str(destino)


def agendar_relatorio(dados: dict, ator: dict) -> int:
    exigir_acao(ator, "exportar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        cursor = conexao.execute("INSERT INTO rh_relatorios_agendados (empresa_id, filial_id, tipo, formato, frequencia, destinatarios, filtros_json, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (empresa_id, filial_id, _texto(dados.get("tipo") or "Colaboradores", 80), _texto(dados.get("formato") or "PDF", 10), _texto(dados.get("frequencia") or "Mensal", 40), _texto(dados.get("destinatarios"), 1000) or None, json.dumps(dados.get("filtros") or {}, ensure_ascii=False), int(ator["id"])))
        identificador = int(cursor.lastrowid); _evento(conexao, ator, "relatorio_agendado", "rh_relatorios_agendados", identificador)
    from enterprise.automacao_motor import registrar_agendamento
    registrar_agendamento(
        modulo="rh", referencia_tipo="rh_relatorios_agendados", referencia_id=identificador,
        handler="relatorio.gerar",
        payload={
            "modulo": "rh", "tipo": dados.get("tipo") or "Colaboradores",
            "formato": dados.get("formato") or "PDF", "filtros": dados.get("filtros") or {},
            "destinatarios": dados.get("destinatarios") or "",
        },
        frequencia=dados.get("frequencia") or "Mensal",
        proxima_execucao=dados.get("proxima_execucao"), ator=ator,
    )
    return identificador


def listar_auditoria_rh(ator: dict, limite=500) -> list[dict]:
    exigir_acao(ator, "auditar")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        linhas = conexao.execute("""SELECT h.id, h.operacao_id, h.usuario_id,
            u.nome usuario_nome, h.entidade, h.entidade_id, h.acao,
            h.dados_antes, h.dados_depois, h.criado_em
            FROM historico_alteracoes h LEFT JOIN usuarios u ON u.id=h.usuario_id
            WHERE h.empresa_id=? AND (h.filial_id=? OR ? IS NULL) AND h.modulo='rh'
            ORDER BY h.id DESC LIMIT ?""", (empresa_id, filial_id, filial_id, max(1, min(int(limite), 2000)))).fetchall()
    return [dict(x) for x in linhas]

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
