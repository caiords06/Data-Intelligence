"""Biblioteca persistente de conjuntos de dados do Analytics V8.1."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from auth import banco
from auth.banco import conectar, registrar_auditoria
from dados.classificador import classificar_dataframe
from dados.leitor import carregar_planilha, validar_arquivo
from dados.periodos import identificar_periodo
from enterprise.contexto import exigir_permissao, obter_escopo_ator


def _hash(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        while bloco := arquivo.read(1024 * 1024):
            resumo.update(bloco)
    return resumo.hexdigest()


def _destino(empresa_id, filial_id, extensao):
    pasta = (
        banco.STORAGE_DIR
        / "datasets"
        / str(empresa_id)
        / str(filial_id or 0)
    )
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"{uuid4().hex}{extensao.lower()}"


def importar_conjunto(
    caminho,
    *,
    nome="",
    descricao="",
    origem="Computador",
    tags="",
    ator,
):
    exigir_permissao(ator, "analytics", "escrever")
    origem_arquivo = validar_arquivo(caminho).expanduser().resolve()
    dataframe = carregar_planilha(origem_arquivo)
    classificacao = classificar_dataframe(dataframe)
    periodo = identificar_periodo(dataframe, origem_arquivo.name)
    empresa_id, filial_id = obter_escopo_ator(ator)
    destino = _destino(empresa_id, filial_id, origem_arquivo.suffix)
    shutil.copy2(origem_arquivo, destino)
    resumo = _hash(destino)
    nome = str(nome).strip() or origem_arquivo.stem
    if len(nome) < 2 or len(nome) > 160:
        destino.unlink(missing_ok=True)
        raise ValueError("O nome do conjunto deve possuir entre 2 e 160 caracteres.")
    relativo = destino.relative_to(banco.STORAGE_DIR).as_posix()
    try:
        with conectar() as conexao:
            existente = conexao.execute(
                """
                SELECT id FROM conjuntos_dados
                WHERE empresa_id=? AND filial_id IS ? AND hash_sha256=?
                  AND estado_registro='Ativo'
                """,
                (empresa_id, filial_id, resumo),
            ).fetchone()
            if existente:
                raise ValueError("Este arquivo já existe na biblioteca de dados.")
            cursor = conexao.execute(
                """
                INSERT INTO conjuntos_dados (
                    empresa_id, filial_id, nome, descricao, origem,
                    nome_original, caminho_relativo, extensao, tamanho_bytes,
                    total_registros, total_colunas, categoria,
                    data_inicial, data_final, status, hash_sha256, tags,
                    responsavel_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          'Pronto', ?, ?, ?)
                """,
                (
                    empresa_id,
                    filial_id,
                    nome,
                    str(descricao).strip()[:1000],
                    str(origem).strip()[:80],
                    origem_arquivo.name,
                    relativo,
                    origem_arquivo.suffix.lower(),
                    destino.stat().st_size,
                    len(dataframe),
                    len(dataframe.columns),
                    classificacao.get("categoria") or "automatica",
                    str(periodo.get("data_inicial") or "") or None,
                    str(periodo.get("data_final") or "") or None,
                    resumo,
                    str(tags).strip()[:500],
                    int(ator["id"]),
                ),
            )
            conjunto_id = int(cursor.lastrowid)
    except Exception:
        destino.unlink(missing_ok=True)
        raise
    registrar_auditoria(
        "dataset_importado",
        usuario_id=int(ator["id"]),
        empresa_id=empresa_id,
        filial_id=filial_id,
        modulo="analytics",
        entidade="conjuntos_dados",
        entidade_id=conjunto_id,
        dados_depois={"nome": nome, "hash": resumo},
    )
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="analytics", categoria="dataset")
    except Exception:
        pass
    return conjunto_id


def listar_conjuntos(ator, *, termo="", limite=200):
    exigir_permissao(ator, "analytics", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    termo = str(termo).strip()
    filtro = ""
    parametros = [empresa_id, filial_id]
    if termo:
        filtro = "AND (nome LIKE ? OR nome_original LIKE ? OR categoria LIKE ?)"
        busca = f"%{termo}%"
        parametros.extend([busca, busca, busca])
    parametros.append(max(1, min(int(limite), 1000)))
    with conectar() as conexao:
        registros = conexao.execute(
            f"""
            SELECT c.*, u.nome AS responsavel_nome
            FROM conjuntos_dados c
            LEFT JOIN usuarios u ON u.id=c.responsavel_id
            WHERE c.empresa_id=? AND c.filial_id IS ?
              AND c.estado_registro='Ativo' {filtro}
            ORDER BY c.atualizado_em DESC, c.id DESC LIMIT ?
            """,
            parametros,
        ).fetchall()
    return [dict(item) for item in registros]


def obter_conjunto(conjunto_id, ator):
    exigir_permissao(ator, "analytics", "ler")
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        registro = conexao.execute(
            """
            SELECT * FROM conjuntos_dados
            WHERE id=? AND empresa_id=? AND filial_id IS ?
              AND estado_registro='Ativo'
            """,
            (int(conjunto_id), empresa_id, filial_id),
        ).fetchone()
    if not registro:
        raise ValueError("Conjunto de dados não encontrado.")
    resultado = dict(registro)
    caminho = (banco.STORAGE_DIR / resultado["caminho_relativo"]).resolve()
    if banco.STORAGE_DIR.resolve() not in caminho.parents or not caminho.is_file():
        raise FileNotFoundError("O arquivo administrado do conjunto não está disponível.")
    if _hash(caminho) != resultado["hash_sha256"]:
        raise ValueError("A integridade do conjunto de dados foi comprometida.")
    resultado["caminho"] = str(caminho)
    return resultado


def excluir_conjunto(conjunto_id, ator):
    exigir_permissao(ator, "analytics", "escrever")
    registro = obter_conjunto(conjunto_id, ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE conjuntos_dados
            SET estado_registro='Lixeira', atualizado_em=CURRENT_TIMESTAMP
            WHERE id=? AND empresa_id=? AND filial_id IS ?
            """,
            (int(conjunto_id), empresa_id, filial_id),
        )
    registrar_auditoria(
        "dataset_movido_lixeira",
        usuario_id=int(ator["id"]),
        empresa_id=empresa_id,
        filial_id=filial_id,
        modulo="analytics",
        entidade="conjuntos_dados",
        entidade_id=int(conjunto_id),
        dados_antes={"nome": registro["nome"], "estado": "Ativo"},
        dados_depois={"estado": "Lixeira"},
    )


def atualizar_metadados_conjunto(
    conjunto_id,
    *,
    nome,
    descricao="",
    tags="",
    ator,
):
    """Atualiza somente metadados sem alterar o arquivo administrado."""
    exigir_permissao(ator, "analytics", "escrever")
    atual = obter_conjunto(conjunto_id, ator)
    nome = str(nome).strip()
    if len(nome) < 2 or len(nome) > 160:
        raise ValueError("O nome do conjunto deve possuir entre 2 e 160 caracteres.")
    empresa_id, filial_id = obter_escopo_ator(ator)
    depois = {
        "nome": nome,
        "descricao": str(descricao).strip()[:1000],
        "tags": str(tags).strip()[:500],
    }
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE conjuntos_dados
            SET nome=?, descricao=?, tags=?, atualizado_em=CURRENT_TIMESTAMP
            WHERE id=? AND empresa_id=? AND filial_id IS ?
              AND estado_registro='Ativo'
            """,
            (
                depois["nome"],
                depois["descricao"],
                depois["tags"],
                int(conjunto_id),
                empresa_id,
                filial_id,
            ),
        )
    registrar_auditoria(
        "dataset_metadados_atualizados",
        usuario_id=int(ator["id"]),
        empresa_id=empresa_id,
        filial_id=filial_id,
        modulo="analytics",
        entidade="conjuntos_dados",
        entidade_id=int(conjunto_id),
        dados_antes={
            "nome": atual["nome"],
            "descricao": atual.get("descricao") or "",
            "tags": atual.get("tags") or "",
        },
        dados_depois=depois,
    )


def substituir_arquivo_conjunto(conjunto_id, caminho, ator):
    """Cria nova versão do arquivo e troca a referência de forma transacional."""
    exigir_permissao(ator, "analytics", "escrever")
    atual = obter_conjunto(conjunto_id, ator)
    origem = validar_arquivo(caminho).expanduser().resolve()
    dataframe = carregar_planilha(origem)
    classificacao = classificar_dataframe(dataframe)
    periodo = identificar_periodo(dataframe, origem.name)
    empresa_id, filial_id = obter_escopo_ator(ator)
    destino = _destino(empresa_id, filial_id, origem.suffix)
    shutil.copy2(origem, destino)
    resumo = _hash(destino)
    relativo = destino.relative_to(banco.STORAGE_DIR).as_posix()
    try:
        with conectar() as conexao:
            duplicado = conexao.execute(
                """
                SELECT id FROM conjuntos_dados
                WHERE empresa_id=? AND filial_id IS ? AND hash_sha256=?
                  AND estado_registro='Ativo' AND id<>?
                """,
                (empresa_id, filial_id, resumo, int(conjunto_id)),
            ).fetchone()
            if duplicado:
                raise ValueError("Este arquivo já pertence a outro conjunto ativo.")
            conexao.execute(
                """
                UPDATE conjuntos_dados
                SET nome_original=?, caminho_relativo=?, extensao=?,
                    tamanho_bytes=?, total_registros=?, total_colunas=?,
                    categoria=?, data_inicial=?, data_final=?, status='Pronto',
                    hash_sha256=?, versao=versao+1,
                    responsavel_id=?, atualizado_em=CURRENT_TIMESTAMP
                WHERE id=? AND empresa_id=? AND filial_id IS ?
                  AND estado_registro='Ativo'
                """,
                (
                    origem.name,
                    relativo,
                    origem.suffix.lower(),
                    destino.stat().st_size,
                    len(dataframe),
                    len(dataframe.columns),
                    classificacao.get("categoria") or "automatica",
                    str(periodo.get("data_inicial") or "") or None,
                    str(periodo.get("data_final") or "") or None,
                    resumo,
                    int(ator["id"]),
                    int(conjunto_id),
                    empresa_id,
                    filial_id,
                ),
            )
    except Exception:
        destino.unlink(missing_ok=True)
        raise
    antigo = Path(atual["caminho"])
    if antigo != destino and banco.STORAGE_DIR.resolve() in antigo.resolve().parents:
        antigo.unlink(missing_ok=True)
    registrar_auditoria(
        "dataset_arquivo_substituido",
        usuario_id=int(ator["id"]),
        empresa_id=empresa_id,
        filial_id=filial_id,
        modulo="analytics",
        entidade="conjuntos_dados",
        entidade_id=int(conjunto_id),
        dados_antes={
            "arquivo": atual["nome_original"],
            "hash": atual["hash_sha256"],
            "versao": atual["versao"],
        },
        dados_depois={
            "arquivo": origem.name,
            "hash": resumo,
            "versao": int(atual["versao"]) + 1,
        },
    )
    try:
        from enterprise.servidor_cliente import espelhar_exportacao
        espelhar_exportacao(destino, modulo="analytics", categoria="dataset")
    except Exception:
        pass

# V9.1: em estações Central/Cliente, as APIs transacionais permitidas acima
# são executadas no Servidor Corporativo. No servidor/standalone permanecem locais.
from core.rpc_central import instalar_proxy_modulo as _instalar_proxy_modulo
_instalar_proxy_modulo(globals(), __name__)
del _instalar_proxy_modulo
