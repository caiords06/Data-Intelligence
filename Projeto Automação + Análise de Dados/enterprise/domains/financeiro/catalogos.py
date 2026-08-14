"""Catálogos e referências financeiras. Extraído na V9.5."""
from __future__ import annotations

from enterprise.domains.financeiro.base import conectar, exigir_acao, obter_escopo_ator

def garantir_catalogos(ator: dict) -> None:
    """Cria o plano mínimo também para empresas abertas após a migração."""
    exigir_acao(ator, "visualizar")
    empresa_id, _ = obter_escopo_ator(ator)
    planos = (
        ("1.1", "Vendas", "Receita", "Receita bruta"),
        ("1.2", "Serviços", "Receita", "Receita bruta"),
        ("1.3", "Receitas financeiras", "Receita", "Resultado financeiro"),
        ("2.1", "Impostos sobre vendas", "Despesa", "Deduções"),
        ("3.1", "Mercadorias e produção", "Despesa", "Custos"),
        ("4.1", "Administrativo", "Despesa", "Despesas operacionais"),
        ("4.2", "Marketing", "Despesa", "Despesas operacionais"),
        ("4.3", "Tecnologia", "Despesa", "Despesas operacionais"),
        ("4.4", "Recursos Humanos", "Despesa", "Despesas operacionais"),
        ("5.1", "Juros e tarifas", "Despesa", "Resultado financeiro"),
        ("9.1", "Transferências internas", "Neutra", "Não operacional"),
    )
    with conectar() as conexao:
        for codigo, nome, natureza, grupo in planos:
            conexao.execute(
                "INSERT OR IGNORE INTO fin_plano_contas "
                "(empresa_id,codigo,nome,natureza,grupo_dre) VALUES (?,?,?,?,?)",
                (empresa_id, codigo, nome, natureza, grupo),
            )


def listar_catalogos(ator: dict) -> dict:
    garantir_catalogos(ator)
    empresa_id, filial_id = obter_escopo_ator(ator)
    with conectar() as conexao:
        def linhas(sql, parametros=()):
            return [dict(item) for item in conexao.execute(sql, parametros).fetchall()]
        return {
            "contas": linhas(
                "SELECT id,nome,banco,tipo,status FROM fin_contas "
                "WHERE empresa_id=? AND filial_id=? ORDER BY nome",
                (empresa_id, filial_id),
            ),
            "partes": linhas(
                "SELECT id,nome,tipo,documento,status FROM fin_partes "
                "WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL) ORDER BY nome",
                (empresa_id, filial_id),
            ),
            "plano_contas": linhas(
                "SELECT id,codigo,nome,natureza,grupo_dre FROM fin_plano_contas "
                "WHERE empresa_id=? AND ativo=1 ORDER BY codigo",
                (empresa_id,),
            ),
            "categorias": linhas(
                "SELECT id,nome,natureza,plano_conta_id FROM fin_categorias "
                "WHERE empresa_id=? AND ativo=1 ORDER BY nome",
                (empresa_id,),
            ),
            "projetos": linhas(
                "SELECT id,codigo,nome,status FROM fin_projetos "
                "WHERE empresa_id=? AND (filial_id=? OR filial_id IS NULL) ORDER BY nome",
                (empresa_id, filial_id),
            ),
            "departamentos": linhas(
                "SELECT id,codigo,nome FROM departamentos WHERE empresa_id=? AND ativo=1 ORDER BY nome",
                (empresa_id,),
            ),
            "centros_custo": linhas(
                "SELECT id,codigo,nome,departamento_id FROM centros_custo "
                "WHERE empresa_id=? AND ativo=1 ORDER BY nome",
                (empresa_id,),
            ),
        }
