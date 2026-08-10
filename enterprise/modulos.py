"""Serviços transacionais e indicadores dos módulos empresariais."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

import pandas as pd

from auth.banco import conectar
from enterprise.catalogo import MODULOS, obter_modulo
from enterprise.contexto import exigir_permissao, garantir_contexto_sessao
from enterprise.workflows import executar_workflows


TABELAS_MODULOS = {
    chave: configuracao["entidade"]
    for chave, configuracao in MODULOS.items()
    if configuracao.get("entidade")
}

CAMPOS_MONETARIOS = {
    "rh": ("salario",),
    "financeiro": ("valor",),
    "estoque": ("custo",),
    "compras": ("valor_estimado",),
    "marketing": ("investimento", "receita"),
    "administrativo": ("valor",),
    "juridico": ("valor",),
    "comercial": ("valor",),
}

ESTADOS_REGISTRO = {"Ativo", "Arquivado", "Lixeira"}


def _numero(valor, inteiro=False):
    if valor in (None, ""):
        return 0
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = float(texto)
    except ValueError as erro:
        raise ValueError(f"Valor numérico inválido: {valor}") from erro
    if numero < 0:
        raise ValueError("Valores negativos não são permitidos neste campo.")
    return int(numero) if inteiro else numero


def _centavos(valor) -> int:
    """Converte dinheiro para inteiro com arredondamento decimal previsível."""
    if valor in (None, ""):
        return 0
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        decimal = Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as erro:
        raise ValueError(f"Valor monetário inválido: {valor}") from erro
    if decimal < 0:
        raise ValueError("Valores negativos não são permitidos neste campo.")
    return int(decimal * 100)


def _incluir_centavos(modulo: str, valores: dict) -> None:
    for campo in CAMPOS_MONETARIOS.get(modulo, ()):
        if campo in valores:
            valores[f"{campo}_centavos"] = _centavos(valores[campo])


def _data_iso(valor):
    if valor in (None, ""):
        return None
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Data inválida. Utilize DD/MM/AAAA ou AAAA-MM-DD.")


def _normalizar_dados(modulo: str, dados: dict) -> dict:
    configuracao = obter_modulo(modulo)
    resultado = {}
    for nome, rotulo, tipo, obrigatorio in configuracao.get("campos", ()):
        valor = dados.get(nome)
        if obrigatorio and (valor is None or str(valor).strip() == ""):
            raise ValueError(f"O campo {rotulo} é obrigatório.")
        if tipo == "decimal":
            valor = _numero(valor)
        elif tipo == "inteiro":
            valor = _numero(valor, inteiro=True)
        elif tipo == "data":
            valor = _data_iso(valor)
        elif tipo in {"departamento", "centro_custo"}:
            valor = int(valor) if valor not in (None, "") else None
        else:
            valor = str(valor).strip() if valor is not None else ""
            if isinstance(tipo, tuple) and valor not in tipo:
                raise ValueError(f"Opção inválida para {rotulo}.")
        resultado[nome] = valor
    return resultado


def criar_registro(modulo: str, dados: dict, ator: dict) -> int:
    exigir_permissao(ator, modulo, "escrever")
    empresa_id, filial_id = garantir_contexto_sessao()
    configuracao = obter_modulo(modulo)
    tabela = TABELAS_MODULOS.get(modulo)
    if not tabela:
        raise ValueError("Este módulo não utiliza registros operacionais.")
    valores = _normalizar_dados(modulo, dados)
    _incluir_centavos(modulo, valores)
    valores["empresa_id"] = empresa_id
    valores["filial_id"] = filial_id
    valores["criado_por"] = int(ator["id"])

    colunas = list(valores)
    marcadores = ", ".join("?" for _ in colunas)
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({marcadores})",
                tuple(valores[coluna] for coluna in colunas),
            )
            registro_id = int(cursor.lastrowid)
            _registrar_atividade(
                conexao,
                empresa_id,
                ator["id"],
                modulo,
                "registro_criado",
                f"{configuracao['nome']}: {descricao_registro(modulo, valores)}",
                tabela,
                registro_id,
            )
            _aplicar_regras_iniciais(
                conexao,
                modulo,
                valores,
                registro_id,
                empresa_id,
                ator,
            )
            _registrar_historico_alteracao(
                conexao,
                empresa_id=empresa_id,
                filial_id=filial_id,
                usuario_id=ator["id"],
                modulo=modulo,
                entidade=tabela,
                entidade_id=registro_id,
                acao="Criado",
                depois=valores,
            )
    except sqlite3.IntegrityError as erro:
        raise ValueError(
            "Não foi possível salvar. Verifique códigos duplicados e campos obrigatórios."
        ) from erro
    executar_workflows(
        modulo,
        "registro_criado",
        valores,
        ator,
        recurso_tipo=tabela,
        recurso_id=registro_id,
    )
    return registro_id


def descricao_registro(modulo: str, dados: dict) -> str:
    chaves = {
        "rh": "nome",
        "financeiro": "descricao",
        "estoque": "descricao",
        "compras": "item",
        "ti": "titulo",
        "marketing": "nome",
        "administrativo": "titulo",
        "juridico": "titulo",
        "comercial": "cliente",
    }
    return str(dados.get(chaves.get(modulo, "id"), "Novo registro"))


def listar_registros(modulo: str, ator: dict, limite: int = 200) -> list[dict]:
    """Compatibilidade: devolve os registros ativos da filial atual."""
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = garantir_contexto_sessao()
    tabela = TABELAS_MODULOS.get(modulo)
    if not tabela:
        return []
    limite = max(1, min(int(limite), 1000))
    if modulo == "rh":
        sql = """
            SELECT r.*, d.nome AS departamento_nome, c.nome AS centro_custo_nome
            FROM colaboradores r
            LEFT JOIN departamentos d ON d.id = r.departamento_id
            LEFT JOIN centros_custo c ON c.id = r.centro_custo_id
            WHERE r.empresa_id = ? AND r.filial_id = ?
              AND r.estado_registro = 'Ativo'
            ORDER BY r.id DESC LIMIT ?
        """
    else:
        sql = (
            f"SELECT * FROM {tabela} "
            "WHERE empresa_id = ? AND filial_id = ? "
            "AND estado_registro = 'Ativo' ORDER BY id DESC LIMIT ?"
        )
    with conectar() as conexao:
        registros = conexao.execute(sql, (empresa_id, filial_id, limite)).fetchall()
    return [dict(registro) for registro in registros]


def listar_registros_paginados(
    modulo: str,
    ator: dict,
    *,
    pagina: int = 1,
    tamanho: int = 50,
    pesquisa: str = "",
    status: str = "",
    estado: str = "Ativo",
    ordenar_por: str = "id",
    direcao: str = "DESC",
) -> dict:
    """Consulta uma página filtrada sem carregar o módulo inteiro na UI."""
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = garantir_contexto_sessao()
    tabela = TABELAS_MODULOS.get(modulo)
    if not tabela:
        return {"registros": [], "total": 0, "pagina": 1, "paginas": 1, "tamanho": 50}

    pagina = max(1, int(pagina))
    tamanho = max(10, min(int(tamanho), 200))
    pesquisa = str(pesquisa or "").strip()
    estado = str(estado or "Ativo").title()
    if estado not in ESTADOS_REGISTRO | {"Todos"}:
        raise ValueError("Estado de registro inválido.")
    direcao = "ASC" if str(direcao).upper() == "ASC" else "DESC"

    with conectar() as conexao:
        colunas_banco = {
            item["name"]
            for item in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
        }
        ordenar_por = ordenar_por if ordenar_por in colunas_banco else "id"
        campos_pesquisa = []
        for nome, _rotulo, tipo, _obrigatorio in obter_modulo(modulo).get("campos", ()):
            if nome in colunas_banco and (tipo == "texto" or isinstance(tipo, tuple)):
                campos_pesquisa.append(nome)

        condicoes = ["r.empresa_id = ?", "r.filial_id = ?"]
        parametros: list = [empresa_id, filial_id]
        if estado != "Todos":
            condicoes.append("r.estado_registro = ?")
            parametros.append(estado)
        if status and "status" in colunas_banco:
            condicoes.append("r.status = ?")
            parametros.append(str(status))
        if pesquisa and campos_pesquisa:
            condicoes.append(
                "(" + " OR ".join(
                    f"LOWER(COALESCE(CAST(r.{campo} AS TEXT), '')) LIKE LOWER(?)"
                    for campo in campos_pesquisa
                ) + ")"
            )
            parametros.extend([f"%{pesquisa}%"] * len(campos_pesquisa))

        where = " AND ".join(condicoes)
        total = int(
            conexao.execute(
                f"SELECT COUNT(*) total FROM {tabela} r WHERE {where}",
                parametros,
            ).fetchone()["total"]
        )
        paginas = max(1, (total + tamanho - 1) // tamanho)
        pagina = min(pagina, paginas)
        offset = (pagina - 1) * tamanho

        if modulo == "rh":
            selecao = (
                "SELECT r.*, d.nome AS departamento_nome, "
                "c.nome AS centro_custo_nome FROM colaboradores r "
                "LEFT JOIN departamentos d ON d.id = r.departamento_id "
                "LEFT JOIN centros_custo c ON c.id = r.centro_custo_id"
            )
        else:
            selecao = f"SELECT r.* FROM {tabela} r"
        registros = conexao.execute(
            f"{selecao} WHERE {where} "
            f"ORDER BY r.{ordenar_por} {direcao} LIMIT ? OFFSET ?",
            (*parametros, tamanho, offset),
        ).fetchall()

    return {
        "registros": [dict(registro) for registro in registros],
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "tamanho": tamanho,
    }


def consultar_dados_para_analytics(
    modulo: str,
    ator: dict,
    *,
    limite_explicito: int | None = None,
) -> pd.DataFrame:
    """Consulta o universo autorizado; qualquer amostra deve ser explícita."""
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = garantir_contexto_sessao()
    tabela = TABELAS_MODULOS.get(modulo)
    if not tabela:
        raise ValueError("Este módulo não possui fonte analítica operacional.")

    limite_sql = ""
    parametros: list = [empresa_id, filial_id]
    if limite_explicito is not None:
        limite = max(1, int(limite_explicito))
        limite_sql = " LIMIT ?"
        parametros.append(limite)
    with conectar() as conexao:
        dataframe = pd.read_sql_query(
            f"SELECT * FROM {tabela} WHERE empresa_id = ? AND filial_id = ? "
            f"AND estado_registro = 'Ativo' ORDER BY id{limite_sql}",
            conexao,
            params=parametros,
        )
    if dataframe.empty:
        raise ValueError("O módulo ainda não possui registros para análise.")

    dataframe.attrs["amostra_explicita"] = limite_explicito is not None
    for campo in CAMPOS_MONETARIOS.get(modulo, ()):
        coluna_centavos = f"{campo}_centavos"
        if coluna_centavos in dataframe.columns:
            dataframe[campo] = pd.to_numeric(
                dataframe[coluna_centavos],
                errors="coerce",
            ).fillna(0) / 100
    tecnicas = {
        "id",
        "empresa_id",
        "filial_id",
        "departamento_id",
        "centro_custo_id",
        "criado_por",
        "arquivado_por",
        "estado_registro",
    }
    tecnicas.update(coluna for coluna in dataframe.columns if coluna.endswith("_centavos"))
    dataframe = dataframe.drop(
        columns=[coluna for coluna in tecnicas if coluna in dataframe.columns]
    ).copy(deep=True)
    if modulo == "financeiro" and "tipo" in dataframe.columns:
        dataframe = dataframe.rename(columns={"tipo": "tipo_movimento"})
    return dataframe


def exportar_dataframe_modulo(modulo: str, ator: dict) -> pd.DataFrame:
    """Compatibilidade pública para o motor analítico sem limite silencioso."""
    return consultar_dados_para_analytics(modulo, ator)


def obter_registro(modulo: str, registro_id: int, ator: dict) -> dict:
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = garantir_contexto_sessao()
    tabela = TABELAS_MODULOS.get(modulo)
    if not tabela:
        raise ValueError("Módulo sem registros operacionais.")
    with conectar() as conexao:
        registro = conexao.execute(
            f"SELECT * FROM {tabela} WHERE id = ? AND empresa_id = ? AND filial_id = ?",
            (int(registro_id), empresa_id, filial_id),
        ).fetchone()
    if registro is None:
        raise ValueError("Registro não encontrado nesta filial.")
    return dict(registro)


def atualizar_registro(modulo: str, registro_id: int, dados: dict, ator: dict) -> None:
    exigir_permissao(ator, modulo, "escrever")
    empresa_id, filial_id = garantir_contexto_sessao()
    tabela = TABELAS_MODULOS.get(modulo)
    if not tabela:
        raise ValueError("Módulo sem registros operacionais.")
    valores = _normalizar_dados(modulo, dados)
    _incluir_centavos(modulo, valores)
    with conectar() as conexao:
        anterior = conexao.execute(
            f"SELECT * FROM {tabela} WHERE id = ? AND empresa_id = ? AND filial_id = ?",
            (int(registro_id), empresa_id, filial_id),
        ).fetchone()
        if anterior is None:
            raise ValueError("Registro não encontrado nesta filial.")
        atribuicoes = ", ".join(f"{coluna} = ?" for coluna in valores)
        conexao.execute(
            f"UPDATE {tabela} SET {atribuicoes}, atualizado_em = CURRENT_TIMESTAMP "
            "WHERE id = ? AND empresa_id = ? AND filial_id = ?",
            (*valores.values(), int(registro_id), empresa_id, filial_id),
        )
        depois = dict(anterior)
        depois.update(valores)
        _registrar_historico_alteracao(
            conexao,
            empresa_id=empresa_id,
            filial_id=filial_id,
            usuario_id=ator["id"],
            modulo=modulo,
            entidade=tabela,
            entidade_id=int(registro_id),
            acao="Atualizado",
            antes=dict(anterior),
            depois=depois,
        )
        _registrar_atividade(
            conexao,
            empresa_id,
            ator["id"],
            modulo,
            "registro_atualizado",
            f"{obter_modulo(modulo)['nome']}: registro atualizado",
            tabela,
            int(registro_id),
        )


def alterar_estado_registro(
    modulo: str,
    registro_id: int,
    estado: str,
    ator: dict,
) -> None:
    """Arquiva, envia à lixeira ou restaura sem apagar dados empresariais."""
    exigir_permissao(ator, modulo, "escrever")
    estado = str(estado).title()
    if estado not in ESTADOS_REGISTRO:
        raise ValueError("Estado de registro inválido.")
    empresa_id, filial_id = garantir_contexto_sessao()
    tabela = TABELAS_MODULOS.get(modulo)
    if not tabela:
        raise ValueError("Módulo sem registros operacionais.")
    with conectar() as conexao:
        anterior = conexao.execute(
            f"SELECT * FROM {tabela} WHERE id = ? AND empresa_id = ? AND filial_id = ?",
            (int(registro_id), empresa_id, filial_id),
        ).fetchone()
        if anterior is None:
            raise ValueError("Registro não encontrado nesta filial.")
        arquivado_em = None if estado == "Ativo" else datetime.now().isoformat(timespec="seconds")
        arquivado_por = None if estado == "Ativo" else int(ator["id"])
        conexao.execute(
            f"UPDATE {tabela} SET estado_registro = ?, arquivado_em = ?, "
            "arquivado_por = ?, atualizado_em = CURRENT_TIMESTAMP "
            "WHERE id = ? AND empresa_id = ? AND filial_id = ?",
            (estado, arquivado_em, arquivado_por, int(registro_id), empresa_id, filial_id),
        )
        depois = dict(anterior)
        depois.update(
            estado_registro=estado,
            arquivado_em=arquivado_em,
            arquivado_por=arquivado_por,
        )
        _registrar_historico_alteracao(
            conexao,
            empresa_id=empresa_id,
            filial_id=filial_id,
            usuario_id=ator["id"],
            modulo=modulo,
            entidade=tabela,
            entidade_id=int(registro_id),
            acao=estado,
            antes=dict(anterior),
            depois=depois,
        )


def listar_historico_registro(modulo: str, registro_id: int, ator: dict) -> list[dict]:
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = garantir_contexto_sessao()
    tabela = TABELAS_MODULOS.get(modulo)
    with conectar() as conexao:
        registros = conexao.execute(
            """
            SELECT h.*, u.nome AS usuario_nome
            FROM historico_alteracoes h
            LEFT JOIN usuarios u ON u.id = h.usuario_id
            WHERE h.empresa_id = ? AND h.filial_id = ?
              AND h.modulo = ? AND h.entidade = ? AND h.entidade_id = ?
            ORDER BY h.id DESC
            """,
            (empresa_id, filial_id, modulo, tabela, int(registro_id)),
        ).fetchall()
    return [dict(item) for item in registros]


def movimentar_estoque(
    item_id: int,
    tipo: str,
    quantidade,
    ator: dict,
    observacao: str = "",
) -> None:
    exigir_permissao(ator, "estoque", "escrever")
    empresa_id, filial_id = garantir_contexto_sessao()
    if tipo not in {"Entrada", "Saída", "Ajuste"}:
        raise ValueError("Tipo de movimentação inválido.")
    quantidade = _numero(quantidade)
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")
    with conectar() as conexao:
        item = conexao.execute(
            "SELECT * FROM itens_estoque "
            "WHERE id = ? AND empresa_id = ? AND filial_id = ? "
            "AND estado_registro = 'Ativo'",
            (int(item_id), empresa_id, filial_id),
        ).fetchone()
        if item is None:
            raise ValueError("Item não encontrado.")
        atual = float(item["quantidade"])
        novo = quantidade if tipo == "Ajuste" else (
            atual + quantidade if tipo == "Entrada" else atual - quantidade
        )
        if novo < 0:
            raise ValueError("A saída deixaria o estoque negativo.")
        conexao.execute(
            "UPDATE itens_estoque SET quantidade = ?, atualizado_em = CURRENT_TIMESTAMP "
            "WHERE id = ? AND empresa_id = ? AND filial_id = ?",
            (novo, int(item_id), empresa_id, filial_id),
        )
        conexao.execute(
            """
            INSERT INTO movimentos_estoque (
                empresa_id, item_id, tipo, quantidade, observacao, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (empresa_id, int(item_id), tipo, quantidade, observacao, ator["id"]),
        )
        _registrar_atividade(
            conexao,
            empresa_id,
            ator["id"],
            "estoque",
            "movimentacao",
            f"{tipo} de {quantidade:g} em {item['descricao']}",
            "itens_estoque",
            int(item_id),
        )
        if novo <= float(item["estoque_minimo"]):
            _notificar(
                conexao,
                empresa_id,
                "estoque",
                "Estoque crítico",
                f"{item['descricao']} possui {novo:g}; mínimo {item['estoque_minimo']:g}.",
                "aviso" if novo > 0 else "critico",
                "itens_estoque",
                int(item_id),
            )


def calcular_resumo_modulo(modulo: str, ator: dict) -> dict:
    exigir_permissao(ator, modulo, "ler")
    empresa_id, filial_id = garantir_contexto_sessao()
    with conectar() as conexao:
        if modulo == "rh":
            linha = conexao.execute(
                """
                SELECT COUNT(*) total,
                       SUM(CASE WHEN status = 'Ativo' THEN 1 ELSE 0 END) ativos,
                       COUNT(DISTINCT departamento_id) departamentos,
                       COALESCE(SUM(CASE WHEN status = 'Ativo' THEN salario_centavos ELSE 0 END), 0) / 100.0 folha
                FROM colaboradores WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            cards = (("COLABORADORES", linha["total"], "inteiro"), ("ATIVOS", linha["ativos"], "inteiro"), ("DEPARTAMENTOS", linha["departamentos"], "inteiro"), ("FOLHA BASE", linha["folha"], "moeda"))
        elif modulo == "financeiro":
            linha = conexao.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN tipo='Receita' AND status!='Cancelado' THEN valor_centavos ELSE 0 END),0) / 100.0 receitas,
                       COALESCE(SUM(CASE WHEN tipo='Despesa' AND status!='Cancelado' THEN valor_centavos ELSE 0 END),0) / 100.0 despesas,
                       SUM(CASE WHEN status='Pendente' THEN 1 ELSE 0 END) pendentes
                FROM lancamentos_financeiros
                WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            saldo = float(linha["receitas"]) - float(linha["despesas"])
            cards = (("RECEITAS", linha["receitas"], "moeda"), ("DESPESAS", linha["despesas"], "moeda"), ("SALDO", saldo, "moeda"), ("PENDENTES", linha["pendentes"], "inteiro"))
        elif modulo == "estoque":
            linha = conexao.execute(
                """
                SELECT COUNT(*) itens, COALESCE(SUM(quantidade),0) unidades,
                       SUM(CASE WHEN quantidade <= estoque_minimo THEN 1 ELSE 0 END) criticos,
                       COALESCE(SUM(quantidade * custo_centavos),0) / 100.0 valor
                FROM itens_estoque WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo' AND status='Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            cards = (("ITENS", linha["itens"], "inteiro"), ("UNIDADES", linha["unidades"], "decimal"), ("CRÍTICOS", linha["criticos"], "inteiro"), ("VALOR", linha["valor"], "moeda"))
        elif modulo == "compras":
            linha = conexao.execute(
                """
                SELECT COUNT(*) total,
                       SUM(CASE WHEN status='Pendente' THEN 1 ELSE 0 END) pendentes,
                       SUM(CASE WHEN status='Aprovado' THEN 1 ELSE 0 END) aprovadas,
                       COALESCE(SUM(valor_estimado_centavos),0) / 100.0 valor
                FROM solicitacoes_compra WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            cards = (("SOLICITAÇÕES", linha["total"], "inteiro"), ("PENDENTES", linha["pendentes"], "inteiro"), ("APROVADAS", linha["aprovadas"], "inteiro"), ("VALOR ESTIMADO", linha["valor"], "moeda"))
        elif modulo == "ti":
            linha = conexao.execute(
                """
                SELECT COUNT(*) total,
                       SUM(CASE WHEN status!='Concluído' THEN 1 ELSE 0 END) abertos,
                       SUM(CASE WHEN prioridade='Crítica' AND status!='Concluído' THEN 1 ELSE 0 END) criticos,
                       SUM(CASE WHEN status='Concluído' THEN 1 ELSE 0 END) concluidos
                FROM chamados_ti WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            ativos = conexao.execute(
                "SELECT COUNT(*) total FROM ativos_ti "
                "WHERE empresa_id = ? AND filial_id = ? "
                "AND estado_registro = 'Ativo'",
                (empresa_id, filial_id),
            ).fetchone()["total"]
            cards = (("CHAMADOS", linha["total"], "inteiro"), ("ABERTOS", linha["abertos"], "inteiro"), ("CRÍTICOS", linha["criticos"], "inteiro"), ("ATIVOS TI", ativos, "inteiro"))
        elif modulo == "marketing":
            linha = conexao.execute(
                """
                SELECT COALESCE(SUM(investimento_centavos),0) / 100.0 investimento,
                       COALESCE(SUM(leads),0) leads,
                       COALESCE(SUM(conversoes),0) conversoes,
                       COALESCE(SUM(receita_centavos),0) / 100.0 receita
                FROM campanhas_marketing WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            cards = (("INVESTIMENTO", linha["investimento"], "moeda"), ("LEADS", linha["leads"], "inteiro"), ("CONVERSÕES", linha["conversoes"], "inteiro"), ("RECEITA", linha["receita"], "moeda"))
        elif modulo == "administrativo":
            linha = conexao.execute(
                """
                SELECT COUNT(*) total,
                       SUM(CASE WHEN status IN ('Pendente','Em análise') THEN 1 ELSE 0 END) pendentes,
                       SUM(CASE WHEN status='Aprovado' THEN 1 ELSE 0 END) aprovadas,
                       COALESCE(SUM(valor_centavos),0) / 100.0 valor
                FROM solicitacoes_administrativas
                WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            cards = (("SOLICITAÇÕES", linha["total"], "inteiro"), ("PENDENTES", linha["pendentes"], "inteiro"), ("APROVADAS", linha["aprovadas"], "inteiro"), ("VALOR", linha["valor"], "moeda"))
        elif modulo == "juridico":
            limite = (date.today() + timedelta(days=30)).isoformat()
            linha = conexao.execute(
                """
                SELECT COUNT(*) total,
                       SUM(CASE WHEN status='Ativo' THEN 1 ELSE 0 END) ativos,
                       SUM(CASE WHEN vencimento IS NOT NULL AND vencimento <= ? AND status='Ativo' THEN 1 ELSE 0 END) vencendo,
                       COALESCE(SUM(CASE WHEN risco IN ('Alto','Crítico') THEN valor_centavos ELSE 0 END),0) / 100.0 risco_valor
                FROM contratos_juridicos WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (limite, empresa_id, filial_id),
            ).fetchone()
            cards = (("CONTRATOS", linha["total"], "inteiro"), ("ATIVOS", linha["ativos"], "inteiro"), ("VENCEM EM 30 DIAS", linha["vencendo"], "inteiro"), ("RISCO ALTO", linha["risco_valor"], "moeda"))
        elif modulo == "comercial":
            linha = conexao.execute(
                """
                SELECT COUNT(*) total,
                       SUM(CASE WHEN status='Aberto' THEN 1 ELSE 0 END) abertas,
                       SUM(CASE WHEN status='Ganho' THEN 1 ELSE 0 END) ganhas,
                       COALESCE(SUM(CASE WHEN status='Aberto' THEN valor_centavos ELSE 0 END),0) / 100.0 pipeline
                FROM oportunidades_comerciais
                WHERE empresa_id = ? AND filial_id = ?
                  AND estado_registro = 'Ativo'
                """,
                (empresa_id, filial_id),
            ).fetchone()
            cards = (("OPORTUNIDADES", linha["total"], "inteiro"), ("ABERTAS", linha["abertas"], "inteiro"), ("GANHAS", linha["ganhas"], "inteiro"), ("PIPELINE", linha["pipeline"], "moeda"))
        else:
            cards = ()
    return {"modulo": modulo, "cards": cards}


def _registrar_atividade(
    conexao,
    empresa_id,
    usuario_id,
    modulo,
    acao,
    descricao,
    recurso_tipo=None,
    recurso_id=None,
):
    conexao.execute(
        """
        INSERT INTO atividades (
            usuario_id, empresa_id, modulo, acao, descricao,
            recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (usuario_id, empresa_id, modulo, acao, descricao, recurso_tipo, recurso_id),
    )


def _registrar_historico_alteracao(
    conexao,
    *,
    empresa_id,
    filial_id,
    usuario_id,
    modulo,
    entidade,
    entidade_id,
    acao,
    antes=None,
    depois=None,
):
    operacao_id = f"AUD-{uuid4().hex[:12].upper()}"
    conexao.execute(
        """
        INSERT INTO historico_alteracoes (
            operacao_id, empresa_id, filial_id, usuario_id,
            modulo, entidade, entidade_id, acao,
            dados_antes, dados_depois
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            operacao_id,
            empresa_id,
            filial_id,
            usuario_id,
            modulo,
            entidade,
            entidade_id,
            acao,
            json.dumps(antes, ensure_ascii=False, default=str) if antes else None,
            json.dumps(depois, ensure_ascii=False, default=str) if depois else None,
        ),
    )


def _notificar(
    conexao,
    empresa_id,
    modulo,
    titulo,
    mensagem,
    nivel="info",
    recurso_tipo=None,
    recurso_id=None,
    usuario_id=None,
):
    conexao.execute(
        """
        INSERT INTO notificacoes (
            usuario_id, empresa_id, modulo, titulo, mensagem, nivel,
            recurso_tipo, recurso_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (usuario_id, empresa_id, modulo, titulo, mensagem, nivel, recurso_tipo, recurso_id),
    )


def _aplicar_regras_iniciais(
    conexao,
    modulo,
    dados,
    registro_id,
    empresa_id,
    ator,
):
    tabela = TABELAS_MODULOS[modulo]
    if modulo == "estoque" and dados["quantidade"] <= dados["estoque_minimo"]:
        _notificar(
            conexao, empresa_id, modulo, "Estoque abaixo do mínimo",
            f"{dados['descricao']} iniciou com {dados['quantidade']:g} unidades.",
            "aviso", tabela, registro_id,
        )
    elif modulo == "ti" and dados["prioridade"] == "Crítica":
        _notificar(
            conexao, empresa_id, modulo, "Chamado crítico aberto",
            dados["titulo"], "critico", tabela, registro_id,
        )
    elif modulo == "juridico" and dados.get("vencimento"):
        vencimento = date.fromisoformat(dados["vencimento"])
        if vencimento <= date.today() + timedelta(days=30):
            _notificar(
                conexao, empresa_id, modulo, "Contrato próximo do vencimento",
                f"{dados['titulo']} vence em {vencimento.strftime('%d/%m/%Y')}.",
                "aviso", tabela, registro_id,
            )
    elif modulo == "rh" and dados.get("status") == "Ativo":
        for destino, titulo in (
            ("rh", f"Preparar documentos de {dados['nome']}"),
            ("ti", f"Preparar acesso e equipamento para {dados['nome']}"),
            ("estoque", f"Separar equipamentos de {dados['nome']}"),
        ):
            conexao.execute(
                """
                INSERT INTO tarefas (
                    empresa_id, modulo, titulo, prioridade,
                    recurso_tipo, recurso_id
                ) VALUES (?, ?, ?, 'Média', ?, ?)
                """,
                (empresa_id, destino, titulo, tabela, registro_id),
            )

    if modulo in {"compras", "administrativo"}:
        valor = float(dados.get("valor_estimado", dados.get("valor", 0)) or 0)
        valor_centavos = _centavos(valor)
        titulo = descricao_registro(modulo, dados)
        conexao.execute(
            """
                INSERT INTO aprovacoes (
                    empresa_id, filial_id, solicitante_id, modulo, recurso_tipo,
                    recurso_id, titulo, valor, valor_centavos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                empresa_id,
                dados.get("filial_id"),
                ator["id"],
                modulo,
                tabela,
                registro_id,
                titulo,
                valor,
                valor_centavos,
            ),
        )
