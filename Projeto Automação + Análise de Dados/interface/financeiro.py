"""Workspace especializado do departamento Financeiro."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.departamentos.financeiro import (
    NATUREZAS,
    STATUS_ABERTOS,
    STATUS_TERMINAIS,
    analisar_financeiro,
    agendar_relatorio,
    anexar_documento,
    atualizar_lancamento,
    atualizar_status_vencidos,
    calcular_dre,
    cancelar_lancamento,
    conciliar_item,
    contabilizar_lancamento,
    criar_categoria,
    criar_conta,
    criar_lancamento,
    criar_parte,
    decidir_aprovacao,
    estornar_lancamento,
    gerar_alertas_financeiros,
    gerar_recorrencias_pendentes,
    gerar_relatorio_financeiro,
    importar_extrato,
    listar_aprovacoes_financeiras,
    listar_auditoria_financeira,
    listar_cartoes,
    listar_catalogos,
    listar_conciliacoes,
    listar_contas_com_saldo,
    listar_lancamentos,
    listar_orcamentos,
    listar_recorrencias,
    listar_relatorios_agendados,
    obter_lancamento,
    projetar_fluxo_caixa,
    registrar_baixa,
    resumo_financeiro,
    salvar_cartao,
    salvar_orcamento,
    salvar_plano_conta,
    submeter_aprovacao,
    tem_permissao_financeira,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_estado_vazio,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
    preparar_janela_secundaria,
)
from interface.grade_editavel import EditorGrade
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_FINANCEIRO = "#34D079"

GRUPOS_MENU = (
    ("FINANCEIRO", (("visao", "⌂", "Visão geral"),)),
    ("OPERAÇÕES", (
        ("lancamentos", "≡", "Lançamentos"),
        ("pagar", "↓", "Contas a pagar"),
        ("receber", "↑", "Contas a receber"),
        ("reembolsos", "$", "Reembolsos"),
        ("transferencias", "⇄", "Transferências"),
        ("recorrencias", "↻", "Recorrências"),
    )),
    ("TESOURARIA", (
        ("fluxo", "≋", "Fluxo de caixa"),
        ("bancos", "▣", "Bancos e contas"),
        ("conciliacao", "✓", "Conciliação"),
        ("cartoes", "▭", "Cartões corporativos"),
    )),
    ("PLANEJAMENTO", (
        ("orcamento", "▥", "Orçamento"),
        ("projecoes", "↗", "Projeções"),
        ("centros_custo", "◇", "Centros de custo"),
    )),
    ("GESTÃO", (
        ("dre", "▤", "DRE"),
        ("relatorios", "↥", "Relatórios"),
        ("aprovacoes_fin", "✓", "Aprovações"),
        ("auditoria_fin", "◎", "Auditoria"),
    )),
    ("CADASTROS", (
        ("plano_contas", "#", "Plano de contas"),
        ("categorias", "◈", "Categorias"),
        ("partes", "◉", "Clientes e fornecedores"),
    )),
)


ROTULOS = {
    chave: titulo
    for _grupo, itens in GRUPOS_MENU
    for chave, _icone, titulo in itens
}


def _moeda(centavos) -> str:
    valor = int(centavos or 0) / 100
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _data_br(valor) -> str:
    texto = str(valor or "")[:10]
    partes = texto.split("-")
    return "/".join(reversed(partes)) if len(partes) == 3 else texto


from interface.financeiro_views import FinanceiroViewsMixin
from interface.financeiro_dialogos import FinanceiroDialogosMixin

class TelaFinanceiro(FinanceiroViewsMixin, FinanceiroDialogosMixin):
    def __init__(self, root, navegacao, secao="visao", periodo_visao="Mês"):
        self.root = root
        self.navegacao = navegacao
        self.secao = secao if secao in ROTULOS else "visao"
        self.periodo_visao = periodo_visao if periodo_visao in {"Hoje", "Mês", "Trimestre", "Ano"} else "Mês"
        self.pagina = 1
        self.paginas = 1
        self.registros = []
        self.tabela = None
        if not tem_permissao(SESSAO.usuario, "financeiro", "ler"):
            raise PermissionError("Seu perfil não possui acesso ao Financeiro.")
        atualizar_status_vencidos(SESSAO.usuario)
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar_interface()

    def _criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_modulo(
            self.container,
            self.navegacao,
            modulo="financeiro",
            titulo="FINANCEIRO",
            ativo=self.secao,
            grupos_menu=GRUPOS_MENU,
            grupos_recolhiveis=True,
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left", fill="both", expand=True,
            padx=LAYOUT["conteudo_padx"], pady=(22, 20),
        )
        self.conteudo = viewport.conteudo
        renderizadores = {
            "visao": self._visao_geral,
            "fluxo": lambda: self._fluxo_caixa("Fluxo de caixa"),
            "projecoes": lambda: self._fluxo_caixa("Projeções e cenários"),
            "bancos": self._bancos,
            "orcamento": self._orcamentos,
            "conciliacao": self._conciliacao,
            "dre": self._dre,
            "relatorios": self._relatorios,
            "aprovacoes_fin": self._aprovacoes,
            "auditoria_fin": self._auditoria,
            "plano_contas": self._plano_contas,
            "categorias": self._categorias,
            "partes": self._partes,
            "centros_custo": self._centros_custo,
            "cartoes": self._cartoes,
            "recorrencias": self._recorrencias,
        }
        renderizadores.get(self.secao, self._livro)()

    def abrir_secao(self, secao):
        callback = self.navegacao.get("secao_modulo")
        if callable(callback):
            callback("financeiro", secao)
            return
        self.container.destroy()
        TelaFinanceiro(self.root, self.navegacao, secao=secao)

    def _acoes_cabecalho(self, parent):
        bloco = tk.Frame(parent, bg=CORES["bg"])
        botao_novo = criar_botao(
            bloco, "+  NOVO REGISTRO", self._menu_novo, compacto=True
        )
        botao_novo.pack(side="right")
        if not tem_permissao_financeira(SESSAO.usuario, "criar"):
            botao_novo.configure(state="disabled", cursor="arrow")
        criar_botao(
            bloco, "◈  ANALISAR FINANCEIRO", self._mostrar_analise,
            tipo="secundario", compacto=True,
        ).pack(side="right", padx=(0, 8))
        return bloco

    def _cabecalho(self, titulo, subtitulo, *, acoes=True):
        criar_cabecalho(
            self.conteudo,
            titulo,
            subtitulo,
            acao=self._acoes_cabecalho if acoes else None,
            breadcrumb=f"MÓDULOS  /  FINANCEIRO  /  {titulo.upper()}",
            etiqueta="FINANCEIRO 2.0",
        )

























































