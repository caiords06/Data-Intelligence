"""Workspace especializado e funcional do Estoque 2.0."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.departamentos.estoque import (
    ACOES_ESTOQUE,
    agendar_relatorio,
    analisar_estoque,
    aprovar_inventario,
    aprovar_operacao,
    atualizar_item,
    calcular_reposicao,
    cancelar_operacao,
    conferir_operacao,
    confirmar_operacao,
    criar_categoria,
    criar_deposito,
    criar_fornecedor,
    criar_item,
    criar_localizacao,
    criar_operacao,
    criar_reserva,
    criar_solicitacao,
    decidir_solicitacao,
    encaminhar_reposicao_compras,
    finalizar_inventario,
    gerar_alertas_estoque,
    gerar_relatorio_estoque,
    iniciar_inventario,
    itens_inventario,
    liberar_reserva,
    listar_auditoria_estoque,
    listar_catalogos,
    listar_inventarios,
    listar_itens,
    listar_movimentacoes,
    listar_operacoes,
    listar_reservas,
    listar_secao,
    obter_item,
    obter_primeiro_item_operacao,
    receber_transferencia,
    registrar_contagem,
    registrar_ocorrencia,
    resolver_alerta,
    resumo_estoque,
    tem_permissao_estoque,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_campo_pesquisa,
    criar_estado_vazio,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
    preparar_janela_secundaria,
)
from interface.grade_editavel import EditorGrade
from interface.componentes_departamentais import renderizar_acessos_rapidos, renderizar_metricas
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_ESTOQUE = "#F59E0B"

GRUPOS_MENU = (
    ("ESTOQUE", (("visao", "⌂", "Visão geral"),)),
    ("CADASTROS", (
        ("itens", "□", "Itens e produtos"),
        ("categorias", "▦", "Categorias"),
        ("patrimonio", "▣", "Patrimônio e ativos"),
        ("fornecedores", "◇", "Fornecedores"),
    )),
    ("OPERAÇÕES", (
        ("movimentacoes", "⇄", "Movimentações"),
        ("recebimentos", "↓", "Recebimentos"),
        ("saidas", "↑", "Saídas e expedição"),
        ("reservas", "○", "Reservas"),
        ("transferencias", "↔", "Transferências"),
        ("devolucoes", "↩", "Devoluções"),
    )),
    ("CONTROLE", (
        ("inventario", "✓", "Inventários"),
        ("depositos", "▦", "Depósitos e endereços"),
        ("lotes", "◫", "Lotes e validade"),
        ("avarias", "!", "Avarias e perdas"),
    )),
    ("PLANEJAMENTO", (
        ("reposicao", "↻", "Reposição e cobertura"),
        ("alertas", "!", "Central de alertas"),
        ("solicitacoes", "◎", "Solicitações"),
    )),
    ("GESTÃO", (
        ("relatorios", "▤", "Relatórios"),
        ("auditoria", "◉", "Auditoria"),
        ("configuracoes", "⚙", "Configurações"),
    )),
)

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "itens": "Ficha completa, saldos físico/disponível/reservado, custos, rastreabilidade e regras de reposição.",
    "categorias": "Classificação hierárquica dos materiais, produtos e ativos.",
    "patrimonio": "Séries, patrimônios, responsáveis, garantias, condição e histórico individual.",
    "fornecedores": "Cadastro central, prazo médio, contatos e avaliação dos fornecedores.",
    "movimentacoes": "Razão imutável: toda alteração de quantidade, origem, destino, usuário e documento.",
    "recebimentos": "Recebimento de compra, conferência, divergências, lote/série e armazenagem.",
    "saidas": "Separação, consumo interno, expedição, centro de custo e responsável.",
    "reservas": "Bloqueio de disponibilidade para admissões, solicitações, projetos e operações futuras.",
    "transferencias": "Solicitação, aprovação, separação, trânsito, recebimento e conferência.",
    "devolucoes": "Retorno de colaboradores, clientes, fornecedores, transferências e reentrada controlada.",
    "inventario": "Contagem geral, parcial ou rotativa, contagem cega, recontagem e ajuste auditado.",
    "depositos": "Depósitos, almoxarifados, corredores, prateleiras, posições e capacidade.",
    "lotes": "Fabricação, validade, quarentena, bloqueio e separação FEFO.",
    "avarias": "Perdas, avarias, vencimentos, quarentena, manutenção e destinação.",
    "reposicao": "Cobertura estimada, consumo médio, ponto de pedido e integração com Compras.",
    "alertas": "Estoque crítico, falta, excesso, validade, divergências e ocorrências suspeitas.",
    "solicitacoes": "Pedido interno, aprovação, reserva, separação e entrega ao solicitante.",
}


def _moeda(centavos):
    if centavos is None:
        return "Acesso restrito"
    return "R$ " + f"{int(centavos or 0)/100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _numero(valor):
    if valor is None: return "—"
    try:
        numero = float(valor)
        return f"{numero:,.3f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return str(valor)


def _formatar(valor, campo=""):
    if valor in (None, ""): return "—"
    if "centavos" in campo: return _moeda(valor)
    if isinstance(valor, float): return _numero(valor)
    if campo in {"ativo", "contagem_cega", "controla_lote", "controla_validade", "controla_serie", "eh_patrimonio"}:
        return "Sim" if valor else "Não"
    return str(valor)



