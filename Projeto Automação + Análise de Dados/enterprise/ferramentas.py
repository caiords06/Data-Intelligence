"""Serviços das ferramentas corporativas expostas na central V8."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import shutil
from pathlib import Path
from uuid import uuid4

from auth import banco
from auth.banco import conectar, registrar_auditoria
from enterprise.catalogo import MODULOS
from enterprise.contexto import (
    exigir_permissao,
    listar_modulos_permitidos,
    obter_escopo_ator,
    validar_usuario_no_escopo,
)
from enterprise.modulos import exportar_dataframe_modulo


PRIORIDADES = {"Baixa", "Média", "Alta", "Crítica"}
STATUS_TAREFAS = {"Pendente", "Em andamento", "Concluída", "Cancelada"}
CLASSIFICACOES = {"Público", "Interno", "Confidencial", "Restrito"}


def _hash_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        while bloco := arquivo.read(1024 * 1024):
            resumo.update(bloco)
    return resumo.hexdigest()


def _admin(ator: dict) -> None:
    if not ator or str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("Esta ferramenta é restrita a administradores.")


def criar_tarefa(dados: dict, ator: dict) -> int:
    modulo = str(dados.get("modulo", "")).strip().lower()
    if modulo not in MODULOS:
        raise ValueError("Módulo da tarefa inválido.")
    exigir_permissao(ator, modulo, "escrever")
    titulo = str(dados.get("titulo", "")).strip()
    if len(titulo) < 3 or len(titulo) > 180:
        raise ValueError("O título deve possuir entre 3 e 180 caracteres.")
    prioridade = str(dados.get("prioridade", "Média")).strip().title()
    if prioridade not in PRIORIDADES:
        raise ValueError("Prioridade inválida.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    responsavel_id = int(dados["responsavel_id"]) if dados.get("responsavel_id") else None
    if responsavel_id is not None:
        validar_usuario_no_escopo(responsavel_id, empresa_id, filial_id)
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO tarefas (
                empresa_id, filial_id, modulo, titulo, descricao,
                responsavel_id, prioridade, vencimento, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pendente')
            """,
            (
                empresa_id,
                filial_id,
                modulo,
                titulo,
                str(dados.get("descricao", "")).strip()[:2000],
                responsavel_id,
                prioridade,
                str(dados.get("vencimento", "")).strip() or None,
            ),
        )
        tarefa_id = int(cursor.lastrowid)
        conexao.execute(
            """
            INSERT INTO atividades (
                usuario_id, empresa_id, filial_id, modulo, acao, descricao,
                recurso_tipo, recurso_id
            ) VALUES (?, ?, ?, ?, 'tarefa_criada', ?, 'tarefas', ?)
            """,
            (int(ator["id"]), empresa_id, filial_id, modulo, titulo, tarefa_id),
        )
    return tarefa_id


def listar_tarefas(ator: dict, *, incluir_concluidas: bool = True) -> list[dict]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    permitidos = list(listar_modulos_permitidos(ator))
    if not permitidos:
        return []
    marcadores = ",".join("?" for _ in permitidos)
    filtro = "" if incluir_concluidas else "AND t.status NOT IN ('Concluída', 'Cancelada')"
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT t.*, u.nome AS responsavel_nome
            FROM tarefas t
            LEFT JOIN usuarios u ON u.id = t.responsavel_id
            WHERE t.empresa_id = ? AND (t.filial_id = ? OR ? IS NULL)
              AND COALESCE(t.estado_registro, 'Ativo') = 'Ativo'
              AND t.modulo IN ({marcadores})
              {filtro}
            ORDER BY CASE t.prioridade
                WHEN 'Crítica' THEN 0 WHEN 'Alta' THEN 1
                WHEN 'Média' THEN 2 ELSE 3 END, t.id DESC
            """,
            (empresa_id, filial_id, filial_id, *permitidos),
        ).fetchall()
    return [dict(item) for item in registros]


def atualizar_status_tarefa(tarefa_id: int, status: str, ator: dict) -> None:
    status = str(status).strip().capitalize()
    normalizados = {item.casefold(): item for item in STATUS_TAREFAS}
    status = normalizados.get(status.casefold(), status)
    if status not in STATUS_TAREFAS:
        raise ValueError("Status de tarefa inválido.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        tarefa = conexao.execute(
            "SELECT * FROM tarefas WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)",
            (int(tarefa_id), empresa_id, filial_id, filial_id),
        ).fetchone()
        if tarefa is None:
            raise ValueError("Tarefa não encontrada.")
        exigir_permissao(ator, tarefa["modulo"], "escrever")
        responsavel = tarefa["responsavel_id"]
        if responsavel and int(responsavel) != int(ator["id"]) and not ator.get("perfil") == "admin":
            raise PermissionError("Somente o responsável ou um administrador pode alterar a tarefa.")
        conexao.execute(
            "UPDATE tarefas SET status = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
            (status, int(tarefa_id)),
        )


def arquivar_tarefa(tarefa_id: int, ator: dict) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        tarefa = conexao.execute(
            "SELECT * FROM tarefas WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)",
            (int(tarefa_id), empresa_id, filial_id, filial_id),
        ).fetchone()
        if tarefa is None:
            raise ValueError("Tarefa não encontrada.")
        exigir_permissao(ator, tarefa["modulo"], "escrever")
        responsavel = tarefa["responsavel_id"]
        if (
            responsavel
            and int(responsavel) != int(ator["id"])
            and str(ator.get("perfil", "")).lower() != "admin"
        ):
            raise PermissionError(
                "Somente o responsável ou um administrador pode arquivar a tarefa."
            )
        conexao.execute(
            "UPDATE tarefas SET estado_registro = 'Arquivado', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
            (int(tarefa_id),),
        )


def registrar_documento(
    caminho_origem: str,
    titulo: str,
    modulo: str,
    classificacao: str,
    ator: dict,
) -> int:
    origem = Path(caminho_origem).expanduser().resolve()
    if not origem.is_file():
        raise ValueError("Arquivo de origem não encontrado.")
    if origem.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("O documento excede o limite local de 100 MB.")
    modulo = str(modulo).strip().lower()
    if modulo not in MODULOS:
        raise ValueError("Módulo do documento inválido.")
    exigir_permissao(ator, modulo, "escrever")
    titulo = str(titulo).strip() or origem.stem
    classificacao = str(classificacao).strip().title()
    if classificacao not in CLASSIFICACOES:
        raise ValueError("Classificação inválida.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    pasta = banco.STORAGE_DIR / "documentos" / str(empresa_id) / str(filial_id or 0)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{uuid4().hex}{origem.suffix.lower()}"
    shutil.copy2(origem, destino)
    resumo = _hash_arquivo(destino)
    relativo = destino.relative_to(banco.STORAGE_DIR).as_posix()
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO documentos (
                    empresa_id, filial_id, modulo, titulo, tipo,
                    caminho_relativo, hash_sha256, classificacao, criado_por
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    empresa_id,
                    filial_id,
                    modulo,
                    titulo[:180],
                    origem.suffix.lower().lstrip("."),
                    relativo,
                    resumo,
                    classificacao,
                    int(ator["id"]),
                ),
            )
            documento_id = int(cursor.lastrowid)
    except Exception:
        destino.unlink(missing_ok=True)
        raise
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo=modulo, categoria="documento")
    except Exception:
        logging.getLogger(__name__).exception("Não foi possível espelhar documento corporativo no servidor")
    return documento_id


def listar_documentos(ator: dict) -> list[dict]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    permitidos = list(listar_modulos_permitidos(ator))
    if not permitidos:
        return []
    marcadores = ",".join("?" for _ in permitidos)
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT d.*, u.nome AS autor_nome
            FROM documentos d
            LEFT JOIN usuarios u ON u.id = d.criado_por
            WHERE d.empresa_id = ? AND (d.filial_id = ? OR ? IS NULL)
              AND COALESCE(d.estado_registro, 'Ativo') = 'Ativo'
              AND d.modulo IN ({marcadores})
            ORDER BY d.id DESC
            """,
            (empresa_id, filial_id, filial_id, *permitidos),
        ).fetchall()
    return [dict(item) for item in registros]


def verificar_documento(documento_id: int, ator: dict) -> dict:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM documentos WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)",
            (int(documento_id), empresa_id, filial_id, filial_id),
        ).fetchone()
    if registro is None:
        raise ValueError("Documento não encontrado.")
    exigir_permissao(ator, registro["modulo"], "ler")
    caminho = (banco.STORAGE_DIR / registro["caminho_relativo"]).resolve()
    dentro_storage = banco.STORAGE_DIR.resolve() in caminho.parents
    existe = dentro_storage and caminho.is_file()
    hash_atual = _hash_arquivo(caminho) if existe else None
    return {
        "existe": existe,
        "integro": bool(existe and hash_atual == registro["hash_sha256"]),
        "caminho": str(caminho) if existe else None,
    }


def arquivar_documento(documento_id: int, ator: dict) -> None:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        documento = conexao.execute(
            "SELECT * FROM documentos WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)",
            (int(documento_id), empresa_id, filial_id, filial_id),
        ).fetchone()
        if documento is None:
            raise ValueError("Documento não encontrado.")
        exigir_permissao(ator, documento["modulo"], "escrever")
        conexao.execute(
            "UPDATE documentos SET estado_registro = 'Arquivado', atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
            (int(documento_id),),
        )


def gerar_relatorio(
    titulo: str,
    modulo: str,
    formato: str,
    ator: dict,
) -> dict:
    titulo = str(titulo).strip()
    if len(titulo) < 3 or len(titulo) > 180:
        raise ValueError("Título de relatório inválido.")
    modulo = str(modulo).strip().lower()
    if modulo not in MODULOS or modulo == "analytics":
        raise ValueError("Selecione um módulo operacional para o relatório.")
    exigir_permissao(ator, modulo, "ler")
    formato = str(formato).strip().upper()
    if formato not in {"HTML", "CSV", "JSON"}:
        raise ValueError("Formato de relatório inválido.")
    dataframe = exportar_dataframe_modulo(modulo, ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    pasta = banco.STORAGE_DIR / "relatorios" / str(empresa_id) / str(filial_id or 0)
    pasta.mkdir(parents=True, exist_ok=True)
    sufixo = {"HTML": ".html", "CSV": ".csv", "JSON": ".json"}[formato]
    arquivo = pasta / f"relatorio_{modulo}_{uuid4().hex[:12]}{sufixo}"
    if formato == "HTML":
        conteudo = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{html.escape(titulo)}</title></head>"
            f"<body><h1>{html.escape(titulo)}</h1>"
            f"<p>Módulo: {MODULOS[modulo]['nome']} · Registros: {len(dataframe)}</p>"
            f"{dataframe.to_html(index=False, border=0)}</body></html>"
        )
        arquivo.write_text(conteudo, encoding="utf-8")
    elif formato == "CSV":
        dataframe.to_csv(arquivo, index=False, encoding="utf-8-sig")
    else:
        dataframe.to_json(arquivo, orient="records", force_ascii=False, indent=2)
    relativo = arquivo.relative_to(banco.STORAGE_DIR).as_posix()
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO relatorios_corporativos (
                empresa_id, filial_id, modulo, titulo, formato,
                arquivo, status, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, 'Concluído', ?)
            """,
            (
                empresa_id,
                filial_id,
                modulo,
                titulo,
                formato,
                relativo,
                int(ator["id"]),
            ),
        )
        relatorio_id = int(cursor.lastrowid)
    return {"id": relatorio_id, "arquivo": str(arquivo), "registros": len(dataframe)}


def listar_relatorios(ator: dict) -> list[dict]:
    empresa_id, filial_id = obter_escopo_ator(ator)
    permitidos = list(listar_modulos_permitidos(ator))
    if not permitidos:
        return []
    marcadores = ",".join("?" for _ in permitidos)
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT * FROM relatorios_corporativos
            WHERE empresa_id = ? AND (filial_id = ? OR ? IS NULL)
              AND modulo IN ({marcadores})
            ORDER BY id DESC
            """,
            (empresa_id, filial_id, filial_id, *permitidos),
        ).fetchall()
    return [dict(item) for item in registros]


def obter_arquivo_relatorio(relatorio_id: int, ator: dict) -> str:
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM relatorios_corporativos "
            "WHERE id = ? AND empresa_id = ? AND (filial_id = ? OR ? IS NULL)",
            (int(relatorio_id), empresa_id, filial_id, filial_id),
        ).fetchone()
    if registro is None:
        raise ValueError("Relatório não encontrado.")
    exigir_permissao(ator, registro["modulo"], "ler")
    caminho = (banco.STORAGE_DIR / str(registro["arquivo"] or "")).resolve()
    dentro_storage = banco.STORAGE_DIR.resolve() in caminho.parents
    if not dentro_storage or not caminho.is_file():
        raise ValueError("O arquivo do relatório não está disponível.")
    return str(caminho)


def listar_auditoria(ator: dict, limite: int = 500) -> list[dict]:
    _admin(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT h.*, u.nome AS usuario_nome
            FROM historico_alteracoes h
            LEFT JOIN usuarios u ON u.id = h.usuario_id
            WHERE h.empresa_id = ? AND (h.filial_id = ? OR h.filial_id IS NULL)
            ORDER BY h.id DESC LIMIT ?
            """,
            (empresa_id, filial_id, max(1, min(int(limite), 2000))),
        ).fetchall()
    return [dict(item) for item in registros]


def registrar_uso_ferramenta(nome: str, ator: dict) -> None:
    registrar_auditoria(
        "ferramenta_corporativa_acessada",
        usuario_id=ator.get("id"),
        detalhes=str(nome)[:120],
    )

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
