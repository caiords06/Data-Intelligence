"""Workspace especializado e funcional de Compras e Suprimentos 2.0."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from services.departamentos.compras import (
    ACOES_COMPRAS,
    adicionar_aditivo,
    adicionar_comentario,
    adicionar_contato_fornecedor,
    agendar_relatorio,
    analisar_compras,
    aprovar_pedido,
    atualizar_status_pedido,
    avaliar_fornecedor,
    atualizar_fornecedor,
    criar_categoria,
    criar_contrato,
    criar_cotacao,
    criar_fornecedor,
    criar_item_catalogo,
    criar_pedido,
    criar_solicitacao,
    decidir_solicitacao,
    enviar_pedido,
    enviar_solicitacao,
    gerar_alertas_compras,
    gerar_pdf_pedido,
    gerar_relatorio_compras,
    garantir_catalogos,
    homologar_fornecedor,
    integrar_recebimento_financeiro,
    listar_historico,
    listar_secao,
    obter_fornecedores_cotacao,
    obter_itens_pedido,
    obter_itens_solicitacao,
    registrar_negociacao,
    registrar_documento_fornecedor,
    registrar_divergencia_manual,
    registrar_proposta,
    registrar_recebimento,
    resolver_alerta,
    resolver_divergencia,
    resumo_compras,
    selecionar_fornecedor,
    salvar_regra_aprovacao,
    tem_permissao_compras,
)
from services.contexto import tem_permissao
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
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_COMPRAS = "#F97316"

GRUPOS_MENU = (
    ("COMPRAS", (("visao", "⌂", "Visão geral"),)),
    ("DEMANDAS", (
        ("minhas_solicitacoes", "◉", "Minhas solicitações"),
        ("solicitacoes", "▣", "Todas as solicitações"),
        ("aprovacoes", "✓", "Aprovações"),
        ("catalogo", "▦", "Catálogo interno"),
    )),
    ("SOURCING", (
        ("cotacoes", "≡", "Cotações"),
        ("comparativo", "≠", "Mapa comparativo"),
        ("negociacoes", "⇄", "Negociações"),
    )),
    ("PEDIDOS", (
        ("pedidos", "▤", "Pedidos de compra"),
        ("entregas", "→", "Acompanhamento"),
    )),
    ("FORNECEDORES", (
        ("fornecedores", "◇", "Cadastro"),
        ("homologacao", "✔", "Homologação"),
        ("avaliacoes", "☆", "Avaliações"),
        ("documentos", "▧", "Documentos"),
    )),
    ("RECEBIMENTO", (
        ("recebimentos", "↓", "Recebimentos"),
        ("divergencias", "!", "Divergências"),
    )),
    ("CONTRATOS", (
        ("contratos", "▦", "Contratos"),
        ("aditivos", "+", "Aditivos"),
    )),
    ("GESTÃO", (
        ("alertas", "!", "Central de alertas"),
        ("relatorios", "▤", "Relatórios"),
        ("auditoria", "◉", "Auditoria"),
        ("configuracoes", "⚙", "Configurações"),
    )),
)

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "minhas_solicitacoes": "Crie, envie e acompanhe as demandas originadas por você.",
    "solicitacoes": "Necessidade, justificativa, itens, prazo, centro de custo e ciclo de aprovação.",
    "aprovacoes": "Fila humana de aprovação por valor, prioridade, departamento e alçada.",
    "catalogo": "Produtos e serviços padronizados de fornecedores homologados.",
    "cotacoes": "Convites, prazo de resposta, propostas e concorrência por solicitação.",
    "comparativo": "Preço, prazo, qualidade e custo-benefício; a escolha continua humana.",
    "negociacoes": "Rodadas, contrapropostas, saving, condições e responsáveis.",
    "pedidos": "Pedido de compra, aprovação, envio, confirmação e documento profissional.",
    "entregas": "Previsão, atraso, produção, transporte e recebimento parcial.",
    "fornecedores": "Cadastro central conectado a Estoque e Financeiro, contatos e categorias.",
    "homologacao": "Documentação, capacidade, restrições, bloqueio e conformidade.",
    "avaliacoes": "Preço, prazo, qualidade, atendimento, conformidade e score histórico.",
    "documentos": "Certidões, documentos fiscais, contratos, propostas e vencimentos.",
    "recebimentos": "Nota fiscal, conferência, aceite, recusa, lote, série, Estoque e Financeiro.",
    "divergencias": "Quantidade, preço, produto, documento, avaria e atraso com resolução auditada.",
    "contratos": "Objeto, fornecedor, vigência, valor, reajuste, renovação e alertas.",
    "aditivos": "Renovação e alterações sem apagar as condições anteriores.",
    "alertas": "Entregas atrasadas, divergências, documentos e contratos vencendo.",
    "auditoria": "Trilha imutável de quem fez, o que mudou, quando e em qual processo.",
}


def _moeda(centavos):
    if centavos is None:
        return "Acesso restrito"
    return "R$ " + f"{int(centavos or 0)/100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _numero(valor):
    if valor is None:
        return "—"
    try:
        numero = float(valor)
        return f"{numero:,.3f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return str(valor)


def _formatar(valor, campo=""):
    if valor in (None, ""):
        return "—"
    if "centavos" in campo:
        return _moeda(valor)
    if isinstance(valor, float):
        return _numero(valor)
    if campo in {"ativo", "selecionado", "possui_divergencia", "homologado", "renovacao_automatica"}:
        return "Sim" if valor else "Não"
    return str(valor)


from interface.compras_views import ComprasViewsMixin
from interface.compras_acoes import ComprasAcoesMixin

class TelaCompras(ComprasViewsMixin, ComprasAcoesMixin):
    def __init__(self, root, navegacao, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.secao = secao if secao in ROTULOS else "visao"
        self.tabela = None
        self.registros = []
        if not tem_permissao(SESSAO.usuario, "compras", "ler"):
            raise PermissionError("Seu perfil não possui acesso a Compras.")
        garantir_catalogos(SESSAO.usuario)
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar_interface()

    def _criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_modulo(
            self.container,
            self.navegacao,
            modulo="compras",
            titulo="COMPRAS",
            ativo=self.secao,
            grupos_menu=GRUPOS_MENU,
            grupos_recolhiveis=True,
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
        self.conteudo = viewport.conteudo
        renderizadores = {
            "visao": self._visao,
            "relatorios": self._relatorios,
            "auditoria": self._auditoria,
            "configuracoes": self._configuracoes,
        }
        renderizadores.get(self.secao, self._secao_operacional)()

    def abrir_secao(self, secao):
        callback = self.navegacao.get("secao_modulo")
        if callable(callback):
            callback("compras", secao)
            return
        self.container.destroy()
        TelaCompras(self.root, self.navegacao, secao=secao)

    def _acoes_cabecalho(self, parent):
        bloco = tk.Frame(parent, bg=CORES["bg"])
        rotulo = {
            "minhas_solicitacoes": "+  NOVA SOLICITAÇÃO",
            "solicitacoes": "+  NOVA SOLICITAÇÃO",
            "cotacoes": "+  COTAÇÃO",
            "fornecedores": "+  FORNECEDOR",
            "contratos": "+  CONTRATO",
            "catalogo": "+  ITEM DE CATÁLOGO",
            "recebimentos": "+  RECEBIMENTO",
            "documentos": "+  DOCUMENTO",
        }.get(self.secao, "+  NOVA SOLICITAÇÃO")
        criar_botao(bloco, rotulo, self._nova_acao, compacto=True).pack(side="right")
        criar_botao(bloco, "◈  ANALISAR COMPRAS", self._mostrar_analise, tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
        return bloco

    def _cabecalho(self, titulo, subtitulo, *, acoes=True):
        criar_cabecalho(
            self.conteudo,
            titulo,
            subtitulo,
            acao=self._acoes_cabecalho if acoes else None,
            breadcrumb=f"MÓDULOS  /  COMPRAS  /  {titulo.upper()}",
            etiqueta="PROCUREMENT 2.0",
        )




















































